"""
Sigurnosne demonstracije - MITM napad na Diffie-Hellman (3.4.4) i
Wienerov napad na RSA s malim d (3.3.6).

Oba napada se izvrsavaju stvarno, u trenutku kad korisnik klikne - nista nije
unaprijed pripremljeno ni simulirano tekstom. Razmjena se prikazuje korak po
korak, jer je poenta napada u redoslijedu poteza, a ne u krajnjem broju.
"""
import os
import sys

import streamlit as st

KORIJEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KORIJEN)

import app_ui  # noqa: E402
from attacks import mitm_dh, wiener_rsa  # noqa: E402
from core import rsa  # noqa: E402

st.set_page_config(page_title="Sigurnosne demonstracije", page_icon="🔓",
                   layout="wide")

app_ui.zaglavlje("pages/4_Sigurnosne_demonstracije.py")

st.title("🔓 Sigurnosne demonstracije")

tab_mitm, tab_wiener = st.tabs([
    "MITM na Diffie-Hellman",
    "Wienerov napad na RSA",
])


# ===========================================================================
# MITM
# ===========================================================================

with tab_mitm:
    st.markdown(
        "Diffie-Hellman omogućava dvjema stranama da preko potpuno nesigurnog "
        "kanala dođu do zajedničke tajne. Ono što **ne** radi jeste provjera "
        "s kim se zapravo razgovara — i upravo to napad iskorištava."
    )

    postavke = st.columns([2, 2, 3])
    with postavke[0]:
        naziv_grupe = st.selectbox(
            "Parametri grupe",
            options=list(mitm_dh.GRUPE),
            format_func=lambda n: mitm_dh.GRUPE[n].naziv,
            help="demo koristi male brojeve da stanu na ekran; RFC 3526 su stvarni parametri",
        )
        grupa = mitm_dh.GRUPE[naziv_grupe]
    with postavke[1]:
        scenario = st.radio(
            "Scenario",
            options=["bez_mallory", "sa_mallory"],
            format_func=lambda s: ("Bez Mallory — uredna razmjena"
                                   if s == "bez_mallory"
                                   else "Sa Mallory — napad posrednika"),
        )
    with postavke[2]:
        poruka = st.text_input(
            "Poruka koju Alice šalje",
            value=mitm_dh.PORUKA,
            help="Alice je šifruje ključem za koji vjeruje da ga dijeli samo s Bobom.",
        )

    st.caption(grupa.opis)

    if not poruka.strip():
        st.warning("Unesi poruku koju Alice šalje.")
        st.stop()

    kljuc_stanja = "mitm_%s_%s" % (scenario, naziv_grupe)

    dugmad = st.columns([1, 1, 4])
    if dugmad[0].button("Pokreni razmjenu", type="primary", use_container_width=True):
        funkcija = (mitm_dh.bez_mallory if scenario == "bez_mallory"
                    else mitm_dh.sa_mallory)
        st.session_state["mitm_rezultat"] = funkcija(grupa=grupa, poruka=poruka)
        st.session_state["mitm_kljuc"] = kljuc_stanja
        st.session_state["mitm_vidljivo"] = 1

    rezultat = st.session_state.get("mitm_rezultat")
    if rezultat is None or st.session_state.get("mitm_kljuc") != kljuc_stanja:
        st.info("Klikni **Pokreni razmjenu** — koraci se onda otkrivaju jedan po jedan.")
    else:
        koraci = rezultat["koraci"]
        vidljivo = st.session_state.get("mitm_vidljivo", 1)

        if dugmad[1].button("Prikaži sve", use_container_width=True):
            vidljivo = len(koraci)
            st.session_state["mitm_vidljivo"] = vidljivo

        st.progress(vidljivo / len(koraci),
                    text="Korak %d od %d" % (vidljivo, len(koraci)))

        for korak in koraci[:vidljivo]:
            with st.container(border=True):
                zaglavlje_koraka = "**%d. %s**" % (korak["broj"], korak["naslov"])
                if korak["istaknuto"]:
                    zaglavlje_koraka += "  ⬅"
                st.markdown(zaglavlje_koraka)
                st.caption(korak["akter"])
                st.write(korak["opis"])
                if korak["vrijednosti"]:
                    app_ui.prikazi_vrijednosti(korak["vrijednosti"])

        if vidljivo < len(koraci):
            if st.button("Sljedeći korak ▸", type="primary", key="mitm_dalje"):
                st.session_state["mitm_vidljivo"] = vidljivo + 1
                st.rerun()
        else:
            if rezultat["scenario"] == "bez_mallory":
                st.success(
                    "Alice i Bob su došli do **iste** tajne, a ona sama nikad nije "
                    "prošla kanalom. Prisluškivač je vidio p, g, A i B — i to mu "
                    "ne pomaže, jer bi iz A morao izvući a, što je problem "
                    "diskretnog logaritma.",
                    icon="✅",
                )
            else:
                st.error(
                    "Mallory je pročitala poruku koju je Alice smatrala sigurnom, i "
                    "mogla ju je izmijeniti prije nego stigne Bobu. Ni Alice ni Bob "
                    "nemaju ništa u protokolu čime bi to primijetili.",
                    icon="🔴",
                )
                st.markdown(
                    "**Ono što je najlakše previdjeti:** Mallory nikad nije saznala "
                    "ni `a` ni `b`, niti je razbila diskretni logaritam. Vodila je "
                    "dvije potpuno regularne DH razmjene. Napad ne ruši matematiku "
                    "nego **izostanak autentifikacije** — zato se DH u praksi nikad "
                    "ne koristi sam, nego uz potpis ili certifikat (STS, TLS)."
                )

    with st.expander("Kako izgleda ista razmjena bez i sa napadačem"):
        st.markdown(
            """
| | Bez Mallory | Sa Mallory |
|---|---|---|
| Broj razmjena | jedna | **dvije odvojene** |
| Alicina tajna | `g^ab mod p` | `g^(a·m₁) mod p` |
| Bobova tajna | `g^ab mod p` — **ista** | `g^(b·m₂) mod p` — **različita** |
| Ko zna ključ | Alice, Bob | Alice+Mallory, Bob+Mallory |
| Šta vidi napadač | `p, g, A, B` — beskorisno | **sve, u čitljivom obliku** |

Alice i Bob bi napad otkrili kad bi uporedili svoje tajne — ali osnovni
protokol taj korak nema, a i da ga ima, poređenje bi išlo preko istog kanala
koji Mallory kontroliše.
"""
        )


# ===========================================================================
# Wiener
# ===========================================================================

with tab_wiener:
    st.markdown(
        "RSA se oslanja na to da je faktorizacija velikog `n` neizvodljiva. "
        "Wienerov napad **ne faktoriše `n`** — pokazuje da je dovoljno da vlasnik "
        "ključa izabere premali privatni eksponent `d` i cijeli ključ pada, "
        "bez diranja problema na kojem RSA počiva."
    )

    izbor = st.columns([2, 5])
    with izbor[0]:
        bita = st.selectbox("Dužina ključa", options=list(rsa.VALID_KEY_SIZES), index=0,
                            help="Duži ključevi traju osjetno duže zbog generisanja ključeva")

    if st.button("Pokreni napad", type="primary", key="wiener_start"):
        with st.spinner("Generisanje ključeva i izvođenje napada…"):
            st.session_state["wiener"] = wiener_rsa.demonstracija(bita)

    demo = st.session_state.get("wiener")
    if demo is None:
        st.info("Klikni **Pokreni napad**. Ključevi se generišu u tom trenutku.")
    else:
        ranjivi = demo["ranjivi"]
        normalni = demo["normalni"]

        lijevo, desno = st.columns(2)

        with lijevo:
            st.subheader("Ranjiv ključ")
            st.caption("d je namjerno izabran malen, radi brže dekripcije")
            app_ui.prikazi_vrijednosti({
                "n": ranjivi["n"],
                "e": ranjivi["e"],
                "d (tajni)": ranjivi["pravi_d"],
                "d — broj bita": ranjivi["pravi_d"].bit_length(),
                "Wienerova granica (bita)": ranjivi["granica"].bit_length(),
            })
            if ranjivi["uspjeh"]:
                st.error(
                    "Napad uspio za **%.4f s** — pregledano %d konvergenti."
                    % (ranjivi["napad"]["trajanje_s"],
                       ranjivi["napad"]["pregledano_konvergenti"]),
                    icon="🔴",
                )
            else:
                st.warning("Napad ovaj put nije uspio — pokreni ponovo.")

        with desno:
            st.subheader("Normalan ključ")
            st.caption("e = 65537, d pune dužine — kako se radi u praksi")
            app_ui.prikazi_vrijednosti({
                "n": normalni["n"],
                "e": normalni["e"],
                "d — broj bita": normalni["pravi_d"].bit_length(),
                "Ukupno konvergenti": normalni["napad"]["ukupno_konvergenti"],
                "Pregledano": normalni["napad"]["pregledano_konvergenti"],
            })
            if normalni["uspjeh"]:
                st.success(
                    "Napad ne uspijeva, i to za **%.4f s** — ostane bez kandidata "
                    "prije nego išta nađe."
                    % normalni["napad"]["trajanje_s"],
                    icon="✅",
                )
            else:
                st.error("Napad je uspio na normalnom ključu — to bi bila greška.")

        st.divider()
        st.subheader("Kako napad prolazi kroz konvergente")
        st.markdown(
            "Iz `e·d ≡ 1 (mod φ)` slijedi da je `k/d` jedna od konvergenti razvoja "
            "`e/n` u verižni razlomak. Napadač ih redom isprobava i za svaku "
            "provjerava da li daje smislen `φ` — onaj kod kojeg "
            "`x² − (n − φ + 1)x + n = 0` ima dva cjelobrojna rješenja (`p` i `q`)."
        )

        koraci = ranjivi["napad"]["koraci"]
        prikazi_zadnjih = st.slider(
            "Koliko posljednjih pokušaja prikazati", 3,
            min(40, max(3, len(koraci))), min(8, len(koraci)),
        )

        for korak in koraci[-prikazi_zadnjih:]:
            with st.container(border=True):
                if korak["uspjeh"]:
                    st.markdown("**#%d — POGODAK**" % korak["broj"])
                    app_ui.prikazi_vrijednosti({
                        "k": korak["k"],
                        "d": korak["d"],
                        "φ(n)": korak["phi"],
                        "p": korak.get("p"),
                        "q": korak.get("q"),
                    })
                    st.success(korak["razlog"], icon="🎯")
                else:
                    st.markdown("**#%d** — odbačeno" % korak["broj"])
                    app_ui.prikazi_vrijednosti({"k": korak["k"], "d": korak["d"]}, 28)
                    st.caption(korak["razlog"])

        st.divider()
        st.subheader("Posljedica")
        st.markdown(
            "Rekonstruisani `d` nije samo broj koji se poklapa — njime se stvarno "
            "dešifruje poruka koju je vlasnik ključa smatrao sigurnom:"
        )
        app_ui.prikazi_vrijednosti({
            "Poslano": ranjivi["poruka"].decode(),
            "Šifrat (hex)": ranjivi["sifrat"].hex()[:64] + "…",
            "Napadač pročitao": (ranjivi["procitano"].decode()
                                 if ranjivi["procitano"] else "—"),
            "Rekonstruisani d = pravi d": ranjivi["napad"]["d"] == ranjivi["pravi_d"],
        })

        st.info(
            "**Zaključak:** ranjivost nije u RSA algoritmu nego u izboru "
            "parametara. Zato se `d` uvijek generiše kao vrijednost uporediva po "
            "veličini s `n`, a ubrzanje dekripcije se postiže kineskom teoremom o "
            "ostacima (CRT), a ne malim eksponentom.",
            icon="💡",
        )
