"""
Core paket - svaki modul (des, aes, rsa, ecc, chacha) implementira isti interfejs:

    generate_keys() -> dict          # vraca kljuceve specificne za algoritam
    encrypt(plaintext, key) -> bytes
    decrypt(ciphertext, key) -> bytes

Ovo omogucava da benchmark/ i app.py tretiraju sve algoritme uniformno.
"""
