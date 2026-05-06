# Session Summary — Odoo TV Dashboard

> สรุปทุกอย่างที่ทำ เพื่อให้ session หน้าคุยต่อได้เลย

---

## สถานะปัจจุบัน (2026-05-06) — อัปเดตล่าสุด

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
│   ├── fonts/
│   │   ├── Sarabun-Regular.ttf       ← Thai font สำหรับ PDF
│   │   └── Sarabun-Bold.ttf
│   └── services/
│       ├── odoo_client.py            ← XML-RPC client (thread-safe)
│       ├── sales_service.py          ← Sales TV
│       ├── store_service.py          ← Store TV (5 columns)
│       ├── transport_service.py      ← Transport TV
│       ├── bill_receipt_service.py   ← Mobile รับบิล + Invoice Transfer
│       ├── dispatch_service.py       ← Tablet ขึ้นรถ
│       └── pdf_service.py            ← สร้างใบสรุปขึ้นรถ (PDF)
├── frontend/
│   ├── home/index.html               ← หน้าหลัก
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
├── presentation.html                 ← สไลด์นำเสนอ 15 หน้า (ใหม่)
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

### x_tv_dashboard_dispatc (Dispatch Transfer — Header)
| Field | Type | Label |
|-------|------|-------|
| `x_name` | char | เลขที่เอกสาร (DT2026/0001) |
| `x_route` | char | เส้นทาง |
| `x_plate` | char | ทะเบียนรถ |
| `x_driver` | char | คนขับ |
| `x_depart_time` | datetime | วันเวลาออกรถ (UTC) |
| `x_state` | selection | สถานะ: draft / confirmed |
| `x_so_ids` | many2many → sale.order | รายการ SO ในรอบนี้ |

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

### Session 3 (2026-05-06)

#### หน้าหลัก (`/`)
- สร้าง `frontend/home/index.html` — grid ปุ่มใหญ่ 5 ปุ่ม สีต่างกันแต่ละหน้า + นาฬิกา
- เพิ่ม route `GET /` ใน `api.py`

#### Invoice Transfer — Odoo Model Integration
- ออกแบบ data model สำหรับ `x_tv_dashboard_invoice` (header + line)
- ตรวจสอบ fields ผ่าน Odoo XML-RPC API
- แนะนำ fields ที่ต้องสร้าง 5 fields + verify หลังสร้าง

#### bill_receipt_service.py — รีไรท์ใหม่
Flow เมื่อ confirm รับบิล:
1. `_next_doc_number()` → IT2026/0001, 0002, ...
2. `create x_tv_dashboard_invoice` (header) — signer, signature, datetime, state=confirmed
3. `create x_tv_dashboard_invoice_line_1992d` — 1 line ต่อ 1 SO
4. `write sale.order` — รับบิลแล้ว=True + เวลา
5. `message_post` บน transfer record
6. `message_post` บนแต่ละ SO — แนบลายเซ็น + เลขเอกสาร

#### Mobile success screen
- แสดงเลขที่เอกสาร (`IT2026/0001`) หลัง confirm

### Session 4 (2026-05-06 ต่อเนื่อง)

#### Dispatch Transfer — Odoo Model Integration
- สร้าง model `TV_dashboard_dispatch` (`x_tv_dashboard_dispatc`) ใน Odoo Studio
- Fields: `x_name`, `x_route`, `x_plate`, `x_driver`, `x_depart_time`, `x_state`, `x_so_ids` (Many2many)

#### dispatch_service.py — รีไรท์ใหม่
Flow เมื่อ confirm ขึ้นรถ:
1. `write sale.order` — `ขึ้นรถจัดส่งแล้ว = True` (**ทำก่อน** เพื่อป้องกัน SO ค้าง)
2. `_next_dispatch_doc_number()` → DT2026/0001, 0002, ...
3. `create x_tv_dashboard_dispatc` — route, plate, driver, datetime, confirmed, many2many SO
4. สร้าง PDF (fpdf2 + Sarabun, Landscape A4)
5. `create ir.attachment` แนบ PDF เข้า dispatch record
6. `message_post` บน dispatch record + แต่ละ SO

#### pdf_service.py (ใหม่)
- `fpdf2` + Sarabun font — ไม่ต้องการ system dependency
- Columns: # | SO | ลูกค้า | จังหวัด | ขนส่ง | บิล | ชิ้น | แพ็ค | หมายเหตุ
- summary row + ช่องเซ็น 2 ช่อง (คนขับ / ผู้รับของ)
- คืน bytes → base64 → แนบ chatter + frontend auto-download

#### Frontend tablet auto-download PDF
- confirm success → decode base64 → Blob → trigger `.pdf` download อัตโนมัติ

### Session 5 (2026-05-06 ต่อเนื่อง)

#### Bug Fix: ยอด Pack ใน ⚠ Pick≠Pack ยังสูงเกินหลัง Return Pack

**สาเหตุ:** SO S18240 มีการแพ็ค BPUL-IS1191 ซ้ำ 2 ครั้งใน FG/PACK/04460 (done=2.0) ทำให้ pack_qty = 9 แต่ pick_qty = 8 → แสดงใน ⚠ warning column  
ผู้ใช้ทำ Return Pack (FG/PACK/04500) คืน 1 ชิ้น แต่โค้ดเดิมแค่ **ตัด return pack ออกทั้งก้อน** ไม่ได้หัก → pack_qty ยังเป็น 9 ≠ 8

**แก้ไข** (`backend/services/sales_service.py` — `_get_problem_so_ids()`):
- เปลี่ยน `pack_pick_ids` (forward only) → `pack_sign` (forward +1 / return −1)
- เพิ่ม `origin_returned_move_id` เข้า moves query เพื่อ detect return picking แบบ reliable
- ใช้ **double-detection**: origin text ("การส่งคืนของ" / "Return of") **OR** `origin_returned_move_id != False`
- ผล: pack_qty = 9 − 1 = 8 = pick_qty → ไม่แสดงใน ⚠ warning ✅

```python
# ก่อนแก้
pack_pick_ids = {p["id"] for p in pack_pickings if not _is_return(p)}
...
pack_qty[so_id] += qty  # ไม่หัก return

# หลังแก้
return_by_move = {m["picking_id"][0] for m in moves if m.get("origin_returned_move_id")}
pack_sign = {p["id"]: -1 if (_is_return(p) or p["id"] in return_by_move) else 1
             for p in pack_pickings}
...
pack_qty[so_id] += pack_sign[pid] * qty  # หัก return ออก
```

**Commit**: `b6f5d5c` — pushed to main, Render deployed

#### สร้างสไลด์นำเสนอ (`presentation.html`)
- HTML standalone 15 หน้า ไม่ต้องพึ่ง library ภายนอก
- Navigation: keyboard arrows / Space / swipe บนมือถือ
- Progress bar + slide counter
- เนื้อหาครอบคลุม: ปัญหาก่อนมีระบบ → overview → ทุก feature → Odoo integration → tech stack → ข้อดี → deployment → roadmap
- Dark theme เหมือน GitHub

---

## Bugs ที่ควรรู้ (Odoo 18 quirks)

| ปัญหา | สาเหตุ | วิธีแก้ |
|-------|--------|---------|
| `attachment_ids` ไม่ทำงาน | Odoo 18 ไม่รับ ORM command tuple | ใช้ `[att_id]` (list of IDs) |
| HTML tag โผล่เป็น text ใน chatter | Odoo 18 sanitize เข้มขึ้น | ใช้ `<p><strong><ul><li>` เท่านั้น |
| Automation ไม่ fire ผ่าน XML-RPC | `write()` ไม่ trigger automation | เขียน field โดยตรงพร้อมกัน |
| เวลาใน chatter เป็น UTC | Odoo เก็บ UTC | เขียน UTC ลง Odoo, แสดง Thai time ใน message body |
| Form view ไม่แสดง field ใหม่ | Studio ไม่ auto-add field เข้า view | drag field เข้า form view ใน Studio ด้วยตนเอง ✅ แก้แล้ว |
| Return Pack ไม่หักยอด pack_qty | โค้ดเดิม exclude แทนที่จะ subtract | ใช้ `pack_sign` + `origin_returned_move_id` (แก้แล้ว Session 5) |

---

## TODO ที่ยังค้างอยู่
- [x] เพิ่ม fields ใน Odoo Studio form view ของ `x_tv_dashboard_invoice` ✅
- [x] เพิ่ม fields ใน Odoo Studio form view ของ `x_tv_dashboard_dispatc` ✅
- [ ] (optional) หน้า list/report สรุปรอบรับบิลแต่ละวัน
- [ ] (optional) Push notification เมื่อมี SO พร้อมออกบิล
- [ ] (optional) Export รายงานรายวัน / รายสัปดาห์

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
