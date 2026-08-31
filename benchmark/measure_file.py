"""
Mjerenje algoritama nad proizvoljnim podacima koje korisnik ucita.

Za razliku od run_benchmark.py, koji mjeri nasumicne podatke unaprijed zadanih
velicina i sluzi za grafove u radu, ovaj modul mjeri JEDAN konkretan ulaz -
korisnikov fajl - i uz vrijeme provjerava da se dekripcijom dobije bajt po bajt
isti sadrzaj.

Koristi ga Streamlit stranica "Mjeri svoj fajl". Moze i samostalno:

    python benchmark/measure_file.py neki_fajl.pdf
    python benchmark/measure_file.py neki_fajl.pdf --algoritmi AES-128 ChaCha20
"""
import argparse
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import aes, chacha, des, modes, rsa  # noqa: E402

# Ručne implementacije u cistom Pythonu su reda 50 KB/s, pa velike fajlove
# jednostavno ne stignu obraditi u interaktivnom vremenu.
LIMIT_RUCNI = 1024 * 1024  # 1 MB
LIMIT_BIBLIOTEKA = 64 * 1024 * 1024  # 64 MB


class Algoritam:


    def __init__(self, naziv, kategorija, opis, pripremi):
        self.naziv = naziv
        self.kategorija = kategorija
        self.opis = opis
        self._pripremi = pripremi

    @property
    def limit_bajtova(self) -> int:
        return LIMIT_RUCNI if self.kategorija == "simetricni-rucni" else LIMIT_BIBLIOTEKA

    def pripremi(self):

        return self._pripremi()


def _cbc_algoritam(encrypt_block, decrypt_block, block_size):


    def enkriptuj(podaci, on_progress=None):
        iv, sifrat = modes.cbc_encrypt(podaci, encrypt_block, block_size,
                                       on_progress=on_progress)
        return iv + sifrat

    def dekriptuj(blob, on_progress=None):
        return modes.cbc_decrypt(blob[block_size:], decrypt_block, block_size,
                                 blob[:block_size], on_progress=on_progress)

    return enkriptuj, dekriptuj


def _pripremi_des():
    kljuc = des.generate_keys()["key"]
    enkriptuj, dekriptuj = _cbc_algoritam(
        lambda b: des.encrypt(b, kljuc), lambda b: des.decrypt(b, kljuc), des.BLOCK_SIZE
    )
    return enkriptuj, dekriptuj, "56-bitni ključ (+8 bita pariteta), CBC"


def _pripremi_3des():
    k = des.generate_keys_3des(keying_option=1)
    enkriptuj, dekriptuj = _cbc_algoritam(
        lambda b: des.encrypt_3des(b, k["k1"], k["k2"], k["k3"]),
        lambda b: des.decrypt_3des(b, k["k1"], k["k2"], k["k3"]),
        des.BLOCK_SIZE,
    )
    return enkriptuj, dekriptuj, "3 × 56 bita (opcija 1), EDE shema, CBC"


def _pripremi_aes(duzina):
    def pripremi():
        kljuc = aes.generate_keys(duzina)["key"]
        enkriptuj, dekriptuj = _cbc_algoritam(
            lambda b: aes.encrypt(b, kljuc), lambda b: aes.decrypt(b, kljuc),
            aes.BLOCK_SIZE,
        )
        return enkriptuj, dekriptuj, "%d-bitni ključ, %d rundi, CBC" % (
            duzina, aes.ROUNDS[duzina]
        )

    return pripremi


def _pripremi_aes_biblioteka():
    from Crypto.Cipher import AES as RefAES

    kljuc = os.urandom(16)

    def enkriptuj(podaci, on_progress=None):
        cipher = RefAES.new(kljuc, RefAES.MODE_CBC)
        return cipher.iv + cipher.encrypt(modes.pkcs7_pad(podaci, 16))

    def dekriptuj(blob, on_progress=None):
        cipher = RefAES.new(kljuc, RefAES.MODE_CBC, iv=blob[:16])
        return modes.pkcs7_unpad(cipher.decrypt(blob[16:]), 16)

    return enkriptuj, dekriptuj, "128-bitni ključ, CBC (pycryptodome, C kod)"


def _pripremi_chacha():
    k = chacha.generate_keys()

    def enkriptuj(podaci, on_progress=None):
        return k["nonce"] + chacha.encrypt(podaci, k["key"], k["nonce"])

    def dekriptuj(blob, on_progress=None):
        return chacha.decrypt(blob[12:], k["key"], blob[:12])

    return enkriptuj, dekriptuj, "256-bitni ključ, 96-bitni nonce (točna šifra)"


def _pripremi_hibridni(rsa_bita=2048):


    def pripremi():
        rsa_kljucevi = rsa.generate_keys(rsa_bita)

        def enkriptuj(podaci, on_progress=None):
            sesijski_kljuc = os.urandom(16)
            omot = rsa.encrypt_bytes(sesijski_kljuc, rsa_kljucevi["public"])
            iv, sifrat = modes.cbc_encrypt(
                podaci, lambda b: aes.encrypt(b, sesijski_kljuc), aes.BLOCK_SIZE,
                on_progress=on_progress,
            )
            return omot + iv + sifrat

        def dekriptuj(blob, on_progress=None):
            duzina_omota = (rsa_kljucevi["public"][0].bit_length() + 7) // 8
            sesijski_kljuc = rsa.decrypt_bytes(blob[:duzina_omota], rsa_kljucevi["private"])
            iv = blob[duzina_omota: duzina_omota + aes.BLOCK_SIZE]
            return modes.cbc_decrypt(
                blob[duzina_omota + aes.BLOCK_SIZE:],
                lambda b: aes.decrypt(b, sesijski_kljuc), aes.BLOCK_SIZE, iv,
                on_progress=on_progress,
            )

        return enkriptuj, dekriptuj, (
            "RSA-%d štiti 128-bitni AES sesijski ključ, AES-128 CBC štiti sadržaj"
            % rsa_bita
        )

    return pripremi


ALGORITMI = [
    Algoritam("DES", "simetricni-rucni", "Ručna implementacija", _pripremi_des),
    Algoritam("3DES", "simetricni-rucni", "Ručna implementacija", _pripremi_3des),
    Algoritam("AES-128", "simetricni-rucni", "Ručna implementacija", _pripremi_aes(128)),
    Algoritam("AES-192", "simetricni-rucni", "Ručna implementacija", _pripremi_aes(192)),
    Algoritam("AES-256", "simetricni-rucni", "Ručna implementacija", _pripremi_aes(256)),
    Algoritam("RSA-2048 + AES-128 (hibridno)", "simetricni-rucni",
              "Ručna implementacija, shema iz 3.5.3", _pripremi_hibridni(2048)),
    Algoritam("AES-128 (biblioteka)", "simetricni-biblioteka",
              "pycryptodome, optimizovani C kod", _pripremi_aes_biblioteka),
    Algoritam("ChaCha20", "simetricni-biblioteka",
              "pycryptodome, optimizovani C kod", _pripremi_chacha),
]

PO_NAZIVU = {a.naziv: a for a in ALGORITMI}



def izmjeri(podaci: bytes, naziv: str, on_progress=None) -> dict:

    algoritam = PO_NAZIVU.get(naziv)
    if algoritam is None:
        raise KeyError("Nepoznat algoritam: %r" % naziv)

    if len(podaci) > algoritam.limit_bajtova:
        raise ValueError(
            "%s može obraditi najviše %s, a traženo je %s"
            % (naziv, formatiraj_velicinu(algoritam.limit_bajtova),
               formatiraj_velicinu(len(podaci)))
        )

    enkriptuj, dekriptuj, opis_kljuca = algoritam.pripremi()

    def napredak_enc(obradjeno, ukupno):
        if on_progress:
            on_progress("enkripcija", obradjeno / ukupno if ukupno else 1.0)

    def napredak_dec(obradjeno, ukupno):
        if on_progress:
            on_progress("dekripcija", obradjeno / ukupno if ukupno else 1.0)

    start = time.perf_counter()
    sifrat = enkriptuj(podaci, on_progress=napredak_enc)
    vrijeme_enc = time.perf_counter() - start

    start = time.perf_counter()
    vraceno = dekriptuj(sifrat, on_progress=napredak_dec)
    vrijeme_dec = time.perf_counter() - start

    return {
        "algoritam": naziv,
        "kategorija": algoritam.kategorija,
        "opis_kljuca": opis_kljuca,
        "velicina_bajta": len(podaci),
        "velicina_sifrata": len(sifrat),
        "vrijeme_enkripcije_s": vrijeme_enc,
        "vrijeme_dekripcije_s": vrijeme_dec,
        "propusnost_enc_mb_s": (len(podaci) / vrijeme_enc) / (1024 * 1024) if vrijeme_enc else None,
        "propusnost_dec_mb_s": (len(podaci) / vrijeme_dec) / (1024 * 1024) if vrijeme_dec else None,
        "ispravno": vraceno == podaci,
    }



ZAMJENA_ZA_PROCJENU = {
    "RSA-2048 + AES-128 (hibridno)": "AES-128",
}


def procijeni_trajanje(naziv: str, velicina: int, propusnosti: dict) -> float:

    propusnost = propusnosti.get(naziv)
    if not propusnost:
        propusnost = propusnosti.get(ZAMJENA_ZA_PROCJENU.get(naziv, ""))
    if not propusnost:
        return None
    sekundi_enc = (velicina / (1024 * 1024)) / propusnost
    return sekundi_enc * 2.2  # dekripcija je po pravilu nesto sporija od enkripcije


def formatiraj_velicinu(bajtova: int) -> str:
    for jedinica, prag in (("MB", 1024 * 1024), ("KB", 1024)):
        if bajtova >= prag:
            return "%.1f %s" % (bajtova / prag, jedinica)
    return "%d B" % bajtova


def formatiraj_vrijeme(sekunde: float) -> str:
    if sekunde is None:
        return "-"
    if sekunde >= 60:
        return "%d min %d s" % (int(sekunde // 60), int(sekunde % 60))
    if sekunde >= 1:
        return "%.2f s" % sekunde
    if sekunde >= 1e-3:
        return "%.1f ms" % (sekunde * 1e3)
    return "%.0f µs" % (sekunde * 1e6)


def main():
    # Windows konzola je podrazumijevano cp1252, pa bi "µs" ispao kao smece
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Mjeri algoritme nad konkretnim fajlom")
    parser.add_argument("fajl")
    parser.add_argument("--algoritmi", nargs="*", default=None,
                        help="podskup algoritama (podrazumijevano: svi koji stanu")
    args = parser.parse_args()

    with open(args.fajl, "rb") as f:
        podaci = f.read()

    print("Fajl: %s (%s)\n" % (args.fajl, formatiraj_velicinu(len(podaci))))
    print("%-34s %12s %12s %10s" % ("algoritam", "enkripcija", "dekripcija", "ispravno"))
    print("-" * 72)

    nazivi = args.algoritmi or [a.naziv for a in ALGORITMI]
    for naziv in nazivi:
        algoritam = PO_NAZIVU.get(naziv)
        if algoritam is None:
            print("%-34s  nepoznat algoritam" % naziv)
            continue
        if len(podaci) > algoritam.limit_bajtova:
            print("%-34s  preskočen (fajl veći od %s)"
                  % (naziv, formatiraj_velicinu(algoritam.limit_bajtova)))
            continue

        rezultat = izmjeri(podaci, naziv)
        print("%-34s %12s %12s %10s" % (
            naziv,
            formatiraj_vrijeme(rezultat["vrijeme_enkripcije_s"]),
            formatiraj_vrijeme(rezultat["vrijeme_dekripcije_s"]),
            "da" if rezultat["ispravno"] else "NE",
        ))


if __name__ == "__main__":
    main()
