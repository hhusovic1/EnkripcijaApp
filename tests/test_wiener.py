"""
Validacija Wienerovog napada iz attacks/wiener_rsa.py. Vidi thesis 3.3.6.

Pokreni: python tests/test_wiener.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from attacks import wiener_rsa  # noqa: E402
from core import rsa  # noqa: E402


def test_napad_rekonstruise_d():
    kljucevi = rsa.generate_vulnerable_keys(1024)
    pravi_d = kljucevi["private"][1]

    rezultat = wiener_rsa.napadni(kljucevi["public"])
    assert rezultat["d"] == pravi_d, "napad nije vratio ispravan d"
    assert rezultat["koraci"], "nijedan korak nije zabiljezen"
    assert rezultat["koraci"][-1]["uspjeh"], "posljednji korak nije oznacen kao pogodak"


def test_pogodak_daje_ispravne_faktore():
    """Kad napad uspije, p i q iz kvadratne jednacine moraju stvarno faktorisati n."""
    kljucevi = rsa.generate_vulnerable_keys(1024)
    n = kljucevi["public"][0]

    rezultat = wiener_rsa.napadni(kljucevi["public"])
    pogodak = rezultat["koraci"][-1]

    assert pogodak["uspjeh"]
    assert pogodak["p"] * pogodak["q"] == n, "p·q se ne poklapa sa n"
    assert {pogodak["p"], pogodak["q"]} == {kljucevi["p"], kljucevi["q"]}


def test_svaki_odbacen_korak_ima_razlog():
    """Za prikaz u aplikaciji svaki pokusaj mora imati objasnjenje zasto je odbacen."""
    kljucevi = rsa.generate_vulnerable_keys(1024)
    rezultat = wiener_rsa.napadni(kljucevi["public"])

    for korak in rezultat["koraci"]:
        assert korak["razlog"], "korak #%d nema razlog" % korak["broj"]
        assert isinstance(korak["k"], int) and isinstance(korak["d"], int)
    brojevi = [k["broj"] for k in rezultat["koraci"]]
    assert brojevi == list(range(1, len(brojevi) + 1))


def test_napad_ne_uspijeva_na_normalnom_kljucu():
    kljucevi = rsa.generate_keys(1024)
    rezultat = wiener_rsa.napadni(kljucevi["public"])

    assert rezultat["d"] is None, "napad je 'uspio' na normalnom kljucu"
    assert rezultat["trajanje_s"] < 1.0
    # Kod e = 65537 razvoj e/n ima svega nekoliko konvergenti
    assert rezultat["ukupno_konvergenti"] < 60


def test_ranjiv_kljuc_je_ispod_wienerove_granice():
    """generate_vulnerable_keys mora dati d < n^(1/4)/3, inace napad nije garantovan."""
    kljucevi = rsa.generate_vulnerable_keys(1024)
    n = kljucevi["public"][0]
    d = kljucevi["private"][1]

    granica = math.isqrt(math.isqrt(n)) // 3
    assert d < granica, "d nije ispod Wienerove granice"


def test_demonstracija_oba_slucaja():
    demo = wiener_rsa.demonstracija(1024)

    assert demo["ranjivi"]["uspjeh"], "napad na ranjiv kljuc nije uspio"
    assert demo["normalni"]["uspjeh"], "napad na normalan kljuc je uspio - greska"

    # Poenta: rekonstruisanim kljucem se stvarno cita poruka
    assert demo["ranjivi"]["procitano"] == demo["ranjivi"]["poruka"]
    assert demo["ranjivi"]["napad"]["d"] == demo["ranjivi"]["pravi_d"]


def test_kontrast_u_broju_konvergenti():
    """
    Razlika koju demonstracija treba pokazati: kod ranjivog kljuca napad ima
    stotine kandidata za pretragu, kod normalnog svega nekoliko.
    """
    demo = wiener_rsa.demonstracija(1024)
    ranjivi = demo["ranjivi"]["napad"]["ukupno_konvergenti"]
    normalni = demo["normalni"]["napad"]["ukupno_konvergenti"]

    assert ranjivi > normalni * 5, (
        "ocekivan jasan kontrast, dobijeno %d naspram %d" % (ranjivi, normalni)
    )


def test_slaze_se_sa_core_implementacijom():
    """Verzija s koracima mora dati isti rezultat kao core/rsa.wiener_attack."""
    kljucevi = rsa.generate_vulnerable_keys(1024)
    assert wiener_rsa.napadni(kljucevi["public"])["d"] == rsa.wiener_attack(kljucevi["public"])

    normalni = rsa.generate_keys(1024)
    assert wiener_rsa.napadni(normalni["public"])["d"] == rsa.wiener_attack(normalni["public"])


def test_ogranicenje_broja_konvergenti():
    """maks_konvergenti mora stvarno zaustaviti pretragu."""
    kljucevi = rsa.generate_vulnerable_keys(1024)
    rezultat = wiener_rsa.napadni(kljucevi["public"], maks_konvergenti=3)

    assert rezultat["pregledano_konvergenti"] <= 3
    assert rezultat["d"] is None, "s 3 konvergente napad ne bi smio uspjeti"


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
