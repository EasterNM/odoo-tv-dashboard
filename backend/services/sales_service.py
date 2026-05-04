"""
Sales TV Service
แสดง SO ที่มี order_line.หยิบแล้ว > 0 และ line นั้นถูก update วันนี้
จัดกลุ่มตามเส้นทางการจัดส่ง เรียงตาม write_date
"""
from services.odoo_client import odoo

SO_FIELDS = [
    "name",
    "partner_id",
    "write_date",
    "date_order",
    "x_studio_char_field_50v_1jnoq3ou3",       # เลขที่บิล easy-acc
    "x_studio_boolean_field_62d_1jnoq6a7n",    # ทำบิลจริงแล้ว
    "x_studio_selection_field_92b_1jnor75f1",  # เส้นทางการจัดส่ง
]

ROUTE_ORDER = ["กรุงเทพ", "สายใน", "สายนอก", "รับหน้าบริษัท", "เซลล์ส่งเอง"]


def get_ready_to_invoice() -> list[dict]:
    """SO ที่มี order_line.หยิบแล้ว > 0 และสร้างตั้งแต่ 4 พ.ค. เป็นต้นไป"""
    orders = odoo.search_read(
        "sale.order",
        [
            ("order_line.x_studio_picked", ">", 0),
            ("date_order", ">=", "2026-05-01 00:00:00"),
        ],
        SO_FIELDS,
        limit=300,
    )

    groups: dict[str, list] = {}
    for o in orders:
        route = o.get("x_studio_selection_field_92b_1jnor75f1") or "ยังไม่ระบุเส้นทาง"
        if route not in groups:
            groups[route] = []
        groups[route].append({
            "id":          o["id"],
            "name":        o["name"],
            "customer":    o["partner_id"][1] if o.get("partner_id") else "-",
            "date":        o.get("write_date") or o.get("date_order") or "",
            "easy_acc_no": o.get("x_studio_char_field_50v_1jnoq3ou3") or "",
            "billed":      bool(o.get("x_studio_boolean_field_62d_1jnoq6a7n")),
            "transport":   "-",
        })

    # รอออกบิล (เวลาล่าสุดก่อน) → ทำบิลแล้วอยู่ท้าย (เวลาล่าสุดก่อน)
    for items in groups.values():
        pending = sorted([x for x in items if not x["billed"]], key=lambda x: x["date"], reverse=True)
        billed  = sorted([x for x in items if x["billed"]],     key=lambda x: x["date"], reverse=True)
        items[:] = pending + billed

    def route_rank(name):
        try:    return ROUTE_ORDER.index(name)
        except: return 99

    return [
        {"route": route, "count": len(items), "pickings": items}
        for route, items in sorted(groups.items(), key=lambda x: route_rank(x[0]))
    ]
