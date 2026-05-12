"""
Transport TV Service
Group delivery SO ตาม เส้นทางการจัดส่ง → วิธีการจัดส่ง (carrier)
"""
from services.odoo_client import odoo
from services.app_config import get_config

PICKING_FIELDS = [
    "name", "origin", "partner_id", "state", "sale_id",
    "package_level_ids",   # จำนวน package
]

STATE_LABEL = {
    "draft":     "รอดำเนินการ",
    "waiting":   "รอสินค้า",
    "confirmed": "ยืนยันแล้ว",
    "assigned":  "พร้อมจัด",
    "done":      "เสร็จสิ้น",
    "cancel":    "ยกเลิก",
}

NO_ROUTE    = "ยังไม่ระบุเส้นทาง"
NO_CARRIER  = "ยังไม่ระบุวิธีส่ง"


def get_transport_pickings() -> list:
    """
    ดึง delivery picking ที่ยังไม่เสร็จ จัดกลุ่มตาม:
      เส้นทางการจัดส่ง → วิธีการจัดส่ง → รายการ SO
    """
    cfg = get_config()
    DATE_FROM = cfg["date_from"] + " 00:00:00"
    ROUTE_ORDER = [r["name"] for r in cfg.get("routes", [])]

    # 1. ดึง delivery picking คลังหลัก
    pickings = odoo.search_read("stock.picking", [
        ("state", "not in", ["cancel", "done"]),
        ("picking_type_id", "=", 2),          # Delivery Orders คลังหลัก
        ("create_date", ">=", DATE_FROM),
        ("origin", "!=", False),
    ], PICKING_FIELDS, limit=500)

    if not pickings:
        return []

    # 2. รวบรวม sale_ids
    sale_ids = list({p["sale_id"][0] for p in pickings if p.get("sale_id")})

    # 3. ดึง sale.order → route + carrier
    so_map: dict[int, dict] = {}
    if sale_ids:
        orders = odoo.search_read("sale.order", [("id", "in", sale_ids)], [
            "id",
            "x_studio_selection_field_92b_1jnor75f1",  # เส้นทางการจัดส่ง
            "delivery_method",                          # วิธีการจัดส่ง (verified field name)
        ], limit=len(sale_ids) + 10)
        for o in orders:
            so_map[o["id"]] = {
                "route":   o.get("x_studio_selection_field_92b_1jnor75f1") or NO_ROUTE,
                "carrier": o["delivery_method"][1] if o.get("delivery_method") else NO_CARRIER,
                "qty":     0,
            }

        # 4. ดึง sale.order.line → sum product_uom_qty ต่อ SO
        lines = odoo.search_read("sale.order.line",
            [("order_id", "in", sale_ids)],
            ["order_id", "product_uom_qty"],
            limit=5000,
        )
        for l in lines:
            so_id = l["order_id"][0]
            if so_id in so_map:
                so_map[so_id]["qty"] += l["product_uom_qty"]

    # 5. จัดกลุ่ม route → carrier → SO
    groups: dict[str, dict[str, dict]] = {}

    for p in pickings:
        so_id    = p["sale_id"][0] if p.get("sale_id") else None
        so_info  = so_map.get(so_id, {}) if so_id else {}
        route    = so_info.get("route",   NO_ROUTE)
        carrier  = so_info.get("carrier", NO_CARRIER)
        so_name  = p.get("origin") or "-"
        customer = p["partner_id"][1] if p.get("partner_id") else "-"

        if route not in groups:
            groups[route] = {}
        if carrier not in groups[route]:
            groups[route][carrier] = {}
        if so_name not in groups[route][carrier]:
            groups[route][carrier][so_name] = {
                "so":       so_name,
                "customer": customer,
                "qty":      so_info.get("qty", 0),   # จำนวนสินค้ารวมจาก SO line
                "pickings": [],
            }

        groups[route][carrier][so_name]["pickings"].append({
            "name":        p["name"],
            "state":       p.get("state", ""),
            "state_label": STATE_LABEL.get(p.get("state", ""), p.get("state", "")),
            "packages":    len(p.get("package_level_ids") or []),
        })

    # 5. แปลงเป็น list เรียง route ตาม ROUTE_ORDER, "ยังไม่ระบุ" ไว้ท้าย
    def route_rank(name: str) -> int:
        try:    return ROUTE_ORDER.index(name)
        except ValueError: return 99

    result = []
    for route, carriers in sorted(groups.items(), key=lambda x: route_rank(x[0])):
        carrier_list = []
        for carrier, sos in sorted(carriers.items(), key=lambda x: (x[0] == NO_CARRIER, x[0])):
            so_list = sorted(sos.values(), key=lambda s: s["so"], reverse=True)
            for row in so_list:
                row["count"]    = len(row["pickings"])
                row["packages"] = sum(p["packages"] for p in row["pickings"])
            carrier_list.append({
                "carrier":  carrier,
                "so_count": len(so_list),
                "sos":      so_list,
            })
        total_so = sum(c["so_count"] for c in carrier_list)
        result.append({
            "route":        route,
            "carrier_count": len(carrier_list),
            "so_count":     total_so,
            "carriers":     carrier_list,
        })

    return result
