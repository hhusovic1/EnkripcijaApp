"""
Interaktivno mjerenje nad korisnikovim fajlom.

Za razliku od stranice Benchmark, koja prikazuje unaprijed izracunate rezultate
nad nasumicnim podacima, ovdje se algoritmi pokrecu uzivo nad fajlom koji
korisnik ucita, i provjerava se da dekripcija vrati bajt po bajt isti sadrzaj.
"""
import os
import sys

import matplotlib
import pandas as pd
import streamlit as st

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

KORIJEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KORIJEN)
sys.path.insert(0, os.path.join(KORIJEN, "benchmark"))

import measure_file as mf  # noqa: E402
import app_ui  # noqa: E402
import plot_results  # noqa: E402

st.set_page_config(page_title="Mjeri svoj fajl", page_icon="📁", layout="wide")

RESULTS_PATH = os.path.join(KORIJEN, "benchmark", "results.csv")
PRAG_UPOZORENJA_S = 30


@st.cache_data
def ucitaj_propusnosti(putanja: str, izmijenjen: float) -> dict:
    """Propusnost po algoritmu iz ranijeg mjerenja - koristi se za procjenu trajanja."""
    if not os.path.exists(putanja):
        return {}
    df = pd.read_csv(putanja)
    enc = df[(df["operacija"] == "enkripcija") & df["propusnost_mb_s"].notna()]
    if enc.empty:
        return {}
    najvece = enc.sort_values("velicina_bajta").groupby("algoritam").last()
    return najvece["propusnost_mb_s"].to_dict()


app_ui.zaglavlje("pages/3_Mjeri_svoj_fajl.py")

st.title("📁 Mjeri svoj fajl")
st.markdown(
    "Učitaj bilo koji fajl i izmjeri koliko svaki algoritam stvarno treba da ga "
    "enkriptuje i dekriptuje. Nakon svakog mjerenja se provjerava da dekripcija "
    "vrati **bajt po bajt isti sadržaj** — mjerenje bez te provjere ne znači ništa."
)

propusnosti = ucitaj_propusnosti(RESULTS_PATH, os.path.getmtime(RESULTS_PATH)
                                 if os.path.exists(RESULTS_PATH) else 0)

fajl = st.file_uploader(
    "Fajl za mjerenje",
    help="Fajl se obrađuje u memoriji i nigdje se ne snima.",
)

if fajl is None:
    st.info(
        "Odaberi fajl iznad. Ako nemaš ništa pri ruci, dobar test je bilo koji "
        "PDF ili slika od nekoliko desetina kilobajta."
    )
    st.stop()

sadrzaj = fajl.getvalue()
st.success("**%s** — %s" % (fajl.name, mf.formatiraj_velicinu(len(sadrzaj))))

# ---------------------------------------------------------------------------
# Koliko fajla mjeriti
# ---------------------------------------------------------------------------

st.subheader("1. Koliko fajla mjeriti")

max_rucni = min(len(sadrzaj), mf.LIMIT_RUCNI)
podrazumijevano = min(len(sadrzaj), 64 * 1024)

uzorak = st.slider(
    "Broj bajtova koji se mjeri",
    min_value=min(1024, len(sadrzaj)),
    max_value=len(sadrzaj),
    value=podrazumijevano,
    step=max(1024, len(sadrzaj) // 200),
    format="%d B",
)
podaci = sadrzaj[:uzorak]

if uzorak < len(sadrzaj):
    st.caption(
        "Mjeri se prvih %s od %s. Vrijeme raste linearno s veličinom, pa se "
        "rezultat lako skalira na cijeli fajl."
        % (mf.formatiraj_velicinu(uzorak), mf.formatiraj_velicinu(len(sadrzaj)))
    )

# ---------------------------------------------------------------------------
# Izbor algoritama i procjena
# ---------------------------------------------------------------------------

st.subheader("2. Algoritmi")

odabrani = []
procjene = {}

for algoritam in mf.ALGORITMI:
    prevelik = uzorak > algoritam.limit_bajtova
    procjena = mf.procijeni_trajanje(algoritam.naziv, uzorak, propusnosti)
    procjene[algoritam.naziv] = procjena

    kolone = st.columns([3, 2, 3])
    with kolone[0]:
        oznaceno = kolone[0].checkbox(
            algoritam.naziv,
            value=not prevelik and (procjena is None or procjena < PRAG_UPOZORENJA_S),
            disabled=prevelik,
            key="mf_%s" % algoritam.naziv,
        )
    with kolone[1]:
        if prevelik:
            st.markdown(":red[preko limita od %s]"
                        % mf.formatiraj_velicinu(algoritam.limit_bajtova))
        elif procjena is not None:
            st.markdown("~%s" % mf.formatiraj_vrijeme(procjena))
        else:
            st.markdown(":grey[nema procjene]")
    with kolone[2]:
        st.caption(algoritam.opis)

    if oznaceno and not prevelik:
        odabrani.append(algoritam.naziv)

if not odabrani:
    st.warning("Odaberi bar jedan algoritam.")
    st.stop()

ukupna_procjena = sum(p for n, p in procjene.items() if n in odabrani and p)
if ukupna_procjena:
    poruka = "Procijenjeno ukupno trajanje: **%s**" % mf.formatiraj_vrijeme(ukupna_procjena)
    if ukupna_procjena > PRAG_UPOZORENJA_S:
        st.warning(poruka + " — stranica će biti blokirana dok mjerenje traje.", icon="⏳")
    else:
        st.info(poruka)

# ---------------------------------------------------------------------------
# Mjerenje
# ---------------------------------------------------------------------------

st.subheader("3. Mjerenje")

if st.button("Pokreni mjerenje", type="primary"):
    rezultati = []
    traka = st.progress(0.0, text="Priprema...")

    for redni_broj, naziv in enumerate(odabrani):
        def napredak(faza, udio, naziv=naziv, redni_broj=redni_broj):
            ukupno = (redni_broj + (udio / 2 if faza == "enkripcija" else 0.5 + udio / 2)) / len(odabrani)
            traka.progress(min(ukupno, 1.0), text="%s — %s..." % (naziv, faza))

        try:
            rezultati.append(mf.izmjeri(podaci, naziv, on_progress=napredak))
        except Exception as greska:  # noqa: BLE001 - greska jednog algoritma ne ruši stranicu
            st.error("**%s** nije izmjeren: %s" % (naziv, greska))

    traka.progress(1.0, text="Gotovo.")
    st.session_state["mf_rezultati"] = rezultati
    st.session_state["mf_ime_fajla"] = "%s (%s)" % (
        fajl.name, mf.formatiraj_velicinu(uzorak)
    )

# ---------------------------------------------------------------------------
# Rezultati
# ---------------------------------------------------------------------------

rezultati = st.session_state.get("mf_rezultati")
if not rezultati:
    st.stop()

st.divider()
st.subheader("Rezultati — %s" % st.session_state.get("mf_ime_fajla", ""))

neispravni = [r for r in rezultati if not r["ispravno"]]
if neispravni:
    st.error(
        "Dekripcija NIJE vratila original kod: %s. To je greška u implementaciji."
        % ", ".join(r["algoritam"] for r in neispravni),
        icon="🔴",
    )
else:
    st.success(
        "Svi algoritmi su vratili bajt po bajt isti sadržaj nakon dekripcije.",
        icon="✅",
    )

df = pd.DataFrame(rezultati).sort_values("vrijeme_enkripcije_s")

@plot_results.serijalizovano
def nacrtaj_rezultate(df):
    """Crtanje ide kroz isto zaključavanje kao i grafovi u plot_results."""
    fig, ax = plt.subplots(figsize=(11, max(3, 0.55 * len(df))))
    pozicije = range(len(df))
    visina = 0.38

    ax.barh([p + visina / 2 for p in pozicije], df["vrijeme_enkripcije_s"], height=visina,
            label="enkripcija", color=[plot_results.boja(a) for a in df["algoritam"]])
    ax.barh([p - visina / 2 for p in pozicije], df["vrijeme_dekripcije_s"], height=visina,
            label="dekripcija", color=[plot_results.boja(a) for a in df["algoritam"]],
            alpha=0.55)

    ax.set_yticks(list(pozicije))
    ax.set_yticklabels(df["algoritam"])
    ax.set_xscale("log")
    plot_results.oznaci_log_osu(ax, "x", "vrijeme")
    ax.set_xlabel("Vrijeme (log skala)")
    ax.grid(True, axis="x", which="both", linewidth=0.4, alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right")
    ax.set_title("Vrijeme obrade fajla — puna traka enkripcija, blijeda dekripcija")
    fig.tight_layout()
    return fig


st.image(plot_results.u_sliku(nacrtaj_rezultate(df)))

# Tabela
prikaz = pd.DataFrame({
    "Algoritam": df["algoritam"],
    "Ključ / režim": df["opis_kljuca"],
    "Enkripcija": df["vrijeme_enkripcije_s"].map(mf.formatiraj_vrijeme),
    "Dekripcija": df["vrijeme_dekripcije_s"].map(mf.formatiraj_vrijeme),
    "Propusnost (MB/s)": df["propusnost_enc_mb_s"].map(
        lambda v: "-" if pd.isna(v) else "%.3f" % v
    ),
    "Šifrat": df["velicina_sifrata"].map(mf.formatiraj_velicinu),
    "Original vraćen": df["ispravno"].map(lambda v: "da" if v else "NE"),
})
st.dataframe(prikaz, use_container_width=True, hide_index=True)

najbrzi = df.iloc[0]
najsporiji = df.iloc[-1]
if najbrzi["vrijeme_enkripcije_s"] > 0:
    odnos = najsporiji["vrijeme_enkripcije_s"] / najbrzi["vrijeme_enkripcije_s"]
    st.caption(
        "Najbrži (%s) je %.0f× brži od najsporijeg (%s) na ovom fajlu. "
        "Dio te razlike je algoritam, dio je ručna Python implementacija naspram "
        "optimizovanog C koda — vidi upozorenje na stranici Benchmark."
        % (najbrzi["algoritam"], odnos, najsporiji["algoritam"])
    )

st.download_button(
    "Preuzmi ove rezultate (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="mjerenje_%s.csv" % fajl.name,
    mime="text/csv",
)
