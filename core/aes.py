"""
AES - rucna implementacija.

Vidi thesis poglavlje 3.2: GF(2^8) aritmetika, SubBytes, ShiftRows, MixColumns,
AddRoundKey, key expansion (RotWord, SubWord, Rcon).

Podrzane su sve tri varijante: AES-128 (10 rundi), AES-192 (12), AES-256 (14).
Blok je uvijek 128 bita (16 bajtova), bez obzira na duzinu kljuca.

Stanje (state) se drzi kao ravna lista od 16 bajtova u redoslijedu kolona:
    state[r + 4*c] = bajt u redu r, koloni c
sto je tacno redoslijed ulaznih bajtova iz standarda.

Validirano protiv zvanicnih FIPS-197 test vektora - vidi tests/test_aes.py.
"""
import os

BLOCK_SIZE = 16  # bajtova
VALID_KEY_SIZES = (128, 192, 256)

# Ireducibilni polinom AES-a: x^8 + x^4 + x^3 + x + 1
IRREDUCIBLE = 0x11B

# Broj rundi po duzini kljuca (3.2.2)
ROUNDS = {128: 10, 192: 12, 256: 14}


# ---------------------------------------------------------------------------
# Aritmetika u Galoisovom polju GF(2^8) - vidi 3.2.3
# ---------------------------------------------------------------------------

def _xtime(a: int) -> int:
    """Mnozenje sa x (tj. sa 02) u GF(2^8), uz redukciju ireducibilnim polinomom."""
    a <<= 1
    if a & 0x100:
        a ^= IRREDUCIBLE
    return a & 0xFF


def gf_multiply(a: int, b: int) -> int:
    """
    Mnozenje dva bajta u GF(2^8) metodom "udvostruci i saberi":
    za svaki postavljen bit u b dodaje se odgovarajuci visekratnik od a.
    """
    result = 0
    for _ in range(8):
        if b & 1:
            result ^= a
        a = _xtime(a)
        b >>= 1
    return result


def _gf_inverse(a: int) -> int:
    """
    Multiplikativni inverz u GF(2^8) (nula nema inverz - po konvenciji se mapira u 0).
    Trazi se iscrpno; radi se samo jednom, pri gradnji S-boxa.
    """
    if a == 0:
        return 0
    for candidate in range(1, 256):
        if gf_multiply(a, candidate) == 1:
            return candidate
    raise ArithmeticError("nema inverza za %d - ireducibilni polinom je pogresan" % a)


def _build_sbox() -> tuple:
    """
    Gradi S-box iz definicije (3.2.4), a ne iz prepisane tabele:
    multiplikativni inverz u GF(2^8), pa afina transformacija nad bitovima.
    """
    sbox = [0] * 256
    for value in range(256):
        inverse = _gf_inverse(value)
        result = inverse
        for shift in (1, 2, 3, 4):
            result ^= ((inverse << shift) | (inverse >> (8 - shift))) & 0xFF
        sbox[value] = result ^ 0x63

    inverse_sbox = [0] * 256
    for value, substituted in enumerate(sbox):
        inverse_sbox[substituted] = value

    return tuple(sbox), tuple(inverse_sbox)


SBOX, INV_SBOX = _build_sbox()

# Rcon: konstante runde, rc[j] = x^(j-1) u GF(2^8). Indeks 0 se ne koristi.
RCON = [0x00]
_rc = 0x01
for _ in range(14):
    RCON.append(_rc)
    _rc = _xtime(_rc)


# ---------------------------------------------------------------------------
# Transformacije runde - vidi 3.2.4
# ---------------------------------------------------------------------------

def _sub_bytes(state: list) -> list:
    """S-box supstitucija. Vidi 3.2.4."""
    return [SBOX[byte] for byte in state]


def _inv_sub_bytes(state: list) -> list:
    return [INV_SBOX[byte] for byte in state]


def _shift_rows(state: list) -> list:
    """Red r se ciklicno pomjera ulijevo za r pozicija."""
    return [state[r + 4 * ((c + r) % 4)] for c in range(4) for r in range(4)]


def _inv_shift_rows(state: list) -> list:
    return [state[r + 4 * ((c - r) % 4)] for c in range(4) for r in range(4)]


def _mix_columns(state: list) -> list:
    """Mnozenje kolone sa fiksnim polinomom u GF(2^8). Vidi 3.2.4."""
    out = [0] * 16
    for c in range(4):
        a0, a1, a2, a3 = state[4 * c: 4 * c + 4]
        out[4 * c + 0] = gf_multiply(a0, 2) ^ gf_multiply(a1, 3) ^ a2 ^ a3
        out[4 * c + 1] = a0 ^ gf_multiply(a1, 2) ^ gf_multiply(a2, 3) ^ a3
        out[4 * c + 2] = a0 ^ a1 ^ gf_multiply(a2, 2) ^ gf_multiply(a3, 3)
        out[4 * c + 3] = gf_multiply(a0, 3) ^ a1 ^ a2 ^ gf_multiply(a3, 2)
    return out


def _inv_mix_columns(state: list) -> list:
    """Inverzno mnozenje, koeficijenti 0e/0b/0d/09."""
    out = [0] * 16
    for c in range(4):
        a0, a1, a2, a3 = state[4 * c: 4 * c + 4]
        out[4 * c + 0] = (gf_multiply(a0, 0x0E) ^ gf_multiply(a1, 0x0B)
                          ^ gf_multiply(a2, 0x0D) ^ gf_multiply(a3, 0x09))
        out[4 * c + 1] = (gf_multiply(a0, 0x09) ^ gf_multiply(a1, 0x0E)
                          ^ gf_multiply(a2, 0x0B) ^ gf_multiply(a3, 0x0D))
        out[4 * c + 2] = (gf_multiply(a0, 0x0D) ^ gf_multiply(a1, 0x09)
                          ^ gf_multiply(a2, 0x0E) ^ gf_multiply(a3, 0x0B))
        out[4 * c + 3] = (gf_multiply(a0, 0x0B) ^ gf_multiply(a1, 0x0D)
                          ^ gf_multiply(a2, 0x09) ^ gf_multiply(a3, 0x0E))
    return out


def _add_round_key(state: list, round_key: list) -> list:
    """XOR stanja s kljucem runde."""
    return [byte ^ round_key[i] for i, byte in enumerate(state)]


# ---------------------------------------------------------------------------
# Prosirenje kljuca - vidi 3.2.5
# ---------------------------------------------------------------------------

def _rot_word(word: list) -> list:
    """[a0, a1, a2, a3] -> [a1, a2, a3, a0]"""
    return word[1:] + word[:1]


def _sub_word(word: list) -> list:
    """S-box nad svakim bajtom rijeci."""
    return [SBOX[byte] for byte in word]


def _key_expansion(key: bytes) -> list:
    """
    Vidi 3.2.5 - RotWord, SubWord, Rcon.
    Vraca listu kljuceva runde, svaki po 16 bajtova (Nr + 1 komada).
    """
    _check_key(key)
    nk = len(key) // 4  # broj rijeci u kljucu: 4, 6 ili 8
    rounds = ROUNDS[len(key) * 8]
    total_words = 4 * (rounds + 1)

    words = [list(key[4 * i: 4 * i + 4]) for i in range(nk)]

    for i in range(nk, total_words):
        temp = list(words[i - 1])
        if i % nk == 0:
            temp = _sub_word(_rot_word(temp))
            temp[0] ^= RCON[i // nk]
        elif nk > 6 and i % nk == 4:
            # Dodatni SubWord postoji samo kod AES-256
            temp = _sub_word(temp)
        words.append([words[i - nk][j] ^ temp[j] for j in range(4)])

    return [
        [byte for word in words[4 * r: 4 * r + 4] for byte in word]
        for r in range(rounds + 1)
    ]


# ---------------------------------------------------------------------------
# Validacija ulaza
# ---------------------------------------------------------------------------

def _check_key(key: bytes) -> None:
    if not isinstance(key, (bytes, bytearray)):
        raise TypeError("Kljuc mora biti bytes, a ne %s" % type(key).__name__)
    if len(key) * 8 not in VALID_KEY_SIZES:
        raise ValueError(
            "AES kljuc mora biti 16, 24 ili 32 bajta (128/192/256 bita), dobijeno %d"
            % len(key)
        )


def _check_block(block: bytes) -> None:
    if not isinstance(block, (bytes, bytearray)):
        raise TypeError("Blok mora biti bytes, a ne %s" % type(block).__name__)
    if len(block) != BLOCK_SIZE:
        raise ValueError(
            "AES radi nad blokom od tacno %d bajta, dobijeno %d "
            "(za tekst proizvoljne duzine treba padding + rezim rada)"
            % (BLOCK_SIZE, len(block))
        )


# ---------------------------------------------------------------------------
# Javni interfejs
# ---------------------------------------------------------------------------

def generate_keys(key_size: int = 128) -> dict:
    """key_size je 128, 192 ili 256."""
    if key_size not in VALID_KEY_SIZES:
        raise ValueError(
            "Duzina kljuca mora biti 128, 192 ili 256 bita, dobijeno %r" % (key_size,)
        )
    return {"key": os.urandom(key_size // 8), "key_size": key_size}


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """16-bajtni blok. Vidi pseudokod u 3.2.6."""
    _check_block(plaintext)
    round_keys = _key_expansion(key)
    rounds = len(round_keys) - 1

    state = _add_round_key(list(plaintext), round_keys[0])

    for r in range(1, rounds):
        state = _sub_bytes(state)
        state = _shift_rows(state)
        state = _mix_columns(state)
        state = _add_round_key(state, round_keys[r])

    # Posljednja runda je bez MixColumns - inace bi se dala trivijalno ponistiti
    state = _sub_bytes(state)
    state = _shift_rows(state)
    state = _add_round_key(state, round_keys[rounds])

    return bytes(state)


def decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """Inverzni sifrat - transformacije obrnutim redom, kljucevi runde unazad."""
    _check_block(ciphertext)
    round_keys = _key_expansion(key)
    rounds = len(round_keys) - 1

    state = _add_round_key(list(ciphertext), round_keys[rounds])

    for r in range(rounds - 1, 0, -1):
        state = _inv_shift_rows(state)
        state = _inv_sub_bytes(state)
        state = _add_round_key(state, round_keys[r])
        state = _inv_mix_columns(state)

    state = _inv_shift_rows(state)
    state = _inv_sub_bytes(state)
    state = _add_round_key(state, round_keys[0])

    return bytes(state)
