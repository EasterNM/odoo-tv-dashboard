"""
Store TV Service
แสดง 3 column: PICK / PACK / DELIVERY จัดกลุ่มตาม SO
"""
from services.odoo_client import odoo

PICKING_FIELDS = [
    "name", "origin", "partner_id", "state", "picking_type_id",
]

STATE_LABEL = {
    "draft":     "รอดำเนินการ",
    "waiting":   "รอสินค้า",
    "confirmed": "ยืนยันแล้ว",
    "assigned":  "พร้อมจัด",
    "done":      "เสร็จสิ้น",
    "cancel":    "ยกเลิก",
}

COLUMNS = ["pick", "pack", "delivery"]

# picking_type_id ของคลังสินค้าหลัก: 3=Pick, 4=Pack, 2=Delivery Orders
TYPE_BY_ID = {3: "pick", 4: "pack", 2: "delivery"}


def get_store_pickings() -> dict:
    """ดึง picking ที่ยังไม่เสร็จ แบ่งเป็น 3 column ตาม type จัดกลุ่มตาม SO"""
    domain = [
        ("state", "not in", ["cancel", "done"]),
        ("picking_type_id", "in", list(TYPE_BY_ID.keys())),
        ("origin", "!=", False),
    ]
    records = odoo.search_read("stock.picking", domain, PICKING_FIELDS, limit=500)

    # จัดกลุ่ม type → SO → pickings
    columns: dict[str, dict] = {col: {} for col in COLUMNS}

    for r in records:
        type_id = r.get("picking_type_id", [0])[0]
        ptype = TYPE_BY_ID.get(type_id)
        if not ptype:
            continue

        so = r.get("origin") or "-"
        customer = r["partner_id"][1] if r.get("partner_id") else "-"

        if so not in columns[ptype]:
            columns[ptype][so] = {"so": so, "customer": customer, "pickings": []}

        columns[ptype][so]["pickings"].append({
            "name":       r["name"],
            "state":      r.get("state", ""),
            "state_label": STATE_LABEL.get(r.get("state", ""), r.get("state", "")),
        })

    # แปลงเป็น list เรียง SO ล่าสุดก่อน
    result = {}
    for col in COLUMNS:
        sos = sorted(columns[col].values(), key=lambda s: s["so"], reverse=True)
        for row in sos:
            row["count"] = len(row["pickings"])
        result[col] = sos

    return result


