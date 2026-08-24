"""
Rute web aplikacije.

Ovdje su samo stranice (Faza 6, korak 2). API pozivi koje forme koriste su u
web/api.py, registrovani pod istim blueprintom.
"""
import json
import os

import pandas as pd
from flask import Blueprint, abort, render_template, send_file

KORIJEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_CSV = os.path.join(KORIJEN, "benchmark", "results.csv")

glavni = Blueprint("glavni", __name__)

# Redoslijed u navigaciji prati specifikaciju
NAVIGACIJA = [
    ("glavni.pocetna", "Početna"),
    ("glavni.core", "Core algoritmi"),
    ("glavni.benchmark", "Benchmark"),
    ("glavni.demonstracije", "Sigurnosne demonstracije"),
]

# Iste boje kao u benchmark/plot_results.py, da grafovi u aplikaciji i slike
# u radu koriste istu paletu
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

NAZIVI_KATEGORIJA = {
    "simetricni-rucni": "Simetrični — ručna implementacija",
    "simetricni-biblioteka": "Simetrični — biblioteka",
    "asimetricni": "Asimetrični",
}

POREDBENA_VELICINA = 4096


@glavni.app_context_processor
def zajednicki_kontekst():
    return {"navigacija": NAVIGACIJA}


# ---------------------------------------------------------------------------
# Stranice
# ---------------------------------------------------------------------------

@glavni.route("/")
def pocetna():
    statistike = [
        {"broj": "6", "oznaka": "Implementiranih algoritama",
         "detalj": "DES, 3DES, AES, RSA, ECDH, ChaCha20"},
        {"broj": "4", "oznaka": "Ručnih implementacija",
         "detalj": "DES/3DES, AES, RSA — od nule, bez biblioteka"},
        {"broj": "2", "oznaka": "Demonstriranih napada",
         "detalj": "MITM na Diffie-Hellman, Wienerov napad na RSA"},
    ]
    kartice = [
        {"putanja": "glavni.core", "ikona": "🔑", "naslov": "Core algoritmi",
         "opis": "Šifruj i dešifruj tekst bilo kojim od šest algoritama."},
        {"putanja": "glavni.benchmark", "ikona": "📊", "naslov": "Benchmark",
         "opis": "Izmjerene performanse kroz veličine podataka i dužine ključeva."},
        {"putanja": "glavni.demonstracije", "ikona": "🔓",
         "naslov": "Sigurnosne demonstracije",
         "opis": "MITM na Diffie-Hellman i Wienerov napad na RSA, korak po korak."},
    ]
    return render_template("pocetna.html", statistike=statistike, kartice=kartice)


@glavni.route("/core")
def core():
    from .algoritmi import ALGORITMI, po_grupama

    return render_template(
        "core.html",
        algoritmi_po_grupi=po_grupama(),
        algoritmi_json=json.dumps(ALGORITMI, ensure_ascii=False),
    )


@glavni.route("/benchmark")
def benchmark():
    if not os.path.exists(RESULTS_CSV):
        return render_template("benchmark.html", ima_rezultate=False)

    df = pd.read_csv(RESULTS_CSV)

    po_kategoriji = {}
    for kategorija, naziv in NAZIVI_KATEGORIJA.items():
        algoritmi = sorted(df[df["kategorija"] == kategorija]["algoritam"].unique())
        if algoritmi:
            po_kategoriji[naziv] = algoritmi

    dostupne = sorted(
        int(v) for v in
        df[df["operacija"] == "enkripcija"]["velicina_bajta"].dropna().unique()
    )

    # NaN ne prezivi JSON serijalizaciju kako treba - pretvara se u None
    mjerenja = json.loads(df.to_json(orient="records"))

    return render_template(
        "benchmark.html",
        ima_rezultate=True,
        algoritmi_po_kategoriji=po_kategoriji,
        boje=BOJE,
        boje_json=json.dumps(BOJE),
        mjerenja_json=json.dumps(mjerenja, ensure_ascii=False),
        dostupne_velicine=dostupne,
        poredbena_velicina=(POREDBENA_VELICINA if POREDBENA_VELICINA in dostupne
                            else (dostupne[len(dostupne) // 2] if dostupne else 0)),
        operacije=sorted(df["operacija"].unique()),
    )


@glavni.route("/demonstracije")
def demonstracije():
    from attacks import mitm_dh

    grupe = [{"id": g.naziv, "naziv": g.naziv, "opis": g.opis}
             for g in mitm_dh.GRUPE.values()]

    return render_template(
        "demonstracije.html",
        grupe=grupe,
        grupe_json=json.dumps(grupe, ensure_ascii=False),
        podrazumijevana_poruka=mitm_dh.PORUKA,
    )


@glavni.route("/benchmark/results.csv")
def preuzmi_csv():
    if not os.path.exists(RESULTS_CSV):
        abort(404)
    return send_file(RESULTS_CSV, as_attachment=True, download_name="results.csv")
