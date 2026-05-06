"""
PDF Service — สร้างใบสรุปขึ้นรถ
"""
import base64
from pathlib import Path
from fpdf import FPDF

FONT_DIR = Path(__file__).parent.parent / "fonts"


class DispatchPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.add_font("Sarabun", style="",  fname=str(FONT_DIR / "Sarabun-Regular.ttf"))
        self.add_font("Sarabun", style="B", fname=str(FONT_DIR / "Sarabun-Bold.ttf"))
        self.set_auto_page_break(auto=True, margin=12)
        self.set_margins(12, 12, 12)

    def header(self):
        pass  # custom header ใน build_dispatch_pdf


def build_dispatch_pdf(
    doc_no: str,
    route: str,
    plate: str,
    driver: str,
    depart_time: str,
    date_str: str,
    sos: list,
    notes: dict,
) -> bytes:
    """
    sos: list of dict {so, customer, province, carrier, received, packages, qty}
    notes: dict {so_id: note_text}
    คืนค่า bytes ของ PDF
    """
    pdf = DispatchPDF()
    pdf.add_page()

    W = pdf.w - pdf.l_margin - pdf.r_margin  # usable width

    # ── Title ──────────────────────────────────────────────────────────────
    pdf.set_font("Sarabun", "B", 18)
    pdf.cell(W, 9, f"ใบสรุปขึ้นรถ  {doc_no}", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Sarabun", "", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(W, 6, "เอกสารนี้สร้างโดยอัตโนมัติจากระบบ Odoo TV Dashboard",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    # ── Info box ────────────────────────────────────────────────────────────
    box_h = 7
    half  = W / 2

    def info_row(label, value, x_offset=0):
        pdf.set_x(pdf.l_margin + x_offset)
        pdf.set_font("Sarabun", "", 11)
        pdf.cell(30, box_h, label, border=0)
        pdf.set_font("Sarabun", "B", 11)
        pdf.cell(half - 30, box_h, value, border=0)

    pdf.set_fill_color(240, 244, 248)
    pdf.rect(pdf.l_margin, pdf.get_y(), W, box_h * 3 + 4, style="F")
    pdf.ln(2)
    info_row("เลขที่เอกสาร :", doc_no)
    info_row("วันที่ :", date_str, x_offset=half)
    pdf.ln(box_h)
    info_row("เส้นทาง :", route)
    info_row("เวลาออกรถ :", f"{depart_time} น.", x_offset=half)
    pdf.ln(box_h)
    info_row("ทะเบียนรถ :", plate)
    info_row("คนขับ :", driver, x_offset=half)
    pdf.ln(box_h + 6)

    # ── Table header ────────────────────────────────────────────────────────
    col = {"#": 8, "SO": 24, "ลูกค้า": 70, "จังหวัด": 28,
           "ขนส่ง": 40, "บิล": 14, "แพ็ค": 14, "ชิ้น": 14, "หมายเหตุ": 54}
    row_h = 7

    pdf.set_fill_color(26, 26, 46)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Sarabun", "B", 10)
    for label, w in col.items():
        pdf.cell(w, row_h, label, border=0, align="C", fill=True)
    pdf.ln(row_h)

    # ── Table rows ──────────────────────────────────────────────────────────
    pdf.set_text_color(0, 0, 0)
    total_pack = total_qty = 0
    for i, s in enumerate(sos):
        fill_color = (248, 250, 252) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill_color)
        pdf.set_font("Sarabun", "", 10)

        note = notes.get(str(s.get("so_id", "")), "") or notes.get(s.get("so", ""), "")
        bill = "รับ" if s.get("received") else "-"
        pkg  = s.get("packages", 0)
        qty  = s.get("qty", 0)
        total_pack += pkg
        total_qty  += qty

        pdf.cell(col["#"],    row_h, str(i + 1),          align="C", fill=True)
        pdf.cell(col["SO"],   row_h, s.get("so", ""),     align="C", fill=True)
        pdf.cell(col["ลูกค้า"], row_h, s.get("customer", ""), fill=True)
        pdf.cell(col["จังหวัด"], row_h, s.get("province", ""), align="C", fill=True)
        pdf.cell(col["ขนส่ง"], row_h, s.get("carrier", ""),  fill=True)
        pdf.cell(col["บิล"],   row_h, bill,               align="C", fill=True)
        pdf.cell(col["แพ็ค"],  row_h, str(pkg),            align="C", fill=True)
        pdf.cell(col["ชิ้น"],  row_h, str(qty),            align="C", fill=True)
        pdf.cell(col["หมายเหตุ"], row_h, note,             fill=True)
        pdf.ln(row_h)

    # ── Summary row ─────────────────────────────────────────────────────────
    pdf.set_fill_color(230, 236, 242)
    pdf.set_font("Sarabun", "B", 10)
    sum_w = sum(col[k] for k in ["#", "SO", "ลูกค้า", "จังหวัด", "ขนส่ง", "บิล"])
    pdf.cell(sum_w, row_h, f"รวม {len(sos)} SO", align="R", fill=True)
    pdf.cell(col["แพ็ค"], row_h, str(total_pack), align="C", fill=True)
    pdf.cell(col["ชิ้น"], row_h, str(total_qty),  align="C", fill=True)
    pdf.cell(col["หมายเหตุ"], row_h, "", fill=True)
    pdf.ln(row_h + 10)

    # ── Signature boxes ──────────────────────────────────────────────────────
    sig_w = W / 2 - 10
    pdf.set_font("Sarabun", "", 10)
    pdf.set_draw_color(100, 100, 100)

    for label, name in [
        ("ลายมือชื่อผู้จัดส่ง / คนขับ", driver),
        ("ลายมือชื่อผู้รับของ", ""),
    ]:
        x = pdf.get_x()
        y = pdf.get_y()
        pdf.rect(x, y, sig_w, 20)
        pdf.set_xy(x, y + 14)
        pdf.cell(sig_w, 5, f"({name})" if name else "", align="C")
        pdf.set_xy(x, y + 20)
        pdf.cell(sig_w, 5, label, align="C")
        pdf.set_xy(x + sig_w + 20, y)

    return bytes(pdf.output())


def pdf_to_base64(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("utf-8")
