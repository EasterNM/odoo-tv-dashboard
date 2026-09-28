"""
Store Zone TV Service
5 column: PICK (รองรับการจัดแบบโซน) | PACK | DELIVERY | SO รวม | ⚠ ยอดไม่ตรง (Pick ≠ Pack)
"""
import time
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

# คลังสินค้าหลัก: 3=Pick, 4=Pack, 2=Delivery | คลังเคลม: 18=Delivery
MAIN_TYPE_BY_ID  = {3: "pick", 4: "pack", 2: "delivery"}
CLAIM_TYPE_BY_ID = {18: "delivery"}
ALL_TYPE_BY_ID   = {**MAIN_TYPE_BY_ID, **CLAIM_TYPE_BY_ID}
COLUMNS = ["pick", "pack", "delivery"]

# In-memory cache for location -> zone mapping (TTL 5 minutes)
_ZONE_CACHE = {
    "loc_to_zone": {},
    "zones_list": [],
    "last_fetched": 0,
}
ZONE_CACHE_TTL = 300  # 5 minutes


def _get_zone_mapping() -> tuple[dict[int, dict], list[dict]]:
    now = time.time()
    if _ZONE_CACHE["loc_to_zone"] and (now - _ZONE_CACHE["last_fetched"]) < ZONE_CACHE_TTL:
        return _ZONE_CACHE["loc_to_zone"], _ZONE_CACHE["zones_list"]

    try:
        zones_raw = odoo.search_read(
            "x_zone_product_categor",
            [],
            ["id", "x_name", "x_studio_one2many_field_8sl_1k2a41p05"],
            limit=100,
            order="id asc"
        )
    except Exception as e:
        print(f"[StoreZone] Warning: Failed to fetch zones from Odoo: {e}")
        return _ZONE_CACHE.get("loc_to_zone", {}), _ZONE_CACHE.get("zones_list", [])

    loc_to_zone: dict[int, dict] = {}
    zones_list: list[dict] = []

    for z in zones_raw:
        z_id = z["id"]
        z_name = (z.get("x_name") or f"Zone {z_id}").strip()
        z_code = z_name.split("-")[0].strip() if "-" in z_name else z_name

        zone_entry = {
            "id": z_id,
            "name": z_name,
            "code": z_code,
        }
        zones_list.append(zone_entry)

        loc_ids = z.get("x_studio_one2many_field_8sl_1k2a41p05") or []
        for lid in loc_ids:
            loc_to_zone[lid] = {
                "zone_id": z_id,
                "zone_name": z_name,
                "zone_code": z_code,
            }

    _ZONE_CACHE["loc_to_zone"] = loc_to_zone
    _ZONE_CACHE["zones_list"] = zones_list
    _ZONE_CACHE["last_fetched"] = now
    return loc_to_zone, zones_list


def get_store_zone_pickings() -> dict:
    DATE_FROM = get_config()["date_from"] + " 00:00:00"
    loc_to_zone, all_zones = _get_zone_mapping()

    # 1. Query คลังหลัก: ต้องมี origin (SO)
    main_records = odoo.search_read("stock.picking", [
        ("state", "not in", ["cancel", "done"]),
        ("picking_type_id", "in", list(MAIN_TYPE_BY_ID.keys())),
        ("origin", "!=", False),
        ("create_date", ">=", DATE_FROM),
    ], PICKING_FIELDS, limit=500)

    # หา partner_id ที่มีของออกจากคลังหลัก
    main_partners: set[int] = {
        r["partner_id"][0]
        for r in main_records
        if r.get("partner_id")
    }

    # 2. Query คลังเคลม: ไม่ filter origin เพราะอาจไม่มี SO
    claim_records = odoo.search_read("stock.picking", [
        ("state", "not in", ["cancel", "done"]),
        ("picking_type_id", "in", list(CLAIM_TYPE_BY_ID.keys())),
        ("partner_id", "in", list(main_partners)),
        ("create_date", ">=", DATE_FROM),
    ], PICKING_FIELDS, limit=200) if main_partners else []

    records = main_records + claim_records

    columns: dict[str, dict] = {col: {} for col in COLUMNS}
    sos: dict[str, dict] = {}
    sale_id_map: dict[int, dict] = {}
    bill_sale_map: dict[str, int] = {}
    pick_picking_ids: list[int] = []

    for r in records:
        type_id = r.get("picking_type_id", [0])[0]
        ptype   = ALL_TYPE_BY_ID.get(type_id)
        if not ptype:
            continue

        p_id     = r["id"]
        so       = r.get("origin") or r["name"]
        customer = r["partner_id"][1] if r.get("partner_id") else "-"
        cdate    = r.get("create_date") or ""

        if ptype == "pick":
            pick_picking_ids.append(p_id)

        if r.get("sale_id"):
            sid = r["sale_id"][0]
            if sid not in sale_id_map:
                sale_id_map[sid] = {"so": so, "customer": customer}
            if ptype in ("pack", "delivery"):
                bill_sale_map[so] = sid

        picking = {
            "id":          p_id,
            "name":        r["name"],
            "state":       r.get("state", ""),
            "state_label": STATE_LABEL.get(r.get("state", ""), r.get("state", "")),
            "printed":     bool(r.get("x_studio_boolean_field_651_1jjl2ncdf", False)),
        }

        # Column view
        if so not in columns[ptype]:
            columns[ptype][so] = {
                "so": so,
                "customer": customer,
                "pickings": [],
                "_cdate": cdate,
                "picking_ids": [],
            }
        else:
            existing = columns[ptype][so]["_cdate"]
            if cdate and (not existing or cdate < existing):
                columns[ptype][so]["_cdate"] = cdate

        columns[ptype][so]["pickings"].append(picking)
        columns[ptype][so]["picking_ids"].append(p_id)

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

    # 3. Query move lines for all PICK pickings to calculate Zone progress
    so_zones_map: dict[str, list[dict]] = {}
    so_zone_summary_map: dict[str, dict] = {}

    if pick_picking_ids:
        try:
            move_lines = odoo.search_read(
                "stock.move.line",
                [("picking_id", "in", pick_picking_ids)],
                ["id", "picking_id", "product_id", "location_id", "quantity", "qty_done", "state"],
                limit=1500,
                order="id asc"
            )
        except Exception as e:
            print(f"[StoreZone] Error fetching move lines: {e}")
            move_lines = []

        # Map picking_id to so_name
        picking_to_so: dict[int, str] = {}
        for so_name, data in columns["pick"].items():
            for pid in data.get("picking_ids", []):
                picking_to_so[pid] = so_name

        # Aggregate quantities by SO and Zone
        so_zone_acc: dict[str, dict[str, dict]] = {}
        for ml in move_lines:
            pid = ml.get("picking_id", [0])[0]
            so_name = picking_to_so.get(pid)
            if not so_name:
                continue

            loc_id = ml.get("location_id", [0])[0]
            z_info = loc_to_zone.get(loc_id, {
                "zone_id": -1,
                "zone_name": "ไม่มีโซน",
                "zone_code": "อื่นๆ"
            })
            z_code = z_info["zone_code"]

            if so_name not in so_zone_acc:
                so_zone_acc[so_name] = {}

            if z_code not in so_zone_acc[so_name]:
                so_zone_acc[so_name][z_code] = {
                    "zone_id":   z_info["zone_id"],
                    "zone_name": z_info["zone_name"],
                    "zone_code": z_code,
                    "demanded":  0.0,
                    "done":      0.0,
                }

            so_zone_acc[so_name][z_code]["demanded"] += float(ml.get("quantity") or 0.0)
            so_zone_acc[so_name][z_code]["done"]     += float(ml.get("qty_done") or 0.0)

        # Process status per zone and overall for each SO
        for so_name, z_dict in so_zone_acc.items():
            zone_list = []
            completed_zones = 0

            for z_code, zd in z_dict.items():
                dem  = round(zd["demanded"], 2)
                done = round(zd["done"], 2)

                # Integer display if whole number
                dem_display  = int(dem) if dem.is_integer() else dem
                done_display = int(done) if done.is_integer() else done

                if done >= dem and dem > 0:
                    status = "done"
                    completed_zones += 1
                elif done > 0:
                    status = "partial"
                else:
                    status = "waiting"

                zone_list.append({
                    "zone_id":      zd["zone_id"],
                    "zone_name":    zd["zone_name"],
                    "zone_code":    z_code,
                    "demanded":     dem_display,
                    "done":         done_display,
                    "status":       status,
                    "is_done":      status == "done",
                })

            # Sort zones alphabetically (A, B, C, MIX, ตู้, อื่นๆ)
            def _zone_sort_key(item):
                code = item["zone_code"]
                if code == "อื่นๆ":
                    return "zzz"
                return code

            zone_list.sort(key=_zone_sort_key)
            so_zones_map[so_name] = zone_list

            total_zones = len(zone_list)
            all_done = (completed_zones == total_zones and total_zones > 0)
            so_zone_summary_map[so_name] = {
                "total_zones":     total_zones,
                "completed_zones": completed_zones,
                "all_done":        all_done,
                "label":           f"{completed_zones}/{total_zones} โซน",
            }

    # 4. ดึงสถานะ "ทำบิลจริงแล้ว" ของ SO ใน pack + delivery column
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

    # 5. แปลง columns เป็น list + attach zone data + sort ตาม priority
    result_cols = {}
    for col in COLUMNS:
        for so_name, row in columns[col].items():
            row["count"]       = len(row["pickings"])
            row["printed"]     = all(p["printed"] for p in row["pickings"])
            row["create_time"] = _format_time(row.pop("_cdate", ""))


            if col == "pick":
                row["zones"]        = so_zones_map.get(so_name, [])
                row["zone_summary"] = so_zone_summary_map.get(so_name, {
                    "total_zones": 0, "completed_zones": 0, "all_done": False, "label": "0 โซน"
                })

        def _priority(row):
            if not row["printed"]:
                return (0, row["so"])
            if not row.get("billed", False):
                return (1, row["so"])
            return (2, row["so"])

        result_cols[col] = sorted(columns[col].values(), key=_priority)

    # 6. SO cross-column เรียงตามเวลาค้าง + แนบ zone summary
    now = datetime.now(timezone.utc)
    so_list = []
    for so_name, so_data in sos.items():
        oldest  = so_data.pop("_oldest", "")
        elapsed = _elapsed_minutes(oldest, now)
        so_data["elapsed_minutes"] = elapsed
        so_data["elapsed_label"]   = _format_elapsed(elapsed)
        if so_name in so_zone_summary_map:
            so_data["zone_summary"] = so_zone_summary_map[so_name]
            so_data["zones"] = so_zones_map.get(so_name, [])
        so_list.append(so_data)

    so_list.sort(key=lambda x: x["elapsed_minutes"], reverse=True)

    # 7. Warning column: PICK done ≠ PACK done
    warnings = _build_warnings(sale_id_map)

    return {
        **result_cols,
        "sos": so_list,
        "warnings": warnings,
        "all_zones": all_zones,
    }


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


def validate_pickings(picking_ids: list[int]) -> dict:
    """
    Validate one or more PICK pickings in Odoo (calls button_validate).
    This completes the PICK operation and triggers Odoo to generate the PACK document.
    """
    if not picking_ids:
        return {"ok": False, "error": "ไม่ได้ระบุรหัสใบจัดสินค้า"}

    validated = []
    errors = []

    for pid in picking_ids:
        try:
            picks = odoo.search_read(
                "stock.picking",
                [("id", "=", pid)],
                ["id", "name", "state", "origin", "picking_type_id"],
                limit=1,
            )
            if not picks:
                errors.append(f"ไม่พบใบจัด ID {pid}")
                continue

            pick = picks[0]
            if pick["state"] == "done":
                validated.append(pick["name"])
                continue
            if pick["state"] == "cancel":
                errors.append(f"ใบจัด {pick['name']} ถูกยกเลิกไปแล้ว")
                continue

            # ตรวจสอบยอดหยิบใน move lines
            lines = odoo.search_read(
                "stock.move.line",
                [("picking_id", "=", pid)],
                ["id", "quantity", "qty_done"],
                limit=500,
            )
            total_done = sum(float(l.get("qty_done") or 0.0) for l in lines)
            if lines and total_done <= 0:
                errors.append(f"ใบจัด {pick['name']} ยังไม่มียอดหยิบสินค้า (ยอดหยิบเป็น 0)")
                continue

            # เรียก button_validate
            res = odoo.execute_method("stock.picking", "button_validate", [pid])

            # กรณี Odoo เด้ง Wizard ยืนยันเรื่อง Backorder (เช่น หยิบไม่ครบ)
            if isinstance(res, dict) and res.get("res_model") == "stock.backorder.confirmation":
                wizard_id = res.get("res_id")
                ctx = res.get("context", {})
                if wizard_id:
                    odoo.models.execute_kw(
                        odoo.db, odoo.authenticate(), odoo.password,
                        "stock.backorder.confirmation", "process",
                        [[wizard_id]],
                        {"context": ctx},
                    )
            elif isinstance(res, dict) and res.get("res_model") == "stock.immediate.transfer":
                wizard_id = res.get("res_id")
                ctx = res.get("context", {})
                if wizard_id:
                    odoo.models.execute_kw(
                        odoo.db, odoo.authenticate(), odoo.password,
                        "stock.immediate.transfer", "process",
                        [[wizard_id]],
                        {"context": ctx},
                    )

            # ตรวจสอบสถานะอีกครั้งว่ากลายเป็น done แล้วหรือไม่
            updated = odoo.search_read(
                "stock.picking",
                [("id", "=", pid)],
                ["id", "name", "state"],
                limit=1,
            )
            if updated and updated[0]["state"] == "done":
                validated.append(pick["name"])
            else:
                curr_st = updated[0]["state"] if updated else "unknown"
                errors.append(f"ใบจัด {pick['name']} ไม่สามารถเปลี่ยนสถานะเป็นเสร็จสิ้นได้ (สถานะ: {curr_st})")

        except Exception as e:
            errors.append(f"เกิดข้อผิดพลาดในการ Validate ใบจัด {pid}: {str(e)}")

    if validated and not errors:
        return {
            "ok": True,
            "message": f"ยืนยันส่งไปแพ็คสำเร็จ ({', '.join(validated)})",
            "validated": validated,
        }
    elif validated and errors:
        return {
            "ok": True,
            "message": f"ยืนยันสำเร็จ ({', '.join(validated)}) แต่พบข้อผิดพลาดบางส่วน: {'; '.join(errors)}",
            "validated": validated,
            "errors": errors,
        }
    else:
        return {
            "ok": False,
            "error": "; ".join(errors) if errors else "ไม่สามารถยืนยันได้",
        }

