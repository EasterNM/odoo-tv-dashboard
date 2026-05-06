"""
Bill Receipt Service
จัดการการรับบิลจากแผนกเซลล์ — mobile flow
"""
from datetime import datetime, timezone, timedelta
from services.odoo_client import odoo

THAI_TZ = timezone(timedelta(hours=7))

FIELD_INVOICED  = "x_studio_boolean_field_62d_1jnoq6a7n"   # ทำบิลจริงแล้ว
FIELD_RECEIVED  = "x_studio_boolean_field_5bd_1jnp0r53i"   # รับบิลแล้ว
FIELD_RECV_TIME = "x_studio_datetime_field_is_1jnrfclrr"   # เวลารับบิล
FIELD_EASY_NO   = "x_studio_char_field_50v_1jnoq3ou3"      # เลขบิล easy-acc
DATE_FROM       = "2026-05-01 00:00:00"

TRANSFER_MODEL  = "x_tv_dashboard_invoice"
LINE_MODEL      = "x_tv_dashboard_invoice_line_1992d"


def _next_doc_number(year: int) -> str:
    prefix = f"IT{year}/"
    count = odoo.models.execute_kw(
        odoo.db, odoo.authenticate(), odoo.password,
        TRANSFER_MODEL, "search_count",
        [[["x_name", "like", prefix + "%"]]],
    )
    return f"{prefix}{count + 1:04d}"


def get_pending_receipts() -> list:
    """SO ที่ทำบิลแล้ว แต่ยังไม่รับบิล"""
    orders = odoo.search_read("sale.order", [
        (FIELD_INVOICED, "=", True),
        (FIELD_RECEIVED, "=", False),
        ("date_order", ">=", DATE_FROM),
    ], ["id", "name", "partner_id", "date_order", FIELD_EASY_NO],
       limit=200, order="name desc")

    result = []
    for o in orders:
        result.append({
            "id":       o["id"],
            "so":       o["name"],
            "customer": o["partner_id"][1] if o.get("partner_id") else "-",
            "date":     (o.get("date_order") or "")[:10],
            "easy_no":  o.get(FIELD_EASY_NO) or "",
        })
    return result


def confirm_receipt(so_ids: list, signature_b64: str, signer_name: str) -> dict:
    """
    1. สร้าง x_tv_dashboard_invoice (header) + lines
    2. Mark รับบิลแล้ว = True บน sale.order
    3. Post chatter บน transfer record และแต่ละ SO
    """
    if not so_ids:
        return {"ok": False, "error": "ไม่มี SO ที่เลือก"}

    orders = odoo.search_read(
        "sale.order", [("id", "in", so_ids)],
        ["id", "name", "partner_id"], limit=len(so_ids) + 5,
    )
    order_map = {o["id"]: o for o in orders}

    now_utc  = datetime.now(timezone.utc)
    now_thai = now_utc.astimezone(THAI_TZ)
    now_str  = now_thai.strftime("%d/%m/%Y %H:%M")
    odoo_dt  = now_utc.strftime("%Y-%m-%d %H:%M:%S")
    so_names = ", ".join(order_map[i]["name"] for i in so_ids if i in order_map)
    sig_data = signature_b64.split(",", 1)[-1]

    # 1. สร้าง transfer header
    doc_no = _next_doc_number(now_thai.year)
    transfer_id = odoo.create(TRANSFER_MODEL, {
        "x_name":              doc_no,
        "x_signer_name":       signer_name,
        "x_signature":         sig_data,
        "x_transfer_datetime": odoo_dt,
        "x_state":             "confirmed",
    })

    # 2. สร้าง line ต่อ SO
    for so_id in so_ids:
        so_name = order_map.get(so_id, {}).get("name", f"ID:{so_id}")
        odoo.create(LINE_MODEL, {
            "x_tv_dashboard_invoice_id": transfer_id,
            "x_so_id":                   so_id,
            "x_name":                    so_name,
        })

    # 3. Write กลับ sale.order ทุกใบพร้อมกัน
    odoo.write("sale.order", so_ids, {
        FIELD_RECEIVED:  True,
        FIELD_RECV_TIME: odoo_dt,
    })

    # 4. Post chatter บน transfer record (สรุปรอบนี้)
    so_list_html = "".join(
        f"<li>{order_map[i]['name']} — {order_map[i]['partner_id'][1] if order_map[i].get('partner_id') else '-'}</li>"
        for i in so_ids if i in order_map
    )
    odoo.execute_method(TRANSFER_MODEL, "message_post", [transfer_id], {
        "body": (
            f"<p>✅ <strong>รับบิลแล้ว</strong></p>"
            f"<p>ผู้รับ: <strong>{signer_name}</strong></p>"
            f"<p>เวลา: {now_str} น.</p>"
            f"<p>รายการ SO:</p><ul>{so_list_html}</ul>"
        ),
        "message_type": "comment",
    })

    # 5. Post chatter บนแต่ละ SO พร้อมลายเซ็น
    for so_id in so_ids:
        so_name = order_map.get(so_id, {}).get("name", f"ID:{so_id}")

        att_id = odoo.create("ir.attachment", {
            "name":      f"รับบิล_{so_name}_{now_thai.strftime('%Y%m%d_%H%M')}.png",
            "res_model": "sale.order",
            "res_id":    so_id,
            "type":      "binary",
            "datas":     sig_data,
            "mimetype":  "image/png",
        })

        odoo.execute_method("sale.order", "message_post", [so_id], {
            "body": (
                f"<p>✅ <strong>รับบิลแล้ว</strong></p>"
                f"<p>ผู้รับ: <strong>{signer_name}</strong></p>"
                f"<p>เวลา: {now_str} น.</p>"
                f"<p>เลขที่เอกสาร: <strong>{doc_no}</strong></p>"
                f"<p>รับพร้อมกัน:</p><ul>{so_list_html}</ul>"
            ),
            "message_type": "comment",
            "attachment_ids": [att_id],
        })

    return {"ok": True, "confirmed": len(so_ids), "so_names": so_names, "doc_no": doc_no}
