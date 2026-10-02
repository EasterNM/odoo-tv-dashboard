"""
Store TV Service
5 column: PICK | PACK | DELIVERY | SO รวม | ⚠ ยอดไม่ตรง (Pick ≠ Pack)
"""
from datetime import datetime, timezone, timedelta
from services.odoo_client import odoo
from services.sales_service import _get_problem_so_ids
from services.app_config import get_config

PICKING_FIELDS = [
    "id", "name", "origin", "partner_id", "state", "picking_type_id", "create_date", "sale_id",
    "x_studio_boolean_field_651_1jjl2ncdf",   # พิมพ์แล้ว
]

STATE_LABEL = {
    "draft":     "รอดำเนินการ",
    "waiting":   "รอสินค้า",
    "confirmed": "ยืนยันแล้ว",
    "assigned":  "พร้อมจัด",
    "done":      "เสร็จสิ้น",
    "cancel":    "ยกเลิก",
}

# คลังสินค้าหลัก: 3=Pick, 4=Pack, 2=Delivery | คลังเคลม: 18=Delivery (CL)
MAIN_TYPE_BY_ID = {3: "pick", 4: "pack", 2: "delivery"}
CLAIM_TYPE_ID   = 18
COLUMNS = ["pick", "pack", "delivery"]


def get_store_pickings() -> dict:
    DATE_FROM = get_config()["date_from"] + " 00:00:00"
    now = datetime.now(timezone.utc)

    # 1. query คลังหลัก: ต้องมี origin (SO)
    main_records = odoo.search_read("stock.picking", [
        ("state", "not in", ["cancel", "done"]),
        ("picking_type_id", "in", list(MAIN_TYPE_BY_ID.keys())),
        ("origin", "!=", False),
        ("create_date", ">=", DATE_FROM),
    ], PICKING_FIELDS, limit=500)

    # รวบรวมข้อมูล partner_id ในคลังหลัก พร้อม stage และ SO
    main_partner_info: dict[int, dict] = {}
    for r in main_records:
        if not r.get("partner_id"):
            continue
        pid = r["partner_id"][0]
        tid = r.get("picking_type_id", [0])[0]
        stage = MAIN_TYPE_BY_ID.get(tid, "").upper()
        so_name = r.get("origin") or ""
        if pid not in main_partner_info:
            main_partner_info[pid] = {"stages": set(), "sos": set()}
        if stage:
            main_partner_info[pid]["stages"].add(stage)
        if so_name:
            main_partner_info[pid]["sos"].add(so_name)

    # 2. query คลังเคลม (CL): แสดงทุกสถานะที่ยังไม่เสร็จ (draft, waiting, assigned ฯลฯ)
    claim_records = odoo.search_read("stock.picking", [
        ("state", "not in", ["cancel", "done"]),
        ("picking_type_id", "=", CLAIM_TYPE_ID),
        ("create_date", ">=", DATE_FROM),
    ], PICKING_FIELDS, limit=200)

    records = main_records

    columns: dict[str, dict] = {col: {} for col in COLUMNS}
    sos: dict[str, dict] = {}
    # map sale_id → {so_name, customer} สำหรับ warning column
    sale_id_map: dict[int, dict] = {}
    # map so_origin → sale_id สำหรับ billed lookup (pack + delivery)
    bill_sale_map: dict[str, int] = {}

    for r in records:
        type_id = r.get("picking_type_id", [0])[0]
        ptype   = MAIN_TYPE_BY_ID.get(type_id)
        if not ptype:
            continue

        so       = r.get("origin") or r["name"]
        customer = r["partner_id"][1] if r.get("partner_id") else "-"
        cdate    = r.get("create_date") or ""

        # เก็บ sale_id → so name + customer
        if r.get("sale_id"):
            sid = r["sale_id"][0]
            if sid not in sale_id_map:
                sale_id_map[sid] = {"so": so, "customer": customer}
            if ptype in ("pack", "delivery"):
                bill_sale_map[so] = sid

        picking = {
            "name":        r["name"],
            "state":       r.get("state", ""),
            "state_label": STATE_LABEL.get(r.get("state", ""), r.get("state", "")),
            "printed":     bool(r.get("x_studio_boolean_field_651_1jjl2ncdf", False)),
        }

        # column view
        if so not in columns[ptype]:
            columns[ptype][so] = {"so": so, "customer": customer, "pickings": [], "_cdate": cdate}
        else:
            existing = columns[ptype][so]["_cdate"]
            if cdate and (not existing or cdate < existing):
                columns[ptype][so]["_cdate"] = cdate
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

    # ดึงสถานะ "ทำบิลจริงแล้ว" ของ SO ใน pack + delivery column
    so_billed: dict[int, bool] = {}
    if bill_sale_map:
        so_rows = odoo.search_read(
            "sale.order",
            [("id", "in", list(set(bill_sale_map.values())))],
            ["id", "x_studio_boolean_field_62d_1jnoq6a7n"],
        )
        so_billed = {s["id"]: bool(s.get("x_studio_boolean_field_62d_1jnoq6a7n")) for s in so_rows}

    for col in ("pack", "delivery"):
        for so_name, entry in columns[col].items():
            sid = bill_sale_map.get(so_name)
            entry["billed"] = so_billed.get(sid, False) if sid else False

    # แปลง columns เป็น list + คำนวณ printed + sort ตาม priority
    # priority: 0 = ยังไม่พิมพ์, 1 = พิมพ์แล้วยังไม่ได้บิล, 2 = พิมพ์แล้วได้บิลแล้ว
    result_cols = {}
    for col in COLUMNS:
        for row in columns[col].values():
            row["count"]       = len(row["pickings"])
            row["printed"]     = all(p["printed"] for p in row["pickings"])
            row["create_time"] = _format_time(row.pop("_cdate", ""))

        def _priority(row):
            if not row["printed"]:
                return (0, row["so"])
            if not row.get("billed", False):
                return (1, row["so"])
            return (2, row["so"])

        result_cols[col] = sorted(columns[col].values(), key=_priority)

    # 3. จัดการคอลัมน์ CL (คลังเคลม)
    cl_list = []
    for r in claim_records:
        pid = r["partner_id"][0] if r.get("partner_id") else None
        customer = r["partner_id"][1] if r.get("partner_id") else "-"
        cdate = r.get("create_date") or ""
        days_float, days_int = _calc_days_elapsed(cdate, now)
        is_over_7_days = days_float >= 7.0
        matches_main = (pid in main_partner_info) if pid else False
        main_stages = sorted(list(main_partner_info[pid]["stages"])) if matches_main else []
        main_sos = sorted(list(main_partner_info[pid]["sos"])) if matches_main else []

        # priority สำหรับจัดลำดับ:
        # 0 = ตรงกับคลังหลัก + เกิน 7 วัน
        # 1 = ตรงกับคลังหลัก (ต้องจัดส่งไปด้วย)
        # 2 = เกิน 7 วัน (รีบติดต่อลูกค้า)
        # 3 = รายการทั่วไป
        if matches_main and is_over_7_days:
            priority = 0
        elif matches_main:
            priority = 1
        elif is_over_7_days:
            priority = 2
        else:
            priority = 3

        cl_list.append({
            "id":                 r.get("id"),
            "name":               r["name"],
            "origin":             r.get("origin") or "-",
            "customer":           customer,
            "state":              r.get("state", ""),
            "state_label":        STATE_LABEL.get(r.get("state", ""), r.get("state", "")),
            "printed":            bool(r.get("x_studio_boolean_field_651_1jjl2ncdf", False)),
            "create_time":        _format_time(cdate),
            "create_date":        cdate,
            "elapsed_days":       days_int,
            "elapsed_days_float": days_float,
            "days_label":         "วันนี้" if days_int == 0 else f"{days_int} วัน",
            "is_over_7_days":     is_over_7_days,
            "matches_main":       matches_main,
            "main_stages":        main_stages,
            "main_sos":           main_sos,
            "_priority":          priority,
        })

    cl_list.sort(key=lambda x: (x["_priority"], -x["elapsed_days_float"], x["name"]))
    for x in cl_list:
        x.pop("_priority", None)

    # SO cross-column เรียงตามเวลาค้าง
    so_list = []
    for so_data in sos.values():
        oldest  = so_data.pop("_oldest", "")
        elapsed = _elapsed_minutes(oldest, now)
        so_data["elapsed_minutes"] = elapsed
        so_data["elapsed_label"]   = _format_elapsed(elapsed)
        so_list.append(so_data)
    so_list.sort(key=lambda x: x["elapsed_minutes"], reverse=True)

    # warning column: PICK done ≠ PACK done
    warnings = _build_warnings(sale_id_map)

    return {**result_cols, "cl": cl_list, "sos": so_list, "warnings": warnings}


def _calc_days_elapsed(date_str: str, now: datetime) -> tuple[float, int]:
    """คำนวณจำนวนวันที่ผ่านไปนับตั้งแต่สร้างเอกสาร (UTC)"""
    if not date_str:
        return 0.0, 0
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        diff_sec = max(0.0, (now - dt).total_seconds())
        diff_days = diff_sec / 86400.0
        return round(diff_days, 1), int(diff_sec // 86400)
    except Exception:
        return 0.0, 0


def _build_warnings(sale_id_map: dict[int, dict]) -> list[dict]:
    if not sale_id_map:
        return []
    problems = _get_problem_so_ids(list(sale_id_map.keys()))
    result = []
    for so_id, qty in problems.items():
        info = sale_id_map.get(so_id, {})
        result.append({
            "so":       info.get("so", f"ID:{so_id}"),
            "customer": info.get("customer", "-"),
            "pick_qty": qty["pick_qty"],
            "pack_qty": qty["pack_qty"],
            "diff":     round(abs(qty["pick_qty"] - qty["pack_qty"]), 3),
        })
    result.sort(key=lambda x: x["diff"], reverse=True)
    return result


def _elapsed_minutes(date_str: str, now: datetime) -> int:
    if not date_str:
        return 0
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return max(0, int((now - dt).total_seconds() / 60))
    except Exception:
        return 0


def _format_time(date_str: str) -> str:
    """แปลง create_date (UTC) เป็นเวลาไทย (UTC+7) แสดงเป็น HH:MM หรือ D/M HH:MM"""
    if not date_str:
        return ""
    try:
        dt_utc = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        dt_th  = dt_utc + timedelta(hours=7)
        today  = (datetime.now(timezone.utc) + timedelta(hours=7)).date()
        if dt_th.date() == today:
            return dt_th.strftime("%H:%M")
        return dt_th.strftime("%-d/%-m %H:%M")
    except Exception:
        return ""


def _format_elapsed(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes}น."
    hours, mins = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}ชม. {mins}น." if mins else f"{hours}ชม."
    days, hrs = divmod(hours, 24)
    return f"{days}วัน {hrs}ชม." if hrs else f"{days}วัน"
