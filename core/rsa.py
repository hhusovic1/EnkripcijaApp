"""
RSA - rucna implementacija.

Vidi thesis poglavlje 3.3: generisanje kljuceva (3.3.3), enkripcija/dekripcija (3.3.4).

TODO: implementirati. sympy.randprime() ti stedi pisanje Miller-Rabina od nule
(ali barem spomeni Miller-Rabin u radu jer ga koristis indirektno).
pow(base, exp, mod) u Pythonu vec radi efikasno kvadriraj-i-mnozi.
"""


def generate_keys(bits: int = 2048) -> dict:
    """
    Vraca {'public': (n, e), 'private': (n, d)}.
    Koraci (3.3.3): generisi p, q -> n = p*q -> phi(n) = (p-1)(q-1)
    -> e = 65537 -> d = e^-1 mod phi(n)
    """
    raise NotImplementedError


def encrypt(message: int, public_key: tuple) -> int:
    """c = m^e mod n"""
    raise NotImplementedError


def decrypt(ciphertext: int, private_key: tuple) -> int:
    """m = c^d mod n"""
    raise NotImplementedError


def wiener_attack(public_key: tuple) -> int:
    """
    Pokusaj rekonstruisati d preko razvoja u verizni razlomak,
    kad je d namjerno mali. Vidi 3.3.6.
    """
    raise NotImplementedError
