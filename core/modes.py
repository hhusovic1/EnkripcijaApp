"""
Padding i rezim rada - sloj iznad blokovnih sifara (DES, 3DES, AES).

DES i AES enkriptuju tacno jedan blok (8 odnosno 16 bajtova). Da bi se
enkriptovao tekst proizvoljne duzine treba dvoje:

1. PKCS#7 dopuna - dopuni poruku do cijelog broja blokova, tako da se dopuna
   moze jednoznacno ukloniti pri dekripciji.
2. Rezim rada - ovdje CBC (Cipher Block Chaining): svaki blok se prije
   enkripcije XOR-uje s prethodnim sifratom, pa isti otvoreni blok daje
   razlicit sifrat na razlicitim mjestima.

Zasto ne ECB: u ECB rezimu jednaki blokovi daju jednake sifrate, pa se struktura
podataka vidi kroz sifrat (poznati primjer je "ECB pingvin"). CBC to rjesava uz
nasumican inicijalizacioni vektor (IV), koji nije tajan i salje se uz sifrat.
"""
import os


# ---------------------------------------------------------------------------
# PKCS#7 dopuna
# ---------------------------------------------------------------------------

def pkcs7_pad(data: bytes, block_size: int) -> bytes:
    """
    Dopunjava podatke do visekratnika velicine bloka. Vrijednost svakog dodatog
    bajta jednaka je broju dodatih bajtova.

    Ako je poruka vec tacan visekratnik, dodaje se cijeli blok dopune - inace se
    ne bi znalo da li su posljednji bajtovi dopuna ili podatak.
    """
    if not 1 <= block_size <= 255:
        raise ValueError("Velicina bloka mora biti izmedju 1 i 255 bajtova")
    padding_length = block_size - (len(data) % block_size)
    return data + bytes([padding_length]) * padding_length


def pkcs7_unpad(data: bytes, block_size: int) -> bytes:
    """Uklanja PKCS#7 dopunu uz provjeru ispravnosti."""
    if not data or len(data) % block_size != 0:
        raise ValueError(
            "Podaci za uklanjanje dopune moraju biti visekratnik bloka (%d bajta), "
            "dobijeno %d" % (block_size, len(data))
        )

    padding_length = data[-1]
    if not 1 <= padding_length <= block_size:
        raise ValueError("Neispravna dopuna - pogresan kljuc ili ostecen sifrat")
    if data[-padding_length:] != bytes([padding_length]) * padding_length:
        raise ValueError("Neispravna dopuna - pogresan kljuc ili ostecen sifrat")

    return data[:-padding_length]


# ---------------------------------------------------------------------------
# CBC rezim
# ---------------------------------------------------------------------------

def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def cbc_encrypt(plaintext: bytes, encrypt_block, block_size: int, iv: bytes = None) -> tuple:
    """
    Enkriptuje poruku proizvoljne duzine u CBC rezimu.

    `encrypt_block` je funkcija jednog bloka - npr. lambda b: aes.encrypt(b, key).
    Vraca (iv, ciphertext); IV se generise nasumicno ako nije zadat.
    """
    if iv is None:
        iv = os.urandom(block_size)
    elif len(iv) != block_size:
        raise ValueError(
            "IV mora imati tacno %d bajta, dobijeno %d" % (block_size, len(iv))
        )

    padded = pkcs7_pad(plaintext, block_size)

    ciphertext = bytearray()
    previous = iv
    for offset in range(0, len(padded), block_size):
        block = padded[offset: offset + block_size]
        encrypted = encrypt_block(_xor(block, previous))
        ciphertext += encrypted
        previous = encrypted

    return iv, bytes(ciphertext)


def cbc_decrypt(ciphertext: bytes, decrypt_block, block_size: int, iv: bytes) -> bytes:
    """Inverz od cbc_encrypt. `decrypt_block` dekriptuje jedan blok."""
    if len(iv) != block_size:
        raise ValueError(
            "IV mora imati tacno %d bajta, dobijeno %d" % (block_size, len(iv))
        )
    if not ciphertext or len(ciphertext) % block_size != 0:
        raise ValueError(
            "Sifrat mora biti visekratnik velicine bloka (%d bajta), dobijeno %d"
            % (block_size, len(ciphertext))
        )

    plaintext = bytearray()
    previous = iv
    for offset in range(0, len(ciphertext), block_size):
        block = ciphertext[offset: offset + block_size]
        plaintext += _xor(decrypt_block(block), previous)
        previous = block

    return pkcs7_unpad(bytes(plaintext), block_size)
