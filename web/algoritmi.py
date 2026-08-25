"""
Metapodaci o algoritmima za web sloj - naziv, vrsta, opis i napomena.

Drzi se odvojeno od ruta jer isti podaci trebaju i sabloni (za padajuci meni) i
JavaScript (za prikaz opisa pri promjeni izbora) i API (za validaciju).
"""
from core import aes

LIMIT_RUCNI = 64 * 1024  # bajtova - iznad ovoga stranica postaje neupotrebljiva


def _aes(bita: int) -> dict:
    return {
        "naziv": "AES-%d" % bita,
        "vrsta": "blokovni",
        "grupa": "Simetrični — ručna implementacija",
        "rucni": True,
        "kljuc_bita": bita,
        "blok": 16,
        "opis": (
            "Supstitucijsko-permutacijska mreža sa %d rundi. Blok je uvijek 128 bita "
            "bez obzira na dužinu ključa. Svaka runda radi SubBytes, ShiftRows, "
            "MixColumns i AddRoundKey; posljednja izostavlja MixColumns."
            % aes.ROUNDS[bita]
        ),
        "napomena": (
            "S-box se ovdje ne prepisuje kao tabela nego izvodi iz definicije — "
            "multiplikativni inverz u GF(2⁸) pa afina transformacija."
        ),
    }


def _rsa(bita: int) -> dict:
    return {
        "naziv": "RSA-%d" % bita,
        "vrsta": "rsa",
        "grupa": "Asimetrični",
        "rucni": True,
        "kljuc_bita": bita,
        "opis": (
            "Asimetrični algoritam: enkripcija javnim ključem c = m^e mod n, "
            "dekripcija privatnim m = c^d mod n. Sigurnost počiva na težini "
            "faktorizacije modula n = p·q."
        ),
        "napomena": (
            "Ovo je udžbenički RSA, bez OAEP dopune — deterministički je, pa ista "
            "poruka uvijek daje isti šifrat. U praksi se nikad ne koristi ovako."
        ),
    }


ALGORITMI = {
    "des": {
        "naziv": "DES",
        "vrsta": "blokovni",
        "grupa": "Simetrični — ručna implementacija",
        "rucni": True,
        "kljuc_bita": 56,
        "blok": 8,
        "opis": (
            "Feistelova mreža sa 16 rundi. Blok je 64 bita, ključ 64 bita od kojih je "
            "56 efektivnih — preostalih 8 su bitovi pariteta i ne doprinose sigurnosti. "
            "Dekripcija koristi isti algoritam, samo s podključevima obrnutim redom."
        ),
        "napomena": (
            "56-bitni ključ je danas probojan grubom silom — EFF DES Cracker ga je "
            "razbio za manje od tri dana još 1998. Struktura algoritma je ostala "
            "solidna; problem je isključivo dužina ključa."
        ),
    },
    "3des": {
        "naziv": "3DES",
        "vrsta": "blokovni",
        "grupa": "Simetrični — ručna implementacija",
        "rucni": True,
        "kljuc_bita": 168,
        "blok": 8,
        "opis": (
            "EDE shema: C = E_k3(D_k2(E_k1(P))). Srednji korak je dekripcija, što "
            "omogućava unazadnu kompatibilnost — ako je k1 = k2 = k3, 3DES se svodi "
            "na obični DES."
        ),
        "napomena": (
            "Nominalnih 168 bita, ali napad tipa susret u sredini svodi efektivnu "
            "sigurnost na oko 2¹¹². NIST ga je povukao prvenstveno zbog 64-bitnog "
            "bloka i napada Sweet32."
        ),
    },
    "aes-128": _aes(128),
    "aes-192": _aes(192),
    "aes-256": _aes(256),
    "chacha20": {
        "naziv": "ChaCha20",
        "vrsta": "tocna",
        "grupa": "Simetrični — biblioteka",
        "rucni": False,
        "kljuc_bita": 256,
        "opis": (
            "Tokovna (stream) šifra — generiše pseudoslučajan tok ključa koji se "
            "XOR-uje s otvorenim tekstom. Nema blokova ni dopune, pa je šifrat tačno "
            "iste dužine kao ulaz."
        ),
        "napomena": (
            "Nonce se nikad ne smije ponoviti s istim ključem. Ponovljen par "
            "(ključ, nonce) daje isti tok ključa, a XOR dva šifrata tada otkriva "
            "XOR dva otvorena teksta."
        ),
    },
    "rsa-1024": _rsa(1024),
    "rsa-2048": _rsa(2048),
    "rsa-3072": _rsa(3072),
    "rsa-4096": _rsa(4096),
    "ecdh": {
        "naziv": "ECC (ECDH)",
        "vrsta": "ecdh",
        "grupa": "Asimetrični",
        "rucni": False,
        "kljuc_bita": 256,
        "opis": (
            "ECDH ne enkriptuje ništa — to je protokol za uspostavu zajedničke tajne. "
            "Obje strane generišu par ključeva, razmijene javne dijelove i nezavisno "
            "izračunaju istu tajnu, koja nikad ne prođe kanalom."
        ),
        "napomena": (
            "Koristi se X25519 iz biblioteke cryptography. Eliptičke krive se ne "
            "implementiraju ručno — previše je suptilnih zamki (timing napadi, "
            "invalid curve napadi) da bi to imalo smisla za demonstraciju."
        ),
    },
}

# id se dodaje u sam zapis, da ga JavaScript ima pri ruci
for _id, _meta in ALGORITMI.items():
    _meta["id"] = _id


def po_grupama() -> dict:
    """Algoritmi grupisani za <optgroup> u padajucem meniju."""
    grupe = {}
    for meta in ALGORITMI.values():
        grupe.setdefault(meta["grupa"], []).append(meta)
    return grupe
