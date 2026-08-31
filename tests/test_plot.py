
import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
KORIJEN = os.path.dirname(HERE)
sys.path.insert(0, KORIJEN)
sys.path.insert(0, os.path.join(KORIJEN, "benchmark"))

import pandas as pd  # noqa: E402

import plot_results  # noqa: E402

CSV = os.path.join(KORIJEN, "benchmark", "results.csv")


def _podaci() -> pd.DataFrame:
    if not os.path.exists(CSV):
        raise RuntimeError(
            "Nema benchmark/results.csv - prvo pokreni "
            "'python benchmark/run_benchmark.py --quick'"
        )
    return pd.read_csv(CSV)


def test_sva_tri_grafa_se_nacrtaju():
    df = _podaci()
    for funkcija in (plot_results.graf_vrijeme_vs_velicina,
                     plot_results.graf_generisanje_kljuca,
                     plot_results.graf_poredjenje):
        slika = plot_results.u_sliku(funkcija(df))
        assert slika.startswith(b"\x89PNG"), "%s nije dala PNG" % funkcija.__name__
        assert len(slika) > 5000, "%s je dala sumnjivo malu sliku" % funkcija.__name__


def test_crtanje_iz_vise_niti():
    """
    Regresija na ParseException iz mathtext parsera. Bez zakljucavanja u
    plot_results ovaj test pada u velikoj vecini pokretanja.
    """
    df = _podaci()
    funkcije = [
        plot_results.graf_vrijeme_vs_velicina,
        plot_results.graf_generisanje_kljuca,
        plot_results.graf_poredjenje,
    ]

    greske = []
    velicine = []
    brava = threading.Lock()

    def radnik(funkcija):
        try:
            slika = plot_results.u_sliku(funkcija(df))
            with brava:
                velicine.append(len(slika))
        except Exception as exc:  # noqa: BLE001 - test bas hvata sve greske
            with brava:
                greske.append("%s: %s: %s" % (funkcija.__name__, type(exc).__name__, exc))

    niti = [threading.Thread(target=radnik, args=(f,)) for f in funkcije * 4]
    for nit in niti:
        nit.start()
    for nit in niti:
        nit.join(timeout=120)

    assert not greske, "crtanje iz vise niti je puklo:\n  " + "\n  ".join(greske)
    assert len(velicine) == len(niti), "nisu sve niti zavrsile"


def test_oznake_osa_nisu_mathtext():
    """
    Oznake na log skali moraju biti obican tekst ("10 KB", "1 ms"), a ne
    mathtext ("$10^{4}$") - i zbog citljivosti i zbog gornje greske.
    """
    assert plot_results.formatiraj_bajtove(1000) == "1 KB"
    assert plot_results.formatiraj_bajtove(10_000) == "10 KB"
    assert plot_results.formatiraj_bajtove(1e7) == "10 MB"
    assert plot_results.formatiraj_bajtove(100) == "100 B"

    assert plot_results.formatiraj_sekunde(1) == "1 s"
    assert plot_results.formatiraj_sekunde(1e-3) == "1 ms"
    assert plot_results.formatiraj_sekunde(1e-4) == "100 µs"
    assert plot_results.formatiraj_sekunde(10) == "10 s"

    for vrijednost in (0, -1):
        assert plot_results.formatiraj_bajtove(vrijednost) == ""
        assert plot_results.formatiraj_sekunde(vrijednost) == ""

    # Nijedna oznaka ne smije sadrzati znak koji pokrece mathtext
    for funkcija in (plot_results.formatiraj_bajtove, plot_results.formatiraj_sekunde):
        for vrijednost in (1e-6, 1e-3, 1, 1e3, 1e6, 1e7):
            assert "$" not in funkcija(vrijednost)


def test_prazan_izbor_ne_puca():
    """Ako odabrani algoritmi nemaju mjerenja enkripcije, graf mora biti poruka."""
    df = _podaci()
    samo_ecdh = df[df["algoritam"] == "ECDH (X25519)"]
    if samo_ecdh.empty:
        return
    slika = plot_results.u_sliku(plot_results.graf_poredjenje(samo_ecdh))
    assert slika.startswith(b"\x89PNG")


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
