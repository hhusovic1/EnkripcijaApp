"""
JSON API koji frontend poziva preko fetch-a.

Sav kriptografski rad se izvrsava OVDJE, u Pythonu, kroz core/ i attacks/.
TypeScript u pregledniku samo salje zahtjeve i prikazuje odgovore.

Dvije stvari na koje se pazi pri serijalizaciji:

1. Veliki cijeli brojevi (RSA modul, DH vrijednosti) prelaze 2^53, koliko
   JavaScript moze tacno predstaviti u tipu number. Zato svaki takav broj ide
   kao STRING - inace bi ga preglednik tiho zaokruzio.

2. Kljucevi putuju do preglednika i nazad, jer je aplikacija bez stanja (bez
   sesija i baze, kako je i zamisljeno). U stvarnom sistemu se tajni kljuc
   nikad ne bi slao klijentu - ovdje je to svjesna posljedica toga sto je rijec
   o demonstraciji u kojoj korisnik treba vidjeti sam kljuc.
"""
import base64
import binascii
import os
import time

from flask import Blueprint, jsonify, request

from attacks import mitm_dh, wiener_rsa
from core import aes, chacha, des, ecc, modes, rsa

from .algoritmi import ALGORITMI, LIMIT_RUCNI

api = Blueprint("api", __name__, url_prefix="/api")


class GreskaZahtjeva(Exception):
    """Greska koju treba prikazati korisniku, a ne kao 500."""

    def __init__(self, poruka, status=400):
        super().__init__(poruka)
        self.poruka = poruka
        self.status = status


@api.errorhandler(GreskaZahtjeva)
def _obradi_gresku(greska):
    return jsonify({"greska": greska.poruka}), greska.status


@api.errorhandler(Exception)
def _obradi_neocekivanu(greska):
    # Poruka se prikazuje korisniku, pa mora biti citljiva, ali bez internih detalja
    return jsonify({"greska": "Neočekivana greška: %s" % greska}), 500


# ---------------------------------------------------------------------------
# Pomocne funkcije
# ---------------------------------------------------------------------------

def _telo() -> dict:
    podaci = request.get_json(silent=True)
    if not isinstance(podaci, dict):
        raise GreskaZahtjeva("Očekivan je JSON objekat u tijelu zahtjeva.")
    return podaci


def _meta(id_algoritma: str) -> dict:
    meta = ALGORITMI.get(id_algoritma)
    if meta is None:
        raise GreskaZahtjeva("Nepoznat algoritam: %r" % id_algoritma)
    return meta


def _tekst(podaci: dict, kljuc="tekst", dozvoli_prazan=False) -> bytes:
    vrijednost = podaci.get(kljuc, "")
    if not isinstance(vrijednost, str):
        raise GreskaZahtjeva("Polje '%s' mora biti tekst." % kljuc)
    if not vrijednost and not dozvoli_prazan:
        raise GreskaZahtjeva("Unesi tekst — prazan unos se ne može šifrovati.")
    return vrijednost.encode("utf-8")


def _iz_hex(vrijednost, naziv: str) -> bytes:
    if not isinstance(vrijednost, str):
        raise GreskaZahtjeva("Polje '%s' nedostaje." % naziv)
    try:
        return bytes.fromhex(vrijednost)
    except (ValueError, binascii.Error):
        raise GreskaZahtjeva("Polje '%s' nije ispravan heksadecimalni zapis." % naziv)


def _cio_broj(vrijednost, naziv: str) -> int:
    """Brojevi stizu kao stringovi - vidi napomenu u zaglavlju modula."""
    try:
        return int(str(vrijednost))
    except (TypeError, ValueError):
        raise GreskaZahtjeva("Polje '%s' nije ispravan broj." % naziv)


def _provjeri_duzinu(podaci: bytes, meta: dict):
    if meta["rucni"] and len(podaci) > LIMIT_RUCNI:
        raise GreskaZahtjeva(
            "Tekst ima %d bajtova. Ručne implementacije obrađuju oko 46 KB/s, pa je "
            "granica %d bajtova da stranica ostane upotrebljiva."
            % (len(podaci), LIMIT_RUCNI)
        )


def _sifrat_odgovor(sifrat: bytes) -> dict:
    return {
        "hex": sifrat.hex().upper(),
        "base64": base64.b64encode(sifrat).decode(),
        "duzina": len(sifrat),
    }


# ---------------------------------------------------------------------------
# Simetricni algoritmi
# ---------------------------------------------------------------------------

@api.post("/kljuc")
def generisi_kljuc():
    podaci = _telo()
    id_alg = podaci.get("algoritam")
    meta = _meta(id_alg)

    if id_alg == "des":
        k = des.generate_keys()
        return jsonify({"kljuc": k["key"].hex().upper(), "duzina_bita": 56})

    if id_alg == "3des":
        k = des.generate_keys_3des(keying_option=1)
        return jsonify({
            "k1": k["k1"].hex().upper(),
            "k2": k["k2"].hex().upper(),
            "k3": k["k3"].hex().upper(),
            "duzina_bita": 168,
        })

    if id_alg.startswith("aes-"):
        k = aes.generate_keys(meta["kljuc_bita"])
        return jsonify({"kljuc": k["key"].hex().upper(),
                        "duzina_bita": meta["kljuc_bita"]})

    if id_alg == "chacha20":
        k = chacha.generate_keys()
        return jsonify({
            "kljuc": k["key"].hex().upper(),
            "nonce": k["nonce"].hex().upper(),
            "duzina_bita": 256,
        })

    raise GreskaZahtjeva("Algoritam %r nema simetrični ključ." % id_alg)


@api.post("/sifruj")
def sifruj():
    """Enkriptuje i odmah dekriptuje, pa vrati oba vremena i potvrdu poklapanja."""
    podaci = _telo()
    id_alg = podaci.get("algoritam")
    meta = _meta(id_alg)
    otvoreni = _tekst(podaci)
    _provjeri_duzinu(otvoreni, meta)

    if id_alg == "des":
        kljuc = _iz_hex(podaci.get("kljuc"), "kljuc")
        enc = lambda b: des.encrypt(b, kljuc)   # noqa: E731
        dec = lambda b: des.decrypt(b, kljuc)   # noqa: E731
        blok = des.BLOCK_SIZE
    elif id_alg == "3des":
        k1 = _iz_hex(podaci.get("k1"), "k1")
        k2 = _iz_hex(podaci.get("k2"), "k2")
        k3 = _iz_hex(podaci.get("k3"), "k3")
        enc = lambda b: des.encrypt_3des(b, k1, k2, k3)   # noqa: E731
        dec = lambda b: des.decrypt_3des(b, k1, k2, k3)   # noqa: E731
        blok = des.BLOCK_SIZE
    elif id_alg.startswith("aes-"):
        kljuc = _iz_hex(podaci.get("kljuc"), "kljuc")
        enc = lambda b: aes.encrypt(b, kljuc)   # noqa: E731
        dec = lambda b: aes.decrypt(b, kljuc)   # noqa: E731
        blok = aes.BLOCK_SIZE
    elif id_alg == "chacha20":
        kljuc = _iz_hex(podaci.get("kljuc"), "kljuc")
        nonce = _iz_hex(podaci.get("nonce"), "nonce")

        start = time.perf_counter()
        sifrat = chacha.encrypt(otvoreni, kljuc, nonce)
        vrijeme_enc = time.perf_counter() - start

        start = time.perf_counter()
        vraceno = chacha.decrypt(sifrat, kljuc, nonce)
        vrijeme_dec = time.perf_counter() - start

        return jsonify({
            "sifrat": _sifrat_odgovor(sifrat),
            "iv": None,
            "vrijeme_enkripcije_ms": vrijeme_enc * 1000,
            "vrijeme_dekripcije_ms": vrijeme_dec * 1000,
            "vraceno": vraceno.decode("utf-8", errors="replace"),
            "ispravno": vraceno == otvoreni,
            "dopuna": None,
        })
    else:
        raise GreskaZahtjeva("Algoritam %r nije simetrična šifra." % id_alg)

    try:
        start = time.perf_counter()
        iv, sifrat = modes.cbc_encrypt(otvoreni, enc, blok)
        vrijeme_enc = time.perf_counter() - start

        start = time.perf_counter()
        vraceno = modes.cbc_decrypt(sifrat, dec, blok, iv)
        vrijeme_dec = time.perf_counter() - start
    except (ValueError, TypeError) as greska:
        raise GreskaZahtjeva(str(greska))

    dopunjeno = modes.pkcs7_pad(otvoreni, blok)
    return jsonify({
        "sifrat": _sifrat_odgovor(iv + sifrat),
        "iv": iv.hex().upper(),
        "vrijeme_enkripcije_ms": vrijeme_enc * 1000,
        "vrijeme_dekripcije_ms": vrijeme_dec * 1000,
        "vraceno": vraceno.decode("utf-8", errors="replace"),
        "ispravno": vraceno == otvoreni,
        "dopuna": {
            "prije": len(otvoreni),
            "poslije": len(dopunjeno),
            "blokova": len(dopunjeno) // blok,
            "velicina_bloka": blok,
        },
    })


# ---------------------------------------------------------------------------
# RSA
# ---------------------------------------------------------------------------

@api.post("/rsa/kljuc")
def rsa_kljuc():
    podaci = _telo()
    bita = _cio_broj(podaci.get("bita", 2048), "bita")
    if bita not in rsa.VALID_KEY_SIZES:
        raise GreskaZahtjeva(
            "Dužina ključa mora biti jedna od: %s."
            % ", ".join(str(b) for b in rsa.VALID_KEY_SIZES)
        )

    start = time.perf_counter()
    kljucevi = rsa.generate_keys(bita)
    trajanje = time.perf_counter() - start

    n, e = kljucevi["public"]
    return jsonify({
        "n": str(n),
        "e": str(e),
        "d": str(kljucevi["private"][1]),
        "p": str(kljucevi["p"]),
        "q": str(kljucevi["q"]),
        "phi": str(kljucevi["phi"]),
        "bita": bita,
        "limit_bajtova": rsa.max_message_bytes(n),
        "vrijeme_generisanja_ms": trajanje * 1000,
    })


@api.post("/rsa/sifruj")
def rsa_sifruj():
    podaci = _telo()
    n = _cio_broj(podaci.get("n"), "n")
    e = _cio_broj(podaci.get("e"), "e")
    d = _cio_broj(podaci.get("d"), "d")
    otvoreni = _tekst(podaci)

    try:
        start = time.perf_counter()
        sifrat = rsa.encrypt_bytes(otvoreni, (n, e))
        vrijeme_enc = time.perf_counter() - start

        start = time.perf_counter()
        vraceno = rsa.decrypt_bytes(sifrat, (n, d))
        vrijeme_dec = time.perf_counter() - start
    except (ValueError, TypeError) as greska:
        raise GreskaZahtjeva(str(greska))

    return jsonify({
        "sifrat": _sifrat_odgovor(sifrat),
        "vrijeme_enkripcije_ms": vrijeme_enc * 1000,
        "vrijeme_dekripcije_ms": vrijeme_dec * 1000,
        "vraceno": vraceno.decode("utf-8", errors="replace"),
        "ispravno": vraceno == otvoreni,
    })


# ---------------------------------------------------------------------------
# ECDH
# ---------------------------------------------------------------------------

@api.post("/ecdh/razmjena")
def ecdh_razmjena():
    alice = ecc.generate_keys()
    bob = ecc.generate_keys()

    tajna_alice = ecc.derive_shared_secret(alice["private"], bob["public"])
    tajna_bob = ecc.derive_shared_secret(bob["private"], alice["public"])

    return jsonify({
        "alice_javni": alice["public"].public_bytes_raw().hex().upper(),
        "bob_javni": bob["public"].public_bytes_raw().hex().upper(),
        "tajna_alice": tajna_alice.hex().upper(),
        "tajna_bob": tajna_bob.hex().upper(),
        "jednake": tajna_alice == tajna_bob,
    })


@api.post("/ecdh/hibridno")
def ecdh_hibridno():
    """Izvedena tajna se koristi kao AES kljuc - hibridna shema iz 3.5.3."""
    import hashlib

    podaci = _telo()
    tajna = _iz_hex(podaci.get("tajna"), "tajna")
    otvoreni = _tekst(podaci)
    _provjeri_duzinu(otvoreni, {"rucni": True})

    izvedeni = hashlib.sha256(tajna).digest()[:16]

    iv, sifrat = modes.cbc_encrypt(
        otvoreni, lambda b: aes.encrypt(b, izvedeni), aes.BLOCK_SIZE
    )
    vraceno = modes.cbc_decrypt(
        sifrat, lambda b: aes.decrypt(b, izvedeni), aes.BLOCK_SIZE, iv
    )

    return jsonify({
        "izvedeni_kljuc": izvedeni.hex().upper(),
        "sifrat": _sifrat_odgovor(iv + sifrat),
        "vraceno": vraceno.decode("utf-8", errors="replace"),
        "ispravno": vraceno == otvoreni,
    })


# ---------------------------------------------------------------------------
# Napadi
# ---------------------------------------------------------------------------

def _vrijednosti_u_tekst(vrijednosti: dict) -> list:
    """
    Vrijednosti koraka sadrze velike cijele brojeve - pretvaraju se u stringove
    (vidi napomenu u zaglavlju). Lista umjesto dicta cuva redoslijed prikaza.
    """
    izlaz = []
    for kljuc, vrijednost in vrijednosti.items():
        if isinstance(vrijednost, bool):
            prikaz = "da" if vrijednost else "ne"
        else:
            prikaz = str(vrijednost)
        izlaz.append({"kljuc": kljuc, "vrijednost": prikaz})
    return izlaz


@api.post("/mitm")
def mitm():
    podaci = _telo()
    naziv_grupe = podaci.get("grupa", "demo")
    scenario = podaci.get("scenario", "bez_mallory")
    poruka = podaci.get("poruka") or mitm_dh.PORUKA

    grupa = mitm_dh.GRUPE.get(naziv_grupe)
    if grupa is None:
        raise GreskaZahtjeva("Nepoznata grupa: %r" % naziv_grupe)
    if scenario not in ("bez_mallory", "sa_mallory"):
        raise GreskaZahtjeva("Nepoznat scenario: %r" % scenario)
    if not isinstance(poruka, str) or not poruka.strip():
        raise GreskaZahtjeva("Unesi poruku koju Alice šalje.")

    funkcija = mitm_dh.bez_mallory if scenario == "bez_mallory" else mitm_dh.sa_mallory
    rezultat = funkcija(grupa=grupa, poruka=poruka)

    return jsonify({
        "scenario": scenario,
        "grupa": {"naziv": grupa.naziv, "opis": grupa.opis},
        "uspjeh": rezultat["uspjeh"],
        "koraci": [
            {
                "broj": k["broj"],
                "naslov": k["naslov"],
                "akter": k["akter"],
                "opis": k["opis"],
                "istaknuto": k["istaknuto"],
                "vrijednosti": _vrijednosti_u_tekst(k["vrijednosti"]),
            }
            for k in rezultat["koraci"]
        ],
    })


@api.post("/wiener")
def wiener():
    podaci = _telo()
    bita = _cio_broj(podaci.get("bita", 1024), "bita")
    if bita not in (1024, 2048):
        raise GreskaZahtjeva("Podržane su dužine 1024 i 2048 bita.")

    demo = wiener_rsa.demonstracija(bita)
    ranjivi, normalni = demo["ranjivi"], demo["normalni"]

    def _koraci(napad, koliko=12):
        return [
            {
                "broj": k["broj"],
                "k": str(k["k"]),
                "d": str(k["d"]),
                "phi": str(k["phi"]) if k["phi"] is not None else None,
                "p": str(k["p"]) if k.get("p") is not None else None,
                "q": str(k["q"]) if k.get("q") is not None else None,
                "razlog": k["razlog"],
                "uspjeh": k["uspjeh"],
            }
            for k in napad["koraci"][-koliko:]
        ]

    return jsonify({
        "bita": bita,
        "ranjivi": {
            "n": str(ranjivi["n"]),
            "e": str(ranjivi["e"]),
            "pravi_d": str(ranjivi["pravi_d"]),
            "d_bita": ranjivi["pravi_d"].bit_length(),
            "granica_bita": ranjivi["granica"].bit_length(),
            "nadjeni_d": (str(ranjivi["napad"]["d"])
                          if ranjivi["napad"]["d"] is not None else None),
            "pregledano": ranjivi["napad"]["pregledano_konvergenti"],
            "ukupno_konvergenti": ranjivi["napad"]["ukupno_konvergenti"],
            "trajanje_ms": ranjivi["napad"]["trajanje_s"] * 1000,
            "uspjeh": ranjivi["uspjeh"],
            "poruka": ranjivi["poruka"].decode(),
            "procitano": (ranjivi["procitano"].decode()
                          if ranjivi["procitano"] else None),
            "koraci": _koraci(ranjivi["napad"]),
        },
        "normalni": {
            "n": str(normalni["n"]),
            "e": str(normalni["e"]),
            "d_bita": normalni["pravi_d"].bit_length(),
            "pregledano": normalni["napad"]["pregledano_konvergenti"],
            "ukupno_konvergenti": normalni["napad"]["ukupno_konvergenti"],
            "trajanje_ms": normalni["napad"]["trajanje_s"] * 1000,
            "uspjeh": normalni["uspjeh"],
        },
    })
