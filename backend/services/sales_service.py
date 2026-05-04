"""
Sales TV Service
แสดง SO ที่มี order_line.หยิบแล้ว > 0
จัดกลุ่มตามเส้นทางการจัดส่ง + คอลัมน์แจ้งเตือนเมื่อยอด PICK ≠ PACK
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

from services.odoo_client import odoo

SO_FIELDS = [
    "name", "partner_id", "write_date", "date_order",
    "x_studio_char_field_50v_1jnoq3ou3",       # เลขที่บิล easy-acc
    "x_studio_boolean_field_62d_1jnoq6a7n",    # ทำบิลจริงแล้ว
    "x_studio_selection_field_92b_1jnor75f1",  # เส้นทางการจัดส่ง
]

ROUTE_ORDER = ["กรุงเทพ", "สายใน", "สายนอก", "รับหน้าบริษัท", "เซลล์ส่งเอง"]

PICK_TYPE_ID = 3
PACK_TYPE_ID = 4


def _get_problem_so_ids(order_ids: list[int]) -> dict[int, dict]:
    """
    คืน dict: so_id → {pick_qty, pack_qty}
    เฉพาะ SO ที่ทั้ง PICK และ PACK มีอยู่แต่ยอดไม่ตรงกัน
    """
    if not order_ids:
        return {}

    # is_return_picking ใน Odoo 18 ไม่น่าเชื่อถือ — ใช้ origin แทน
    # return pick จะมี origin ขึ้นต้นด้วย "การส่งคืนของ"
    # สอง query นี้ independent — ทำงานพร้อมกัน
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_pick = ex.submit(
            odoo.search_read, "stock.picking",
            [("sale_id", "in", order_ids), ("picking_type_id", "=", PICK_TYPE_ID),
             ("state", "=", "done"),
             ("origin", "not ilike", "การส่งคืนของ")],
            ["id", "sale_id", "picking_type_id"], limit=2000,
        )
        f_pack = ex.submit(
            odoo.search_read, "stock.picking",
            [("sale_id", "in", order_ids), ("picking_type_id", "=", PACK_TYPE_ID),
             ("state", "=", "done")],
            ["id", "sale_id", "picking_type_id"], limit=2000,
        )
        pick_pickings = f_pick.result()
        pack_pickings = f_pack.result()
    pickings = pick_pickings + pack_pickings
    if not pickings:
        return {}

    picking_ids   = [p["id"] for p in pickings]
    pick_pick_ids = {p["id"] for p in pick_pickings}
    pack_pick_ids = {p["id"] for p in pack_pickings}
    picking_so    = {p["id"]: p["sale_id"][0] for p in pickings if p.get("sale_id")}

    moves = odoo.search_read(
        "stock.move",
        [("picking_id", "in", picking_ids), ("state", "=", "done")],
        ["picking_id", "quantity"],
        limit=10000,
    )

    pick_qty: dict[int, float] = {}
    pack_qty: dict[int, float] = {}

    for m in moves:
        pid   = m["picking_id"][0]
        so_id = picking_so.get(pid)
        if not so_id:
            continue
        qty = m["quantity"]
        if pid in pick_pick_ids:
            pick_qty[so_id] = pick_qty.get(so_id, 0.0) + qty
        elif pid in pack_pick_ids:
            pack_qty[so_id] = pack_qty.get(so_id, 0.0) + qty

    # SO ที่มีทั้ง pick และ pack แต่ยอดต่างกัน
    problems = {}
    for so_id in pick_qty:
        if so_id in pack_qty:
            diff = abs(pick_qty[so_id] - pack_qty[so_id])
            if diff > 0.001:
                problems[so_id] = {
                    "pick_qty": pick_qty[so_id],
                    "pack_qty": pack_qty[so_id],
                }
    return problems


def get_ready_to_invoice() -> list[dict]:
    orders = odoo.search_read(
        "sale.order",
        [
            ("order_line.x_studio_picked", ">", 0),
            ("date_order", ">=", "2026-05-01 00:00:00"),
        ],
        SO_FIELDS,
        limit=300,
    )

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    def _billed_and_expired(o: dict) -> bool:
        if not o.get("x_studio_boolean_field_62d_1jnoq6a7n"):
            return False
        raw = o.get("write_date", "")
        if not raw:
            return False
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            return dt < cutoff
        except ValueError:
            return False

    orders = [o for o in orders if not _billed_and_expired(o)]

    order_ids = [o["id"] for o in orders]
    problems  = _get_problem_so_ids(order_ids)

    groups: dict[str, list] = {}
    problem_list: list[dict] = []

    for o in orders:
        route   = o.get("x_studio_selection_field_92b_1jnor75f1") or "ยังไม่ระบุเส้นทาง"
        prob    = problems.get(o["id"])
        item = {
            "id":          o["id"],
            "name":        o["name"],
            "customer":    o["partner_id"][1] if o.get("partner_id") else "-",
            "date":        o.get("write_date") or o.get("date_order") or "",
            "easy_acc_no": o.get("x_studio_char_field_50v_1jnoq3ou3") or "",
            "billed":      bool(o.get("x_studio_boolean_field_62d_1jnoq6a7n")),
            "has_problem": bool(prob),
            "pick_qty":    prob["pick_qty"] if prob else 0,
            "pack_qty":    prob["pack_qty"] if prob else 0,
        }

        if route not in groups:
            groups[route] = []
        groups[route].append(item)

        if prob:
            problem_list.append(item)

    # รอออกบิลก่อน → ทำบิลแล้วอยู่ท้าย
    for items in groups.values():
        pending = sorted([x for x in items if not x["billed"]], key=lambda x: x["date"], reverse=True)
        billed  = sorted([x for x in items if x["billed"]],     key=lambda x: x["date"], reverse=True)
        items[:] = pending + billed

    def route_rank(name):
        try:    return ROUTE_ORDER.index(name)
        except ValueError: return 99

    result = [
        {"route": route, "count": len(items), "pickings": items}
        for route, items in sorted(groups.items(), key=lambda x: route_rank(x[0]))
    ]

    # คอลัมน์ปัญหาอยู่ขวาสุด
    if problem_list:
        problem_list.sort(key=lambda x: x["date"], reverse=True)
        result.append({
            "route":    "⚠ บิลมีปัญหา",
            "count":    len(problem_list),
            "pickings": problem_list,
            "is_problem_col": True,
        })

    return result
