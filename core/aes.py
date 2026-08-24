"""
AES - rucna implementacija.

Vidi thesis poglavlje 3.2: GF(2^8) aritmetika, SubBytes, ShiftRows, MixColumns,
AddRoundKey, key expansion (RotWord, SubWord, Rcon).

TODO: implementirati prema 3.2.3 - 3.2.6.
Validacija: koristi zvanicne FIPS-197 test vektore (Appendix B/C imaju gotove primjere).
Podrzi sve tri varijante: AES-128 (10 rundi), AES-192 (12), AES-256 (14).
"""


def generate_keys(key_size: int = 128) -> dict:
    """key_size je 128, 192 ili 256."""
    raise NotImplementedError


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """16-bajtni blok. Vidi pseudokod u 3.2.6."""
    raise NotImplementedError


def decrypt(ciphertext: bytes, key: bytes) -> bytes:
    raise NotImplementedError


def _key_expansion(key: bytes) -> list:
    """Vidi 3.2.5 - RotWord, SubWord, Rcon."""
    raise NotImplementedError


def _sub_bytes(state):
    """S-box supstitucija. Vidi 3.2.4."""
    raise NotImplementedError


def _shift_rows(state):
    raise NotImplementedError


def _mix_columns(state):
    """Mnozenje kolone sa fiksnim polinomom u GF(2^8). Vidi 3.2.4."""
    raise NotImplementedError
