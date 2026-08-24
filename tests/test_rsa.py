"""
Validacija RSA implementacije iz core/rsa.py.

Kod RSA nema fiksnih test vektora kao kod DES-a i AES-a (kljucevi su nasumicni),
pa se provjeravaju matematicka svojstva: da je n proizvod dva prosta broja tacne
duzine, da je d inverz od e po modulu phi, da je dekripcija inverz enkripcije,
i da Wienerov napad uspijeva tacno tamo gdje teorija kaze da treba.

Pokreni: python tests/test_rsa.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sympy import isprime  # noqa: E402

from core import rsa  # noqa: E402


def test_struktura_kljuca():
    """n = p*q, oba prosta, modul ima tacno trazenu duzinu."""
    keys = rsa.generate_keys(1024)
    n, e = keys["public"]
    n_priv, d = keys["private"]

    assert n == n_priv, "javni i privatni kljuc moraju dijeliti isti modul"
    assert n == keys["p"] * keys["q"]
    assert isprime(keys["p"]) and isprime(keys["q"])
    assert n.bit_length() == 1024, "modul ima %d bita umjesto 1024" % n.bit_length()
    assert e == rsa.DEFAULT_EXPONENT
    assert (e * d) % keys["phi"] == 1, "d nije multiplikativni inverz od e mod phi(n)"


def test_roundtrip_brojevi():
    """m^e^d = m (mod n) za razne poruke."""
    keys = rsa.generate_keys(1024)
    n, _ = keys["public"]

    for message in (0, 1, 2, 42, 65537, n - 1, n // 3):
        ciphertext = rsa.encrypt(message, keys["public"])
        assert rsa.decrypt(ciphertext, keys["private"]) == message, (
            "poruka %d se nije vratila ispravno" % message
        )


def test_roundtrip_bajtovi():
    keys = rsa.generate_keys(1024)

    poruke = [
        b"",
        b"a",
        b"\x00\x00vodece nule",
        "Šifrovanje sa dijakritikom".encode("utf-8"),
        os.urandom(rsa.max_message_bytes(keys["public"][0])),
    ]
    for plaintext in poruke:
        ciphertext = rsa.encrypt_bytes(plaintext, keys["public"])
        assert rsa.decrypt_bytes(ciphertext, keys["private"]) == plaintext


def test_duzina_sifrata():
    """Sifrat je uvijek pune velicine modula, bez obzira na duzinu poruke."""
    keys = rsa.generate_keys(1024)
    for plaintext in (b"a", b"x" * 50):
        assert len(rsa.encrypt_bytes(plaintext, keys["public"])) == 128


def test_predugacka_poruka():
    """Poruka duza od modula mora dati jasnu gresku, ne tihi pogresan rezultat."""
    keys = rsa.generate_keys(1024)
    n, _ = keys["public"]
    limit = rsa.max_message_bytes(n)

    try:
        rsa.encrypt_bytes(b"x" * (limit + 1), keys["public"])
    except ValueError as exc:
        assert "bajtova" in str(exc)
    else:
        raise AssertionError("predugacka poruka je prosla bez greske")

    try:
        rsa.encrypt(n, keys["public"])
    except ValueError:
        pass
    else:
        raise AssertionError("poruka m >= n je prosla bez greske")


def test_pogresan_kljuc():
    """Dekripcija tudjim kljucem ne smije vratiti originalni tekst."""
    alice = rsa.generate_keys(1024)
    bob = rsa.generate_keys(1024)

    ciphertext = rsa.encrypt_bytes(b"tajna poruka", alice["public"])
    try:
        recovered = rsa.decrypt_bytes(ciphertext, bob["private"])
    except ValueError:
        return  # ocekivano - oznaka 0x01 se ne poklapa
    assert recovered != b"tajna poruka"


def test_nevazeca_duzina_kljuca():
    for bad in (256, 512, 1000, 8192):
        try:
            rsa.generate_keys(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("generate_keys(%d) je prosao bez greske" % bad)


def test_verizni_razlomak():
    """Poznat primjer razvoja: 649/200 = [3; 4, 12, 4]."""
    assert rsa._continued_fraction(649, 200) == [3, 4, 12, 4]
    assert list(rsa._convergents([3, 4, 12, 4]))[-1] == (649, 200)


def test_wiener_uspijeva_na_slabom_kljucu():
    """Mali d se mora rekonstruisati samo iz javnog kljuca (n, e)."""
    keys = rsa.generate_vulnerable_keys(1024)
    n, e = keys["public"]
    pravi_d = keys["private"][1]

    assert pravi_d.bit_length() < n.bit_length() // 4, "d nije dovoljno mali za napad"

    nadjeni_d = rsa.wiener_attack(keys["public"])
    assert nadjeni_d == pravi_d, "napad je vratio %r umjesto %d" % (nadjeni_d, pravi_d)

    # Kljucni dokaz: napadac sada dekriptuje poruku koju nije trebao moci procitati
    ciphertext = rsa.encrypt_bytes(b"napadnuta poruka", keys["public"])
    assert rsa.decrypt_bytes(ciphertext, (n, nadjeni_d)) == b"napadnuta poruka"


def test_wiener_ne_uspijeva_na_normalnom_kljucu():
    """Isti napad na kljuc s e = 65537 mora podbaciti, i to brzo."""
    keys = rsa.generate_keys(1024)

    start = time.perf_counter()
    rezultat = rsa.wiener_attack(keys["public"])
    trajanje = time.perf_counter() - start

    assert rezultat is None, "napad je 'uspio' na normalnom kljucu - to je greska"
    assert trajanje < 1.0, "napad je trajao %.2fs, ocekivano je da odustane odmah" % trajanje


def test_generisanje_2048():
    """Sporiji slucaj - provjera da duzine iz benchmarka stvarno rade."""
    keys = rsa.generate_keys(2048)
    assert keys["public"][0].bit_length() == 2048
    ciphertext = rsa.encrypt_bytes(b"test", keys["public"])
    assert rsa.decrypt_bytes(ciphertext, keys["private"]) == b"test"


def _run_all():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failed = 0
    for test in tests:
        start = time.perf_counter()
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - test runner namjerno hvata sve
            failed += 1
            print("FAIL  %s\n      %s: %s" % (test.__name__, type(exc).__name__, exc))
        else:
            print("ok    %s  (%.2fs)" % (test.__name__, time.perf_counter() - start))
    print("\n%d/%d testova proslo" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
