# Session Summary — Odoo TV Dashboard

> สรุปทุกอย่างที่ทำ เพื่อให้ session หน้าคุยต่อได้เลย

---

## สถานะปัจจุบัน (2026-05-06)

### URL ที่ใช้งานได้
| หน้า | URL |
|------|-----|
| Home (หน้าหลัก) | https://odoo-tv-dashboard.onrender.com/ |
| Sales TV | https://odoo-tv-dashboard.onrender.com/sales |
| Store TV | https://odoo-tv-dashboard.onrender.com/store |
| Transport TV | https://odoo-tv-dashboard.onrender.com/transport |
| Mobile รับบิล | https://odoo-tv-dashboard.onrender.com/mobile/receive-bill |
| Tablet ขึ้นรถ | https://odoo-tv-dashboard.onrender.com/tablet/dispatch |
| API Docs | https://odoo-tv-dashboard.onrender.com/docs |

### Deployment
- **Platform**: Render.com (Singapore region, Free tier)
- **Service name**: `odoo-tv-dashboard`
- **GitHub**: https://github.com/EasterNM/odoo-tv-dashboard (branch: main)
- **Auto-deploy**: ทุกครั้งที่ push ขึ้น main
- **Keep-alive**: UptimeRobot ping `/health` ทุก 5 นาที (ป้องกัน Render sleep)
- **Note**: เดิมใช้ Fly.io แต่ trial หมด ย้ายมา Render.com แทน

---

## โครงสร้าง Project

```
odoo-tv-dashboard/
├── backend/
│   ├── config/.env                   ← Odoo credentials (ไม่ขึ้น GitHub)
│   ├── main.py                       ← FastAPI app + static mount
│   ├── routes/api.py                 ← ทุก endpoint
│   └── services/
│       ├── odoo_client.py            ← XML-RPC client (thread-safe)
│       ├── sales_service.py          ← Sales TV
│       ├── store_service.py          ← Store TV (5 columns)
│       ├── transport_service.py      ← Transport TV
│       ├── bill_receipt_service.py   ← Mobile รับบิล + Invoice Transfer
│       └── dispatch_service.py       ← Tablet ขึ้นรถ
├── frontend/
│   ├── home/index.html               ← หน้าหลัก (ใหม่)
│   ├── sales-tv/index.html
│   ├── store-tv/index.html
│   ├── transport-tv/index.html
│   ├── mobile-receive-bill/index.html   ← PWA
│   ├── tablet-dispatch/index.html       ← PWA
│   └── shared/
│       ├── tv.css / tv.js
│       ├── qrcode.min.js
│       ├── sw.js                     ← Service Worker (PWA)
│       ├── manifest-receive-bill.json / manifest-dispatch.json
│       └── icon-receive-bill.svg / icon-dispatch.svg
├── Dockerfile                        ← ที่ root สำหรับ Render
├── docker-compose.yml
├── render.yaml
└── fly.toml                          ← เก็บไว้ (Fly.io เดิม)
```

---

## Odoo Field Reference

### sale.order
| Field | Type | Label |
|-------|------|-------|
| `x_studio_selection_field_92b_1jnor75f1` | selection | เส้นทางการจัดส่ง |
| `x_studio_boolean_field_62d_1jnoq6a7n` | boolean | ทำบิลจริงแล้ว |
| `x_studio_boolean_field_5bd_1jnp0r53i` | boolean | รับบิลแล้ว |
| `x_studio_boolean_field_2dc_1jnrn22ck` | boolean | ขึ้นรถจัดส่งแล้ว |
| `x_studio_char_field_50v_1jnoq3ou3` | char | เลขบิล easy-acc |
| `x_studio_datetime_field_is_1jnrfclrr` | datetime | เวลารับบิล |
| `delivery_method` | many2one → delivery.carrier | วิธีการจัดส่ง |
| `package_level_ids` | one2many → stock.package.level | จำนวน package |

### x_tv_dashboard_invoice (Invoice Transfer — Header)
| Field | Type | Label |
|-------|------|-------|
| `x_name` | char | เลขที่เอกสาร (IT2026/0001) |
| `x_transfer_datetime` | datetime | วันเวลาที่รับบิล (UTC) |
| `x_signer_name` | char | ชื่อผู้รับบิล |
| `x_signature` | binary | ลายเซ็น (PNG base64) |
| `x_state` | selection | สถานะ: draft / confirmed |
| `x_studio_notes` | html | หมายเหตุ |
| `x_tv_dashboard_invoice_line_ids_90795` | one2many → line | รายการ SO |

### x_tv_dashboard_invoice_line_1992d (Invoice Transfer — Line)
| Field | Type | Label |
|-------|------|-------|
| `x_name` | char | ชื่อ SO |
| `x_so_id` | many2one → sale.order | Sale Order |
| `x_tv_dashboard_invoice_id` | many2one → header | เอกสาร header |

### Picking Type IDs
| ID | ชื่อ | ใช้ใน |
|----|------|-------|
| 2 | Delivery Orders | Transport TV, Dispatch |
| 3 | Pick | Store TV |
| 4 | Pack | Store TV |
| 18 | Delivery Orders (คลังเคลม) | Store TV |

---

## สิ่งที่สร้าง/แก้ไขทั้งหมด

### Session 1 (ก่อนหน้า)
- **Store TV** — 3 column (PICK/PACK/DELIVERY) + column รวม SO + column ⚠ Pick≠Pack
- **Transport TV** — จัดกลุ่มตาม route → carrier → SO cards + แก้ scroll bug
- **Fly.io deployment** — Singapore region (trial หมดแล้ว)

### Session 2 (ก่อนหน้า)
- **Mobile รับบิล** (`/mobile/receive-bill`) — PWA: QR scan → ติ้ก SO → เซ็น → confirm
- **Tablet ขึ้นรถ** (`/tablet/dispatch`) — PWA: เลือกเส้นทาง → ติ้ก SO → กรอกรถ/คนขับ → confirm
- **Render.com deployment** — ย้ายจาก Fly.io พร้อม `/health` + UptimeRobot

### Session 3 (วันนี้ 2026-05-06)

#### หน้าหลัก (`/`)
- สร้าง `frontend/home/index.html` — grid ปุ่มใหญ่ 5 ปุ่ม สีต่างกันแต่ละหน้า + นาฬิกา
- เพิ่ม route `GET /` ใน `api.py`

#### Invoice Transfer — Odoo Model Integration
- ออกแบบ data model สำหรับ `x_tv_dashboard_invoice` (header + line)
- ตรวจสอบ fields ผ่าน Odoo XML-RPC API
- แนะนำ fields ที่ต้องสร้าง 5 fields
- verify fields หลังสร้างว่าครบและถูกต้อง

#### bill_receipt_service.py — รีไรท์ใหม่
Flow ใหม่เมื่อ confirm รับบิล:
1. `_next_doc_number()` → สร้างเลข IT2026/0001, 0002, ...
2. `create x_tv_dashboard_invoice` (header) — signer, signature, datetime, state=confirmed
3. `create x_tv_dashboard_invoice_line_1992d` — 1 line ต่อ 1 SO
4. `write sale.order` — รับบิลแล้ว=True + เวลา
5. `message_post` บน transfer record — สรุปรอบ
6. `message_post` บนแต่ละ SO — แนบลายเซ็น + ระบุเลขเอกสาร

#### Mobile success screen
- แสดงเลขที่เอกสาร (`IT2026/0001`) หลัง confirm สำเร็จ

---

## Bugs ที่ควรรู้ (Odoo 18 quirks)

| ปัญหา | สาเหตุ | วิธีแก้ |
|-------|--------|---------|
| `attachment_ids` ไม่ทำงาน | Odoo 18 ไม่รับ ORM command tuple | ใช้ `[att_id]` (list of IDs) |
| HTML tag โผล่เป็น text ใน chatter | Odoo 18 sanitize เข้มขึ้น | ใช้ `<p><strong><ul><li>` เท่านั้น |
| Automation ไม่ fire ผ่าน XML-RPC | `write()` ไม่ trigger automation | เขียน field โดยตรงพร้อมกัน |
| เวลาใน chatter เป็น UTC | Odoo เก็บ UTC | เขียน UTC ลง Odoo, แสดง Thai time ใน message body |
| Form view ไม่แสดง field ใหม่ | Studio ไม่ auto-add field เข้า view | ต้อง drag field เข้า form view ใน Studio ด้วยตนเอง |

---

## TODO ที่ยังค้างอยู่
- [ ] เพิ่ม fields ใน Odoo Studio form view ของ `x_tv_dashboard_invoice` เพื่อให้แสดงข้อมูล
- [ ] (optional) หน้า list/report สรุปรอบรับบิลแต่ละวัน

---

## คำสั่งที่ใช้บ่อย

```bash
# Run local (port 8001 เพราะ 8000 ถูกใช้อยู่)
uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8001

# Deploy (auto เมื่อ push main)
git push origin main

# ดู Render logs
# เปิด https://dashboard.render.com → odoo-tv-dashboard → Logs

# ค้นหา field ใน Odoo
python3 -c "
import sys; sys.path.insert(0,'backend')
from dotenv import load_dotenv; from pathlib import Path
load_dotenv(Path('backend/config/.env'))
from services.odoo_client import odoo
uid = odoo.authenticate()
fields = odoo.models.execute_kw(odoo.db,uid,odoo.password,'sale.order','fields_get',[],{'attributes':['string','type']})
[print(k,v['string']) for k,v in sorted(fields.items()) if 'KEYWORD' in v.get('string','')]
"
```
