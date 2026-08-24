"""
RSA - rucna implementacija.

Vidi thesis poglavlje 3.3: generisanje kljuceva (3.3.3), enkripcija/dekripcija (3.3.4),
Wienerov napad na mali eksponent d (3.3.6).

sympy.randprime() interno koristi Miller-Rabinov test primalnosti, a ugradjeni
pow(base, exp, mod) vec radi efikasno kvadriraj-i-mnozi.

UPOZORENJE: ovo je "udzbenicki" RSA, bez OAEP dopune. Deterministican je i time
ranjiv na napade odabranim otvorenim tekstom - u praksi se nikad ne koristi ovako.
Ovdje sluzi da se matematika iz 3.3 vidi golim okom.
"""
import math

from sympy import randprime

DEFAULT_EXPONENT = 65537
VALID_KEY_SIZES = (1024, 2048, 3072, 4096)


# ---------------------------------------------------------------------------
# Generisanje kljuceva - vidi 3.3.3
# ---------------------------------------------------------------------------

def _random_prime(bits: int) -> int:
    """
    Prost broj sa tacno `bits` bita, iz gornjeg dijela opsega.

    Donja granica je 2^(bits-1) * sqrt(2), cime se garantuje da proizvod dva
    ovakva prosta broja ima tacno 2*bits bita - inace modul zna ispasti kraci
    od trazenog, pa "RSA-2048" u stvari bude 2047-bitni.
    """
    low = int((1 << (bits - 1)) * 1.4142135623730951)
    high = (1 << bits) - 1
    return randprime(low, high)


def generate_keys(bits: int = 2048) -> dict:
    """
    Vraca {'public': (n, e), 'private': (n, d)}.
    Koraci (3.3.3): generisi p, q -> n = p*q -> phi(n) = (p-1)(q-1)
    -> e = 65537 -> d = e^-1 mod phi(n)
    """
    if bits not in VALID_KEY_SIZES:
        raise ValueError(
            "Duzina kljuca mora biti jedna od %s bita, dobijeno %r"
            % (", ".join(str(s) for s in VALID_KEY_SIZES), bits)
        )

    half = bits // 2
    e = DEFAULT_EXPONENT

    while True:
        p = _random_prime(half)
        q = _random_prime(half)
        if p == q:
            continue

        phi = (p - 1) * (q - 1)
        if math.gcd(e, phi) != 1:
            continue  # e mora biti uzajamno prost sa phi(n) da bi inverz postojao

        n = p * q
        d = pow(e, -1, phi)
        return {
            "public": (n, e),
            "private": (n, d),
            # Ispod je materijal za prikaz u UI-ju i za Wienerov napad.
            # U stvarnom sistemu p, q i phi se unistavaju odmah po generisanju.
            "p": p,
            "q": q,
            "phi": phi,
            "bits": bits,
        }


def generate_vulnerable_keys(bits: int = 1024) -> dict:
    """
    Namjerno slab kljuc za demonstraciju Wienerovog napada (3.3.6):
    bira se mali privatni eksponent d < n^(1/4) / 3, pa se e racuna iz njega.

    Ovakav izbor se u praksi radio da bi dekripcija bila brza - Wiener je 1990.
    pokazao da je time cijeli kljuc gotov.
    """
    half = bits // 2

    while True:
        p = _random_prime(half)
        q = _random_prime(half)
        if p == q:
            continue

        n = p * q
        phi = (p - 1) * (q - 1)

        # Wienerova granica: napad garantovano uspijeva za d < (1/3) * n^(1/4)
        bound = math.isqrt(math.isqrt(n)) // 3
        if bound < 3:
            continue

        d = _random_prime(max(bound.bit_length() - 2, 2))
        if d >= bound or math.gcd(d, phi) != 1:
            continue

        e = pow(d, -1, phi)
        if e.bit_length() < n.bit_length() - 8:
            # e mora biti "veliko" (tj. blizu velicine n) da napad bude smislen
            continue

        return {
            "public": (n, e),
            "private": (n, d),
            "p": p,
            "q": q,
            "phi": phi,
            "bits": bits,
        }


# ---------------------------------------------------------------------------
# Enkripcija / dekripcija - vidi 3.3.4
# ---------------------------------------------------------------------------

def encrypt(message: int, public_key: tuple) -> int:
    """c = m^e mod n"""
    n, e = public_key
    if not isinstance(message, int):
        raise TypeError("Poruka mora biti cijeli broj, a ne %s" % type(message).__name__)
    if message < 0:
        raise ValueError("Poruka mora biti nenegativna")
    if message >= n:
        raise ValueError(
            "Poruka (%d bita) je veca od modula n (%d bita) - RSA moze enkriptovati "
            "samo brojeve manje od n" % (message.bit_length(), n.bit_length())
        )
    return pow(message, e, n)


def decrypt(ciphertext: int, private_key: tuple) -> int:
    """m = c^d mod n"""
    n, d = private_key
    if not isinstance(ciphertext, int):
        raise TypeError("Sifrat mora biti cijeli broj, a ne %s" % type(ciphertext).__name__)
    if not 0 <= ciphertext < n:
        raise ValueError("Sifrat mora biti u opsegu [0, n)")
    return pow(ciphertext, d, n)


# ---------------------------------------------------------------------------
# Rad s bajtovima - most izmedju teksta u UI-ju i cijelih brojeva iznad
# ---------------------------------------------------------------------------

def max_message_bytes(n: int) -> int:
    """
    Najveci broj bajtova otvorenog teksta koji stane u jedan RSA blok.

    Jedan bajt se trosi na vodecu 0x01 oznaku, koja cuva vodece nule poruke
    pri konverziji bajtovi -> broj -> bajtovi.
    """
    return (n.bit_length() - 1) // 8 - 1


def encrypt_bytes(plaintext: bytes, public_key: tuple) -> bytes:
    """Enkriptuje bajtove kao jedan blok; duzina sifrata je velicina modula."""
    n, _ = public_key
    limit = max_message_bytes(n)
    if len(plaintext) > limit:
        raise ValueError(
            "Poruka ima %d bajtova, a s ovim kljucem (%d bita) moze najvise %d. "
            "Duzi tekst se u praksi salje hibridno: RSA enkriptuje AES kljuc, "
            "AES enkriptuje sam tekst (vidi 3.5.3)."
            % (len(plaintext), n.bit_length(), limit)
        )

    message = int.from_bytes(b"\x01" + plaintext, "big")
    ciphertext = encrypt(message, public_key)
    return ciphertext.to_bytes((n.bit_length() + 7) // 8, "big")


def decrypt_bytes(ciphertext: bytes, private_key: tuple) -> bytes:
    """Inverz od encrypt_bytes - skida vodecu 0x01 oznaku."""
    n, _ = private_key
    message = decrypt(int.from_bytes(ciphertext, "big"), private_key)
    raw = message.to_bytes((n.bit_length() + 7) // 8, "big")

    stripped = raw.lstrip(b"\x00")
    if not stripped or stripped[0] != 0x01:
        raise ValueError("Dekripcija nije uspjela - pogresan kljuc ili ostecen sifrat")
    return stripped[1:]


# ---------------------------------------------------------------------------
# Wienerov napad - vidi 3.3.6
# ---------------------------------------------------------------------------

def _continued_fraction(numerator: int, denominator: int) -> list:
    """Razvoj razlomka numerator/denominator u verizni razlomak [a0; a1, a2, ...]."""
    quotients = []
    while denominator:
        quotient = numerator // denominator
        quotients.append(quotient)
        numerator, denominator = denominator, numerator - quotient * denominator
    return quotients


def _convergents(quotients: list):
    """Konvergente veriznog razlomka, redom - svaka je aproksimacija k/d."""
    numerator_prev, numerator = 0, 1
    denominator_prev, denominator = 1, 0
    for quotient in quotients:
        numerator, numerator_prev = quotient * numerator + numerator_prev, numerator
        denominator, denominator_prev = quotient * denominator + denominator_prev, denominator
        yield numerator, denominator


def _is_perfect_square(value: int) -> bool:
    if value < 0:
        return False
    root = math.isqrt(value)
    return root * root == value


def wiener_attack(public_key: tuple):
    """
    Pokusaj rekonstruisati d preko razvoja u verizni razlomak,
    kad je d namjerno mali. Vidi 3.3.6.

    Ideja: iz e*d = 1 (mod phi) slijedi e/n ~ k/d, pa je k/d jedna od konvergenti
    veriznog razlomka za e/n. Za svaku konvergentu se provjeri da li daje
    cjelobrojno phi cije rjesenje kvadratne jednacine x^2 - (n-phi+1)x + n = 0
    daje dva cijela faktora - ako da, d je pogodjen.

    Vraca d ako uspije, inace None.
    """
    n, e = public_key

    for k, d in _convergents(_continued_fraction(e, n)):
        if k == 0 or d == 0:
            continue
        if (e * d - 1) % k != 0:
            continue

        phi = (e * d - 1) // k

        # p i q su korijeni jednacine x^2 - (n - phi + 1)x + n = 0
        sum_pq = n - phi + 1
        discriminant = sum_pq * sum_pq - 4 * n
        if discriminant < 0 or not _is_perfect_square(discriminant):
            continue
        if (sum_pq + math.isqrt(discriminant)) % 2 != 0:
            continue

        return d

    return None
