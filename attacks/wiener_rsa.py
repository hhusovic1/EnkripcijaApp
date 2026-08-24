"""
Wienerov napad na RSA s malim privatnim eksponentom. Vidi thesis 3.3.6.

core/rsa.py vec ima wiener_attack() koji samo vrati d ili None. Ovdje je isti
postupak, ali s biljezenjem svakog koraka - da se u aplikaciji vidi kako napad
zapravo radi, a ne samo da je uspio.

Ideja napada: iz e*d = 1 (mod phi) slijedi da je k/d jedna od konvergenti
razvoja e/n u verizni razlomak. Napadac redom prolazi konvergente i za svaku
provjerava da li daje smislen phi - onaj kod kojeg jednacina

    x^2 - (n - phi + 1)x + n = 0

ima dva cjelobrojna rjesenja (to su p i q). Cim se to poklopi, d je pogodjen.
Faktorizacija n nije potrebna, sto je i poenta: mali d rusi RSA bez razbijanja
problema na kojem RSA pociva.

Pokreni:
    python attacks/wiener_rsa.py
    python attacks/wiener_rsa.py --bita 2048
"""
import argparse
import math
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import rsa  # noqa: E402

# Koliko konvergenti najvise pregledati prije odustajanja. Kod ranjivog kljuca
# se rjesenje nadje medju prvih nekoliko desetina; kod normalnog ih nema uopste.
MAKS_KONVERGENTI = 5000


def napadni(public_key: tuple, maks_konvergenti: int = MAKS_KONVERGENTI) -> dict:
    """
    Pokusava rekonstruisati d iz (n, e) i biljezi svaki pregledani kandidat.

    Vraca dict s pronadjenim d (ili None), listom koraka i statistikom.
    """
    n, e = public_key
    start = time.perf_counter()

    koraci = []
    pronadjeno = None
    kvocijenti = rsa._continued_fraction(e, n)

    for redni_broj, (k, d) in enumerate(rsa._convergents(kvocijenti), start=1):
        if redni_broj > maks_konvergenti:
            break

        korak = {
            "broj": redni_broj,
            "k": k,
            "d": d,
            "phi": None,
            "razlog": None,
            "uspjeh": False,
        }

        if k == 0 or d == 0:
            korak["razlog"] = "k ili d je nula - konvergenta se preskace"
            koraci.append(korak)
            continue

        if (e * d - 1) % k != 0:
            korak["razlog"] = "(e·d − 1) nije djeljivo sa k, pa phi ne bi bio cio broj"
            koraci.append(korak)
            continue

        phi = (e * d - 1) // k
        korak["phi"] = phi

        suma_pq = n - phi + 1
        diskriminanta = suma_pq * suma_pq - 4 * n

        if diskriminanta < 0:
            korak["razlog"] = "diskriminanta je negativna - nema realnih rjesenja"
            koraci.append(korak)
            continue

        korijen = math.isqrt(diskriminanta)
        if korijen * korijen != diskriminanta:
            korak["razlog"] = "diskriminanta nije potpun kvadrat - p i q ne bi bili cijeli"
            koraci.append(korak)
            continue

        if (suma_pq + korijen) % 2 != 0:
            korak["razlog"] = "p i q ne bi ispali cijeli brojevi"
            koraci.append(korak)
            continue

        # Pogodak: konvergenta daje ispravan phi, pa je d pronadjen
        p = (suma_pq + korijen) // 2
        q = (suma_pq - korijen) // 2
        korak["razlog"] = "poklopilo se - phi je cio, diskriminanta potpun kvadrat"
        korak["uspjeh"] = True
        korak["p"] = p
        korak["q"] = q
        koraci.append(korak)
        pronadjeno = d
        break

    return {
        "d": pronadjeno,
        "koraci": koraci,
        "pregledano_konvergenti": len(koraci),
        "ukupno_konvergenti": len(kvocijenti),
        "trajanje_s": time.perf_counter() - start,
        "kvocijenti": kvocijenti,
    }


def demonstracija(bita: int = 1024) -> dict:
    """
    Puna demonstracija: ranjiv kljuc se probije, normalan ne.

    Vraca sve sto aplikaciji treba za prikaz oba slucaja jedan pored drugog.
    """
    ranjivi = rsa.generate_vulnerable_keys(bita)
    n_r, e_r = ranjivi["public"]
    pravi_d = ranjivi["private"][1]

    napad_ranjivi = napadni(ranjivi["public"])

    # Dokaz da rekonstruisani d stvarno radi - napadac sada moze desifrovati
    poruka = b"poruka koju je vlasnik kljuca smatrao sigurnom"
    sifrat = rsa.encrypt_bytes(poruka, ranjivi["public"])
    procitano = None
    if napad_ranjivi["d"] is not None:
        try:
            procitano = rsa.decrypt_bytes(sifrat, (n_r, napad_ranjivi["d"]))
        except ValueError:
            procitano = None

    normalni = rsa.generate_keys(bita)
    napad_normalni = napadni(normalni["public"])

    return {
        "bita": bita,
        "ranjivi": {
            "kljucevi": ranjivi,
            "n": n_r,
            "e": e_r,
            "pravi_d": pravi_d,
            "granica": math.isqrt(math.isqrt(n_r)) // 3,
            "napad": napad_ranjivi,
            "poruka": poruka,
            "sifrat": sifrat,
            "procitano": procitano,
            "uspjeh": napad_ranjivi["d"] == pravi_d and procitano == poruka,
        },
        "normalni": {
            "kljucevi": normalni,
            "n": normalni["public"][0],
            "e": normalni["public"][1],
            "pravi_d": normalni["private"][1],
            "napad": napad_normalni,
            "uspjeh": napad_normalni["d"] is None,
        },
    }


# ---------------------------------------------------------------------------
# Ispis u terminalu
# ---------------------------------------------------------------------------

def skrati(vrijednost, maks=60) -> str:
    tekst = str(vrijednost)
    if len(tekst) <= maks:
        return tekst
    return "%s...%s  (%d cifara)" % (tekst[:24], tekst[-10:], len(tekst))


def ispisi(rezultat):
    r = rezultat["ranjivi"]
    nrm = rezultat["normalni"]

    print("\n" + "=" * 78)
    print("WIENEROV NAPAD - ranjiv kljuc (namjerno mali d), %d bita" % rezultat["bita"])
    print("=" * 78)
    print("  n                 %s" % skrati(r["n"]))
    print("  e                 %s" % skrati(r["e"]))
    print("  d (tajni)         %s  [%d bita]" % (skrati(r["pravi_d"]), r["pravi_d"].bit_length()))
    print("  Wienerova granica %s  [d mora biti manji od ovoga]" % skrati(r["granica"]))
    print("\n  Napadac zna samo n i e. Prolazi konvergente razvoja e/n:")

    for korak in r["napad"]["koraci"][-6:]:
        oznaka = "  <-- POGODAK" if korak["uspjeh"] else ""
        print("    #%-3d k=%-14s d=%s%s"
              % (korak["broj"], skrati(korak["k"], 12), skrati(korak["d"], 24), oznaka))
        if not korak["uspjeh"]:
            print("         odbaceno: %s" % korak["razlog"])

    print("\n  Pregledano konvergenti: %d od %d"
          % (r["napad"]["pregledano_konvergenti"], r["napad"]["ukupno_konvergenti"]))
    print("  Trajanje:               %.4f s" % r["napad"]["trajanje_s"])
    print("  Rekonstruisan d:        %s" % skrati(r["napad"]["d"]))
    print("  Poklapa se s pravim d:  %s" % (r["napad"]["d"] == r["pravi_d"]))
    print("\n  Posljedica - napadac cita poruku:")
    print("    poslano:   %s" % r["poruka"].decode())
    print("    procitano: %s" % (r["procitano"].decode() if r["procitano"] else "-"))

    print("\n" + "=" * 78)
    print("KONTROLA - normalan kljuc (e = 65537, d pune duzine)")
    print("=" * 78)
    granica = math.isqrt(math.isqrt(nrm["n"])) // 3
    print("  d ima %d bita; Wienerova granica je %d bita, dakle d je daleko iznad nje"
          % (nrm["pravi_d"].bit_length(), granica.bit_length()))
    print("  Razvoj e/n ima svega %d konvergenti (kod ranjivog kljuca ih ima stotine),"
          % nrm["napad"]["ukupno_konvergenti"])
    print("  jer je e = 65537 sicusan u odnosu na n - pa napad odmah ostane bez kandidata.")
    print("  Pregledano konvergenti: %d" % nrm["napad"]["pregledano_konvergenti"])
    print("  Trajanje:               %.4f s" % nrm["napad"]["trajanje_s"])
    print("  Rezultat:               %s"
          % ("nije pronadjen d - napad ne uspijeva" if nrm["napad"]["d"] is None
             else "NEOCEKIVANO: %s" % nrm["napad"]["d"]))

    print("\nZakljucak (3.3.6): napad ne faktorise n niti razbija RSA kao takav.")
    print("Ranjiv je iskljucivo izbor malog d. Zato se d uvijek generise kao")
    print("vrijednost uporediva po velicini s n, a e se fiksira na 65537.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Wienerov napad na RSA")
    parser.add_argument("--bita", type=int, default=1024, choices=rsa.VALID_KEY_SIZES)
    args = parser.parse_args()

    ispisi(demonstracija(args.bita))


if __name__ == "__main__":
    main()
