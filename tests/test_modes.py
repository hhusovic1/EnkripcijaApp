"""
Validacija PKCS#7 dopune i CBC rezima iz core/modes.py, plus provjera da
bibliotecki moduli (ECC, ChaCha20) rade kako treba.

Pokreni: python tests/test_modes.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import aes, chacha, des, ecc, modes  # noqa: E402


# ---------------------------------------------------------------------------
# PKCS#7
# ---------------------------------------------------------------------------

def test_pkcs7_poznati_primjeri():
    assert modes.pkcs7_pad(b"", 8) == b"\x08" * 8
    assert modes.pkcs7_pad(b"ABCD", 8) == b"ABCD\x04\x04\x04\x04"
    assert modes.pkcs7_pad(b"ABCDEFGH", 8) == b"ABCDEFGH" + b"\x08" * 8
    assert modes.pkcs7_pad(b"A" * 15, 16) == b"A" * 15 + b"\x01"


def test_pkcs7_roundtrip():
    for block_size in (8, 16):
        for length in range(0, 3 * block_size + 1):
            data = os.urandom(length)
            padded = modes.pkcs7_pad(data, block_size)
            assert len(padded) % block_size == 0
            assert modes.pkcs7_unpad(padded, block_size) == data


def test_pkcs7_odbija_neispravnu_dopunu():
    for bad in (b"ABCDEFG\x09", b"ABCDEFG\x00", b"ABCDEF\x03\x03"):
        try:
            modes.pkcs7_unpad(bad, 8)
        except ValueError:
            pass
        else:
            raise AssertionError("neispravna dopuna %r je prosla" % bad)


# ---------------------------------------------------------------------------
# CBC nad rucnim implementacijama
# ---------------------------------------------------------------------------

def _cbc_roundtrip(modul, key, block_size):
    for length in (0, 1, block_size - 1, block_size, block_size + 1, 1000):
        plaintext = os.urandom(length)
        iv, ciphertext = modes.cbc_encrypt(
            plaintext, lambda b: modul.encrypt(b, key), block_size
        )
        recovered = modes.cbc_decrypt(
            ciphertext, lambda b: modul.decrypt(b, key), block_size, iv
        )
        assert recovered == plaintext, "duzina %d se nije vratila" % length


def test_cbc_des():
    _cbc_roundtrip(des, des.generate_keys()["key"], des.BLOCK_SIZE)


def test_cbc_aes_sve_duzine():
    for key_size in aes.VALID_KEY_SIZES:
        _cbc_roundtrip(aes, aes.generate_keys(key_size)["key"], aes.BLOCK_SIZE)


def test_cbc_3des():
    keys = des.generate_keys_3des()
    plaintext = b"Poruka duza od jednog bloka, pa se lancanje stvarno vidi."

    iv, ciphertext = modes.cbc_encrypt(
        plaintext,
        lambda b: des.encrypt_3des(b, keys["k1"], keys["k2"], keys["k3"]),
        des.BLOCK_SIZE,
    )
    recovered = modes.cbc_decrypt(
        ciphertext,
        lambda b: des.decrypt_3des(b, keys["k1"], keys["k2"], keys["k3"]),
        des.BLOCK_SIZE,
        iv,
    )
    assert recovered == plaintext


def test_cbc_cross_check_pycryptodome():
    """CBC nad rucnim AES-om mora dati isti sifrat kao referentna biblioteka."""
    from Crypto.Cipher import AES as RefAES

    key = aes.generate_keys(128)["key"]
    iv = os.urandom(16)
    plaintext = os.urandom(64)  # tacan visekratnik, da dopuna ne smeta poredjenju

    _, mine = modes.cbc_encrypt(plaintext, lambda b: aes.encrypt(b, key), 16, iv=iv)
    reference = RefAES.new(key, RefAES.MODE_CBC, iv=iv).encrypt(
        modes.pkcs7_pad(plaintext, 16)
    )
    assert mine == reference


def test_cbc_isti_blokovi_daju_razlicit_sifrat():
    """Poenta CBC-a: ponovljeni otvoreni blok ne daje ponovljeni sifrat."""
    key = aes.generate_keys(128)["key"]
    plaintext = b"A" * 32  # dva identicna bloka

    _, ciphertext = modes.cbc_encrypt(plaintext, lambda b: aes.encrypt(b, key), 16)
    assert ciphertext[:16] != ciphertext[16:32]

    # Za kontrast: u ECB rezimu bi bili identicni
    assert aes.encrypt(b"A" * 16, key) == aes.encrypt(b"A" * 16, key)


def test_cbc_progress_callback():
    """
    Callback za napredak mora se pozvati, zavrsiti na 100% i ne smije mijenjati
    rezultat - koristi ga aplikacija za progress bar kod velikih fajlova.
    """
    key = aes.generate_keys(128)["key"]
    plaintext = os.urandom(50_000)

    pozivi = []
    iv, ciphertext = modes.cbc_encrypt(
        plaintext, lambda b: aes.encrypt(b, key), 16,
        on_progress=lambda obradjeno, ukupno: pozivi.append((obradjeno, ukupno)),
    )

    assert pozivi, "callback nije pozvan nijednom"
    assert pozivi[-1][0] == pozivi[-1][1], "posljednji poziv nije 100%"
    assert all(o <= u for o, u in pozivi), "napredak je premasio ukupno"

    # Rezultat mora biti identican onome bez callbacka
    _, bez_callbacka = modes.cbc_encrypt(
        plaintext, lambda b: aes.encrypt(b, key), 16, iv=iv
    )
    assert ciphertext == bez_callbacka

    pozivi_dec = []
    vraceno = modes.cbc_decrypt(
        ciphertext, lambda b: aes.decrypt(b, key), 16, iv,
        on_progress=lambda obradjeno, ukupno: pozivi_dec.append((obradjeno, ukupno)),
    )
    assert vraceno == plaintext
    assert pozivi_dec and pozivi_dec[-1][0] == pozivi_dec[-1][1]


def test_cbc_docstring_nije_pokvaren():
    """
    Regresija: docstring je bio napisan kao string s % operatorom, sto ga je
    pretvorilo u obican izraz i ostavilo __doc__ prazan.
    """
    assert modes.cbc_encrypt.__doc__, "cbc_encrypt nema docstring"
    assert "on_progress" in modes.cbc_encrypt.__doc__


def test_cbc_razliciti_iv_daje_razlicit_sifrat():
    key = aes.generate_keys(128)["key"]
    plaintext = b"ista poruka svaki put"

    _, prvi = modes.cbc_encrypt(plaintext, lambda b: aes.encrypt(b, key), 16)
    _, drugi = modes.cbc_encrypt(plaintext, lambda b: aes.encrypt(b, key), 16)
    assert prvi != drugi, "isti sifrat dva puta - IV se ne koristi kako treba"


# ---------------------------------------------------------------------------
# Bibliotecki moduli (Faza 2)
# ---------------------------------------------------------------------------

def test_chacha_roundtrip():
    keys = chacha.generate_keys()
    for length in (0, 1, 1000, 100_000):
        plaintext = os.urandom(length)
        ciphertext = chacha.encrypt(plaintext, keys["key"], keys["nonce"])
        assert len(ciphertext) == length, "ChaCha20 je tocna sifra - duzina se ne mijenja"
        assert chacha.decrypt(ciphertext, keys["key"], keys["nonce"]) == plaintext


def test_ecdh_obje_strane_dobiju_isti_secret():
    alice = ecc.generate_keys()
    bob = ecc.generate_keys()

    alice_secret = ecc.derive_shared_secret(alice["private"], bob["public"])
    bob_secret = ecc.derive_shared_secret(bob["private"], alice["public"])

    assert alice_secret == bob_secret, "ECDH nije dao isti shared secret"
    assert len(alice_secret) == 32, "X25519 shared secret je 32 bajta"


def test_ecdh_treca_strana_ne_pogadja():
    alice = ecc.generate_keys()
    bob = ecc.generate_keys()
    mallory = ecc.generate_keys()

    pravi = ecc.derive_shared_secret(alice["private"], bob["public"])
    mallorijev = ecc.derive_shared_secret(mallory["private"], bob["public"])
    assert pravi != mallorijev


def _run_all():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - test runner namjerno hvata sve
            failed += 1
            print("FAIL  %s\n      %s: %s" % (test.__name__, type(exc).__name__, exc))
        else:
            print("ok    %s" % test.__name__)
    print("\n%d/%d testova proslo" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
