
import os


# Inicijalna permutacija IP (3.1.3)
IP = [
    58, 50, 42, 34, 26, 18, 10, 2,
    60, 52, 44, 36, 28, 20, 12, 4,
    62, 54, 46, 38, 30, 22, 14, 6,
    64, 56, 48, 40, 32, 24, 16, 8,
    57, 49, 41, 33, 25, 17, 9, 1,
    59, 51, 43, 35, 27, 19, 11, 3,
    61, 53, 45, 37, 29, 21, 13, 5,
    63, 55, 47, 39, 31, 23, 15, 7,
]

# Zavrsna permutacija IP^-1
IP_INV = [
    40, 8, 48, 16, 56, 24, 64, 32,
    39, 7, 47, 15, 55, 23, 63, 31,
    38, 6, 46, 14, 54, 22, 62, 30,
    37, 5, 45, 13, 53, 21, 61, 29,
    36, 4, 44, 12, 52, 20, 60, 28,
    35, 3, 43, 11, 51, 19, 59, 27,
    34, 2, 42, 10, 50, 18, 58, 26,
    33, 1, 41, 9, 49, 17, 57, 25,
]

# Ekspanziona permutacija E: 32 -> 48 bita
E = [
    32, 1, 2, 3, 4, 5,
    4, 5, 6, 7, 8, 9,
    8, 9, 10, 11, 12, 13,
    12, 13, 14, 15, 16, 17,
    16, 17, 18, 19, 20, 21,
    20, 21, 22, 23, 24, 25,
    24, 25, 26, 27, 28, 29,
    28, 29, 30, 31, 32, 1,
]

# Permutacija P na izlazu iz S-blokova
P = [
    16, 7, 20, 21, 29, 12, 28, 17,
    1, 15, 23, 26, 5, 18, 31, 10,
    2, 8, 24, 14, 32, 27, 3, 9,
    19, 13, 30, 6, 22, 11, 4, 25,
]

# PC-1: 64 -> 56 bita (izbacuje bite pariteta 8, 16, 24, ...)
PC1 = [
    57, 49, 41, 33, 25, 17, 9,
    1, 58, 50, 42, 34, 26, 18,
    10, 2, 59, 51, 43, 35, 27,
    19, 11, 3, 60, 52, 44, 36,
    63, 55, 47, 39, 31, 23, 15,
    7, 62, 54, 46, 38, 30, 22,
    14, 6, 61, 53, 45, 37, 29,
    21, 13, 5, 28, 20, 12, 4,
]

# PC-2: 56 -> 48 bita (daje podkljuc runde)
PC2 = [
    14, 17, 11, 24, 1, 5,
    3, 28, 15, 6, 21, 10,
    23, 19, 12, 4, 26, 8,
    16, 7, 27, 20, 13, 2,
    41, 52, 31, 37, 47, 55,
    30, 40, 51, 45, 33, 48,
    44, 49, 39, 56, 34, 53,
    46, 42, 50, 36, 29, 32,
]

# Broj lijevih rotacija po rundi (3.1.3)
SHIFTS = [1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1]

# S-blokovi S1..S8, svaki 4 reda x 16 kolona
SBOXES = [
    [  # S1
        [14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7],
        [0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8],
        [4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0],
        [15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13],
    ],
    [  # S2
        [15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10],
        [3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5],
        [0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15],
        [13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9],
    ],
    [  # S3
        [10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8],
        [13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1],
        [13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7],
        [1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12],
    ],
    [  # S4
        [7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15],
        [13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9],
        [10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4],
        [3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14],
    ],
    [  # S5
        [2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9],
        [14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6],
        [4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14],
        [11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3],
    ],
    [  # S6
        [12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11],
        [10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8],
        [9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6],
        [4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13],
    ],
    [  # S7
        [4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1],
        [13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6],
        [1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2],
        [6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12],
    ],
    [  # S8
        [13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7],
        [1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2],
        [7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8],
        [2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11],
    ],
]

BLOCK_SIZE = 8  # bajtova
KEY_SIZE = 8  # bajtova

WEAK_KEYS = {
    bytes.fromhex("0101010101010101"),
    bytes.fromhex("FEFEFEFEFEFEFEFE"),
    bytes.fromhex("E0E0E0E0F1F1F1F1"),
    bytes.fromhex("1F1F1F1F0E0E0E0E"),
}


SEMI_WEAK_KEY_PAIRS = [
    (bytes.fromhex("01FE01FE01FE01FE"), bytes.fromhex("FE01FE01FE01FE01")),
    (bytes.fromhex("1FE01FE00EF10EF1"), bytes.fromhex("E01FE01FF10EF10E")),
    (bytes.fromhex("01E001E001F101F1"), bytes.fromhex("E001E001F101F101")),
    (bytes.fromhex("1FFE1FFE0EFE0EFE"), bytes.fromhex("FE1FFE1FFE0EFE0E")),
    (bytes.fromhex("011F011F010E010E"), bytes.fromhex("1F011F010E010E01")),
    (bytes.fromhex("E0FEE0FEF1FEF1FE"), bytes.fromhex("FEE0FEE0FEF1FEF1")),
]

# Svi kljucevi koje generate_keys() preskace pri generisanju (4 + 12 = 16 od 2^56).
AVOIDED_KEYS = WEAK_KEYS | {key for pair in SEMI_WEAK_KEY_PAIRS for key in pair}



def _permute(block: int, table: list, in_bits: int) -> int:

    result = 0
    for position in table:
        result = (result << 1) | ((block >> (in_bits - position)) & 1)
    return result


def _rotate_left_28(value: int, amount: int) -> int:
    """Ciklicna rotacija ulijevo unutar 28-bitne polovine kljuca."""
    return ((value << amount) | (value >> (28 - amount))) & 0x0FFFFFFF


def _feistel(right: int, subkey: int) -> int:

    expanded = _permute(right, E, 32) ^ subkey

    substituted = 0
    for i in range(8):
        # i-ta grupa od 6 bita, s lijeva na desno
        chunk = (expanded >> (42 - 6 * i)) & 0x3F
        # red = prvi i posljednji bit, kolona = srednja cetiri
        row = ((chunk & 0x20) >> 4) | (chunk & 0x01)
        col = (chunk >> 1) & 0x0F
        substituted = (substituted << 4) | SBOXES[i][row][col]

    return _permute(substituted, P, 32)



def _check_key(key: bytes) -> None:
    if not isinstance(key, (bytes, bytearray)):
        raise TypeError("Kljuc mora biti bytes, a ne %s" % type(key).__name__)
    if len(key) != KEY_SIZE:
        raise ValueError(
            "DES kljuc mora imati tacno %d bajta (64 bita), dobijeno %d"
            % (KEY_SIZE, len(key))
        )


def _check_block(block: bytes) -> None:
    if not isinstance(block, (bytes, bytearray)):
        raise TypeError("Blok mora biti bytes, a ne %s" % type(block).__name__)
    if len(block) != BLOCK_SIZE:
        raise ValueError(
            "DES radi nad blokom od tacno %d bajta, dobijeno %d "
            "(za tekst proizvoljne duzine treba padding + rezim rada)"
            % (BLOCK_SIZE, len(block))
        )



def _key_schedule(key: bytes) -> list:

    _check_key(key)
    key_int = int.from_bytes(key, "big")

    permuted = _permute(key_int, PC1, 64)  # 56 bita
    c = permuted >> 28
    d = permuted & 0x0FFFFFFF

    subkeys = []
    for shift in SHIFTS:
        c = _rotate_left_28(c, shift)
        d = _rotate_left_28(d, shift)
        subkeys.append(_permute((c << 28) | d, PC2, 56))
    return subkeys


def set_odd_parity(key: bytes) -> bytes:

    out = bytearray()
    for byte in key:
        b = byte & 0xFE
        if bin(b).count("1") % 2 == 0:
            b |= 1
        out.append(b)
    return bytes(out)


def generate_keys() -> dict:

    while True:
        key = set_odd_parity(os.urandom(KEY_SIZE))
        if key not in AVOIDED_KEYS:
            return {"key": key}


def generate_keys_3des(keying_option: int = 1) -> dict:

    if keying_option not in (1, 2, 3):
        raise ValueError("keying_option mora biti 1, 2 ili 3 (vidi Tabelu 3.11)")

    k1 = generate_keys()["key"]
    if keying_option == 3:
        k2 = k3 = k1
    elif keying_option == 2:
        k2 = generate_keys()["key"]
        k3 = k1
    else:
        k2 = generate_keys()["key"]
        k3 = generate_keys()["key"]

    return {"k1": k1, "k2": k2, "k3": k3, "keying_option": keying_option}


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    return _process_block(plaintext, _key_schedule(key))


def decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """Isti algoritam kao encrypt, ali s podkljucevima u obrnutom redoslijedu K16...K1."""
    return _process_block(ciphertext, list(reversed(_key_schedule(key))))


def _process_block(block: bytes, subkeys: list) -> bytes:
    """Zajednicko jezgro za encrypt/decrypt - razlika je samo redoslijed podkljuceva."""
    _check_block(block)

    permuted = _permute(int.from_bytes(block, "big"), IP, 64)
    left = permuted >> 32
    right = permuted & 0xFFFFFFFF

    for subkey in subkeys:
        left, right = right, left ^ _feistel(right, subkey)

    # Zamjena polovina prije zavrsne permutacije: preoutput = R16 || L16
    preoutput = (right << 32) | left
    return _permute(preoutput, IP_INV, 64).to_bytes(BLOCK_SIZE, "big")


def encrypt_3des(plaintext: bytes, k1: bytes, k2: bytes, k3: bytes) -> bytes:

    return encrypt(decrypt(encrypt(plaintext, k1), k2), k3)


def decrypt_3des(ciphertext: bytes, k1: bytes, k2: bytes, k3: bytes) -> bytes:

    return decrypt(encrypt(decrypt(ciphertext, k3), k2), k1)
