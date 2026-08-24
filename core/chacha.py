"""
ChaCha20 - omotac oko pycryptodome. Vidi thesis 2.3.1.
"""
import os

from Crypto.Cipher import ChaCha20


def generate_keys() -> dict:
    return {"key": os.urandom(32), "nonce": os.urandom(12)}


def encrypt(plaintext: bytes, key: bytes, nonce: bytes) -> bytes:
    cipher = ChaCha20.new(key=key, nonce=nonce)
    return cipher.encrypt(plaintext)


def decrypt(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
    cipher = ChaCha20.new(key=key, nonce=nonce)
    return cipher.decrypt(ciphertext)
