
import datetime
import io
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

NASLOV_DOKUMENTA = "EncryptionApp — rezultati mjerenja"

# Iste boje kao u web aplikaciji, samo na bijeloj podlozi
AKCENAT = colors.HexColor("#2e7da8")
TAMNA = colors.HexColor("#1b1f27")
PRIGUSENA = colors.HexColor("#5d6675")
LINIJA = colors.HexColor("#d7dbe2")
ZEBRA = colors.HexColor("#f4f6f9")

ZAGLAVLJA = [
    "Algoritam", "Operacija", "Veličina", "Ključ (bit)",
    "Srednje vrijeme", "Std. dev.", "Ponavljanja", "Propusnost (MB/s)",
]
SIRINE = [42 * mm, 34 * mm, 24 * mm, 22 * mm, 32 * mm, 28 * mm, 26 * mm, 34 * mm]


def _registruj_fontove() -> tuple[str, str]:
    """DejaVu iz matplotliba (vec je zavisnost); Helvetica je zadnja linija odbrane."""
    try:
        import matplotlib

        ttf = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
        pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(ttf, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(ttf, "DejaVuSans-Bold.ttf")))
        return "DejaVu", "DejaVu-Bold"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


def formatiraj_vrijeme(sekunde: float) -> str:
    if sekunde is None:
        return "—"
    if sekunde >= 1:
        return f"{sekunde:.2f} s"
    if sekunde >= 1e-3:
        return f"{sekunde * 1e3:.2f} ms"
    return f"{sekunde * 1e6:.0f} µs"


def formatiraj_bajtove(bajtova) -> str:
    """Tri znacajne cifre, isto kao u tabeli na stranici (1.02 KB, 16.4 KB)."""
    if bajtova is None:
        return "—"
    bajtova = float(bajtova)
    if bajtova >= 1e6:
        return f"{bajtova / 1e6:.3g} MB"
    if bajtova >= 1e3:
        return f"{bajtova / 1e3:.3g} KB"
    return f"{bajtova:g} B"


def napravi_pdf(df, nazivi_operacija: dict, nazivi_kategorija: dict,
                opis_izbora: str = "") -> io.BytesIO:

    font, font_bold = _registruj_fontove()

    # Podrazumijevani leading u reportlabu je 12 bez obzira na velicinu fonta,
    # pa se veci naslov preklapa s narednim redom - zato je svugdje eksplicitan.
    stil_naslov = ParagraphStyle("naslov", fontName=font_bold, fontSize=16,
                                 leading=21, textColor=TAMNA, spaceAfter=6,
                                 alignment=TA_LEFT)
    stil_podnaslov = ParagraphStyle("podnaslov", fontName=font, fontSize=8.5,
                                    leading=12.5, textColor=PRIGUSENA, spaceAfter=12)
    stil_grupa = ParagraphStyle("grupa", fontName=font_bold, fontSize=10,
                                leading=14, textColor=AKCENAT,
                                spaceBefore=10, spaceAfter=5)

    spremnik = io.BytesIO()
    dokument = BaseDocTemplate(
        spremnik, pagesize=landscape(A4),
        leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=13 * mm, bottomMargin=15 * mm,
        title=NASLOV_DOKUMENTA, author="EncryptionApp",
        subject="Izmjerene performanse enkripcijskih algoritama",
    )

    def podnozje(platno, dok):
        platno.saveState()
        platno.setFont(font, 7.5)
        platno.setFillColor(PRIGUSENA)
        platno.drawString(14 * mm, 8 * mm,
                          "EncryptionApp · završni rad prvog ciklusa · "
                          "Elektrotehnički fakultet, Univerzitet u Sarajevu")
        platno.drawRightString(dok.pagesize[0] - 14 * mm, 8 * mm, f"Strana {dok.page}")
        platno.setStrokeColor(LINIJA)
        platno.line(14 * mm, 11 * mm, dok.pagesize[0] - 14 * mm, 11 * mm)
        platno.restoreState()

    okvir = Frame(dokument.leftMargin, dokument.bottomMargin,
                  dokument.width, dokument.height, id="glavni")
    dokument.addPageTemplates([PageTemplate(id="sve", frames=[okvir], onPage=podnozje)])

    datum = datetime.datetime.now().strftime("%d.%m.%Y. u %H:%M")
    obim = (f"Izbor: <b>{opis_izbora}</b> — {len(df)} mjerenja"
            if opis_izbora else f"Svih {len(df)} mjerenja")
    prica = [
        Paragraph(NASLOV_DOKUMENTA, stil_naslov),
        Paragraph(
            f"{obim} iz <b>benchmark/results.csv</b>, grupisano po "
            f"algoritmu. Srednje vrijeme i standardna devijacija računati su preko "
            f"navedenog broja ponavljanja. Izvezeno {datum}.",
            stil_podnaslov,
        ),
    ]

    kategorije = {k: naziv for k, naziv in nazivi_kategorija.items()}
    for algoritam in sorted(df["algoritam"].unique()):
        dio = df[df["algoritam"] == algoritam].sort_values(
            ["operacija", "velicina_bajta"], na_position="first")
        kategorija = kategorije.get(dio.iloc[0]["kategorija"], dio.iloc[0]["kategorija"])
        prica.append(Paragraph(f"{algoritam} — {kategorija}", stil_grupa))

        podaci = [ZAGLAVLJA]
        for _, m in dio.iterrows():
            velicina = m["velicina_bajta"]
            propusnost = m["propusnost_mb_s"]
            kljuc = m["duzina_kljuca_bita"]
            podaci.append([
                algoritam,
                nazivi_operacija.get(m["operacija"], m["operacija"]),
                formatiraj_bajtove(None if velicina != velicina else velicina),
                "—" if kljuc != kljuc else f"{int(kljuc)}",
                formatiraj_vrijeme(m["srednje_vrijeme_s"]),
                formatiraj_vrijeme(m["std_dev_s"]),
                f"{int(m['ponavljanja'])}",
                "—" if propusnost != propusnost else f"{propusnost:.3f}",
            ])

        tabela = Table(podaci, colWidths=SIRINE, repeatRows=1, hAlign="LEFT")
        tabela.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), font_bold),
            ("FONTNAME", (0, 1), (-1, -1), font),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 0), (-1, 0), AKCENAT),
            ("TEXTCOLOR", (0, 1), (-1, -1), TAMNA),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
            ("LINEBELOW", (0, 1), (-1, -1), 0.25, LINIJA),
            ("BOX", (0, 0), (-1, -1), 0.5, LINIJA),
        ]))
        prica.append(tabela)
        prica.append(Spacer(1, 4))

    dokument.build(prica)
    spremnik.seek(0)
    return spremnik
