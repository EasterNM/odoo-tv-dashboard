# Odoo Field Mapping

## Model: stock.picking

| Field ใน Code          | Field ใน Odoo        | หมายเหตุ                                      |
|------------------------|----------------------|-----------------------------------------------|
| name                   | name                 | เลขที่ใบ เช่น WH/OUT/00001                    |
| partner_id             | partner_id           | ลูกค้า (many2one)                             |
| origin                 | origin               | เลขที่ SO ต้นทาง                              |
| state                  | state                | draft/confirmed/assigned/done/cancel          |
| date_done              | date_done            | วันที่ทำรายการเสร็จ                          |
| picking_type_id        | picking_type_id      | ประเภท: Pick, Pack, Delivery/OUT              |
| picking_type_code      | picking_type_code    | incoming / outgoing / internal               |

## Custom Field สำหรับ Store TV

ต้องตรวจสอบชื่อ field จริงใน Odoo ที่ใช้ระบุ "ขนส่งท้องถิ่น"

วิธีหาชื่อ field:
1. เปิด Odoo > Settings > Technical > Fields
2. ค้นหา model `stock.picking`
3. มองหา field ที่ชื่อเกี่ยวกับขนส่ง / transport / delivery note

แล้วอัปเดตใน `.env`:
```
LOCAL_TRANSPORT_FIELD=x_ชื่อจริง
LOCAL_TRANSPORT_VALUE=ค่าจริงที่ใช้ใน Odoo
```
