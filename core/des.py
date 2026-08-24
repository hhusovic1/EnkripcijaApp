"""
DES / 3DES - rucna implementacija.

Vidi thesis poglavlje 3.1: Feistelova mreza, IP/IP^-1, key schedule (PC-1, PC-2),
S-blokovi S1-S8, ekspanziona permutacija E, permutacija P.

TODO: implementirati prema strukturi opisanoj u 3.1.2 - 3.1.3.
Validacija: koristi zvanicne FIPS 46-3 test vektore prije nego predjes na AES.
"""


def generate_keys() -> dict:
    """Generise 64-bitni DES kljuc (56 efektivnih + 8 bita pariteta)."""
    raise NotImplementedError("Generisi nasumican 64-bitni kljuc")


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """
    Enkriptuje 64-bitni blok. Koraci (3.1.3):
    1. Inicijalna permutacija IP
    2. 16 rundi Feistelove mreze (koristi _key_schedule ispod)
    3. Zamjena L16/R16
    4. Zavrsna permutacija IP^-1
    """
    raise NotImplementedError


def decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """Isti algoritam kao encrypt, ali s podkljucevima u obrnutom redoslijedu K16...K1."""
    raise NotImplementedError


def _key_schedule(key: bytes) -> list:
    """Generise 16 podkljuceva K1..K16 (PC-1 -> rotacije -> PC-2). Vidi 3.1.3, Slika 3.4."""
    raise NotImplementedError


def encrypt_3des(plaintext: bytes, k1: bytes, k2: bytes, k3: bytes) -> bytes:
    """EDE sema: C = E_k3(D_k2(E_k1(P))). Vidi 3.1.5."""
    raise NotImplementedError


def decrypt_3des(ciphertext: bytes, k1: bytes, k2: bytes, k3: bytes) -> bytes:
    """P = D_k1(E_k2(D_k3(C)))."""
    raise NotImplementedError
