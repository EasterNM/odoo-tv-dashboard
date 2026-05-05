"""
Store TV Service
4 column: PICK | PACK | DELIVERY | SO (รวมเอกสารทั้งหมดของ SO เดียวกัน)
"""
from datetime import datetime, timezone
from services.odoo_client import odoo

PICKING_FIELDS = [
    "name", "origin", "partner_id", "state", "picking_type_id", "create_date",
]

STATE_LABEL = {
    "draft":     "รอดำเนินการ",
    "waiting":   "รอสินค้า",
    "confirmed": "ยืนยันแล้ว",
    "assigned":  "พร้อมจัด",
    "done":      "เสร็จสิ้น",
    "cancel":    "ยกเลิก",
}

# คลังสินค้าหลัก: 3=Pick, 4=Pack, 2=Delivery | คลังเคลม: 18=Delivery
MAIN_TYPE_BY_ID  = {3: "pick", 4: "pack", 2: "delivery"}
CLAIM_TYPE_BY_ID = {18: "delivery"}
ALL_TYPE_BY_ID   = {**MAIN_TYPE_BY_ID, **CLAIM_TYPE_BY_ID}
COLUMNS = ["pick", "pack", "delivery"]


def get_store_pickings() -> dict:
    # query คลังหลัก: ต้องมี origin (SO)
    main_records = odoo.search_read("stock.picking", [
        ("state", "not in", ["cancel", "done"]),
        ("picking_type_id", "in", list(MAIN_TYPE_BY_ID.keys())),
        ("origin", "!=", False),
    ], PICKING_FIELDS, limit=500)

    # หา partner_id ที่มีของออกจากคลังหลัก
    main_partners: set[int] = {
        r["partner_id"][0]
        for r in main_records
        if r.get("partner_id")
    }

    # query คลังเคลม: ไม่ filter origin เพราะอาจไม่มี SO
    claim_records = odoo.search_read("stock.picking", [
        ("state", "not in", ["cancel", "done"]),
        ("picking_type_id", "in", list(CLAIM_TYPE_BY_ID.keys())),
        ("partner_id", "in", list(main_partners)),   # เฉพาะลูกค้าที่มีของคลังหลัก
    ], PICKING_FIELDS, limit=200) if main_partners else []

    records = main_records + claim_records

    columns: dict[str, dict] = {col: {} for col in COLUMNS}
    sos: dict[str, dict] = {}

    for r in records:
        type_id = r.get("picking_type_id", [0])[0]
        ptype   = ALL_TYPE_BY_ID.get(type_id)
        if not ptype:
            continue

        # ถ้าไม่มี origin ใช้ชื่อเอกสารเป็น key แทน
        so       = r.get("origin") or r["name"]
        customer = r["partner_id"][1] if r.get("partner_id") else "-"
        cdate    = r.get("create_date") or ""

        picking = {
            "name":        r["name"],
            "state":       r.get("state", ""),
            "state_label": STATE_LABEL.get(r.get("state", ""), r.get("state", "")),
        }

        # column view
        if so not in columns[ptype]:
            columns[ptype][so] = {"so": so, "customer": customer, "pickings": []}
        columns[ptype][so]["pickings"].append(picking)

        # SO cross-column view
        if so not in sos:
            sos[so] = {
                "so": so, "customer": customer,
                "ops": {"pick": [], "pack": [], "delivery": []},
                "_oldest": cdate,
            }
        if cdate and cdate < sos[so]["_oldest"]:
            sos[so]["_oldest"] = cdate
        sos[so]["ops"][ptype].append(picking)

    # แปลง columns เป็น list
    result_cols = {}
    for col in COLUMNS:
        sos_list = sorted(columns[col].values(), key=lambda s: s["so"], reverse=True)
        for row in sos_list:
            row["count"] = len(row["pickings"])
        result_cols[col] = sos_list

    # แปลง SO cross-column เป็น list เรียงตามเวลาค้าง
    now = datetime.now(timezone.utc)
    so_list = []
    for so_data in sos.values():
        oldest = so_data.pop("_oldest", "")
        elapsed = _elapsed_minutes(oldest, now)
        so_data["elapsed_minutes"] = elapsed
        so_data["elapsed_label"]   = _format_elapsed(elapsed)
        so_list.append(so_data)
    so_list.sort(key=lambda x: x["elapsed_minutes"], reverse=True)

    return {**result_cols, "sos": so_list}


def _elapsed_minutes(date_str: str, now: datetime) -> int:
    if not date_str:
        return 0
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return max(0, int((now - dt).total_seconds() / 60))
    except Exception:
        return 0


def _format_elapsed(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes}น."
    hours, mins = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}ชม. {mins}น." if mins else f"{hours}ชม."
    days, hrs = divmod(hours, 24)
    return f"{days}วัน {hrs}ชม." if hrs else f"{days}วัน"
