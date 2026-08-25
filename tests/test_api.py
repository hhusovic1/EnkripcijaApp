"""
Provjera Flask API-ja (web/api.py) — svaka ruta koju frontend poziva.

Frontend je u TypeScriptu i provjerava se kompajlerom; ovdje se provjerava
strana koja stvarno radi kriptografiju.

Posebna pažnja na jednu stvar koju je lako previdjeti: veliki cijeli brojevi
(RSA modul, DH vrijednosti) moraju putovati kao STRINGOVI. JavaScript tip
number tačno predstavlja samo do 2^53, pa bi ih inače tiho zaokružio.

Pokreni: python tests/test_api.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web import create_app  # noqa: E402

klijent = create_app({"TESTING": True}).test_client()


def _post(putanja, telo=None):
    odgovor = klijent.post(putanja, json=telo or {})
    return odgovor.status_code, odgovor.get_json()


# ---------------------------------------------------------------------------
# Stranice
# ---------------------------------------------------------------------------

def test_sve_stranice_vracaju_200():
    for putanja in ("/", "/core", "/benchmark", "/demonstracije"):
        odgovor = klijent.get(putanja)
        assert odgovor.status_code == 200, "%s je vratio %d" % (putanja, odgovor.status_code)


def test_preuzimanje_csv():
    odgovor = klijent.get("/benchmark/results.csv")
    assert odgovor.status_code == 200
    assert b"algoritam" in odgovor.data[:200]


def test_preuzimanje_pdf():
    odgovor = klijent.get("/benchmark/rezultati.pdf")
    assert odgovor.status_code == 200
    assert odgovor.mimetype == "application/pdf"
    assert odgovor.data[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Simetricni algoritmi
# ---------------------------------------------------------------------------

def test_kljuc_i_sifrovanje_svih_simetricnih():
    for algoritam in ("des", "aes-128", "aes-192", "aes-256", "chacha20"):
        kod, kljuc = _post("/api/kljuc", {"algoritam": algoritam})
        assert kod == 200, "%s: generisanje kljuca vratilo %d" % (algoritam, kod)

        telo = {"algoritam": algoritam, "tekst": "Poruka sa šđčćž", **kljuc}
        kod, r = _post("/api/sifruj", telo)
        assert kod == 200, "%s: sifrovanje vratilo %d (%s)" % (algoritam, kod, r)
        assert r["ispravno"], "%s: dekripcija nije vratila original" % algoritam
        assert r["vraceno"] == "Poruka sa šđčćž"
        assert r["sifrat"]["hex"] and r["sifrat"]["base64"]


def test_3des():
    kod, kljuc = _post("/api/kljuc", {"algoritam": "3des"})
    assert kod == 200
    assert {"k1", "k2", "k3"} <= set(kljuc)

    kod, r = _post("/api/sifruj", {"algoritam": "3des", "tekst": "test", **kljuc})
    assert kod == 200 and r["ispravno"]
    assert r["dopuna"]["velicina_bloka"] == 8


def test_chacha_nema_dopunu_ni_iv():
    """Tokovna sifra ne dopunjuje - sifrat je iste duzine kao ulaz."""
    kod, kljuc = _post("/api/kljuc", {"algoritam": "chacha20"})
    tekst = "abcdefghij"
    kod, r = _post("/api/sifruj", {"algoritam": "chacha20", "tekst": tekst, **kljuc})

    assert kod == 200
    assert r["iv"] is None
    assert r["dopuna"] is None
    assert r["sifrat"]["duzina"] == len(tekst.encode())


def test_prazan_tekst_daje_gresku():
    kod, kljuc = _post("/api/kljuc", {"algoritam": "aes-128"})
    kod, r = _post("/api/sifruj", {"algoritam": "aes-128", "tekst": "", **kljuc})
    assert kod == 400
    assert "prazan" in r["greska"].lower()


def test_nepoznat_algoritam():
    kod, r = _post("/api/kljuc", {"algoritam": "izmisljeni"})
    assert kod == 400
    assert "Nepoznat" in r["greska"]


def test_neispravan_hex_kljuc():
    kod, r = _post("/api/sifruj", {"algoritam": "aes-128", "tekst": "x", "kljuc": "nijehex"})
    assert kod == 400
    assert "heksadecimalni" in r["greska"]


# ---------------------------------------------------------------------------
# RSA
# ---------------------------------------------------------------------------

def test_rsa_veliki_brojevi_su_stringovi():
    """
    Regresija koju je lako previdjeti: n i d prelaze 2^53, pa bi ih JavaScript
    kao broj zaokruzio i dekripcija bi tiho davala smece.
    """
    kod, k = _post("/api/rsa/kljuc", {"bita": 1024})
    assert kod == 200

    for polje in ("n", "e", "d", "p", "q", "phi"):
        assert isinstance(k[polje], str), "%s se salje kao %s" % (polje, type(k[polje]).__name__)

    assert int(k["n"]).bit_length() == 1024
    assert int(k["n"]) > 2 ** 53, "test nema smisla ako modul stane u number"


def test_rsa_ciklus():
    kod, k = _post("/api/rsa/kljuc", {"bita": 1024})
    kod, r = _post("/api/rsa/sifruj",
                   {"n": k["n"], "e": k["e"], "d": k["d"], "tekst": "tajna poruka"})
    assert kod == 200
    assert r["ispravno"] and r["vraceno"] == "tajna poruka"
    # Dekripcija je bitno sporija od enkripcije jer je e = 65537 (3.3.3)
    assert r["vrijeme_dekripcije_ms"] > r["vrijeme_enkripcije_ms"]


def test_rsa_predugacka_poruka():
    kod, k = _post("/api/rsa/kljuc", {"bita": 1024})
    kod, r = _post("/api/rsa/sifruj",
                   {"n": k["n"], "e": k["e"], "d": k["d"], "tekst": "x" * 500})
    assert kod == 400
    assert "hibridno" in r["greska"], "greska treba uputiti na hibridnu shemu"


def test_rsa_nevazeca_duzina():
    kod, r = _post("/api/rsa/kljuc", {"bita": 777})
    assert kod == 400


# ---------------------------------------------------------------------------
# ECDH
# ---------------------------------------------------------------------------

def test_ecdh():
    kod, r = _post("/api/ecdh/razmjena")
    assert kod == 200
    assert r["jednake"]
    assert r["tajna_alice"] == r["tajna_bob"]
    assert len(r["alice_javni"]) == 64  # 32 bajta u hexu

    kod, h = _post("/api/ecdh/hibridno", {"tajna": r["tajna_alice"], "tekst": "hibrid"})
    assert kod == 200
    assert h["ispravno"]
    assert len(h["izvedeni_kljuc"]) == 32  # AES-128 kljuc u hexu


# ---------------------------------------------------------------------------
# Napadi
# ---------------------------------------------------------------------------

def test_mitm_oba_scenarija():
    for scenario in ("bez_mallory", "sa_mallory"):
        kod, r = _post("/api/mitm", {"grupa": "demo", "scenario": scenario,
                                     "poruka": "poruka za test"})
        assert kod == 200, "%s vratio %d" % (scenario, kod)
        assert r["uspjeh"]
        assert len(r["koraci"]) >= 6
        assert [k["broj"] for k in r["koraci"]] == list(range(1, len(r["koraci"]) + 1))

        for korak in r["koraci"]:
            for stavka in korak["vrijednosti"]:
                assert isinstance(stavka["vrijednost"], str), (
                    "vrijednosti moraju biti stringovi zbog velikih brojeva"
                )


def test_mitm_prazna_poruka():
    kod, r = _post("/api/mitm", {"grupa": "demo", "scenario": "sa_mallory", "poruka": "  "})
    assert kod == 400


def test_mitm_nepoznata_grupa():
    kod, r = _post("/api/mitm", {"grupa": "izmisljena"})
    assert kod == 400


def test_wiener():
    kod, r = _post("/api/wiener", {"bita": 1024})
    assert kod == 200

    ranjivi, normalni = r["ranjivi"], r["normalni"]
    assert ranjivi["uspjeh"], "napad na ranjiv kljuc nije uspio"
    assert ranjivi["nadjeni_d"] == ranjivi["pravi_d"]
    assert ranjivi["procitano"] == ranjivi["poruka"]
    assert normalni["uspjeh"], "napad na normalan kljuc je 'uspio'"

    # Kontrast koji demonstracija treba pokazati
    assert ranjivi["ukupno_konvergenti"] > normalni["ukupno_konvergenti"] * 5

    for korak in ranjivi["koraci"]:
        assert isinstance(korak["k"], str) and isinstance(korak["d"], str)
        assert korak["razlog"]


def _run_all():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - test runner namjerno hvata sve
            failed += 1
            print("FAIL  %s\n      %s: %s" % (test.__name__, type(exc).__name__, str(exc)[:300]))
        else:
            print("ok    %s" % test.__name__)
    print("\n%d/%d testova proslo" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
