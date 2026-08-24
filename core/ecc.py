"""
ECC (ECDH) - omotac oko `cryptography` biblioteke (X25519).

Ovdje se elipticka kriva ne implementira rucno - to nosi previse suptilnih
sigurnosnih zamki (timing napadi, invalid curve napadi) da bi vrijedilo
raditi od nule za demonstracionu aplikaciju. Vidi thesis 3.4.5.
"""
from cryptography.hazmat.primitives.asymmetric import x25519


def generate_keys() -> dict:
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    return {"private": private_key, "public": public_key}


def derive_shared_secret(my_private_key, their_public_key) -> bytes:
    """ECDH razmjena - obje strane dobiju isti shared secret."""
    return my_private_key.exchange(their_public_key)
