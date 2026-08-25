"""
MITM demo na neautentifikovani Diffie-Hellman. Vidi thesis 3.4.4.

Tri strane dijele isti "kanal" objekat - Mallory ga kontrolise i moze
presresti/zamijeniti poruke, a Alice i Bob ne primjecuju nista.

Protokol prati pet koraka iz 3.4.3:
    1. Alice i Bob se dogovore o javnim parametrima (p, g).
    2. Alice bira tajni eksponent a i salje A = g^a mod p.
    3. Bob bira tajni eksponent b i salje B = g^b mod p.
    4. Alice racuna K = B^a mod p.
    5. Bob racuna K = A^b mod p.

Napad iz 3.4.4: Mallory se ubaci izmedju njih i vodi DVIJE odvojene razmjene -
jednu s Alice (predstavljajuci se kao Bob) i jednu s Bobom (kao Alice). Dobije
dva razlicita kljuca i moze citati i mijenjati sav saobracaj, a nijedna strana
ne primijeti nista, jer osnovni DH nema nikakvu autentifikaciju sagovornika.

Pokreni:
    python attacks/mitm_dh.py              # oba scenarija
    python attacks/mitm_dh.py --grupa rfc3526-2048
"""
import argparse
import hashlib
import os
import secrets
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import aes, modes  # noqa: E402


# ---------------------------------------------------------------------------
# Javni parametri grupe (korak 1 iz 3.4.3)
# ---------------------------------------------------------------------------

class Grupa:
    """
    Javni Diffie-Hellman parametri.

    `naziv` je kratak identifikator (koristi ga --grupa i web API), `opis`
    je kratko objasnjenje za ispis u terminalu. Duzi tekst za web je u
    web/routes.py, uz ostale nazive koje aplikacija prikazuje.
    """

    def __init__(self, naziv, p, g, opis):
        self.naziv = naziv
        self.p = p
        self.g = g
        self.opis = opis

    @property
    def bita(self):
        """Duzina prostog broja p u bitima - mjera sigurnosti grupe."""
        return self.p.bit_length()


# Mali siguran prost broj p = 2q + 1 (q = 9223372036854777359), g = 2.
# Sluzi samo da se brojevi mogu procitati na ekranu - 65 bita je daleko ispod
# svega sto bi bilo sigurno u praksi.
DEMO = Grupa(
    "demo",
    p=18446744073709554719,
    g=2,
    opis="65-bitni siguran prost broj - brojevi stanu na ekran, nije siguran",
)

# RFC 3526, MODP grupa 14 (2048 bita) - stvarno standardizovani parametri,
# upravo ono na sta 3.4.3 misli pod "javno poznatim skupovima parametara".
RFC3526_2048 = Grupa(
    "rfc3526-2048",
    p=int(
        "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74"
        "020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F1437"
        "4FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
        "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF05"
        "98DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB"
        "9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
        "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718"
        "3995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF",
        16,
    ),
    g=2,
    opis="MODP grupa 14 iz RFC 3526 (2048 bita) - realni parametri",
)

GRUPE = {g.naziv: g for g in (DEMO, RFC3526_2048)}


# ---------------------------------------------------------------------------
# Kanal
# ---------------------------------------------------------------------------

class Channel:
    """
    Simulira nesiguran komunikacioni kanal.

    Uz samu poruku vodi i dnevnik svega sto je proslo, da se razmjena moze
    prikazati korak po korak (i u terminalu i u aplikaciji).
    """

    def __init__(self, naziv="kanal"):
        self.naziv = naziv
        self.last_message = None
        self.dnevnik = []

    def send(self, message, posiljalac=None, primalac=None, opis=""):
        self.last_message = message
        self.dnevnik.append({
            "kanal": self.naziv,
            "posiljalac": posiljalac,
            "primalac": primalac,
            "opis": opis,
            "vrijednost": message,
        })
        return message

    def receive(self):
        return self.last_message


# ---------------------------------------------------------------------------
# Ucesnici
# ---------------------------------------------------------------------------

def izvedi_kljuc(shared_secret: int, p: int) -> bytes:
    """
    Iz zajednicke tajne (velik cio broj) izvodi 128-bitni AES kljuc.

    Sam DH rezultat se nikad ne koristi direktno kao kljuc - propusta se kroz
    hash funkciju (ovdje SHA-256, uzima se prvih 16 bajtova). Broj se pretvara
    u fiksan broj bajtova prema velicini modula, da izvodjenje bude jednoznacno.
    """
    duzina = (p.bit_length() + 7) // 8
    return hashlib.sha256(shared_secret.to_bytes(duzina, "big")).digest()[:16]


class Party:
    def __init__(self, name, channel, p, g, private_key=None):
        self.name = name
        self.channel = channel
        self.p = p
        self.g = g
        # Tajni eksponent iz [2, p-2]; u praksi je efemeran, po sesiji (PFS)
        self.private_key = private_key or (secrets.randbelow(p - 3) + 2)
        self.public_value = None
        self.shared_secret = None

    def generate_and_send_public_value(self):
        """Izracuna g^a mod p i posalje preko kanala (koraci 2 i 3 iz 3.4.3)."""
        self.public_value = pow(self.g, self.private_key, self.p)
        self.channel.send(
            self.public_value,
            posiljalac=self.name,
            opis="javna vrijednost g^%s mod p" % self.name[0].lower(),
        )
        return self.public_value

    def compute_shared_secret(self, their_public_value):
        """Izracuna (njihova_vrijednost)^moj_privatni mod p (koraci 4 i 5)."""
        self.shared_secret = pow(their_public_value, self.private_key, self.p)
        return self.shared_secret

    # -- sloj iznad DH: stvarna razmjena poruka -----------------------------

    @property
    def kljuc(self) -> bytes:
        if self.shared_secret is None:
            raise ValueError("%s jos nema zajednicku tajnu" % self.name)
        return izvedi_kljuc(self.shared_secret, self.p)

    def sifruj(self, tekst: str) -> bytes:
        """AES-128 CBC nad izvedenim kljucem - koristi rucnu implementaciju iz core/."""
        kljuc = self.kljuc
        iv, sifrat = modes.cbc_encrypt(
            tekst.encode("utf-8"), lambda b: aes.encrypt(b, kljuc), aes.BLOCK_SIZE
        )
        return iv + sifrat

    def desifruj(self, blob: bytes) -> str:
        kljuc = self.kljuc
        otvoreno = modes.cbc_decrypt(
            blob[aes.BLOCK_SIZE:], lambda b: aes.decrypt(b, kljuc),
            aes.BLOCK_SIZE, blob[:aes.BLOCK_SIZE],
        )
        return otvoreno.decode("utf-8")


class Mallory:
    """
    Napadac - presrece i zamjenjuje javne vrijednosti obje strane.

    Kljucni detalj: Mallory ne razbija diskretni logaritam i ne saznaje ni a ni b.
    Ona jednostavno vodi dvije potpuno regularne DH razmjene i zavrsi s dva
    razlicita kljuca. Napad ne cilja matematiku nego nedostatak autentifikacije.
    """

    def __init__(self, channel_alice, channel_bob, p, g):
        self.name = "Mallory"
        self.channel_alice = channel_alice
        self.channel_bob = channel_bob
        self.p = p
        self.g = g

        # Dva nezavisna tajna eksponenta - po jedan za svaku zrtvu
        self.private_to_alice = secrets.randbelow(p - 3) + 2
        self.private_to_bob = secrets.randbelow(p - 3) + 2

        self.secret_with_alice = None
        self.secret_with_bob = None

    def javna_vrijednost_za(self, prema: str) -> int:
        tajni = self.private_to_alice if prema == "Alice" else self.private_to_bob
        return pow(self.g, tajni, self.p)

    def presretni_od_alice(self, alicina_vrijednost: int) -> int:
        """
        Uhvati A, izracuna kljuc s Alice, pa Bobu proslijedi SVOJU vrijednost
        umjesto Alicine.
        """
        self.secret_with_alice = pow(alicina_vrijednost, self.private_to_alice, self.p)
        podmetnuto = self.javna_vrijednost_za("Bob")
        self.channel_bob.send(
            podmetnuto,
            posiljalac="Mallory (predstavlja se kao Alice)",
            primalac="Bob",
            opis="podmetnuta javna vrijednost umjesto Alicine",
        )
        return podmetnuto

    def presretni_od_boba(self, bobova_vrijednost: int) -> int:
        """Isto u drugom smjeru: uhvati B, Alici posalje svoju vrijednost."""
        self.secret_with_bob = pow(bobova_vrijednost, self.private_to_bob, self.p)
        podmetnuto = self.javna_vrijednost_za("Alice")
        self.channel_alice.send(
            podmetnuto,
            posiljalac="Mallory (predstavlja se kao Bob)",
            primalac="Alice",
            opis="podmetnuta javna vrijednost umjesto Bobove",
        )
        return podmetnuto

    def kljuc_sa(self, ko: str) -> bytes:
        tajna = self.secret_with_alice if ko == "Alice" else self.secret_with_bob
        if tajna is None:
            raise ValueError("Mallory jos nema tajnu s %s" % ko)
        return izvedi_kljuc(tajna, self.p)

    def procitaj(self, blob: bytes, od: str) -> str:
        kljuc = self.kljuc_sa(od)
        otvoreno = modes.cbc_decrypt(
            blob[aes.BLOCK_SIZE:], lambda b: aes.decrypt(b, kljuc),
            aes.BLOCK_SIZE, blob[:aes.BLOCK_SIZE],
        )
        return otvoreno.decode("utf-8")

    def proslijedi(self, tekst: str, prema: str) -> bytes:
        """Ponovo sifruje poruku kljucem koji dijeli s primaocem - zato niko ne primijeti."""
        kljuc = self.kljuc_sa(prema)
        iv, sifrat = modes.cbc_encrypt(
            tekst.encode("utf-8"), lambda b: aes.encrypt(b, kljuc), aes.BLOCK_SIZE
        )
        return iv + sifrat


# ---------------------------------------------------------------------------
# Scenariji - vracaju listu koraka koju prikazuje i terminal i aplikacija
# ---------------------------------------------------------------------------

PORUKA = "Bobe, broj racuna je BA39 1290 0000 0012 3456."


def _korak(koraci, naslov, akter, opis, vrijednosti=None, istaknuto=False):
    koraci.append({
        "broj": len(koraci) + 1,
        "naslov": naslov,
        "akter": akter,
        "opis": opis,
        "vrijednosti": vrijednosti or {},
        "istaknuto": istaknuto,
    })


def bez_mallory(grupa=DEMO, poruka=PORUKA) -> dict:
    """Uredna razmjena: Alice i Bob dodju do iste tajne (3.4.3)."""
    koraci = []
    kanal = Channel("Alice <-> Bob")

    _korak(koraci, "Javni parametri", "Alice i Bob",
           "Dogovaraju se o prostom broju p i generatoru g. Oba su javna i "
           "smiju se prenositi otvoreno.",
           {"p": grupa.p, "g": grupa.g})

    alice = Party("Alice", kanal, grupa.p, grupa.g)
    bob = Party("Bob", kanal, grupa.p, grupa.g)

    _korak(koraci, "Tajni eksponenti", "Alice i Bob",
           "Svako nasumicno bira svoj tajni eksponent. Ove vrijednosti nikad ne "
           "napustaju vlasnika i ne salju se preko kanala.",
           {"a (Alicin tajni)": alice.private_key, "b (Bobov tajni)": bob.private_key})

    A = alice.generate_and_send_public_value()
    _korak(koraci, "Alice salje A", "Alice -> Bob",
           "Alice racuna A = g^a mod p i salje ga otvorenim kanalom. Prisluskivac "
           "vidi A, ali iz njega ne moze izvuci a - to je problem diskretnog logaritma.",
           {"A = g^a mod p": A})

    B = bob.generate_and_send_public_value()
    _korak(koraci, "Bob salje B", "Bob -> Alice",
           "Bob analogno racuna B = g^b mod p i salje ga Alici.",
           {"B = g^b mod p": B})

    alice.compute_shared_secret(B)
    bob.compute_shared_secret(A)

    _korak(koraci, "Obje strane racunaju istu tajnu", "Alice i Bob",
           "Alice racuna B^a mod p, Bob racuna A^b mod p. Kako je g^ab = g^ba, "
           "rezultat je identican - a sama tajna nikad nije prosla kanalom.",
           {"Alicina tajna": alice.shared_secret, "Bobova tajna": bob.shared_secret,
            "Jednake?": alice.shared_secret == bob.shared_secret},
           istaknuto=True)

    blob = alice.sifruj(poruka)
    procitano = bob.desifruj(blob)

    _korak(koraci, "Alice salje sifrovanu poruku", "Alice -> Bob",
           "Iz zajednicke tajne se preko SHA-256 izvodi AES-128 kljuc, kojim se "
           "poruka sifruje. Bob je desifruje istim kljucem.",
           {"Poruka": poruka, "Sifrat (hex)": blob.hex(),
            "Bob procitao": procitano},
           istaknuto=True)

    return {
        "scenario": "bez_mallory",
        "grupa": grupa,
        "koraci": koraci,
        "uspjeh": alice.shared_secret == bob.shared_secret and procitano == poruka,
        "alice": alice,
        "bob": bob,
        "mallory": None,
    }


def sa_mallory(grupa=DEMO, poruka=PORUKA) -> dict:
    """Ista razmjena, ali Mallory sjedi u sredini (3.4.4)."""
    koraci = []
    kanal_alice = Channel("Alice <-> Mallory")
    kanal_bob = Channel("Mallory <-> Bob")

    _korak(koraci, "Javni parametri", "Alice i Bob",
           "Isti javni parametri kao maloprije. Alice i Bob vjeruju da "
           "razgovaraju direktno; ne postoji nista u protokolu sto bi to potvrdilo.",
           {"p": grupa.p, "g": grupa.g})

    alice = Party("Alice", kanal_alice, grupa.p, grupa.g)
    bob = Party("Bob", kanal_bob, grupa.p, grupa.g)
    mallory = Mallory(kanal_alice, kanal_bob, grupa.p, grupa.g)

    _korak(koraci, "Mallory se ubacuje u sredinu", "Mallory",
           "Mallory kontrolise kanal i bira DVA tajna eksponenta - jedan za "
           "razmjenu s Alice, drugi za razmjenu s Bobom.",
           {"tajni prema Alici": mallory.private_to_alice,
            "tajni prema Bobu": mallory.private_to_bob})

    A = alice.generate_and_send_public_value()
    _korak(koraci, "Alice salje A (misli da ide Bobu)", "Alice -> Mallory",
           "Alice salje svoju javnu vrijednost. Do Boba nikad ne stigne.",
           {"A = g^a mod p": A})

    podmetnuto_bobu = mallory.presretni_od_alice(A)
    _korak(koraci, "Mallory podmece svoju vrijednost Bobu", "Mallory -> Bob",
           "Mallory zadrzava A za sebe i Bobu salje svoju vrijednost. Bob nema "
           "nacina provjeriti da ova vrijednost nije Alicina.",
           {"Bob prima (misli da je A)": podmetnuto_bobu,
            "Prava Alicina vrijednost": A})

    B = bob.generate_and_send_public_value()
    _korak(koraci, "Bob salje B (misli da ide Alici)", "Bob -> Mallory",
           "Bob odgovara svojom javnom vrijednoscu.",
           {"B = g^b mod p": B})

    podmetnuto_alici = mallory.presretni_od_boba(B)
    _korak(koraci, "Mallory podmece svoju vrijednost Alici", "Mallory -> Alice",
           "Isti potez u drugom smjeru. Sada su uspostavljene dvije odvojene "
           "razmjene umjesto jedne.",
           {"Alice prima (misli da je B)": podmetnuto_alici,
            "Prava Bobova vrijednost": B})

    alice.compute_shared_secret(podmetnuto_alici)
    bob.compute_shared_secret(podmetnuto_bobu)

    _korak(koraci, "Dvije razlicite tajne umjesto jedne", "svi",
           "Alicina tajna se poklapa s Mallorynom tajnom prema Alici, a Bobova s "
           "Mallorynom prema Bobu. Alice i Bob nemaju istu tajnu - ali to nikad ne "
           "provjere, jer protokol to od njih ne trazi.",
           {"Alicina tajna": alice.shared_secret,
            "Malloryna tajna s Alice": mallory.secret_with_alice,
            "Bobova tajna": bob.shared_secret,
            "Malloryna tajna s Bobom": mallory.secret_with_bob,
            "Alice == Bob?": alice.shared_secret == bob.shared_secret},
           istaknuto=True)

    blob_od_alice = alice.sifruj(poruka)
    procitala_mallory = mallory.procitaj(blob_od_alice, od="Alice")
    blob_za_boba = mallory.proslijedi(procitala_mallory, prema="Bob")
    bob_procitao = bob.desifruj(blob_za_boba)

    _korak(koraci, "Mallory cita poruku i prosljedjuje je dalje", "Alice -> Mallory -> Bob",
           "Alice sifruje poruku kljucem za koji misli da ga dijeli samo s Bobom. "
           "Mallory je desifruje, procita, pa ponovo sifruje drugim kljucem i "
           "posalje Bobu. Bob dobije ocekivanu poruku i nista ne posumnja.",
           {"Alice poslala": poruka,
            "MALLORY PROCITALA": procitala_mallory,
            "Bob primio": bob_procitao,
            "Primijetio iko nesto?": "ne"},
           istaknuto=True)

    # Mallory salje svoj sadrzaj, a ne izmjenu Alicinog - tako se vidi da nije
    # rijec o kvarenju sifrata nego o punoj kontroli nad porukom, i demonstracija
    # radi bez obzira sta je korisnik unio kao originalnu poruku.
    izmijenjeno = "Bobe, zanemari prethodnu poruku. Novi broj racuna je BA39 6666 9999 0000 1111."
    blob_izmijenjen = mallory.proslijedi(izmijenjeno, prema="Bob")
    bob_primio_izmijenjeno = bob.desifruj(blob_izmijenjen)

    _korak(koraci, "Mallory moze i mijenjati poruke", "Mallory -> Bob",
           "Posto Mallory posjeduje kljuc prema Bobu, ne mora se zadrzati na "
           "citanju - moze poslati bilo sta, a Bobu ce se uciniti da dolazi od Alice.",
           {"Alice je poslala": poruka,
            "Bob je primio": bob_primio_izmijenjeno},
           istaknuto=True)

    return {
        "scenario": "sa_mallory",
        "grupa": grupa,
        "koraci": koraci,
        "uspjeh": (
            alice.shared_secret != bob.shared_secret
            and alice.shared_secret == mallory.secret_with_alice
            and bob.shared_secret == mallory.secret_with_bob
            and procitala_mallory == poruka
        ),
        "alice": alice,
        "bob": bob,
        "mallory": mallory,
    }


# ---------------------------------------------------------------------------
# Ispis u terminalu
# ---------------------------------------------------------------------------

def skrati(vrijednost, maks=68) -> str:
    tekst = str(vrijednost)
    if len(tekst) <= maks:
        return tekst
    return "%s...%s  (%d cifara)" % (tekst[:28], tekst[-12:], len(tekst))


def ispisi(rezultat):
    grupa = rezultat["grupa"]
    naslov = ("BEZ Mallory - uredna razmjena"
              if rezultat["scenario"] == "bez_mallory"
              else "SA Mallory - napad posrednika")

    print("\n" + "=" * 78)
    print(naslov)
    print("grupa: %s (%s)" % (grupa.naziv, grupa.opis))
    print("=" * 78)

    for korak in rezultat["koraci"]:
        oznaka = " *" if korak["istaknuto"] else ""
        print("\n[%d] %s%s" % (korak["broj"], korak["naslov"], oznaka))
        print("    %s" % korak["akter"])
        for red in _prelomi(korak["opis"], 72):
            print("    %s" % red)
        for kljuc, vrijednost in korak["vrijednosti"].items():
            print("      %-28s %s" % (kljuc + ":", skrati(vrijednost)))

    print("\n" + "-" * 78)
    print("Ishod: %s" % ("kako se ocekivalo" if rezultat["uspjeh"] else "NEOCEKIVANO"))


def _prelomi(tekst, sirina):
    rijeci = tekst.split()
    redovi, tekuci = [], ""
    for rijec in rijeci:
        if len(tekuci) + len(rijec) + 1 > sirina:
            redovi.append(tekuci)
            tekuci = rijec
        else:
            tekuci = (tekuci + " " + rijec).strip()
    if tekuci:
        redovi.append(tekuci)
    return redovi


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="MITM napad na Diffie-Hellman")
    parser.add_argument("--grupa", choices=sorted(GRUPE), default="demo",
                        help="parametri grupe (demo = citljivi brojevi)")
    parser.add_argument("--scenario", choices=("oba", "bez", "sa"), default="oba")
    args = parser.parse_args()

    grupa = GRUPE[args.grupa]

    if args.scenario in ("oba", "bez"):
        ispisi(bez_mallory(grupa))
    if args.scenario in ("oba", "sa"):
        ispisi(sa_mallory(grupa))

    print(
        "\nZakljucak (3.4.4): napad ne razbija diskretni logaritam - Mallory nikad\n"
        "ne sazna ni a ni b. Rusi ga izostanak autentifikacije. Zato se DH u praksi\n"
        "koristi iskljucivo uz potpis ili certifikat (STS, TLS)."
    )


if __name__ == "__main__":
    main()
