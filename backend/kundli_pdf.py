"""Branded PDF of the computed Kundli report (fpdf2, bundled fonts; Devanagari omitted, IAST kept)."""
import re
from pathlib import Path

from fpdf import FPDF

FONTS = Path(__file__).parent / "data" / "fonts"
LOGO = Path(__file__).parent.parent / "frontend" / "public" / "brand-mark.png"
NAVY, GOLD, INK, MUTED = (11, 18, 37), (176, 143, 42), (30, 34, 45), (95, 104, 120)
_DEVA = re.compile(r"[\u0900-\u097F]+[\s\u0900-\u097F]*")


def _clean(s):
    s = _DEVA.sub("", str(s)).replace("()", "").replace("( ", "(")
    s = re.sub(r": \(([^()]*)\)$", r": \1", s)
    return re.sub(r"\s{2,}", " ", s).strip()


class _Doc(FPDF):
    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 18, "F")
        if LOGO.exists():
            self.image(str(LOGO), 10, 3, 12, 12)
        self.set_xy(25, 5)
        self.set_font("Cinzel", size=13)
        self.set_text_color(244, 214, 117)
        self.cell(0, 8, "NAKSHATRAVEDA")
        self.set_xy(120, 5)
        self.set_font("Jakarta", size=8)
        self.set_text_color(185, 194, 211)
        self.cell(80, 8, "Verified Vedic Astrologers", align="R")
        self.set_y(24)

    def footer(self):
        self.set_y(-12)
        self.set_font("Jakarta", size=7)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"Calculated by NakshatraVeda. Traditional guidance only, not a guarantee.   Page {self.page_no()}", align="C")


def build(inp, chart, ai=None):
    pdf = _Doc(format="A4")
    pdf.add_font("Jakarta", "", str(FONTS / "Jakarta.ttf"))
    pdf.add_font("Cinzel", "", str(FONTS / "Cinzel.ttf"))
    pdf.set_auto_page_break(True, margin=16)
    pdf.set_margins(14, 24, 14)
    pdf.add_page()
    W = pdf.epw

    def h(text, size=12, color=GOLD, gap=2):
        pdf.ln(gap)
        pdf.set_font("Cinzel", size=size)
        pdf.set_text_color(*color)
        pdf.multi_cell(W, size * 0.5, _clean(text))
        pdf.ln(1)

    def p(text, size=9, color=INK):
        pdf.set_font("Jakarta", size=size)
        pdf.set_text_color(*color)
        pdf.multi_cell(W, size * 0.48, _clean(text))
        pdf.ln(0.8)

    b, rep = chart["birth"], chart["report"]
    h(f"Kundli report: {inp.get('name') or 'Birth chart'}", 16, NAVY, 0)
    p(f"{inp['date']} {'(birth time unknown, 12:00 used)' if rep['time_unknown'] else inp['time']}  |  {inp['place']}  |  {inp['tz']}", 9, MUTED)
    p(f"Lagna {chart['ascendant']['sign']}  |  Moon {chart['moon_sign']}  |  Nakshatra {chart['janma_nakshatra']} pada {chart['janma_pada']}  |  "
      f"D9 Lagna {chart['navamsa']['ascendant']['sign']}  |  D10 Lagna {chart['dashamsa']['ascendant']['sign']}", 9)
    h("Summary", 12)
    for s in rep["summary"]:
        p(f"- {s}")
    ai_map = {"overview": "personality", "career": "career", "finance": "finance", "relationships": "relationships", "education": "education", "family": "wellbeing", "dasha": "dasha"}
    for s in rep["sections"]:
        if s["id"] == "overview":
            continue
        h(s["title"] + ("  (depends on birth time)" if s["time_sensitive"] and rep["time_unknown"] else ""), 12)
        if s["facts"]:
            p("Calculated", 8, MUTED)
            for f in s["facts"]:
                p(f"- {f}")
        for t in s["text"]:
            p(t)
        for it in s["items"]:
            p(it["title"], 9.5, NAVY)
            for k, v in it["rows"]:
                p(f"{k}: {v}", 8.5)
        if s.get("checklist"):
            for d in s["checklist"]:
                p(f"[ ] Day {d['day']}: {d['task']}", 8.5)
        if s.get("unavailable"):
            p("Not available: " + "; ".join(s["unavailable"]), 8, MUTED)
        if ai and ai_map.get(s["id"]) in ai.get("sections", {}):
            p("AI interpretation (written from the calculations above)", 8, GOLD)
            p(ai["sections"][ai_map[s["id"]]])
    return bytes(pdf.output())
