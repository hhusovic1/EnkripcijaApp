
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import des  # noqa: E402

# (kljuc, otvoreni tekst, sifrat) - sve u hex zapisu
TEST_VECTORS = [
    ("133457799BBCDFF1", "0123456789ABCDEF", "85E813540F0AB405"),
    ("0E329232EA6D0D73", "8787878787878787", "0000000000000000"),
    ("0000000000000000", "0000000000000000", "8CA64DE9C1B123A7"),
    ("FFFFFFFFFFFFFFFF", "FFFFFFFFFFFFFFFF", "7359B2163E4EDC58"),
    ("3000000000000000", "1000000000000001", "958E6E627A05557B"),
    ("1111111111111111", "1111111111111111", "F40379AB9E0EC533"),
    ("0123456789ABCDEF", "1111111111111111", "17668DFC7292532D"),
    ("1111111111111111", "0123456789ABCDEF", "8A5AE1F81AB8F2DD"),
    ("FEDCBA9876543210", "0123456789ABCDEF", "ED39D950FA74BCC4"),
    ("7CA110454A1A6E57", "01A1D6D039776742", "690F5B0D9A26939B"),
    ("0131D9619DC1376E", "5CD54CA83DEF57DA", "7A389D10354BD271"),
    ("07A1133E4A0B2686", "0248D43806F67172", "868EBB51CAB4599A"),
]


def test_official_vectors():
    """Enkripcija mora dati tacno sifrat iz standarda."""
    for key_hex, pt_hex, ct_hex in TEST_VECTORS:
        key = bytes.fromhex(key_hex)
        plaintext = bytes.fromhex(pt_hex)
        expected = bytes.fromhex(ct_hex)

        actual = des.encrypt(plaintext, key)
        assert actual == expected, (
            "encrypt(%s, kljuc=%s) = %s, ocekivano %s"
            % (pt_hex, key_hex, actual.hex().upper(), ct_hex)
        )


def test_official_vectors_decrypt():
    """Dekripcija sifrata iz standarda mora vratiti originalni otvoreni tekst."""
    for key_hex, pt_hex, ct_hex in TEST_VECTORS:
        key = bytes.fromhex(key_hex)
        expected = bytes.fromhex(pt_hex)

        actual = des.decrypt(bytes.fromhex(ct_hex), key)
        assert actual == expected, (
            "decrypt(%s, kljuc=%s) = %s, ocekivano %s"
            % (ct_hex, key_hex, actual.hex().upper(), pt_hex)
        )


def test_key_schedule_shape():
    """16 podkljuceva, svaki tacno 48 bita."""
    subkeys = des._key_schedule(bytes.fromhex("133457799BBCDFF1"))
    assert len(subkeys) == 16, "ocekivano 16 podkljuceva, dobijeno %d" % len(subkeys)
    for i, subkey in enumerate(subkeys, start=1):
        assert 0 <= subkey < (1 << 48), "podkljuc K%d nije 48-bitni" % i

    # Prvi podkljuc za ovaj kljuc je poznat iz standardnog primjera key schedulea
    assert subkeys[0] == 0x1B02EFFC7072, "K1 = %012X" % subkeys[0]


def test_roundtrip_random():
    """decrypt(encrypt(x)) == x za nasumicne kljuceve i blokove."""
    for _ in range(200):
        key = des.generate_keys()["key"]
        block = os.urandom(des.BLOCK_SIZE)
        assert des.decrypt(des.encrypt(block, key), key) == block


def test_cross_check_pycryptodome():
    """Unakrsna provjera protiv referentne biblioteke nad nasumicnim ulazima."""
    from Crypto.Cipher import DES as RefDES

    for _ in range(200):
        key = des.generate_keys()["key"]
        block = os.urandom(des.BLOCK_SIZE)

        reference = RefDES.new(key, RefDES.MODE_ECB).encrypt(block)
        mine = des.encrypt(block, key)
        assert mine == reference, (
            "razlika na kljucu %s, bloku %s: moje=%s, referenca=%s"
            % (key.hex(), block.hex(), mine.hex(), reference.hex())
        )


def test_3des_roundtrip():
    """EDE/DED par mora biti inverzan."""
    for _ in range(50):
        keys = des.generate_keys_3des()
        block = os.urandom(des.BLOCK_SIZE)
        ciphertext = des.encrypt_3des(block, keys["k1"], keys["k2"], keys["k3"])
        assert des.decrypt_3des(ciphertext, keys["k1"], keys["k2"], keys["k3"]) == block


def test_3des_degenerira_u_des():
    """
    Kad je k1 = k2 = k3, EDE sema se svodi na obicni DES.
    To je razlog zasto je 3DES kompatibilan unazad sa DES-om (3.1.5).
    """
    key = des.generate_keys()["key"]
    block = os.urandom(des.BLOCK_SIZE)
    assert des.encrypt_3des(block, key, key, key) == des.encrypt(block, key)


def test_3des_cross_check_pycryptodome():
    """3DES protiv referentne biblioteke (keying option 1 - tri nezavisna kljuca)."""
    from Crypto.Cipher import DES3 as RefDES3

    checked = 0
    while checked < 50:
        keys = des.generate_keys_3des(keying_option=1)
        bundle = keys["k1"] + keys["k2"] + keys["k3"]
        try:
            cipher = RefDES3.new(bundle, RefDES3.MODE_ECB)
        except ValueError:
            continue  # biblioteka odbija degenerisane snopove kljuceva

        block = os.urandom(des.BLOCK_SIZE)
        mine = des.encrypt_3des(block, keys["k1"], keys["k2"], keys["k3"])
        assert mine == cipher.encrypt(block)
        checked += 1


def test_weak_keys_are_involutive():
    """Kod slabog kljuca su svi podkljucevi jednaki, pa je E_k(E_k(P)) = P (3.1.4)."""
    assert len(des.WEAK_KEYS) == 4, "rad navodi tacno 4 slaba kljuca"

    block = os.urandom(des.BLOCK_SIZE)
    for weak_key in des.WEAK_KEYS:
        subkeys = des._key_schedule(weak_key)
        assert len(set(subkeys)) == 1, "slab kljuc %s nema jednake podkljuceve" % weak_key.hex()
        assert des.encrypt(des.encrypt(block, weak_key), weak_key) == block


def test_semi_weak_keys():
    """Za polu-slabe parove vrijedi E_K = D_K' (3.1.4) - sest parova, 12 kljuceva."""
    assert len(des.SEMI_WEAK_KEY_PAIRS) == 6, "rad navodi 6 parova polu-slabih kljuceva"

    block = os.urandom(des.BLOCK_SIZE)
    for k, k_prim in des.SEMI_WEAK_KEY_PAIRS:
        assert des.encrypt(block, k) == des.decrypt(block, k_prim), (
            "par (%s, %s) nije polu-slab" % (k.hex(), k_prim.hex())
        )
        # Posljedica: enkripcija jednim pa drugim kljucem vraca original
        assert des.encrypt(des.encrypt(block, k), k_prim) == block


def test_generate_keys_izbjegava_slabe():
    """Generator ne smije vratiti slab ni polu-slab kljuc, i mora postaviti paritet."""
    assert len(des.AVOIDED_KEYS) == 16, "4 slaba + 12 polu-slabih = 16"

    for _ in range(100):
        key = des.generate_keys()["key"]
        assert len(key) == des.KEY_SIZE
        assert key not in des.AVOIDED_KEYS
        for byte in key:
            assert bin(byte).count("1") % 2 == 1, "bajt %02X nema neparan paritet" % byte


def test_3des_opcije_kljuceva():
    """Numeracija opcija mora pratiti Tabelu 3.11 iz rada."""
    block = os.urandom(des.BLOCK_SIZE)

    opcija1 = des.generate_keys_3des(1)
    assert len({opcija1["k1"], opcija1["k2"], opcija1["k3"]}) == 3

    opcija2 = des.generate_keys_3des(2)
    assert opcija2["k1"] == opcija2["k3"] != opcija2["k2"]

    # Opcija 3 se mora svesti na obicni DES - to je unazadna kompatibilnost iz 3.1.5
    opcija3 = des.generate_keys_3des(3)
    assert opcija3["k1"] == opcija3["k2"] == opcija3["k3"]
    assert des.encrypt_3des(block, **{k: opcija3[k] for k in ("k1", "k2", "k3")}) == (
        des.encrypt(block, opcija3["k1"])
    )

    for bad in (0, 4, -1):
        try:
            des.generate_keys_3des(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("keying_option=%r je prosao bez greske" % bad)


def test_error_handling():
    """Jasne greske na pogresnoj duzini kljuca i bloka."""
    key = des.generate_keys()["key"]

    for bad_block in (b"", b"prekratko", b"x" * 16):
        try:
            des.encrypt(bad_block, key)
        except ValueError:
            pass
        else:
            raise AssertionError("blok duzine %d je prosao bez greske" % len(bad_block))

    for bad_key in (b"", b"kratak", b"k" * 24):
        try:
            des.encrypt(b"12345678", bad_key)
        except ValueError:
            pass
        else:
            raise AssertionError("kljuc duzine %d je prosao bez greske" % len(bad_key))


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
