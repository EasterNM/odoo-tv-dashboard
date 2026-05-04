"""
Store TV Service
จัดกลุ่ม SO ตามชื่อขนส่ง
"""
from services.odoo_client import odoo

TRANSPORT_FIELD = "x_studio_x_cust_del_method"

PICKING_FIELDS = [
    "name", "origin", "partner_id", "state",
    "picking_type_id", TRANSPORT_FIELD,
]

STATE_LABEL = {
    "draft":     "รอดำเนินการ",
    "waiting":   "รอสินค้า",
    "confirmed": "ยืนยันแล้ว",
    "assigned":  "พร้อมจัด",
    "done":      "เสร็จสิ้น",
    "cancel":    "ยกเลิก",
}


def get_store_pickings() -> list[dict]:
    """ดึง picking ที่ยังไม่เสร็จ จัดกลุ่มตามขนส่ง แต่ละกลุ่มแบ่ง SO"""
    domain = [
        ("state", "not in", ["cancel", "done"]),
        ("picking_type_code", "=", "outgoing"),
        ("origin", "!=", False),
    ]
    records = odoo.search_read("stock.picking", domain, PICKING_FIELDS, limit=500)

    # จัดกลุ่ม transport → SO → pickings
    transport_groups: dict[str, dict] = {}

    for r in records:
        transport = r.get(TRANSPORT_FIELD) or "ยังไม่ระบุขนส่ง"
        so = r.get("origin") or "-"
        customer = r["partner_id"][1] if r.get("partner_id") else "-"

        if transport not in transport_groups:
            transport_groups[transport] = {"transport": transport, "sos": {}}

        if so not in transport_groups[transport]["sos"]:
            transport_groups[transport]["sos"][so] = {
                "so": so,
                "customer": customer,
                "pickings": [],
            }

        transport_groups[transport]["sos"][so]["pickings"].append({
            "name": r["name"],
            "type":       _get_type(r),
            "type_label": _get_type_label(r),
            "state":      r.get("state", ""),
            "state_label": STATE_LABEL.get(r.get("state", ""), r.get("state", "")),
        })

    # แปลงเป็น list เรียง: มีขนส่งก่อน, "ยังไม่ระบุ" ไว้ท้าย
    result = []
    for name, group in sorted(transport_groups.items(), key=lambda x: (x[0] == "ยังไม่ระบุขนส่ง", x[0])):
        sos = sorted(group["sos"].values(), key=lambda s: s["so"], reverse=True)
        for row in sos:
            row["count"] = len(row["pickings"])
        result.append({
            "transport": group["transport"],
            "so_count":  len(sos),
            "sos":       sos,
        })

    return result


def _get_type(r: dict) -> str:
    name: str = r.get("picking_type_id", [0, ""])[1].lower()
    if "pick" in name:    return "pick"
    if "pack" in name:    return "pack"
    if "delivery" in name or "out" in name: return "delivery"
    return "other"


def _get_type_label(r: dict) -> str:
    return {"pick": "PICK", "pack": "PACK", "delivery": "DEL"}.get(_get_type(r),
           r.get("picking_type_id", [0, ""])[1])
