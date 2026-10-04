"""Reserveplan als PDF (fpdf2, Kernschrift Helvetica: Umlaute gehen, Gedankenstrich, Euro-Zeichen, Emoji und U+2212 nicht)."""
from __future__ import annotations

from fpdf import FPDF

from rsv_constants import UNITS_PER_MIN as UNITS

_REPLACE = {"–": "-", "—": "-", "−": "-", "≤": "<=", "≥": ">=", "→": "->", "↔": "<->", "…": "...", "€": "EUR", "·": ".", "Ø": "Durchschnitt"}


def _clean(text: str) -> str:
    for a, b in _REPLACE.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def table_rows(cfg: dict, alloc: list) -> list:
    """Zeilen der Tabelle: Abschnitt | Fahrzeit | Reserve (min, eine Nachkommastelle) | Fahrplanzeit; Engpässe sind gekennzeichnet."""
    rows = []
    for k in range(cfg["n"]):
        run = int(cfg["r"][k])
        res = alloc[k] / UNITS
        rows.append(f"{k + 1} | {run} | {res:.1f} | {run + res:.1f}" + ("  (Engpass)" if k in cfg["bott"] else ""))
    return rows


def generate_plan_pdf(cfg: dict, alloc: list, title: str, summary_lines: list) -> bytes:
    """`alloc` in Zehntelminuten. Je Abschnitt: planmäßige Fahrzeit, Reserve in Minuten, Fahrzeit mit Reserve (Fahrplanzeit) und Engpass-Kennzeichnung."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _clean(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for line in summary_lines:
        pdf.multi_cell(0, 5, _clean(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, _clean("Abschnitt | Fahrzeit (min) | Reserve (min) | Fahrplanzeit (min)"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for row in table_rows(cfg, alloc):
        pdf.cell(0, 5, _clean(row), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.cell(0, 5, _clean(f"Summe: Fahrzeit {int(cfg['r'].sum())} min, Reserve {sum(alloc) / UNITS:.1f} min"), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
