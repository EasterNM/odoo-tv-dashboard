"""
Dispatch Service — Tablet Loading Page
จัดการข้อมูลสำหรับหน้า tablet ยืนยันขึ้นรถ
"""
from datetime import datetime, timezone, timedelta
from services.odoo_client import odoo
from services.pdf_service import build_dispatch_pdf, pdf_to_base64

FIELD_ROUTE      = "x_studio_selection_field_92b_1jnor75f1"
FIELD_RECEIVED   = "x_studio_boolean_field_5bd_1jnp0r53i"
FIELD_DISPATCHED = "x_studio_boolean_field_2dc_1jnrn22ck"
DATE_FROM        = "2026-05-01 00:00:00"
THAI_TZ          = timezone(timedelta(hours=7))

DISPATCH_MODEL   = "x_tv_dashboard_dispatc"

ROUTE_ORDER = ["กรุงเทพ", "สายใน", "สายนอก", "รับหน้าบริษัท", "เซลล์ส่งเอง"]
ROUTE_COLOR = {
    "กรุงเทพ":       "#1f6feb",
    "สายใน":         "#238636",
    "สายนอก":        "#b45309",
    "รับหน้าบริษัท": "#7c3aed",
    "เซลล์ส่งเอง":   "#dc2626",
}
ROUTE_ICON = {
    "กรุงเทพ":       "🏙️",
    "สายใน":         "🛣️",
    "สายนอก":        "🚛",
    "รับหน้าบริษัท": "🏢",
    "เซลล์ส่งเอง":   "🧑‍💼",
}
NO_ROUTE = "ยังไม่ระบุเส้นทาง"


def _next_dispatch_doc_number(year: int) -> str:
    prefix = f"DT{year}/"
    count = odoo.models.execute_kw(
        odoo.db, odoo.authenticate(), odoo.password,
        DISPATCH_MODEL, "search_count",
        [[["x_name", "like", prefix + "%"]]],
    )
    return f"{prefix}{count + 1:04d}"


def _parse_depart_time(depart_time: str, thai_now: datetime) -> str:
    """แปลง 'HH:MM' + วันที่ไทย → UTC datetime string สำหรับ Odoo"""
    try:
        parts = depart_time.replace(".", ":").split(":")
        hh, mm = int(parts[0]), int(parts[1])
        d = thai_now.date()
        depart_thai = datetime(d.year, d.month, d.day, hh, mm, 0, tzinfo=THAI_TZ)
        return depart_thai.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _get_pickings() -> list:
    return odoo.search_read("stock.picking", [
        ("state", "not in", ["cancel", "done"]),
        ("picking_type_id", "=", 2),
        ("create_date", ">=", DATE_FROM),
        ("origin", "!=", False),
    ], ["name", "origin", "partner_id", "sale_id", "package_level_ids"], limit=500)


def get_dispatch_routes() -> list:
    pickings = _get_pickings()
    if not pickings:
        return []

    sale_ids = list({p["sale_id"][0] for p in pickings if p.get("sale_id")})
    orders = odoo.search_read("sale.order",
        [("id", "in", sale_ids), (FIELD_DISPATCHED, "=", False)],
        ["id", FIELD_ROUTE], limit=len(sale_ids) + 10)

    route_sos: dict[str, set] = {}
    for o in orders:
        route = o.get(FIELD_ROUTE) or NO_ROUTE
        route_sos.setdefault(route, set()).add(o["id"])

    result = []
    seen = set()
    for route in ROUTE_ORDER:
        if route in route_sos:
            result.append({
                "route":    route,
                "so_count": len(route_sos[route]),
                "color":    ROUTE_COLOR.get(route, "#555"),
                "icon":     ROUTE_ICON.get(route, "📦"),
            })
            seen.add(route)
    for route in sorted(route_sos):
        if route not in seen:
            result.append({
                "route":    route,
                "so_count": len(route_sos[route]),
                "color":    "#555",
                "icon":     "📦",
            })
    return result


def get_route_sos(route_name: str) -> dict:
    pickings = _get_pickings()
    if not pickings:
        return {"route": route_name, "so_count": 0, "sos": []}

    sale_ids = list({p["sale_id"][0] for p in pickings if p.get("sale_id")})

    orders = odoo.search_read("sale.order",
        [("id", "in", sale_ids), (FIELD_DISPATCHED, "=", False)], [
        "id", "name", FIELD_ROUTE, "delivery_method", FIELD_RECEIVED, "partner_id",
    ], limit=len(sale_ids) + 10)

    route_order_ids = {
        o["id"] for o in orders
        if (o.get(FIELD_ROUTE) or NO_ROUTE) == route_name
    }
    if not route_order_ids:
        return {"route": route_name, "so_count": 0, "sos": []}

    lines = odoo.search_read("sale.order.line",
        [("order_id", "in", list(route_order_ids))],
        ["order_id", "product_uom_qty"], limit=5000)
    qty_map: dict[int, float] = {}
    for l in lines:
        oid = l["order_id"][0]
        qty_map[oid] = qty_map.get(oid, 0) + l["product_uom_qty"]

    partner_ids = list({
        o["partner_id"][0] for o in orders
        if o.get("partner_id") and o["id"] in route_order_ids
    })
    partners = odoo.search_read("res.partner", [("id", "in", partner_ids)],
        ["id", "state_id"], limit=len(partner_ids) + 5)
    partner_province = {
        p["id"]: p["state_id"][1].replace(" (TH)", "") if p.get("state_id") else "-"
        for p in partners
    }

    so_map: dict[int, dict] = {}
    for o in orders:
        if o["id"] not in route_order_ids:
            continue
        pid = o["partner_id"][0] if o.get("partner_id") else None
        so_map[o["id"]] = {
            "so_id":    o["id"],
            "so":       o["name"],
            "customer": o["partner_id"][1] if o.get("partner_id") else "-",
            "province": partner_province.get(pid, "-"),
            "carrier":  o["delivery_method"][1] if o.get("delivery_method") else "-",
            "received": bool(o.get(FIELD_RECEIVED)),
            "qty":      int(qty_map.get(o["id"], 0)),
            "packages": 0,
        }

    for p in pickings:
        so_id = p["sale_id"][0] if p.get("sale_id") else None
        if so_id and so_id in so_map:
            so_map[so_id]["packages"] += len(p.get("package_level_ids") or [])

    result = sorted(so_map.values(), key=lambda x: (x["carrier"], x["so"]))
    return {
        "route":    route_name,
        "color":    ROUTE_COLOR.get(route_name, "#555"),
        "so_count": len(result),
        "sos":      result,
    }


def confirm_dispatch(route: str, so_ids: list, plate: str, driver: str,
                     depart_time: str, notes: dict) -> dict:
    """
    1. สร้าง x_tv_dashboard_dispatc record
    2. Mark ขึ้นรถจัดส่งแล้ว = True บน sale.order
    3. Post chatter บน dispatch record + แต่ละ SO
    """
    if not so_ids:
        return {"ok": False, "error": "ไม่มี SO ที่เลือก"}

    now_thai   = datetime.now(timezone.utc).astimezone(THAI_TZ)
    date_str   = now_thai.strftime("%d/%m/%Y")
    depart_utc = _parse_depart_time(depart_time, now_thai)

    orders = odoo.search_read("sale.order", [("id", "in", so_ids)],
        ["id", "name", "partner_id", "delivery_method",
         FIELD_RECEIVED, "x_studio_selection_field_92b_1jnor75f1"],
        limit=len(so_ids) + 5)
    order_map  = {o["id"]: o for o in orders}
    so_names   = ", ".join(order_map[i]["name"] for i in so_ids if i in order_map)

    # ── 1. Mark ขึ้นรถแล้ว บน sale.order ────────────────────────────────
    odoo.write("sale.order", so_ids, {FIELD_DISPATCHED: True})

    # ── 2. สร้าง dispatch record ─────────────────────────────────────────
    doc_no      = _next_dispatch_doc_number(now_thai.year)
    dispatch_id = odoo.create(DISPATCH_MODEL, {
        "x_name":        doc_no,
        "x_route":       route,
        "x_plate":       plate,
        "x_driver":      driver,
        "x_depart_time": depart_utc,
        "x_state":       "confirmed",
        "x_so_ids":      [[6, 0, so_ids]],
    })

    # ── 3. สร้าง PDF ──────────────────────────────────────────────────────
    # ดึง packages/qty จาก get_route_sos (มีแล้วใน soData ฝั่ง frontend)
    # แต่ที่นี่ต้องดึง packages จาก pickings
    pickings = odoo.search_read("stock.picking", [
        ("sale_id", "in", so_ids),
        ("picking_type_id", "=", 2),
        ("state", "not in", ["cancel"]),
    ], ["sale_id", "package_level_ids"], limit=500)
    pkg_map: dict[int, int] = {}
    for p in pickings:
        sid = p["sale_id"][0] if p.get("sale_id") else None
        if sid:
            pkg_map[sid] = pkg_map.get(sid, 0) + len(p.get("package_level_ids") or [])

    lines = odoo.search_read("sale.order.line",
        [("order_id", "in", so_ids)], ["order_id", "product_uom_qty"], limit=5000)
    qty_map: dict[int, int] = {}
    for l in lines:
        oid = l["order_id"][0]
        qty_map[oid] = qty_map.get(oid, 0) + int(l["product_uom_qty"])

    partner_ids = [o["partner_id"][0] for o in orders if o.get("partner_id")]
    partners    = odoo.search_read("res.partner", [("id", "in", partner_ids)],
                      ["id", "state_id"], limit=len(partner_ids) + 5)
    prov_map    = {
        p["id"]: p["state_id"][1].replace(" (TH)", "") if p.get("state_id") else "-"
        for p in partners
    }

    sos_for_pdf = []
    for so_id in so_ids:
        o   = order_map.get(so_id, {})
        pid = o.get("partner_id", [None])[0] if o.get("partner_id") else None
        sos_for_pdf.append({
            "so_id":    so_id,
            "so":       o.get("name", f"ID:{so_id}"),
            "customer": o["partner_id"][1] if o.get("partner_id") else "-",
            "province": prov_map.get(pid, "-"),
            "carrier":  o["delivery_method"][1] if o.get("delivery_method") else "-",
            "received": bool(o.get(FIELD_RECEIVED)),
            "packages": pkg_map.get(so_id, 0),
            "qty":      qty_map.get(so_id, 0),
        })

    pdf_bytes  = build_dispatch_pdf(doc_no, route, plate, driver,
                                    depart_time, date_str, sos_for_pdf, notes)
    pdf_b64    = pdf_to_base64(pdf_bytes)
    pdf_name   = f"ขึ้นรถ_{doc_no}_{route}.pdf"

    # ── 4. แนบ PDF เข้า chatter ของ dispatch record ──────────────────────
    att_id = odoo.create("ir.attachment", {
        "name":      pdf_name,
        "res_model": DISPATCH_MODEL,
        "res_id":    dispatch_id,
        "type":      "binary",
        "datas":     pdf_b64,
        "mimetype":  "application/pdf",
    })

    so_list_html = "".join(
        f"<li>{order_map[i]['name']}</li>" for i in so_ids if i in order_map
    )
    odoo.execute_method(DISPATCH_MODEL, "message_post", [dispatch_id], {
        "body": (
            f"<p>🚚 <strong>ยืนยันขึ้นรถ — {doc_no}</strong></p>"
            f"<p>เส้นทาง: <strong>{route}</strong></p>"
            f"<p>ทะเบียนรถ: <strong>{plate}</strong> | คนขับ: <strong>{driver}</strong></p>"
            f"<p>เวลาออกรถ: <strong>{depart_time} น.</strong> | วันที่: {date_str}</p>"
            f"<p>รายการ SO:</p><ul>{so_list_html}</ul>"
        ),
        "message_type": "comment",
        "attachment_ids": [att_id],
    })

    # ── 5. Post chatter บนแต่ละ SO ───────────────────────────────────────
    for so_id in so_ids:
        note      = (notes.get(str(so_id)) or "").strip()
        note_html = f"<p>หมายเหตุ: {note}</p>" if note else ""
        odoo.execute_method("sale.order", "message_post", [so_id], {
            "body": (
                f"<p>🚚 <strong>ขึ้นรถแล้ว — เส้นทาง {route}</strong></p>"
                f"<p>ทะเบียนรถ: <strong>{plate}</strong> | คนขับ: <strong>{driver}</strong></p>"
                f"<p>เวลาออกรถ: <strong>{depart_time} น.</strong> | วันที่: {date_str}</p>"
                f"<p>เลขที่เอกสาร: <strong>{doc_no}</strong></p>"
                f"<p>รับพร้อมกัน: {so_names}</p>"
                f"{note_html}"
            ),
            "message_type": "comment",
        })

    return {
        "ok":        True,
        "confirmed": len(so_ids),
        "route":     route,
        "doc_no":    doc_no,
        "pdf_b64":   pdf_b64,
        "pdf_name":  pdf_name,
    }
