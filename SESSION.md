# Session Summary — Odoo TV Dashboard

> สรุปทุกอย่างที่ทำ เพื่อให้ session หน้าคุยต่อได้เลย

---

## สถานะปัจจุบัน (2026-05-05)

### URL ที่ใช้งานได้
| หน้า | URL |
|------|-----|
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
│       ├── bill_receipt_service.py   ← Mobile รับบิล
│       └── dispatch_service.py       ← Tablet ขึ้นรถ
├── frontend/
│   ├── sales-tv/index.html
│   ├── store-tv/index.html
│   ├── transport-tv/index.html
│   ├── mobile-receive-bill/index.html   ← PWA
│   ├── tablet-dispatch/index.html       ← PWA
│   └── shared/
│       ├── tv.css
│       ├── tv.js
│       ├── qrcode.min.js
│       ├── sw.js                     ← Service Worker (PWA)
│       ├── manifest-receive-bill.json
│       ├── manifest-dispatch.json
│       ├── icon-receive-bill.svg
│       └── icon-dispatch.svg
├── Dockerfile                        ← ที่ root สำหรับ Render
├── docker/Dockerfile                 ← ของเดิมสำหรับ Fly.io / local
├── docker-compose.yml
├── render.yaml                       ← Render.com config
└── fly.toml                          ← Fly.io config (เก็บไว้)
```

---

## Odoo Field Reference

| Field | Model | Label |
|-------|-------|-------|
| `x_studio_selection_field_92b_1jnor75f1` | `sale.order` | เส้นทางการจัดส่ง |
| `x_studio_boolean_field_62d_1jnoq6a7n` | `sale.order` | ทำบิลจริงแล้ว |
| `x_studio_boolean_field_5bd_1jnp0r53i` | `sale.order` | รับบิลแล้ว |
| `x_studio_boolean_field_2dc_1jnrn22ck` | `sale.order` | ขึ้นรถจัดส่งแล้ว |
| `x_studio_char_field_50v_1jnoq3ou3` | `sale.order` | เลขบิล easy-acc |
| `x_studio_datetime_field_is_1jnrfclrr` | `sale.order` | เวลารับบิล |
| `delivery_method` | `sale.order` | วิธีการจัดส่ง (many2one → delivery.carrier) |
| `package_level_ids` | `stock.picking` | นับจำนวน package |

### Picking Type IDs
| ID | ชื่อ | ใช้ใน |
|----|------|-------|
| 2 | Delivery Orders | Transport TV, Dispatch |
| 3 | Pick | Store TV |
| 4 | Pack | Store TV |
| 18 | Delivery Orders (คลังเคลม) | Store TV |

---

## สิ่งที่สร้าง/แก้ไขทั้งหมด

### Session แรก
- **Store TV** — 3 column (PICK/PACK/DELIVERY) + column รวม SO + column ⚠ Pick≠Pack
- **Transport TV** — จัดกลุ่มตาม route → carrier → SO cards + แก้ scroll bug (root cause: `overflow:hidden` บน `.carrier-group`)
- **Fly.io deployment** — Singapore region, 2 machines, ไม่ spin down

### Session นี้

#### Mobile รับบิล (`/mobile/receive-bill`) — PWA
- QR code บนหน้า Sales TV มุมขวาล่าง → สแกนเปิดหน้าบนมือถือ
- แสดง SO ที่ทำบิลจริงแล้วแต่ยังไม่รับบิล
- ติ้กเลือก SO + กรอกชื่อผู้รับ + เซ็นลายมือบน canvas
- ยืนยัน → เขียน `รับบิลแล้ว = True` + เวลา (UTC) ใน Odoo + แนบ signature image ใน chatter
- แสดงเลข easy-acc ชัดเจน
- **Bug ที่แก้**: `attachment_ids` ใน Odoo 18 ต้องเป็น `[id]` ไม่ใช่ `[(4,id)]`, ใช้ `<p><strong>` ไม่ใช่ `<b><br>`, เวลาแสดงเป็น UTC+7

#### Tablet ขึ้นรถ (`/tablet/dispatch`) — PWA
- หน้าแรก: ปุ่มเส้นทางใหญ่ สีตาม route พร้อม emoji + จำนวน SO รอขึ้นรถ
- กดปุ่มเส้นทาง → ตาราง SO: S.O. / ลูกค้า / จังหวัด / ขนส่ง / บิลจริง✓ / แพ็ค / ชิ้น / หมายเหตุ
- SO จัดกลุ่มตามขนส่ง มีเส้นคั่นสีทอง
- checkbox ต่อแถว + เลือกทั้งหมด
- กดยืนยันขึ้นรถ → modal กรอก ทะเบียนรถ / คนขับ / เวลา → post chatter ทุก SO
- เขียน `ขึ้นรถจัดส่งแล้ว = True` → SO หายออกจากรายการทันที
- **Bug ที่แก้**: `JSON.stringify` ใน HTML attribute ชนกับ double quote → ใช้ `data-*` แทน, checkbox double-fire → `stopPropagation`, `carrier_id` ว่างทุกใบ → ใช้ `delivery_method` แทน

#### PWA (ทั้งสองหน้า)
- `manifest.json` แยกแต่ละหน้า (theme-color, icon, orientation: any)
- Service Worker cache HTML+CSS, network-only สำหรับ API
- SVG icon สำหรับ Android/iOS
- Apple meta tags สำหรับ iOS Safari "Add to Home Screen"

#### Render.com deployment
- ย้ายจาก Fly.io (trial หมด) มา Render.com
- `render.yaml` + `Dockerfile` ที่ root
- `/health` endpoint สำหรับ UptimeRobot ping ป้องกัน sleep

---

## Bugs ที่ควรรู้ (Odoo 18 quirks)

| ปัญหา | สาเหตุ | วิธีแก้ |
|-------|--------|---------|
| `attachment_ids` ไม่ทำงาน | Odoo 18 เปลี่ยน API — ไม่รับ ORM command tuple | ใช้ `[att_id]` (list of IDs) |
| HTML tag โผล่เป็น text ใน chatter | Odoo 18 sanitize เข้มขึ้น | ใช้ `<p><strong><ul><li>` เท่านั้น |
| Automation ไม่ fire ผ่าน XML-RPC | Odoo automation ไม่ trigger จาก `write()` | เขียน datetime field โดยตรงพร้อม write |
| เวลาใน chatter เป็น UTC | Odoo เก็บ UTC แต่ display ตาม timezone user | เขียน UTC ลง Odoo, แสดง Thai time ใน message body |

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
