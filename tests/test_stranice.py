"""
Provjera Streamlit stranica kroz ugradjeni AppTest - stranice se izvrsavaju
headless, bez preglednika.

Cilj nije provjeriti izgled nego da se svaka grana koda stvarno izvrsi bez
izuzetka: svi algoritmi na stranici Core algoritmi, oba scenarija MITM-a,
Wienerov napad, i da grafovi na Benchmark stranici prodju.

Pokreni: python tests/test_stranice.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KORIJEN = os.path.dirname(HERE)
sys.path.insert(0, KORIJEN)

from streamlit.testing.v1 import AppTest  # noqa: E402

CORE = os.path.join(KORIJEN, "pages", "1_Core_algoritmi.py")
BENCHMARK = os.path.join(KORIJEN, "pages", "2_Benchmark.py")
MJERI = os.path.join(KORIJEN, "pages", "3_Mjeri_svoj_fajl.py")
DEMO = os.path.join(KORIJEN, "pages", "4_Sigurnosne_demonstracije.py")
POCETNA = os.path.join(KORIJEN, "app.py")

TIMEOUT = 300


def _pokreni(putanja, timeout=TIMEOUT) -> AppTest:
    app = AppTest.from_file(putanja, default_timeout=timeout)
    app.run()
    return app


def _bez_izuzetaka(app, gdje):
    assert not app.exception, "%s: %s" % (
        gdje, [str(e.value)[:300] for e in app.exception]
    )


def test_pocetna_se_ucitava():
    _bez_izuzetaka(_pokreni(POCETNA), "Početna")


def test_sve_stranice_se_ucitavaju():
    for putanja in (CORE, BENCHMARK, MJERI, DEMO):
        _bez_izuzetaka(_pokreni(putanja), os.path.basename(putanja))


def test_core_simetricni_algoritmi():
    """Za svaki simetrični algoritam: generiši ključ, šifruj, provjeri poklapanje."""
    for algoritam in ("DES", "3DES", "AES-128", "AES-192", "AES-256", "ChaCha20"):
        app = _pokreni(CORE)
        app.selectbox[0].select(algoritam).run()
        _bez_izuzetaka(app, "%s - izbor" % algoritam)

        app.button[0].click().run()  # Generiši ključ
        _bez_izuzetaka(app, "%s - generisanje kljuca" % algoritam)

        dugme = [b for b in app.button if b.label == "Enkriptuj i dekriptuj"]
        assert dugme, "%s: nema dugmeta za enkripciju" % algoritam
        dugme[0].click().run()
        _bez_izuzetaka(app, "%s - enkripcija" % algoritam)

        poruke = " ".join(s.value for s in app.success)
        assert "bajt po bajt isti" in poruke, (
            "%s: nema potvrde da se dekripcija poklapa s originalom" % algoritam
        )


def test_core_rsa():
    app = _pokreni(CORE)
    app.selectbox[0].select("RSA-1024").run()
    _bez_izuzetaka(app, "RSA - izbor")

    app.button[0].click().run()  # Generiši par ključeva
    _bez_izuzetaka(app, "RSA - generisanje kljuceva")

    dugme = [b for b in app.button if b.label == "Enkriptuj i dekriptuj"]
    assert dugme, "nema dugmeta za RSA enkripciju"
    dugme[0].click().run()
    _bez_izuzetaka(app, "RSA - enkripcija")

    poruke = " ".join(s.value for s in app.success)
    assert "originalnu poruku" in poruke, "RSA nije vratio originalnu poruku"

    # Upozorenje da se privatni kljuc ne dijeli mora biti prikazano
    greske = " ".join(e.value for e in app.error)
    assert "nikad ne prikazuje" in greske, "nema upozorenja o privatnom kljucu"


def test_core_rsa_predugacka_poruka():
    """Tekst duži od modula mora dati jasnu grešku, ne tihi pogrešan rezultat."""
    app = _pokreni(CORE)
    app.selectbox[0].select("RSA-1024").run()
    app.button[0].click().run()

    app.text_area[0].set_value("x" * 500).run()
    _bez_izuzetaka(app, "RSA - predugacka poruka")

    greske = " ".join(e.value for e in app.error)
    assert "najviše" in greske and "hibridno" in greske, (
        "nema objasnjenja zasto poruka ne stane: %s" % greske[:200]
    )


def test_core_prazan_unos():
    """Prazan tekst ne smije srušiti stranicu."""
    app = _pokreni(CORE)
    app.button[0].click().run()
    app.text_area[0].set_value("").run()
    _bez_izuzetaka(app, "prazan unos")
    assert app.warning, "prazan unos treba dati upozorenje"


def test_core_ecdh():
    app = _pokreni(CORE)
    app.selectbox[0].select("ECC (ECDH)").run()
    _bez_izuzetaka(app, "ECDH - izbor")

    app.button[0].click().run()  # Pokreni razmjenu
    _bez_izuzetaka(app, "ECDH - razmjena")

    poruke = " ".join(s.value for s in app.success)
    assert "iste" in poruke, "ECDH nije potvrdio jednaku tajnu"

    hibridno = [b for b in app.button if b.label == "Izvedi AES ključ i šifruj"]
    assert hibridno, "nema dugmeta za hibridnu shemu"
    hibridno[0].click().run()
    _bez_izuzetaka(app, "ECDH - hibridno")


def test_demonstracije_mitm_oba_scenarija():
    # set_value ocekuje sirovu vrijednost opcije, dok .options vraca
    # labele proizvedene kroz format_func - zato se vrijednosti pisu doslovno
    for scenario, ocekivano in (("bez_mallory", "iste"), ("sa_mallory", None)):
        app = _pokreni(DEMO)
        app.radio[0].set_value(scenario).run()
        _bez_izuzetaka(app, "MITM - izbor scenarija")

        pokreni = [b for b in app.button if b.label == "Pokreni razmjenu"]
        assert pokreni, "nema dugmeta Pokreni razmjenu"
        pokreni[0].click().run()
        _bez_izuzetaka(app, "MITM - pokretanje")

        # Otkrij sve korake
        prikazi_sve = [b for b in app.button if b.label == "Prikaži sve"]
        if prikazi_sve:
            prikazi_sve[0].click().run()
            _bez_izuzetaka(app, "MITM - prikazi sve")

        if ocekivano:
            assert any(ocekivano in s.value for s in app.success)
        else:
            assert app.error, "napad sa Mallory mora zavrsiti crvenom porukom"


def test_demonstracije_wiener():
    app = _pokreni(DEMO)
    pokreni = [b for b in app.button if b.label == "Pokreni napad"]
    assert pokreni, "nema dugmeta Pokreni napad"
    pokreni[0].click().run()
    _bez_izuzetaka(app, "Wiener")

    greske = " ".join(e.value for e in app.error)
    uspjesi = " ".join(s.value for s in app.success)
    assert "Napad uspio" in greske, "napad na ranjiv kljuc nije uspio"
    assert "ne uspijeva" in uspjesi, "napad na normalan kljuc je 'uspio'"


def _run_all():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - test runner namjerno hvata sve
            failed += 1
            print("FAIL  %s\n      %s: %s" % (test.__name__, type(exc).__name__, str(exc)[:400]))
        else:
            print("ok    %s" % test.__name__)
    print("\n%d/%d testova proslo" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
