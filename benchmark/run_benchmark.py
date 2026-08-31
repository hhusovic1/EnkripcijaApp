
import argparse
import os
import statistics
import sys
import time

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import aes, chacha, des, ecc, modes, rsa  # noqa: E402

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.csv")

# Velicine podataka u bajtovima. Rucne implementacije idu do 64 KB - na ~50 KB/s
# koliko postize cisti Python, 1 MB bi trajalo pola minute po jednom ponavljanju.
SIZES_RUCNI = [64, 256, 1_024, 4_096, 16_384, 65_536]
SIZES_BIBLIOTEKA = [1_024, 4_096, 10_000, 100_000, 1_000_000, 10_000_000]

AES_KEY_SIZES = [128, 192, 256]
RSA_KEY_SIZES = [1024, 2048, 3072, 4096]

# Velicina na kojoj se pravi direktno poredjenje svih algoritama (bar chart).
# Bira se mala da bi i rucne implementacije bile mjerljive u razumnom vremenu.
POREDBENA_VELICINA = 4_096

MIN_PONAVLJANJA = 5
MAX_PONAVLJANJA = 50
DEFAULT_BUDGET = 2.0  # sekundi po mjernoj tacki


# ---------------------------------------------------------------------------
# Mjerenje
# ---------------------------------------------------------------------------

def izmjeri(func, *args, budget=DEFAULT_BUDGET, min_rep=MIN_PONAVLJANJA,
            max_rep=MAX_PONAVLJANJA) -> dict:

    func(*args)  # zagrijavanje - prvi poziv placa import/alokacije/cache

    times = []
    start_ukupno = time.perf_counter()
    while True:
        start = time.perf_counter()
        func(*args)
        times.append(time.perf_counter() - start)

        if len(times) >= max_rep:
            break
        if len(times) >= min_rep and (time.perf_counter() - start_ukupno) >= budget:
            break

    return {
        "ponavljanja": len(times),
        "srednje_vrijeme_s": statistics.mean(times),
        "std_dev_s": statistics.stdev(times) if len(times) > 1 else 0.0,
        "min_vrijeme_s": min(times),
    }


def zapisi(rezultati, algoritam, kategorija, operacija, mjerenje,
           velicina_bajta=None, duzina_kljuca_bita=None):
    """Dodaje jedan red u rezultate, uz izvedenu propusnost."""
    propusnost = None
    if velicina_bajta and mjerenje["srednje_vrijeme_s"] > 0:
        propusnost = (velicina_bajta / mjerenje["srednje_vrijeme_s"]) / (1024 * 1024)

    rezultati.append({
        "algoritam": algoritam,
        "kategorija": kategorija,
        "operacija": operacija,
        "velicina_bajta": velicina_bajta,
        "duzina_kljuca_bita": duzina_kljuca_bita,
        "ponavljanja": mjerenje["ponavljanja"],
        "srednje_vrijeme_s": mjerenje["srednje_vrijeme_s"],
        "std_dev_s": mjerenje["std_dev_s"],
        "min_vrijeme_s": mjerenje["min_vrijeme_s"],
        "propusnost_mb_s": propusnost,
    })

    opis = algoritam
    if velicina_bajta:
        opis += "  %8d B" % velicina_bajta
    print("  %-28s %-18s %9.4f s  +/- %.4f  (n=%d)" % (
        opis, operacija, mjerenje["srednje_vrijeme_s"], mjerenje["std_dev_s"],
        mjerenje["ponavljanja"],
    ))



def mjeri_blokovsku_sifru(rezultati, naziv, kategorija, encrypt_block, decrypt_block,
                          block_size, velicine, duzina_kljuca, budget):
    """Zajednicko mjerenje za DES/3DES/AES u CBC rezimu (padding ukljucen)."""
    for velicina in velicine:
        podaci = os.urandom(velicina)

        mjerenje = izmjeri(
            lambda: modes.cbc_encrypt(podaci, encrypt_block, block_size),
            budget=budget,
        )
        zapisi(rezultati, naziv, kategorija, "enkripcija", mjerenje,
               velicina, duzina_kljuca)

        iv, sifrat = modes.cbc_encrypt(podaci, encrypt_block, block_size)
        mjerenje = izmjeri(
            lambda: modes.cbc_decrypt(sifrat, decrypt_block, block_size, iv),
            budget=budget,
        )
        zapisi(rezultati, naziv, kategorija, "dekripcija", mjerenje,
               velicina, duzina_kljuca)


def mjeri_des(rezultati, velicine, budget):
    print("\nDES (rucna implementacija)")
    kljuc = des.generate_keys()["key"]
    mjeri_blokovsku_sifru(
        rezultati, "DES", "simetricni-rucni",
        lambda b: des.encrypt(b, kljuc),
        lambda b: des.decrypt(b, kljuc),
        des.BLOCK_SIZE, velicine, 56, budget,
    )
    zapisi(rezultati, "DES", "simetricni-rucni", "generisanje_kljuca",
           izmjeri(des.generate_keys, budget=budget), None, 56)


def mjeri_3des(rezultati, velicine, budget):
    print("\n3DES (rucna implementacija, opcija 1 - tri nezavisna kljuca)")
    k = des.generate_keys_3des(keying_option=1)
    mjeri_blokovsku_sifru(
        rezultati, "3DES", "simetricni-rucni",
        lambda b: des.encrypt_3des(b, k["k1"], k["k2"], k["k3"]),
        lambda b: des.decrypt_3des(b, k["k1"], k["k2"], k["k3"]),
        des.BLOCK_SIZE, velicine, 168, budget,
    )
    zapisi(rezultati, "3DES", "simetricni-rucni", "generisanje_kljuca",
           izmjeri(des.generate_keys_3des, budget=budget), None, 168)


def mjeri_aes(rezultati, velicine, budget):
    for duzina in AES_KEY_SIZES:
        naziv = "AES-%d" % duzina
        print("\n%s (rucna implementacija)" % naziv)
        kljuc = aes.generate_keys(duzina)["key"]
        mjeri_blokovsku_sifru(
            rezultati, naziv, "simetricni-rucni",
            lambda b: aes.encrypt(b, kljuc),
            lambda b: aes.decrypt(b, kljuc),
            aes.BLOCK_SIZE, velicine, duzina, budget,
        )
        zapisi(rezultati, naziv, "simetricni-rucni", "generisanje_kljuca",
               izmjeri(aes.generate_keys, duzina, budget=budget), None, duzina)


def mjeri_aes_biblioteka(rezultati, velicine, budget):

    from Crypto.Cipher import AES as RefAES

    print("\nAES-128 (biblioteka, pycryptodome)")
    kljuc = os.urandom(16)
    for velicina in velicine:
        podaci = os.urandom(velicina)

        def enkriptuj():
            cipher = RefAES.new(kljuc, RefAES.MODE_CBC)
            return cipher.encrypt(modes.pkcs7_pad(podaci, 16))

        mjerenje = izmjeri(enkriptuj, budget=budget)
        zapisi(rezultati, "AES-128 (biblioteka)", "simetricni-biblioteka",
               "enkripcija", mjerenje, velicina, 128)

        cipher = RefAES.new(kljuc, RefAES.MODE_CBC)
        iv, sifrat = cipher.iv, cipher.encrypt(modes.pkcs7_pad(podaci, 16))
        mjerenje = izmjeri(
            lambda: RefAES.new(kljuc, RefAES.MODE_CBC, iv=iv).decrypt(sifrat),
            budget=budget,
        )
        zapisi(rezultati, "AES-128 (biblioteka)", "simetricni-biblioteka",
               "dekripcija", mjerenje, velicina, 128)


def mjeri_chacha(rezultati, velicine, budget):
    print("\nChaCha20 (biblioteka, pycryptodome)")
    k = chacha.generate_keys()
    for velicina in velicine:
        podaci = os.urandom(velicina)

        mjerenje = izmjeri(chacha.encrypt, podaci, k["key"], k["nonce"], budget=budget)
        zapisi(rezultati, "ChaCha20", "simetricni-biblioteka", "enkripcija",
               mjerenje, velicina, 256)

        sifrat = chacha.encrypt(podaci, k["key"], k["nonce"])
        mjerenje = izmjeri(chacha.decrypt, sifrat, k["key"], k["nonce"], budget=budget)
        zapisi(rezultati, "ChaCha20", "simetricni-biblioteka", "dekripcija",
               mjerenje, velicina, 256)

    zapisi(rezultati, "ChaCha20", "simetricni-biblioteka", "generisanje_kljuca",
           izmjeri(chacha.generate_keys, budget=budget), None, 256)


def mjeri_rsa(rezultati, budget, keygen_budget):

    for duzina in RSA_KEY_SIZES:
        naziv = "RSA-%d" % duzina
        print("\n%s (rucna implementacija)" % naziv)

        mjerenje = izmjeri(rsa.generate_keys, duzina,
                           budget=keygen_budget, min_rep=3, max_rep=10)
        zapisi(rezultati, naziv, "asimetricni", "generisanje_kljuca",
               mjerenje, None, duzina)

        kljucevi = rsa.generate_keys(duzina)
        blok = os.urandom(rsa.max_message_bytes(kljucevi["public"][0]))

        mjerenje = izmjeri(rsa.encrypt_bytes, blok, kljucevi["public"], budget=budget)
        zapisi(rezultati, naziv, "asimetricni", "enkripcija", mjerenje,
               len(blok), duzina)

        sifrat = rsa.encrypt_bytes(blok, kljucevi["public"])
        mjerenje = izmjeri(rsa.decrypt_bytes, sifrat, kljucevi["private"], budget=budget)
        zapisi(rezultati, naziv, "asimetricni", "dekripcija", mjerenje,
               len(blok), duzina)


def mjeri_ecdh(rezultati, budget):

    print("\nECDH / X25519 (biblioteka, cryptography)")
    zapisi(rezultati, "ECDH (X25519)", "asimetricni", "generisanje_kljuca",
           izmjeri(ecc.generate_keys, budget=budget), None, 256)

    alice = ecc.generate_keys()
    bob = ecc.generate_keys()
    mjerenje = izmjeri(ecc.derive_shared_secret, alice["private"], bob["public"],
                       budget=budget)
    zapisi(rezultati, "ECDH (X25519)", "asimetricni", "razmjena_kljuca",
           mjerenje, None, 256)


def run_all(quick=False, budget=DEFAULT_BUDGET):
    if quick:
        # Poredbena velicina mora ostati u obje liste da bar chart ima
        # zajednicku tacku za sve algoritme.
        velicine_rucni = [64, POREDBENA_VELICINA]
        velicine_biblioteka = [POREDBENA_VELICINA, 100_000]
        budget = 0.2
        keygen_budget = 0.2
    else:
        velicine_rucni = SIZES_RUCNI
        velicine_biblioteka = SIZES_BIBLIOTEKA
        keygen_budget = max(budget, 5.0)

    print("=" * 78)
    print("Benchmark enkripcijskih algoritama%s" % ("  [QUICK]" if quick else ""))
    print("Budzet po mjernoj tacki: %.1fs   ponavljanja: %d-%d"
          % (budget, MIN_PONAVLJANJA, MAX_PONAVLJANJA))
    print("=" * 78)

    start = time.perf_counter()
    rezultati = []

    mjeri_des(rezultati, velicine_rucni, budget)
    mjeri_3des(rezultati, velicine_rucni, budget)
    mjeri_aes(rezultati, velicine_rucni, budget)
    mjeri_aes_biblioteka(rezultati, velicine_biblioteka, budget)
    mjeri_chacha(rezultati, velicine_biblioteka, budget)
    mjeri_rsa(rezultati, budget, keygen_budget)
    mjeri_ecdh(rezultati, budget)

    df = pd.DataFrame(rezultati)
    df.to_csv(RESULTS_PATH, index=False)

    print("\n" + "=" * 78)
    print("Zapisano %d mjerenja u %s" % (len(df), RESULTS_PATH))
    print("Ukupno trajanje: %.1f s" % (time.perf_counter() - start))
    print("=" * 78)
    return df


def main():
    parser = argparse.ArgumentParser(description="Benchmark enkripcijskih algoritama")
    parser.add_argument("--quick", action="store_true",
                        help="brzo mjerenje s malo tacaka, za provjeru da harness radi")
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET,
                        help="vremenski budzet po mjernoj tacki u sekundama")
    args = parser.parse_args()

    run_all(quick=args.quick, budget=args.budget)


if __name__ == "__main__":
    main()
