"""
Core algoritmi - interaktivna enkripcija i dekripcija.

Svaki algoritam se pokrece stvarno, kroz implementacije iz core/. Simetricni
rade nad tekstom proizvoljne duzine (PKCS#7 dopuna + CBC), RSA nad jednim
blokom, a ECDH nema sta enkriptovati - kod njega se demonstrira razmjena
kljuceva i hibridna shema.
"""
import base64
import hashlib
import os
import sys
import time

import streamlit as st

KORIJEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KORIJEN)

import app_ui  # noqa: E402
from core import aes, chacha, des, ecc, modes, rsa  # noqa: E402

st.set_page_config(page_title="Core algoritmi", page_icon="🔑", layout="wide")

app_ui.zaglavlje("pages/1_Core_algoritmi.py")

st.title("🔑 Core algoritmi")

# Rucne implementacije su reda 46 KB/s - duzi tekst bi blokirao stranicu
LIMIT_RUCNI = 64 * 1024

ALGORITMI = {
    "DES": {
        "vrsta": "blokovni",
        "rucni": True,
        "opis": (
            "Feistelova mreža sa 16 rundi. Blok je 64 bita, ključ 64 bita od kojih "
            "je 56 efektivnih — preostalih 8 su bitovi pariteta i ne doprinose "
            "sigurnosti. Dekripcija koristi isti algoritam, samo s podključevima "
            "u obrnutom redoslijedu."
        ),
        "napomena": (
            "56-bitni ključ je danas probojan grubom silom — EFF DES Cracker ga je "
            "razbio za manje od tri dana još 1998. Struktura algoritma je ostala "
            "solidna; problem je isključivo dužina ključa."
        ),
    },
    "3DES": {
        "vrsta": "blokovni",
        "rucni": True,
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
    "AES-128": {"vrsta": "blokovni", "rucni": True, "kljuc_bita": 128},
    "AES-192": {"vrsta": "blokovni", "rucni": True, "kljuc_bita": 192},
    "AES-256": {"vrsta": "blokovni", "rucni": True, "kljuc_bita": 256},
    "ChaCha20": {
        "vrsta": "tocna",
        "rucni": False,
        "opis": (
            "Tokovna (stream) šifra — generiše pseudoslučajan tok ključa koji se "
            "XOR-uje s otvorenim tekstom. Nema blokova ni dopune, pa je šifrat "
            "tačno iste dužine kao ulaz."
        ),
        "napomena": (
            "Nonce se nikad ne smije ponoviti s istim ključem. Ponovljen par "
            "(ključ, nonce) daje isti tok ključa, a XOR dva šifrata tada otkriva "
            "XOR dva otvorena teksta."
        ),
    },
    "RSA-1024": {"vrsta": "rsa", "rucni": True, "kljuc_bita": 1024},
    "RSA-2048": {"vrsta": "rsa", "rucni": True, "kljuc_bita": 2048},
    "RSA-3072": {"vrsta": "rsa", "rucni": True, "kljuc_bita": 3072},
    "RSA-4096": {"vrsta": "rsa", "rucni": True, "kljuc_bita": 4096},
    "ECC (ECDH)": {
        "vrsta": "ecdh",
        "rucni": False,
        "opis": (
            "ECDH ne enkriptuje ništa — to je protokol za uspostavu zajedničke "
            "tajne. Obje strane generišu par ključeva, razmijene javne dijelove i "
            "nezavisno izračunaju istu tajnu, koja nikad ne prođe kanalom."
        ),
        "napomena": (
            "Ovdje se koristi X25519 iz biblioteke `cryptography`. Eliptičke krive "
            "se ne implementiraju ručno — previše je suptilnih zamki (timing "
            "napadi, invalid curve napadi) da bi to imalo smisla za demonstraciju."
        ),
    },
}

for naziv, meta in ALGORITMI.items():
    if naziv.startswith("AES"):
        bita = meta["kljuc_bita"]
        meta["opis"] = (
            "Supstitucijsko-permutacijska mreža sa %d rundi. Blok je uvijek 128 "
            "bita bez obzira na dužinu ključa. Svaka runda radi SubBytes, "
            "ShiftRows, MixColumns i AddRoundKey; posljednja izostavlja MixColumns."
            % aes.ROUNDS[bita]
        )
        meta["napomena"] = (
            "S-box se ovdje ne prepisuje kao tabela nego **izvodi iz definicije** — "
            "multiplikativni inverz u GF(2⁸) pa afina transformacija."
        )
    elif naziv.startswith("RSA"):
        meta["opis"] = (
            "Asimetrični algoritam: enkripcija javnim ključem `c = m^e mod n`, "
            "dekripcija privatnim `m = c^d mod n`. Sigurnost počiva na težini "
            "faktorizacije modula n = p·q."
        )
        meta["napomena"] = (
            "Ovo je **udžbenički RSA, bez OAEP dopune** — deterministički je, pa "
            "ista poruka uvijek daje isti šifrat. U praksi se nikad ne koristi "
            "ovako."
        )

izbor = st.columns([2, 5])
with izbor[0]:
    naziv = st.selectbox("Algoritam", options=list(ALGORITMI))
meta = ALGORITMI[naziv]

with izbor[1]:
    vrsta_implementacije = "ručna implementacija" if meta["rucni"] else "biblioteka"
    st.markdown("&nbsp;\n\n**%s** · %s" % (naziv, vrsta_implementacije))

st.write(meta["opis"])
with st.expander("Na šta paziti"):
    st.markdown(meta["napomena"])

st.divider()

# Kljucevi se drze po algoritmu, da se ne izgube pri svakom rerunu
if "core_kljucevi" not in st.session_state:
    st.session_state["core_kljucevi"] = {}
kljucevi = st.session_state["core_kljucevi"]


def hex_prikaz(podaci: bytes) -> str:
    return podaci.hex().upper()


# ===========================================================================
# Simetricni algoritmi (DES, 3DES, AES, ChaCha20)
# ===========================================================================

if meta["vrsta"] in ("blokovni", "tocna"):
    st.subheader("1. Ključ")

    if st.button("Generiši ključ", type="primary"):
        if naziv == "DES":
            kljucevi[naziv] = des.generate_keys()
        elif naziv == "3DES":
            kljucevi[naziv] = des.generate_keys_3des(keying_option=1)
        elif naziv.startswith("AES"):
            kljucevi[naziv] = aes.generate_keys(meta["kljuc_bita"])
        elif naziv == "ChaCha20":
            kljucevi[naziv] = chacha.generate_keys()

    kljuc = kljucevi.get(naziv)
    if kljuc is None:
        st.info("Klikni **Generiši ključ** da nastaviš.")
        st.stop()

    if naziv == "3DES":
        app_ui.prikazi_vrijednosti({
            "k1 (hex)": hex_prikaz(kljuc["k1"]),
            "k2 (hex)": hex_prikaz(kljuc["k2"]),
            "k3 (hex)": hex_prikaz(kljuc["k3"]),
            "Ukupno": "3 × 56 efektivnih bita",
        })
    elif naziv == "ChaCha20":
        app_ui.prikazi_vrijednosti({
            "Ključ (hex)": hex_prikaz(kljuc["key"]),
            "Nonce (hex)": hex_prikaz(kljuc["nonce"]),
        })
    else:
        app_ui.prikazi_vrijednosti({
            "Ključ (hex)": hex_prikaz(kljuc["key"]),
            "Dužina": "%d bita" % (len(kljuc["key"]) * 8),
        })

    st.subheader("2. Otvoreni tekst")
    tekst = st.text_area(
        "Tekst proizvoljne dužine",
        value="Ovo je tajna poruka koju šifrujemo ručno implementiranim algoritmom.",
        height=110,
    )
    podaci = tekst.encode("utf-8")

    if not tekst:
        st.warning("Unesi tekst za enkripciju.")
        st.stop()

    if meta["rucni"] and len(podaci) > LIMIT_RUCNI:
        st.error(
            "Tekst ima %d bajtova. Ručne implementacije obrađuju oko 46 KB/s, pa je "
            "ovdje granica %d bajtova da stranica ostane upotrebljiva. Za veće "
            "ulaze koristi stranicu *Mjeri svoj fajl*."
            % (len(podaci), LIMIT_RUCNI)
        )
        st.stop()

    if meta["vrsta"] == "blokovni":
        velicina_bloka = des.BLOCK_SIZE if naziv in ("DES", "3DES") else aes.BLOCK_SIZE
        dopunjeno = modes.pkcs7_pad(podaci, velicina_bloka)
        st.caption(
            "%d bajtova → PKCS#7 dopuna do %d bajtova (%d blokova po %d B) → CBC režim"
            % (len(podaci), len(dopunjeno), len(dopunjeno) // velicina_bloka,
               velicina_bloka)
        )
    else:
        st.caption("%d bajtova — tokovna šifra, šifrat je iste dužine" % len(podaci))

    st.subheader("3. Enkripcija i dekripcija")

    if st.button("Enkriptuj i dekriptuj", type="primary"):
        try:
            if naziv == "DES":
                enc_blok = lambda b: des.encrypt(b, kljuc["key"])       # noqa: E731
                dec_blok = lambda b: des.decrypt(b, kljuc["key"])       # noqa: E731
            elif naziv == "3DES":
                enc_blok = lambda b: des.encrypt_3des(b, kljuc["k1"], kljuc["k2"], kljuc["k3"])  # noqa: E731
                dec_blok = lambda b: des.decrypt_3des(b, kljuc["k1"], kljuc["k2"], kljuc["k3"])  # noqa: E731
            elif naziv.startswith("AES"):
                enc_blok = lambda b: aes.encrypt(b, kljuc["key"])       # noqa: E731
                dec_blok = lambda b: aes.decrypt(b, kljuc["key"])       # noqa: E731

            if meta["vrsta"] == "blokovni":
                start = time.perf_counter()
                iv, sifrat = modes.cbc_encrypt(podaci, enc_blok, velicina_bloka)
                vrijeme_enc = time.perf_counter() - start

                start = time.perf_counter()
                vraceno = modes.cbc_decrypt(sifrat, dec_blok, velicina_bloka, iv)
                vrijeme_dec = time.perf_counter() - start
                puni_sifrat = iv + sifrat
            else:
                start = time.perf_counter()
                sifrat = chacha.encrypt(podaci, kljuc["key"], kljuc["nonce"])
                vrijeme_enc = time.perf_counter() - start

                start = time.perf_counter()
                vraceno = chacha.decrypt(sifrat, kljuc["key"], kljuc["nonce"])
                vrijeme_dec = time.perf_counter() - start
                iv, puni_sifrat = None, sifrat

            st.session_state["core_rezultat"] = {
                "algoritam": naziv,
                "iv": iv,
                "sifrat": puni_sifrat,
                "vrijeme_enc": vrijeme_enc,
                "vrijeme_dec": vrijeme_dec,
                "vraceno": vraceno,
                "original": podaci,
            }
        except (ValueError, TypeError) as greska:
            st.error("Greška: %s" % greska)

    rezultat = st.session_state.get("core_rezultat")
    if rezultat and rezultat["algoritam"] == naziv:
        mjere = st.columns(3)
        mjere[0].metric("Enkripcija", "%.2f ms" % (rezultat["vrijeme_enc"] * 1000))
        mjere[1].metric("Dekripcija", "%.2f ms" % (rezultat["vrijeme_dec"] * 1000))
        mjere[2].metric("Veličina šifrata", "%d B" % len(rezultat["sifrat"]))

        if rezultat["iv"]:
            st.caption("IV (prvih %d bajtova šifrata): `%s`"
                       % (len(rezultat["iv"]), hex_prikaz(rezultat["iv"])))

        format_prikaza = st.radio("Prikaz šifrata", ["hex", "base64"], horizontal=True)
        if format_prikaza == "hex":
            st.code(hex_prikaz(rezultat["sifrat"]), language=None)
        else:
            st.code(base64.b64encode(rezultat["sifrat"]).decode(), language=None)

        if rezultat["vraceno"] == rezultat["original"]:
            st.success(
                "Dekripcija je vratila **bajt po bajt isti** tekst.", icon="✅"
            )
            st.text_area("Dekriptovani tekst",
                         value=rezultat["vraceno"].decode("utf-8", errors="replace"),
                         height=110, disabled=True)
        else:
            st.error("Dekriptovani tekst se NE poklapa s originalom.", icon="🔴")


# ===========================================================================
# RSA
# ===========================================================================

elif meta["vrsta"] == "rsa":
    bita = meta["kljuc_bita"]

    st.subheader("1. Par ključeva")
    if st.button("Generiši par ključeva", type="primary"):
        with st.spinner("Traženje dva prosta broja od po %d bita…" % (bita // 2)):
            start = time.perf_counter()
            kljucevi[naziv] = rsa.generate_keys(bita)
            kljucevi[naziv]["_vrijeme"] = time.perf_counter() - start

    kljuc = kljucevi.get(naziv)
    if kljuc is None:
        st.info("Klikni **Generiši par ključeva**. Kod 4096 bita traje nekoliko sekundi.")
        st.stop()

    st.caption("Generisano za %.2f s" % kljuc["_vrijeme"])

    javni, privatni = st.columns(2)
    with javni:
        st.markdown("**Javni ključ (n, e)** — smije se slobodno dijeliti")
        app_ui.prikazi_vrijednosti({"n": kljuc["public"][0], "e": kljuc["public"][1]})
    with privatni:
        st.markdown("**Privatni ključ (n, d)**")
        app_ui.prikazi_vrijednosti({"d": kljuc["private"][1]})
        st.error(
            "Privatni eksponent se u praksi **nikad ne prikazuje niti prenosi**. "
            "Ovdje je vidljiv samo zato što je ovo demonstracija. Isto vrijedi za "
            "p, q i φ(n) — oni se nakon generisanja ključa uništavaju.",
            icon="⚠️",
        )
        with st.expander("Prikaži p, q i φ(n)"):
            app_ui.prikazi_vrijednosti({
                "p": kljuc["p"], "q": kljuc["q"], "φ(n)": kljuc["phi"],
            })

    st.subheader("2. Poruka")
    limit = rsa.max_message_bytes(kljuc["public"][0])
    tekst = st.text_area("Poruka (najviše %d bajtova s ovim ključem)" % limit,
                         value="Tajna poruka.", height=90)
    podaci = tekst.encode("utf-8")

    if not tekst:
        st.warning("Unesi poruku.")
        st.stop()

    st.caption("%d od %d dopuštenih bajtova" % (len(podaci), limit))
    if len(podaci) > limit:
        st.error(
            "Poruka ima %d bajtova, a s %d-bitnim ključem RSA može enkriptovati "
            "najviše %d. RSA obrađuje samo brojeve manje od modula n — zato se u "
            "praksi koristi hibridno: RSA štiti AES ključ, AES štiti sadržaj."
            % (len(podaci), bita, limit),
            icon="🔴",
        )
        st.stop()

    st.subheader("3. Enkripcija javnim, dekripcija privatnim")
    if st.button("Enkriptuj i dekriptuj", type="primary", key="rsa_run"):
        try:
            start = time.perf_counter()
            sifrat = rsa.encrypt_bytes(podaci, kljuc["public"])
            vrijeme_enc = time.perf_counter() - start

            start = time.perf_counter()
            vraceno = rsa.decrypt_bytes(sifrat, kljuc["private"])
            vrijeme_dec = time.perf_counter() - start

            st.session_state["core_rsa"] = {
                "algoritam": naziv, "sifrat": sifrat, "vraceno": vraceno,
                "original": podaci, "enc": vrijeme_enc, "dec": vrijeme_dec,
            }
        except (ValueError, TypeError) as greska:
            st.error("Greška: %s" % greska)

    r = st.session_state.get("core_rsa")
    if r and r["algoritam"] == naziv:
        mjere = st.columns(3)
        mjere[0].metric("Enkripcija (javnim)", "%.2f ms" % (r["enc"] * 1000))
        mjere[1].metric("Dekripcija (privatnim)", "%.2f ms" % (r["dec"] * 1000))
        mjere[2].metric("Odnos", "%.0f×" % (r["dec"] / r["enc"]) if r["enc"] else "—")

        st.caption(
            "Dekripcija je znatno sporija jer je e = 65537 broj sa samo dva "
            "postavljena bita, dok je d pune dužine modula."
        )
        st.code(hex_prikaz(r["sifrat"]), language=None)

        if r["vraceno"] == r["original"]:
            st.success("Dekripcija privatnim ključem vratila je originalnu poruku.",
                       icon="✅")
            st.code(r["vraceno"].decode("utf-8", errors="replace"), language=None)
        else:
            st.error("Poruka se ne poklapa.", icon="🔴")


# ===========================================================================
# ECDH
# ===========================================================================

elif meta["vrsta"] == "ecdh":
    st.subheader("1. Obje strane generišu par ključeva")

    if st.button("Pokreni razmjenu", type="primary"):
        alice = ecc.generate_keys()
        bob = ecc.generate_keys()
        kljucevi[naziv] = {
            "alice_tajna": ecc.derive_shared_secret(alice["private"], bob["public"]),
            "bob_tajna": ecc.derive_shared_secret(bob["private"], alice["public"]),
            "alice_javni": alice["public"].public_bytes_raw(),
            "bob_javni": bob["public"].public_bytes_raw(),
        }

    stanje = kljucevi.get(naziv)
    if stanje is None:
        st.info("Klikni **Pokreni razmjenu**.")
        st.stop()

    alice_kol, bob_kol = st.columns(2)
    with alice_kol:
        st.markdown("**Alice**")
        app_ui.prikazi_vrijednosti({"Javni ključ (hex)": hex_prikaz(stanje["alice_javni"])})
    with bob_kol:
        st.markdown("**Bob**")
        app_ui.prikazi_vrijednosti({"Javni ključ (hex)": hex_prikaz(stanje["bob_javni"])})

    st.subheader("2. Zajednička tajna")
    app_ui.prikazi_vrijednosti({
        "Alice izračunala": hex_prikaz(stanje["alice_tajna"]),
        "Bob izračunao": hex_prikaz(stanje["bob_tajna"]),
    })

    if stanje["alice_tajna"] == stanje["bob_tajna"]:
        st.success(
            "Obje strane su došle do **iste** tajne, a ona sama nikad nije prošla "
            "kanalom — prenijeti su samo javni ključevi.", icon="✅",
        )
    else:
        st.error("Tajne se ne poklapaju.", icon="🔴")

    st.divider()
    st.subheader("3. Hibridna primjena")
    st.markdown(
        "Sama tajna se nikad ne koristi direktno kao ključ — propušta se kroz hash "
        "funkciju. Ovdje se iz nje izvodi AES-128 ključ kojim se šifruje tekst, što "
        "je tačno ono što radi TLS: **(EC)DHE uspostavi tajnu, AES štiti saobraćaj**."
    )

    tekst = st.text_area("Tekst koji Alice šalje Bobu",
                         value="Poruka zaštićena ključem izvedenim iz ECDH tajne.",
                         height=90)
    if not tekst:
        st.warning("Unesi tekst.")
        st.stop()

    if st.button("Izvedi AES ključ i šifruj", type="primary", key="ecdh_run"):
        # X25519 tajna je vec fiksnih 32 bajta, pa se hesuje direktno.
        # (mitm_dh.izvedi_kljuc radi isto, ali prima cio broj jer klasicni DH
        # daje vrijednost promjenljive duzine koju prvo treba normalizovati.)
        izvedeni = hashlib.sha256(stanje["alice_tajna"]).digest()[:16]
        podaci = tekst.encode("utf-8")
        iv, sifrat = modes.cbc_encrypt(
            podaci, lambda b: aes.encrypt(b, izvedeni), aes.BLOCK_SIZE
        )
        vraceno = modes.cbc_decrypt(
            sifrat, lambda b: aes.decrypt(b, izvedeni), aes.BLOCK_SIZE, iv
        )

        app_ui.prikazi_vrijednosti({
            "Izvedeni AES-128 ključ (hex)": hex_prikaz(izvedeni),
            "Šifrat (hex)": hex_prikaz(iv + sifrat)[:96] + "…",
        })
        if vraceno == podaci:
            st.success(
                "Bob je istim izvedenim ključem dešifrovao poruku — nijedna strana "
                "nije morala unaprijed dijeliti tajnu.", icon="✅",
            )
        else:
            st.error("Dešifrovanje nije uspjelo.", icon="🔴")
