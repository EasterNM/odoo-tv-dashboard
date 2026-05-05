"""
Dispatch Service — Tablet Loading Page
จัดการข้อมูลสำหรับหน้า tablet ยืนยันขึ้นรถ
"""
from datetime import datetime, timezone, timedelta
from services.odoo_client import odoo

FIELD_ROUTE    = "x_studio_selection_field_92b_1jnor75f1"
FIELD_RECEIVED = "x_studio_boolean_field_5bd_1jnp0r53i"
DATE_FROM      = "2026-05-01 00:00:00"
THAI_TZ        = timezone(timedelta(hours=7))

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
    orders = odoo.search_read("sale.order", [("id", "in", sale_ids)],
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

    orders = odoo.search_read("sale.order", [("id", "in", sale_ids)], [
        "id", "name", FIELD_ROUTE, "carrier_id", FIELD_RECEIVED, "partner_id",
    ], limit=len(sale_ids) + 10)

    route_order_ids = {
        o["id"] for o in orders
        if (o.get(FIELD_ROUTE) or NO_ROUTE) == route_name
    }
    if not route_order_ids:
        return {"route": route_name, "so_count": 0, "sos": []}

    # Qty from order lines
    lines = odoo.search_read("sale.order.line",
        [("order_id", "in", list(route_order_ids))],
        ["order_id", "product_uom_qty"], limit=5000)
    qty_map: dict[int, float] = {}
    for l in lines:
        oid = l["order_id"][0]
        qty_map[oid] = qty_map.get(oid, 0) + l["product_uom_qty"]

    # Partner provinces
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

    # Build SO map
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
            "carrier":  o["carrier_id"][1] if o.get("carrier_id") else "-",
            "received": bool(o.get(FIELD_RECEIVED)),
            "qty":      int(qty_map.get(o["id"], 0)),
            "packages": 0,
        }

    for p in pickings:
        so_id = p["sale_id"][0] if p.get("sale_id") else None
        if so_id and so_id in so_map:
            so_map[so_id]["packages"] += len(p.get("package_level_ids") or [])

    result = sorted(so_map.values(), key=lambda x: x["so"], reverse=True)
    return {
        "route":    route_name,
        "color":    ROUTE_COLOR.get(route_name, "#555"),
        "so_count": len(result),
        "sos":      result,
    }


def confirm_dispatch(route: str, so_ids: list, plate: str, driver: str,
                     depart_time: str, notes: dict) -> dict:
    if not so_ids:
        return {"ok": False, "error": "ไม่มี SO ที่เลือก"}

    now_thai = datetime.now(timezone.utc).astimezone(THAI_TZ)
    date_str = now_thai.strftime("%d/%m/%Y")

    orders = odoo.search_read("sale.order", [("id", "in", so_ids)],
        ["id", "name"], limit=len(so_ids) + 5)
    order_map = {o["id"]: o["name"] for o in orders}
    so_names = ", ".join(order_map.get(i, f"ID:{i}") for i in so_ids)

    for so_id in so_ids:
        note = (notes.get(str(so_id)) or "").strip()
        note_html = f"<p>หมายเหตุ: {note}</p>" if note else ""
        odoo.execute_method("sale.order", "message_post", [so_id], {
            "body": (
                f"<p>🚚 <strong>ขึ้นรถแล้ว — เส้นทาง {route}</strong></p>"
                f"<p>ทะเบียนรถ: <strong>{plate}</strong></p>"
                f"<p>คนขับ: <strong>{driver}</strong></p>"
                f"<p>เวลาออกรถ: <strong>{depart_time} น.</strong></p>"
                f"<p>วันที่: {date_str}</p>"
                f"<p>รับพร้อมกัน: {so_names}</p>"
                f"{note_html}"
            ),
            "message_type": "comment",
        })

    return {"ok": True, "confirmed": len(so_ids), "route": route}
