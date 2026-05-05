"""
Bill Receipt Service
จัดการการรับบิลจากแผนกเซลล์ — mobile flow
"""
from datetime import datetime, timezone
from services.odoo_client import odoo

FIELD_INVOICED = "x_studio_boolean_field_62d_1jnoq6a7n"   # ทำบิลจริงแล้ว
FIELD_RECEIVED = "x_studio_boolean_field_5bd_1jnp0r53i"   # รับบิลแล้ว
FIELD_EASY_NO  = "x_studio_char_field_50v_1jnoq3ou3"      # เลขบิล easy-acc
DATE_FROM      = "2026-05-01 00:00:00"


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
    1. Mark รับบิลแล้ว = True
    2. Attach signature image + post chatter message บน SO แรก (batch)
    3. Post brief note บน SO ที่เหลือ
    """
    if not so_ids:
        return {"ok": False, "error": "ไม่มี SO ที่เลือก"}

    # ดึง SO details สำหรับ message
    orders = odoo.search_read("sale.order", [("id", "in", so_ids)],
                              ["id", "name", "partner_id"], limit=len(so_ids) + 5)
    order_map = {o["id"]: o for o in orders}

    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    so_names = ", ".join(order_map[i]["name"] for i in so_ids if i in order_map)

    # 1. Write field
    odoo.write("sale.order", so_ids, {FIELD_RECEIVED: True})

    # 2. สร้าง attachment (signature) และ post chatter ต่อ SO
    sig_data = signature_b64.split(",", 1)[-1]  # ตัด data:image/png;base64, ออก

    for so_id in so_ids:
        so = order_map.get(so_id)
        so_name = so["name"] if so else f"ID:{so_id}"

        # สร้าง attachment
        att_id = odoo.create("ir.attachment", {
            "name":      f"รับบิล_{so_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            "res_model": "sale.order",
            "res_id":    so_id,
            "type":      "binary",
            "datas":     sig_data,
            "mimetype":  "image/png",
        })

        # post chatter
        odoo.execute_method("sale.order", "message_post", [so_id], {
            "body": (
                f"<b>✅ รับบิลแล้ว</b><br/>"
                f"ผู้รับ: <b>{signer_name}</b><br/>"
                f"วันที่: {now_str}<br/>"
                f"รับพร้อมกัน: {so_names}"
            ),
            "message_type": "comment",
            "attachment_ids": [(4, att_id)],
        })

    return {"ok": True, "confirmed": len(so_ids), "so_names": so_names}
