
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sympy import isprime  # noqa: E402

from attacks import mitm_dh  # noqa: E402


def test_parametri_grupe():
    """p mora biti siguran prost broj (p = 2q+1), a g netrivijalan generator."""
    for grupa in mitm_dh.GRUPE.values():
        assert isprime(grupa.p), "%s: p nije prost" % grupa.naziv
        assert isprime((grupa.p - 1) // 2), (
            "%s: p nije siguran prost broj (p-1)/2 nije prost - vidi 3.4.4, "
            "napad malih podgrupa" % grupa.naziv
        )
        assert grupa.g == 2
        # g mora generisati podgrupu reda q, ne nesto trivijalno malo
        q = (grupa.p - 1) // 2
        assert pow(grupa.g, q, grupa.p) == 1
        assert pow(grupa.g, 2, grupa.p) != 1


def test_bez_mallory_iste_tajne():
    """Koraci 4 i 5 iz 3.4.3: g^ab = g^ba, pa obje strane dobiju istu vrijednost."""
    rezultat = mitm_dh.bez_mallory()
    alice, bob = rezultat["alice"], rezultat["bob"]

    assert alice.shared_secret == bob.shared_secret
    assert alice.shared_secret is not None
    assert rezultat["uspjeh"]

    # Tajni eksponenti nikad ne smiju biti jednaki javnim vrijednostima
    assert alice.private_key != alice.public_value
    assert bob.private_key != bob.public_value


def test_bez_mallory_poruka_prolazi():
    rezultat = mitm_dh.bez_mallory(poruka="tajna poruka za Boba")
    alice, bob = rezultat["alice"], rezultat["bob"]

    blob = alice.sifruj("tajna poruka za Boba")
    assert bob.desifruj(blob) == "tajna poruka za Boba"


def test_treca_strana_ne_moze_procitati():
    """Neko ko nije u razmjeni ne smije doci do kljuca."""
    rezultat = mitm_dh.bez_mallory()
    alice = rezultat["alice"]
    blob = alice.sifruj("povjerljivo")

    uljez = mitm_dh.Party("Uljez", mitm_dh.Channel(), mitm_dh.DEMO.p, mitm_dh.DEMO.g)
    uljez.compute_shared_secret(rezultat["bob"].public_value)

    try:
        procitano = uljez.desifruj(blob)
    except ValueError:
        return  # ocekivano - PKCS7 dopuna ne valja s pogresnim kljucem
    assert procitano != "povjerljivo"


def test_mallory_uspostavi_dvije_tajne():
    """Sustina napada iz 3.4.4: dvije odvojene razmjene umjesto jedne."""
    rezultat = mitm_dh.sa_mallory()
    alice, bob, mallory = rezultat["alice"], rezultat["bob"], rezultat["mallory"]

    assert alice.shared_secret != bob.shared_secret, (
        "Alice i Bob imaju istu tajnu - napad nije uspio"
    )
    assert alice.shared_secret == mallory.secret_with_alice
    assert bob.shared_secret == mallory.secret_with_bob
    assert mallory.secret_with_alice != mallory.secret_with_bob
    assert rezultat["uspjeh"]


def test_mallory_cita_poruku():
    """Mallory mora procitati tacno ono sto je Alice poslala."""
    poruka = "broj kartice je 4111 1111 1111 1111"
    rezultat = mitm_dh.sa_mallory(poruka=poruka)

    alice, mallory, bob = rezultat["alice"], rezultat["mallory"], rezultat["bob"]

    blob = alice.sifruj(poruka)
    assert mallory.procitaj(blob, od="Alice") == poruka

    # I moze je proslijediti Bobu tako da Bob nista ne primijeti
    proslijedjeno = mallory.proslijedi(poruka, prema="Bob")
    assert bob.desifruj(proslijedjeno) == poruka


def test_mallory_moze_izmijeniti_poruku():
    """Napad nije samo pasivan - Mallory moze podmetnuti drugi sadrzaj."""
    rezultat = mitm_dh.sa_mallory()
    mallory, bob = rezultat["mallory"], rezultat["bob"]

    podmetnuto = mallory.proslijedi("posalji novac na drugi racun", prema="Bob")
    assert bob.desifruj(podmetnuto) == "posalji novac na drugi racun"


def test_korak_izmjene_radi_sa_bilo_kojom_porukom():
    """
    Regresija: korak koji pokazuje izmjenu poruke je ranije radio str.replace
    konkretnog broja racuna, pa s korisnickom porukom nije mijenjao nista i
    demonstracija je gubila smisao.
    """
    for poruka in ("test poruka", "bilo sta", mitm_dh.PORUKA):
        rezultat = mitm_dh.sa_mallory(poruka=poruka)
        korak = rezultat["koraci"][-1]
        assert "mijenjati" in korak["naslov"]

        poslala = korak["vrijednosti"]["Alice je poslala"]
        primio = korak["vrijednosti"]["Bob je primio"]
        assert poslala == poruka
        assert primio != poslala, (
            "s porukom %r Bob je primio isti tekst - izmjena se ne vidi" % poruka
        )


def test_mallory_ne_zna_tajne_eksponente():
    """
    Kljucna poenta 3.4.4: napad ne razbija diskretni logaritam. Mallory nema
    ni a ni b - samo je iskoristila izostanak autentifikacije.
    """
    rezultat = mitm_dh.sa_mallory()
    alice, bob, mallory = rezultat["alice"], rezultat["bob"], rezultat["mallory"]

    Malloryne = {mallory.private_to_alice, mallory.private_to_bob}
    assert alice.private_key not in Malloryne
    assert bob.private_key not in Malloryne


def test_alice_i_bob_ne_mogu_komunicirati_direktno():
    """
    Posljedica napada: kljucevi Alice i Boba se razlikuju, pa bi im poruka
    sifrovana bez Mallorynog posredovanja bila necitljiva.
    """
    rezultat = mitm_dh.sa_mallory()
    alice, bob = rezultat["alice"], rezultat["bob"]

    blob = alice.sifruj("ovo Bob ne moze procitati")
    try:
        procitano = bob.desifruj(blob)
    except ValueError:
        return  # ocekivano
    assert procitano != "ovo Bob ne moze procitati"


def test_izvedeni_kljuc():
    """Kljuc je 128-bitni, deterministican, i mijenja se sa tajnom."""
    p = mitm_dh.DEMO.p
    k1 = mitm_dh.izvedi_kljuc(12345, p)
    k2 = mitm_dh.izvedi_kljuc(12345, p)
    k3 = mitm_dh.izvedi_kljuc(12346, p)

    assert len(k1) == 16
    assert k1 == k2, "izvodjenje kljuca mora biti deterministicko"
    assert k1 != k3


def test_koraci_za_prikaz():
    """Scenariji vracaju strukturu koju aplikacija prikazuje korak po korak."""
    for scenario in (mitm_dh.bez_mallory(), mitm_dh.sa_mallory()):
        koraci = scenario["koraci"]
        assert len(koraci) >= 6
        assert [k["broj"] for k in koraci] == list(range(1, len(koraci) + 1))
        for korak in koraci:
            assert korak["naslov"] and korak["akter"] and korak["opis"]
            assert isinstance(korak["vrijednosti"], dict)
        assert any(k["istaknuto"] for k in koraci)


def test_rfc3526_grupa_radi():
    """Napad mora raditi i sa stvarnim 2048-bitnim parametrima, ne samo demo."""
    rezultat = mitm_dh.sa_mallory(grupa=mitm_dh.RFC3526_2048)
    assert rezultat["uspjeh"]
    assert rezultat["alice"].shared_secret != rezultat["bob"].shared_secret

    uredno = mitm_dh.bez_mallory(grupa=mitm_dh.RFC3526_2048)
    assert uredno["alice"].shared_secret == uredno["bob"].shared_secret


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
