"""
Streamlit aplikacija - demonstracija enkripcijskih algoritama.

Pokreni:
    streamlit run app.py

Stranice se nalaze u pages/ i Streamlit ih automatski dodaje u navigaciju.
"""
import os

import streamlit as st

import app_ui

st.set_page_config(
    page_title="Enkripcijski algoritmi",
    page_icon="🔐",
    layout="wide",
)

BENCHMARK_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "benchmark", "results.csv")

app_ui.zaglavlje("app.py")

st.title("Enkripcijski algoritmi")
st.markdown(
    "Demonstraciona aplikacija uz završni rad prvog ciklusa — "
    "**Elektrotehnički fakultet, Univerzitet u Sarajevu**."
)

st.markdown(
    """
Rad analizira enkripcijske algoritme teorijski; ova aplikacija ih pokazuje na djelu.
DES, 3DES, AES i RSA su **ručno implementirani** u čistom Pythonu, prema opisu iz
poglavlja 3 rada, i validirani protiv zvaničnih test vektora (FIPS 46-3, FIPS-197).
ECDH i ChaCha20 idu kroz provjerene biblioteke.
"""
)

kolone = st.columns(3)

with kolone[0]:
    st.metric("Implementiranih algoritama", "6")
    st.caption("DES, 3DES, AES, RSA, ECDH, ChaCha20")

with kolone[1]:
    st.metric("Ručnih implementacija", "4")
    st.caption("DES/3DES, AES, RSA — od nule, bez biblioteka")

with kolone[2]:
    st.metric("Demonstriranih napada", "2")
    st.caption("MITM na Diffie-Hellman, Wienerov napad na RSA")

st.caption("87 testova validacije — `python tests/run_all.py`")

st.divider()

st.subheader("Sadržaj")

st.page_link(
    "pages/1_Core_algoritmi.py",
    label="**Core algoritmi** — šifruj i dešifruj tekst bilo kojim od šest algoritama",
    icon="🔑",
)

if os.path.exists(BENCHMARK_CSV):
    st.page_link(
        "pages/2_Benchmark.py",
        label="**Benchmark** — izmjerene performanse svih algoritama",
        icon="📊",
    )
else:
    st.warning(
        "Benchmark rezultati još nisu generisani. Pokreni:\n\n"
        "```\npython benchmark/run_benchmark.py\n```"
    )

st.page_link(
    "pages/3_Mjeri_svoj_fajl.py",
    label="**Mjeri svoj fajl** — učitaj fajl i izmjeri algoritme na njemu",
    icon="📁",
)
st.page_link(
    "pages/4_Sigurnosne_demonstracije.py",
    label="**Sigurnosne demonstracije** — MITM na Diffie-Hellman i Wienerov napad na RSA",
    icon="🔓",
)


st.divider()
st.caption(
    "Validacija: `python tests/run_all.py` · "
    "Ponovno mjerenje: `python benchmark/run_benchmark.py`"
)
