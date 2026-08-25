"""
Benchmark stranica - prikazuje izmjerene performanse iz benchmark/results.csv.

Mjerenje se NE pokrece ovdje: rucne implementacije DES-a i AES-a u cistom Pythonu
su prespore za rad uzivo u pregledniku (jedan prolaz kroz 64 KB traje sekundama).
Rezultati se generisu offline sa `python benchmark/run_benchmark.py`.

Grafovi se crtaju istim funkcijama koje prave i slike za rad (benchmark/plot_results.py),
pa su brojevi u aplikaciji i u izvjestaju garantovano isti.
"""
import os
import sys

import pandas as pd
import streamlit as st

KORIJEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KORIJEN)
sys.path.insert(0, os.path.join(KORIJEN, "benchmark"))

import app_ui  # noqa: E402
import plot_results  # noqa: E402

st.set_page_config(page_title="Benchmark - Enkripcijski algoritmi",
                   page_icon="📊", layout="wide")

RESULTS_PATH = os.path.join(KORIJEN, "benchmark", "results.csv")


@st.cache_data
def ucitaj_rezultate(putanja: str, izmijenjen: float) -> pd.DataFrame:
    """`izmijenjen` je u potpisu da se kes ponisti kad se CSV regeneriše."""
    return pd.read_csv(putanja)


def formatiraj_vrijeme(sekunde) -> str:
    if pd.isna(sekunde):
        return "-"
    return plot_results._formatiraj_vrijeme(sekunde)


def formatiraj_velicinu(bajtova) -> str:
    if pd.isna(bajtova):
        return "-"
    bajtova = int(bajtova)
    if bajtova >= 1_000_000:
        return "%.1f MB" % (bajtova / 1_000_000)
    if bajtova >= 1_000:
        return "%.1f KB" % (bajtova / 1_000)
    return "%d B" % bajtova


# ---------------------------------------------------------------------------

app_ui.zaglavlje("pages/2_Benchmark.py")

st.title("📊 Benchmark")

if not os.path.exists(RESULTS_PATH):
    st.error("Nema `benchmark/results.csv`.")
    st.code("python benchmark/run_benchmark.py", language="bash")
    st.stop()

df = ucitaj_rezultate(RESULTS_PATH, os.path.getmtime(RESULTS_PATH))

st.markdown(
    "Stvarna izmjerena vremena, ne brojevi preuzeti iz literature. "
    "Svaka tačka je prosjek više ponavljanja; error bar je standardna devijacija."
)

st.warning(
    "**Kako čitati ove brojeve.** DES, 3DES, AES i RSA su ručne implementacije u "
    "čistom Pythonu, pisane radi čitljivosti — ne radi "
    "brzine. ChaCha20, ECDH i varijante označene *(biblioteka)* izvršavaju se kroz "
    "optimizovani C kod. Razlika među tim grupama mjeri **implementaciju**, ne samo "
    "algoritam. Poređenja unutar iste grupe su ono što nosi zaključak.",
    icon="⚠️",
)

# ---------------------------------------------------------------------------
# Izbor algoritama
# ---------------------------------------------------------------------------

KATEGORIJE = {
    "simetricni-rucni": "Simetrični — ručna implementacija",
    "simetricni-biblioteka": "Simetrični — biblioteka",
    "asimetricni": "Asimetrični",
}

with st.sidebar:
    st.header("Prikazani algoritmi")

    dugmad = st.columns(2)
    if dugmad[0].button("Svi", use_container_width=True):
        for alg in df["algoritam"].unique():
            st.session_state["alg_%s" % alg] = True
    if dugmad[1].button("Nijedan", use_container_width=True):
        for alg in df["algoritam"].unique():
            st.session_state["alg_%s" % alg] = False

    odabrani = []
    for kategorija, naslov in KATEGORIJE.items():
        algoritmi = sorted(df[df["kategorija"] == kategorija]["algoritam"].unique())
        if not algoritmi:
            continue

        st.subheader(naslov)
        for algoritam in algoritmi:
            kljuc = "alg_%s" % algoritam
            if st.checkbox(algoritam, value=st.session_state.get(kljuc, False), key=kljuc):
                odabrani.append(algoritam)

if not odabrani:
    st.info("Odaberi bar jedan algoritam u lijevoj traci.")
    st.stop()

filtrirano = df[df["algoritam"].isin(odabrani)]

# ---------------------------------------------------------------------------
# Grafovi
# ---------------------------------------------------------------------------

tab_velicina, tab_kljuc, tab_poredjenje = st.tabs([
    "Vrijeme vs veličina podataka",
    "Generisanje ključa",
    "Direktno poređenje",
])

with tab_velicina:
    st.markdown(
        "Obje ose su logaritamske — raspon između ručnog 3DES-a i ChaCha20 "
        "prelazi četiri reda veličine, pa bi na linearnoj skali sve osim "
        "najsporijeg algoritma bilo spljošteno uz nulu."
    )
    ima_velicine = filtrirano[filtrirano["velicina_bajta"].notna()]
    if ima_velicine.empty:
        st.info("Odabrani algoritmi nemaju mjerenja po veličini podataka.")
    else:
        st.image(plot_results.u_sliku(plot_results.graf_vrijeme_vs_velicina(filtrirano)))

    with st.expander("Zašto RSA ima samo jednu tačku, a ostali imaju liniju?"):
        st.markdown(
            """
DES, AES i ChaCha20 obrađuju **ulaz proizvoljne dužine** — dijele ga na blokove i
vrte petlju. Daš im 64 bajta ili 64 kilobajta, oni rade isto, samo duže. Zato se
mogu izmjeriti na više veličina i dobiješ liniju.

RSA nije petlja. To je **jedna matematička operacija** nad jednim brojem:
`c = m^e mod n`. Poruka `m` mora biti manja od modula `n`, inače je rezultat
besmislen. Dužina ključa time direktno određuje jedinu moguću veličinu ulaza:

| Ključ | Najveća poruka |
|---|---|
| RSA-1024 | 126 B |
| RSA-2048 | 254 B |
| RSA-3072 | 382 B |
| RSA-4096 | 510 B |

Dakle nema šta da se mjeri na više veličina — jedna dužina ključa, jedno mjerenje,
jedna tačka. Položaj romba na horizontalnoj osi **nije izbor**, nego posljedica
dužine ključa.

#### Gdje graf vara

Rombovi za enkripciju leže nisko, što izgleda kao da je RSA brz. Nije — obradio je
126–510 bajtova, dok su ostali obradili do 64 KB. Kad se preračuna **po bajtu**,
slika se okreće:

| Operacija | Propusnost |
|---|---|
| RSA-2048 dekripcija | 13.7 KB/s |
| RSA-4096 dekripcija | **3.8 KB/s** |
| AES-128 dekripcija (ručna) | 24.3 KB/s |

RSA-4096 dekriptuje **6× sporije po bajtu** nego ručno pisani AES u čistom Pythonu —
a RSA pritom koristi ugrađeni `pow()` koji je optimizovani C kod, dok je AES ovdje
petlja u Pythonu. Stvarna algoritamska razlika je još mnogo veća.

Nesrazmjera enkripcija/dekripcija (RSA-4096: 0.5 ms naspram 133 ms) dolazi od toga
što je `e = 65537` broj sa samo dva postavljena bita, dok je `d` pune dužine
modula — tačno razlog zbog kojeg se `e = 65537` i bira.

**Zaključak koji iz ovoga slijedi:** RSA se u praksi nikad ne koristi za enkripciju
samih podataka, nego samo za zaštitu simetričnog ključa. To je **hibridni
kriptosistem** — možeš ga isprobati na stranici *Mjeri svoj fajl*.
"""
        )

with tab_kljuc:
    st.markdown(
        "Kod simetričnih algoritama generisanje ključa je samo čitanje slučajnih "
        "bajtova. Kod RSA znači traženje dva velika prosta broja, pa vrijeme "
        "raste naglo s dužinom ključa — i jako varira između pokretanja."
    )
    ima_keygen = filtrirano[filtrirano["operacija"] == "generisanje_kljuca"]
    if ima_keygen.empty:
        st.info("Odabrani algoritmi nemaju mjerenja generisanja ključa.")
    else:
        st.image(plot_results.u_sliku(plot_results.graf_generisanje_kljuca(filtrirano)))

with tab_poredjenje:
    dostupne_velicine = sorted(
        int(v) for v in df[df["operacija"] == "enkripcija"]["velicina_bajta"].dropna().unique()
    )
    podrazumijevana = (
        plot_results.POREDBENA_VELICINA
        if plot_results.POREDBENA_VELICINA in dostupne_velicine
        else dostupne_velicine[len(dostupne_velicine) // 2]
    )
    velicina = st.select_slider(
        "Veličina podataka za poređenje",
        options=dostupne_velicine,
        value=podrazumijevana,
        format_func=formatiraj_velicinu,
    )
    st.image(plot_results.u_sliku(plot_results.graf_poredjenje(filtrirano, velicina)))

# ---------------------------------------------------------------------------
# Tabela sirovih brojeva
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Sirovi brojevi")

operacije = st.multiselect(
    "Operacije",
    options=sorted(df["operacija"].unique()),
    default=sorted(df["operacija"].unique()),
)

tabela = filtrirano[filtrirano["operacija"].isin(operacije)].copy()
tabela = tabela.sort_values(["algoritam", "operacija", "velicina_bajta"])

prikaz = pd.DataFrame({
    "Algoritam": tabela["algoritam"],
    "Operacija": tabela["operacija"],
    "Veličina": tabela["velicina_bajta"].map(formatiraj_velicinu),
    "Ključ (bita)": tabela["duzina_kljuca_bita"].map(
        lambda v: "-" if pd.isna(v) else "%d" % int(v)
    ),
    "Srednje vrijeme": tabela["srednje_vrijeme_s"].map(formatiraj_vrijeme),
    "Std. devijacija": tabela["std_dev_s"].map(formatiraj_vrijeme),
    "Najbrže": tabela["min_vrijeme_s"].map(formatiraj_vrijeme),
    "Ponavljanja": tabela["ponavljanja"],
    "Propusnost (MB/s)": tabela["propusnost_mb_s"].map(
        lambda v: "-" if pd.isna(v) else "%.2f" % v
    ),
})

st.dataframe(prikaz, use_container_width=True, hide_index=True)

st.download_button(
    "Preuzmi results.csv",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="results.csv",
    mime="text/csv",
)

st.caption(
    "Ukupno %d mjerenja · %d algoritama · mjereno %s"
    % (
        len(df),
        df["algoritam"].nunique(),
        pd.Timestamp(os.path.getmtime(RESULTS_PATH), unit="s").strftime("%d.%m.%Y. %H:%M"),
    )
)
