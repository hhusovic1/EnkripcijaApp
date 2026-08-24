"""
Pokrece sve test module odjednom.

Pokreni: python tests/run_all.py
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import test_aes  # noqa: E402
import test_des  # noqa: E402
import test_mitm  # noqa: E402
import test_modes  # noqa: E402
import test_plot  # noqa: E402
import test_rsa  # noqa: E402

MODULI = [
    ("DES / 3DES", test_des),
    ("AES", test_aes),
    ("RSA", test_rsa),
    ("Padding / CBC / ECC / ChaCha20", test_modes),
    ("MITM na Diffie-Hellman", test_mitm),
    ("Grafovi", test_plot),
]


def main():
    ukupno_neuspjelih = 0
    start = time.perf_counter()

    for naziv, modul in MODULI:
        print("\n=== %s ===" % naziv)
        ukupno_neuspjelih += modul._run_all()

    print("\n%s" % ("-" * 50))
    if ukupno_neuspjelih:
        print("NEUSPJESNO - %d modula ima greske" % ukupno_neuspjelih)
    else:
        print("Sve prolazi (%.1fs)" % (time.perf_counter() - start))
    return ukupno_neuspjelih


if __name__ == "__main__":
    sys.exit(main())
