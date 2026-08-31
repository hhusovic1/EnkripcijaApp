
import os


def pkcs7_pad(data: bytes, block_size: int) -> bytes:
    if not 1 <= block_size <= 255:
        raise ValueError("Velicina bloka mora biti izmedju 1 i 255 bajtova")
    padding_length = block_size - (len(data) % block_size)
    return data + bytes([padding_length]) * padding_length


def pkcs7_unpad(data: bytes, block_size: int) -> bytes:

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



def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


PROGRESS_SVAKIH_BLOKOVA = 512


def cbc_encrypt(plaintext: bytes, encrypt_block, block_size: int, iv: bytes = None,
                on_progress=None) -> tuple:
    if iv is None:
        iv = os.urandom(block_size)
    elif len(iv) != block_size:
        raise ValueError(
            "IV mora imati tacno %d bajta, dobijeno %d" % (block_size, len(iv))
        )

    padded = pkcs7_pad(plaintext, block_size)

    ciphertext = bytearray()
    previous = iv
    for redni_broj, offset in enumerate(range(0, len(padded), block_size)):
        block = padded[offset: offset + block_size]
        encrypted = encrypt_block(_xor(block, previous))
        ciphertext += encrypted
        previous = encrypted

        if on_progress is not None and redni_broj % PROGRESS_SVAKIH_BLOKOVA == 0:
            on_progress(offset, len(padded))

    if on_progress is not None:
        on_progress(len(padded), len(padded))

    return iv, bytes(ciphertext)


def cbc_decrypt(ciphertext: bytes, decrypt_block, block_size: int, iv: bytes,
                on_progress=None) -> bytes:

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
    for redni_broj, offset in enumerate(range(0, len(ciphertext), block_size)):
        block = ciphertext[offset: offset + block_size]
        plaintext += _xor(decrypt_block(block), previous)
        previous = block

        if on_progress is not None and redni_broj % PROGRESS_SVAKIH_BLOKOVA == 0:
            on_progress(offset, len(ciphertext))

    if on_progress is not None:
        on_progress(len(ciphertext), len(ciphertext))

    return pkcs7_unpad(bytes(plaintext), block_size)
