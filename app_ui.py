"""
Zajednicki elementi korisnickog interfejsa - navigacija i pomocno formatiranje.

Streamlit sam pravi navigaciju u bocnoj traci, ali ona se na uzem ekranu
sklapa. Zaglavlje ispod daje vidljive linkove na sve stranice bez obzira na
sirinu prozora, kako specifikacija trazi.
"""
import os

import streamlit as st

KORIJEN = os.path.dirname(os.path.abspath(__file__))

# (putanja, oznaka, ikona) - putanje su relativne u odnosu na app.py
STRANICE = [
    ("app.py", "Početna", "🏠"),
    ("pages/1_Core_algoritmi.py", "Core algoritmi", "🔑"),
    ("pages/2_Benchmark.py", "Benchmark", "📊"),
    ("pages/3_Mjeri_svoj_fajl.py", "Mjeri svoj fajl", "📁"),
    ("pages/4_Sigurnosne_demonstracije.py", "Sigurnosne demonstracije", "🔓"),
]


def zaglavlje(aktivna: str = None):
    """
    Iscrtava red linkova na sve stranice.

    `aktivna` je putanja trenutne stranice - ona se prikazuje kao onemogucen
    link, da se vidi gdje se korisnik nalazi.
    """
    postojece = [s for s in STRANICE
                 if os.path.exists(os.path.join(KORIJEN, s[0]))]
    if not postojece:
        return

    kolone = st.columns(len(postojece))
    for kolona, (putanja, oznaka, ikona) in zip(kolone, postojece):
        with kolona:
            try:
                st.page_link(putanja, label=oznaka, icon=ikona,
                             disabled=(putanja == aktivna),
                             use_container_width=True)
            except KeyError:
                # st.page_link trazi kontekst stranica koji ne postoji kad se
                # stranica izvrsava izvan uobicajenog toka (npr. pod AppTest-om
                # u testovima). Tada se ispise obicna oznaka - navigacija nije
                # sustina stranice, pa nema razloga da zbog nje sve pukne.
                st.markdown("%s %s" % (ikona, oznaka))
    st.divider()


def skrati_broj(vrijednost, maks_cifara: int = 40) -> str:
    """
    Veliki brojevi (moduli, tajne) se ne mogu prikazati u cijelosti bez da
    razbiju prelom stranice - prikazuje se pocetak, kraj i broj cifara.
    """
    tekst = str(vrijednost)
    if len(tekst) <= maks_cifara:
        return tekst
    pola = maks_cifara // 2
    return "%s…%s  (%d cifara)" % (tekst[:pola], tekst[-8:], len(tekst))


def prikazi_vrijednosti(vrijednosti: dict, maks_cifara: int = 40):
    """Prikazuje par kljuc-vrijednost iz koraka demonstracije."""
    for kljuc, vrijednost in vrijednosti.items():
        if isinstance(vrijednost, bool):
            prikaz = "da" if vrijednost else "ne"
        elif isinstance(vrijednost, int):
            prikaz = skrati_broj(vrijednost, maks_cifara)
        else:
            prikaz = str(vrijednost)

        st.markdown(
            "<div style='display:flex;gap:.75rem;padding:.15rem 0;'>"
            "<div style='min-width:14rem;opacity:.7;'>%s</div>"
            "<div style='font-family:monospace;word-break:break-all;'>%s</div>"
            "</div>" % (kljuc, prikaz),
            unsafe_allow_html=True,
        )
