"""
Transport TV Service
Group delivery SO ตาม เส้นทางการจัดส่ง → วิธีการจัดส่ง (carrier)
"""
from services.odoo_client import odoo

DATE_FROM = "2026-05-01 00:00:00"

PICKING_FIELDS = [
    "name", "origin", "partner_id", "state", "sale_id",
    "package_level_ids",               # จำนวน package ที่แพ็คแล้ว
    "move_line_ids_without_package",   # รายการที่ยังไม่มี package
]

STATE_LABEL = {
    "draft":     "รอดำเนินการ",
    "waiting":   "รอสินค้า",
    "confirmed": "ยืนยันแล้ว",
    "assigned":  "พร้อมจัด",
    "done":      "เสร็จสิ้น",
    "cancel":    "ยกเลิก",
}

ROUTE_ORDER = ["กรุงเทพ", "สายใน", "สายนอก", "รับหน้าบริษัท", "เซลล์ส่งเอง"]
NO_ROUTE    = "ยังไม่ระบุเส้นทาง"
NO_CARRIER  = "ยังไม่ระบุวิธีส่ง"


def get_transport_pickings() -> list:
    """
    ดึง delivery picking ที่ยังไม่เสร็จ จัดกลุ่มตาม:
      เส้นทางการจัดส่ง → วิธีการจัดส่ง → รายการ SO
    """
    # 1. ดึง delivery picking คลังหลัก
    pickings = odoo.search_read("stock.picking", [
        ("state", "not in", ["cancel", "done"]),
        ("picking_type_id", "=", 2),          # Delivery Orders คลังหลัก
        ("create_date", ">=", DATE_FROM),
        ("origin", "!=", False),
    ], PICKING_FIELDS, limit=500)

    if not pickings:
        return []

    # 2. เก็บ sale_id → picking info
    sale_ids = list({p["sale_id"][0] for p in pickings if p.get("sale_id")})

    # 3. ดึง sale.order เพื่อเอา route + carrier
    so_map: dict[int, dict] = {}
    if sale_ids:
        orders = odoo.search_read("sale.order", [("id", "in", sale_ids)], [
            "id", "name",
            "x_studio_selection_field_92b_1jnor75f1",  # เส้นทางการจัดส่ง
            "carrier_id",                               # วิธีการจัดส่ง
        ], limit=len(sale_ids) + 10)
        for o in orders:
            so_map[o["id"]] = {
                "route":   o.get("x_studio_selection_field_92b_1jnor75f1") or NO_ROUTE,
                "carrier": o["carrier_id"][1] if o.get("carrier_id") else NO_CARRIER,
            }

    # 4. จัดกลุ่ม route → carrier → SO
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
            groups[route][carrier][so_name] = {"so": so_name, "customer": customer, "pickings": []}

        groups[route][carrier][so_name]["pickings"].append({
            "name":        p["name"],
            "state":       p.get("state", ""),
            "state_label": STATE_LABEL.get(p.get("state", ""), p.get("state", "")),
            "packages":    len(p.get("package_level_ids") or []),
            "unpackaged":  len(p.get("move_line_ids_without_package") or []),
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
                row["count"]      = len(row["pickings"])
                row["packages"]   = sum(p["packages"]   for p in row["pickings"])
                row["unpackaged"] = sum(p["unpackaged"] for p in row["pickings"])
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
