"""
Crta grafove iz benchmark/results.csv i snima ih kao PNG u benchmark/figures/.

Pokreni (nakon run_benchmark.py):
    python benchmark/plot_results.py

Ove slike idu direktno u poglavlje 3.5 rada. Streamlit aplikacija ne koristi
ove PNG-ove nego crta interaktivne verzije istih grafova iz istog CSV-a, pa su
brojevi u radu i u aplikaciji garantovano isti.
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")  # bez GUI-ja - skripta se pokrece iz terminala
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_PATH = os.path.join(HERE, "results.csv")
FIGURES_DIR = os.path.join(HERE, "figures")

# Velicina na kojoj se pravi direktno poredjenje (mora postojati u results.csv)
POREDBENA_VELICINA = 4_096

# Stabilne boje po algoritmu - ista boja na svim grafovima i u aplikaciji
BOJE = {
    "DES": "#c1440e",
    "3DES": "#e07a3f",
    "AES-128": "#1f5673",
    "AES-192": "#2e7da8",
    "AES-256": "#4aa3d0",
    "AES-128 (biblioteka)": "#7fbf7f",
    "ChaCha20": "#2e8b57",
    "RSA-1024": "#6a4c93",
    "RSA-2048": "#8360b0",
    "RSA-3072": "#a07bc9",
    "RSA-4096": "#bd97e0",
    "ECDH (X25519)": "#b0306a",
}


def ucitaj() -> pd.DataFrame:
    if not os.path.exists(RESULTS_PATH):
        sys.exit(
            "Nema %s - prvo pokreni:\n    python benchmark/run_benchmark.py"
            % RESULTS_PATH
        )
    return pd.read_csv(RESULTS_PATH)


def boja(algoritam: str) -> str:
    return BOJE.get(algoritam, "#888888")


def _stil_ose(ax, xlabel, ylabel, naslov):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(naslov)
    ax.grid(True, which="both", linewidth=0.4, alpha=0.5)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# Graf 1: vrijeme vs velicina podataka
# ---------------------------------------------------------------------------

def graf_vrijeme_vs_velicina(df: pd.DataFrame):
    """
    Log-log skala jer se raspon proteze preko vise redova velicine: rucni DES
    na 64 KB i ChaCha20 na 1 KB razlikuju se za faktor od preko 10^5.
    """
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)

    for ax, operacija in zip(axes, ("enkripcija", "dekripcija")):
        podaci = df[(df["operacija"] == operacija) & df["velicina_bajta"].notna()]

        for algoritam in sorted(podaci["algoritam"].unique()):
            serija = podaci[podaci["algoritam"] == algoritam].sort_values("velicina_bajta")
            if serija.empty:
                continue

            # RSA ima samo jednu tacku (jedan blok), pa se crta kao marker
            stil = "o-" if len(serija) > 1 else "D"
            ax.errorbar(
                serija["velicina_bajta"], serija["srednje_vrijeme_s"],
                yerr=serija["std_dev_s"], fmt=stil, capsize=3, markersize=5,
                linewidth=1.6, label=algoritam, color=boja(algoritam),
            )

        ax.set_xscale("log")
        ax.set_yscale("log")
        _stil_ose(ax, "Velicina podataka (bajtova)", "Vrijeme (s)", operacija.capitalize())

    axes[1].legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, frameon=False)
    fig.suptitle(
        "Vrijeme obrade u odnosu na velicinu podataka (log-log)",
        fontsize=13, fontweight="bold",
    )
    fig.text(
        0.5, 0.005,
        "DES/3DES/AES su rucne Python implementacije; ChaCha20 i '(biblioteka)' "
        "idu kroz optimizovani C kod. RSA je jedan blok, pa ima jednu tacku.",
        ha="center", fontsize=8, style="italic",
    )
    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    return fig


# ---------------------------------------------------------------------------
# Graf 2: generisanje kljuca vs duzina kljuca
# ---------------------------------------------------------------------------

def graf_generisanje_kljuca(df: pd.DataFrame):
    """
    RSA je ovdje jedini zanimljiv slucaj: generisanje kljuca znaci trazenje dva
    velika prosta broja, pa vrijeme raste naglo s duzinom kljuca - i ima ogromnu
    varijansu, jer je pretraga probabilisticka.
    """
    podaci = df[df["operacija"] == "generisanje_kljuca"].copy()
    fig, (ax_rsa, ax_ostali) = plt.subplots(1, 2, figsize=(13, 5))

    # Lijevo: RSA kroz duzine kljuca
    rsa_podaci = podaci[podaci["algoritam"].str.startswith("RSA")].sort_values(
        "duzina_kljuca_bita"
    )
    if not rsa_podaci.empty:
        ax_rsa.errorbar(
            rsa_podaci["duzina_kljuca_bita"], rsa_podaci["srednje_vrijeme_s"],
            yerr=rsa_podaci["std_dev_s"], fmt="o-", capsize=4, markersize=7,
            linewidth=2, color=boja("RSA-2048"),
        )
        ax_rsa.set_xticks(rsa_podaci["duzina_kljuca_bita"])
        ax_rsa.set_yscale("log")
        _stil_ose(ax_rsa, "Duzina kljuca (bita)", "Vrijeme (s)",
                  "RSA - generisanje para kljuceva")
        ax_rsa.text(
            0.03, 0.95,
            "Error bar = standardna devijacija.\nVelika varijansa je ocekivana:\n"
            "trazenje prostog broja je probabilisticko.",
            transform=ax_rsa.transAxes, va="top", fontsize=8,
            bbox=dict(boxstyle="round", facecolor="#f5f5f5", edgecolor="#cccccc"),
        )

    # Desno: svi ostali - red velicine manji, pa idu na zaseban graf
    ostali = podaci[~podaci["algoritam"].str.startswith("RSA")].sort_values(
        "srednje_vrijeme_s"
    )
    if not ostali.empty:
        pozicije = list(range(len(ostali)))
        # Tacke umjesto traka: na logaritamskoj skali duzina trake nije
        # proporcionalna vrijednosti, pa bi trake obmanjivale oko.
        ax_ostali.hlines(
            pozicije, 0, ostali["srednje_vrijeme_s"],
            color=[boja(a) for a in ostali["algoritam"]], linewidth=1.5, alpha=0.5,
        )
        ax_ostali.errorbar(
            ostali["srednje_vrijeme_s"], pozicije, xerr=ostali["std_dev_s"],
            fmt="o", markersize=9, capsize=4, linestyle="none", color="#333333",
            zorder=3,
        )
        for pozicija, (_, red) in zip(pozicije, ostali.iterrows()):
            ax_ostali.plot(red["srednje_vrijeme_s"], pozicija, "o", markersize=7,
                           color=boja(red["algoritam"]), zorder=4)

        ax_ostali.set_yticks(pozicije)
        ax_ostali.set_yticklabels(ostali["algoritam"])
        ax_ostali.set_xscale("log")
        _stil_ose(ax_ostali, "Vrijeme (s)", "",
                  "Ostali algoritmi - generisanje kljuca")
        ax_ostali.text(
            0.97, 0.05,
            "Svi su reda mikrosekunde ili brze -\ngenerisanje simetricnog kljuca je\nsamo citanje iz izvora slucajnosti.",
            transform=ax_ostali.transAxes, va="bottom", ha="right", fontsize=8,
            bbox=dict(boxstyle="round", facecolor="#f5f5f5", edgecolor="#cccccc"),
        )

    fig.suptitle(
        "Vrijeme generisanja kljuca u odnosu na duzinu kljuca",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


# ---------------------------------------------------------------------------
# Graf 3: direktno poredjenje pri fiksnoj velicini
# ---------------------------------------------------------------------------

def graf_poredjenje(df: pd.DataFrame, velicina=POREDBENA_VELICINA):
    """
    Bar chart pri fiksnoj velicini podataka. RSA ne moze enkriptovati 4 KB
    odjednom, pa se za njega uzima njegov jedini blok - to je na grafu
    eksplicitno oznaceno, da poredjenje ne bude obmanjujuce.
    """
    podaci = df[(df["operacija"] == "enkripcija") & df["velicina_bajta"].notna()]

    redovi = []
    for algoritam in podaci["algoritam"].unique():
        serija = podaci[podaci["algoritam"] == algoritam].copy()
        # Najbliza izmjerena velicina trazenoj
        serija["razlika"] = (serija["velicina_bajta"] - velicina).abs()
        redovi.append(serija.sort_values("razlika").iloc[0])

    if not redovi:
        # Npr. odabran je samo ECDH, koji ne enkriptuje nego razmjenjuje kljuceve
        fig, ax = plt.subplots(figsize=(11, 3))
        ax.text(0.5, 0.5,
                "Odabrani algoritmi nemaju mjerenja enkripcije,\n"
                "pa nema sta da se poredi pri fiksnoj velicini podataka.",
                ha="center", va="center", fontsize=11)
        ax.axis("off")
        return fig

    poredjenje = pd.DataFrame(redovi).sort_values("srednje_vrijeme_s")

    fig, ax = plt.subplots(figsize=(11, 6))
    pozicije = range(len(poredjenje))
    ax.bar(
        list(pozicije), poredjenje["srednje_vrijeme_s"],
        yerr=poredjenje["std_dev_s"], capsize=4,
        color=[boja(a) for a in poredjenje["algoritam"]],
    )

    oznake = []
    for _, red in poredjenje.iterrows():
        oznaka = red["algoritam"]
        if int(red["velicina_bajta"]) != velicina:
            oznaka += "\n(%d B)" % int(red["velicina_bajta"])
        oznake.append(oznaka)

    ax.set_xticks(list(pozicije))
    ax.set_xticklabels(oznake, rotation=45, ha="right", fontsize=9)
    ax.set_yscale("log")
    _stil_ose(ax, "", "Vrijeme enkripcije (s, log skala)",
              "Poredjenje algoritama pri velicini podataka od %d B" % velicina)

    for pozicija, vrijeme in zip(pozicije, poredjenje["srednje_vrijeme_s"]):
        ax.text(pozicija, vrijeme * 1.35, _formatiraj_vrijeme(vrijeme),
                ha="center", fontsize=8)

    fig.text(
        0.5, 0.01,
        "Velicina u zagradi znaci da algoritam nije mjeren na %d B - RSA obradjuje "
        "samo jedan blok manji od modula." % velicina,
        ha="center", fontsize=8, style="italic",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


def _formatiraj_vrijeme(sekunde: float) -> str:
    if sekunde >= 1:
        return "%.2f s" % sekunde
    if sekunde >= 1e-3:
        return "%.2f ms" % (sekunde * 1e3)
    return "%.1f us" % (sekunde * 1e6)


def snimi(fig, ime: str) -> str:
    os.makedirs(FIGURES_DIR, exist_ok=True)
    putanja = os.path.join(FIGURES_DIR, ime)
    fig.savefig(putanja, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  snimljeno: %s" % putanja)
    return putanja


# ---------------------------------------------------------------------------
# Tabela sirovih brojeva
# ---------------------------------------------------------------------------

def ispisi_tabelu(df: pd.DataFrame):
    """Sazeta tabela za brzu kontrolu - puna tabela je u aplikaciji ispod grafova."""
    print("\nPoredjenje pri %d B (enkripcija):" % POREDBENA_VELICINA)
    print("-" * 72)
    print("%-24s %14s %14s %8s" % ("algoritam", "vrijeme", "std dev", "n"))
    print("-" * 72)

    podaci = df[
        (df["operacija"] == "enkripcija")
        & (df["velicina_bajta"] == POREDBENA_VELICINA)
    ].sort_values("srednje_vrijeme_s")

    for _, red in podaci.iterrows():
        print("%-24s %14s %14s %8d" % (
            red["algoritam"],
            _formatiraj_vrijeme(red["srednje_vrijeme_s"]),
            _formatiraj_vrijeme(red["std_dev_s"]),
            red["ponavljanja"],
        ))
    print("-" * 72)


def main():
    df = ucitaj()
    print("Ucitano %d mjerenja iz %s\n" % (len(df), RESULTS_PATH))

    snimi(graf_vrijeme_vs_velicina(df), "slika_vrijeme_vs_velicina.png")
    snimi(graf_generisanje_kljuca(df), "slika_generisanje_kljuca.png")
    snimi(graf_poredjenje(df), "slika_poredjenje.png")

    ispisi_tabelu(df)


if __name__ == "__main__":
    main()
