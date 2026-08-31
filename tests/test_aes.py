
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import aes  # noqa: E402

# FIPS-197 Appendix C: isti otvoreni tekst, tri duzine kljuca
APPENDIX_C = [
    (
        "000102030405060708090a0b0c0d0e0f",
        "00112233445566778899aabbccddeeff",
        "69c4e0d86a7b0430d8cdb78070b4c55a",
    ),
    (
        "000102030405060708090a0b0c0d0e0f1011121314151617",
        "00112233445566778899aabbccddeeff",
        "dda97ca4864cdfe06eaf70a0ec0d7191",
    ),
    (
        "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
        "00112233445566778899aabbccddeeff",
        "8ea2b7ca516745bfeafc49904b496089",
    ),
]

# FIPS-197 Appendix B - primjer koji se korak po korak razvija u standardu
APPENDIX_B = (
    "2b7e151628aed2a6abf7158809cf4f3c",
    "3243f6a8885a308d313198a2e0370734",
    "3925841d02dc09fbdc118597196a0b32",
)

# Prvih 16 vrijednosti S-boxa iz FIPS-197, Tabela 4 - kontrola da izvedeni
# S-box nije "izveden pogresno pa dosljedno pogresan"
SBOX_PRVI_RED = [
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5,
    0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
]


def test_sbox_odgovara_standardu():
    """S-box izveden iz inverza + afine transformacije mora dati tabelu iz standarda."""
    assert list(aes.SBOX[:16]) == SBOX_PRVI_RED, (
        "prvi red S-boxa: %s" % [hex(b) for b in aes.SBOX[:16]]
    )
    assert aes.SBOX[0x53] == 0xED, "poznata vrijednost S[53] = %02X" % aes.SBOX[0x53]
    assert len(set(aes.SBOX)) == 256, "S-box mora biti permutacija svih 256 bajtova"


def test_inv_sbox_je_inverzan():
    for value in range(256):
        assert aes.INV_SBOX[aes.SBOX[value]] == value


def test_gf_multiply():
    """Poznati primjeri mnozenja u GF(2^8) iz 3.2.3."""
    assert aes.gf_multiply(0x57, 0x83) == 0xC1
    assert aes.gf_multiply(0x57, 0x13) == 0xFE
    assert aes.gf_multiply(0x02, 0x87) == 0x15
    assert aes.gf_multiply(0x00, 0xFF) == 0x00
    assert aes.gf_multiply(0x01, 0xAB) == 0xAB


def test_appendix_c_encrypt():
    """AES-128/192/256 protiv zvanicnih vektora."""
    for key_hex, pt_hex, ct_hex in APPENDIX_C:
        key = bytes.fromhex(key_hex)
        actual = aes.encrypt(bytes.fromhex(pt_hex), key)
        assert actual.hex() == ct_hex, (
            "AES-%d: dobijeno %s, ocekivano %s" % (len(key) * 8, actual.hex(), ct_hex)
        )


def test_appendix_c_decrypt():
    for key_hex, pt_hex, ct_hex in APPENDIX_C:
        key = bytes.fromhex(key_hex)
        actual = aes.decrypt(bytes.fromhex(ct_hex), key)
        assert actual.hex() == pt_hex, (
            "AES-%d: dobijeno %s, ocekivano %s" % (len(key) * 8, actual.hex(), pt_hex)
        )


def test_appendix_b():
    key_hex, pt_hex, ct_hex = APPENDIX_B
    assert aes.encrypt(bytes.fromhex(pt_hex), bytes.fromhex(key_hex)).hex() == ct_hex
    assert aes.decrypt(bytes.fromhex(ct_hex), bytes.fromhex(key_hex)).hex() == pt_hex


def test_key_expansion_appendix_a():
    """
    FIPS-197 Appendix A: prosirenje kljuca 2b7e1516... Prvi kljuc runde je sam
    kljuc, a posljednji (w40..w43) je poznata vrijednost iz standarda.
    """
    key = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
    round_keys = aes._key_expansion(key)

    assert len(round_keys) == 11, "AES-128 ima 11 kljuceva runde, dobijeno %d" % len(round_keys)
    assert bytes(round_keys[0]) == key
    assert bytes(round_keys[1]).hex() == "a0fafe1788542cb123a339392a6c7605"
    assert bytes(round_keys[10]).hex() == "d014f9a8c9ee2589e13f0cc8b6630ca6"


def test_broj_rundi():
    for key_size, expected in ((128, 11), (192, 13), (256, 15)):
        key = aes.generate_keys(key_size)["key"]
        assert len(aes._key_expansion(key)) == expected


def test_roundtrip_random():
    for key_size in aes.VALID_KEY_SIZES:
        for _ in range(50):
            key = aes.generate_keys(key_size)["key"]
            block = os.urandom(aes.BLOCK_SIZE)
            assert aes.decrypt(aes.encrypt(block, key), key) == block


def test_cross_check_pycryptodome():
    """Unakrsna provjera protiv referentne biblioteke, sve tri duzine kljuca."""
    from Crypto.Cipher import AES as RefAES

    for key_size in aes.VALID_KEY_SIZES:
        for _ in range(50):
            key = aes.generate_keys(key_size)["key"]
            block = os.urandom(aes.BLOCK_SIZE)

            reference = RefAES.new(key, RefAES.MODE_ECB).encrypt(block)
            mine = aes.encrypt(block, key)
            assert mine == reference, (
                "AES-%d razlika: kljuc %s, blok %s" % (key_size, key.hex(), block.hex())
            )


def test_shift_rows_je_inverzibilan():
    state = list(range(16))
    assert aes._inv_shift_rows(aes._shift_rows(state)) == state


def test_mix_columns_je_inverzibilan():
    state = list(os.urandom(16))
    assert aes._inv_mix_columns(aes._mix_columns(state)) == state


def test_error_handling():
    key = aes.generate_keys(128)["key"]

    for bad_block in (b"", b"prekratko", b"x" * 17):
        try:
            aes.encrypt(bad_block, key)
        except ValueError:
            pass
        else:
            raise AssertionError("blok duzine %d je prosao bez greske" % len(bad_block))

    for bad_key in (b"", b"k" * 15, b"k" * 20, b"k" * 33):
        try:
            aes.encrypt(b"x" * 16, bad_key)
        except ValueError:
            pass
        else:
            raise AssertionError("kljuc duzine %d je prosao bez greske" % len(bad_key))

    try:
        aes.generate_keys(512)
    except ValueError:
        pass
    else:
        raise AssertionError("generate_keys(512) je prosao bez greske")


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
