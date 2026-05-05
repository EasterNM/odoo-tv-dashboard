# Session Summary — Odoo TV Dashboard

> สรุปสิ่งที่ทำใน session นี้ เพื่อให้ session หน้าคุยต่อได้เลย

---

## สถานะปัจจุบัน (2026-05-05)

### URL ที่ใช้งานได้
| หน้า | Local | Production (Fly.io) |
|------|-------|---------------------|
| Sales TV | http://localhost:8000/sales | https://odoo-tv-dashboard.fly.dev/sales |
| Store TV | http://localhost:8000/store | https://odoo-tv-dashboard.fly.dev/store |
| Transport TV | http://localhost:8000/transport | https://odoo-tv-dashboard.fly.dev/transport |
| API Docs | http://localhost:8000/docs | https://odoo-tv-dashboard.fly.dev/docs |

### Deployment
- **Platform**: Fly.io (Singapore region)
- **App name**: `odoo-tv-dashboard`
- **Machines**: 2 shared VMs, 256MB RAM, ไม่ spin down
- **Command deploy ใหม่**: `~/.fly/bin/flyctl deploy` (รันใน project root)
- **GitHub**: https://github.com/EasterNM/odoo-tv-dashboard

---

## สิ่งที่สร้าง/แก้ไขใน Session นี้

### 1. Store TV — ปรับใหม่ทั้งหมด (`backend/services/store_service.py`)
- **3 column หลัก**: PICK / PACK / DELIVERY จัดกลุ่มตาม SO
- **column 4 (รวม SO)**: cross-column view แสดงทุก operation ของ SO เดียว + elapsed time (สีเขียว < 4ชม / เหลือง 4-8ชม / แดง > 8ชม)
- **column 5 (⚠ Pick ≠ Pack)**: SO ที่ยอด PICK done ≠ PACK done เรียงตาม diff มากสุด
- **คลังเคลม (picking_type_id = 18)**: ดึงมาด้วย เฉพาะลูกค้าที่มีของออกคลังหลักด้วย
- **Date filter**: แสดงเฉพาะตั้งแต่ 2026-05-01

### 2. Transport TV — สร้างใหม่ทั้งหมด
**Backend** (`backend/services/transport_service.py`):
- ดึง `stock.picking` (picking_type_id = 2, Delivery คลังหลัก)
- join `sale.order` → เส้นทาง (`x_studio_selection_field_92b_1jnor75f1`) + carrier (`carrier_id`)
- join `sale.order.line` → sum qty ต่อ SO
- ใช้ `package_level_ids` นับ package ต่อ picking
- จัดกลุ่ม: route → carrier → SO cards

**Frontend** (`frontend/transport-tv/index.html`):
- แสดง column ตาม route (กรุงเทพ / สายใน / สายนอก / รับหน้าบริษัท / เซลล์ส่งเอง / ยังไม่ระบุ)
- แต่ละ SO card แสดง: SO number, ชื่อลูกค้า, จำนวน package (🟡), จำนวนชิ้น (🟢), picking badges + state
- scroll แนวนอน (ระหว่าง column) + scroll แนวตั้ง (ภายใน column)

**Bug ที่เจอและแก้แล้ว:**
- `overflow: hidden` บน `.carrier-group` ทำให้ `route-body` เห็น scrollHeight == clientHeight → ลบออก scroll ใช้งานได้
- field `carrier_id` อยู่ที่ `sale.order` (ไม่ใช่ `stock.picking`)
- field `package_level_ids` (ไม่ใช่ `package_ids`)

### 3. Fly.io Deployment
- ติดตั้ง flyctl, login, สร้าง app `odoo-tv-dashboard`
- สร้าง `fly.toml` (region: sin, port: 8000, min_machines: 1, auto_stop: false)
- Set secrets จาก `backend/config/.env` ขึ้น Fly.io โดยตรง (ไม่ commit ขึ้น GitHub)
- Deploy สำเร็จ ทุกหน้าตอบ HTTP 200

---

## โครงสร้าง Project

```
odoo-tv-dashboard/
├── backend/
│   ├── config/.env               ← Odoo credentials (ไม่ขึ้น GitHub)
│   ├── services/
│   │   ├── odoo_client.py        ← XML-RPC client (thread-safe ด้วย threading.local)
│   │   ├── sales_service.py      ← Sales TV logic + _get_problem_so_ids() (shared)
│   │   ├── store_service.py      ← Store TV logic (5 columns)
│   │   └── transport_service.py  ← Transport TV logic
│   ├── routes/api.py             ← FastAPI endpoints
│   └── main.py
├── frontend/
│   ├── sales-tv/index.html
│   ├── store-tv/index.html
│   ├── transport-tv/index.html
│   └── shared/
│       ├── tv.css                ← Dark theme, flex layout base
│       └── tv.js                 ← startClock()
├── docker/Dockerfile
├── docker-compose.yml
├── fly.toml                      ← Fly.io config
└── README.md
```

---

## Odoo Field Reference

| Field | Model | ใช้งาน |
|-------|-------|--------|
| `x_studio_selection_field_92b_1jnor75f1` | `sale.order` | เส้นทางการจัดส่ง |
| `carrier_id` | `sale.order` | วิธีการจัดส่ง → `delivery.carrier` |
| `x_studio_picked` | `sale.order.line` | จำนวนที่หยิบแล้ว |
| `x_studio_char_field_50v_1jnoq3ou3` | `sale.order` | เลขบิล easy-acc |
| `x_studio_boolean_field_62d_1jnoq6a7n` | `sale.order` | ทำบิลจริงแล้ว |
| `package_level_ids` | `stock.picking` | นับจำนวน package |

### Picking Type IDs (คลังสินค้าหลัก)
| ID | ชื่อ | ใช้ใน |
|----|------|-------|
| 2 | Delivery Orders | Transport TV, Store TV (delivery column) |
| 3 | Pick | Store TV (pick column) |
| 4 | Pack | Store TV (pack column) |
| 18 | Delivery Orders (คลังเคลม) | Store TV (delivery column รวม) |

---

## สิ่งที่อาจทำต่อ (Backlog)

- [ ] ข้อมูล Sales TV ยังไม่ได้ระบุเส้นทางใน Odoo → column ส่วนใหญ่อยู่ "ยังไม่ระบุ"
- [ ] Transport TV อาจเพิ่ม auto-scroll แนวตั้งเป็น marquee สำหรับ TV ที่ไม่มีคนควบคุม
- [ ] อาจเพิ่ม `/claim` หน้าสำหรับคลังเคลมโดยเฉพาะ
- [ ] Fly.io free tier: ถ้าใช้เกิน 160 ชม./เดือน อาจต้องจ่ายเงิน (ปัจจุบัน 2 machines × 24ชม. = ~1,460 ชม./เดือน → เกิน free tier แน่นอน แนะนำ upgrade หรือลด machine เหลือ 1)

---

## คำสั่งที่ใช้บ่อย

```bash
# Run local
cd ~/odoo-tv-dashboard
docker compose up -d --build

# Deploy ขึ้น Fly.io
~/.fly/bin/flyctl deploy

# ดู logs Fly.io
~/.fly/bin/flyctl logs --app odoo-tv-dashboard --no-tail

# Set secret ใหม่
~/.fly/bin/flyctl secrets set KEY=value --app odoo-tv-dashboard
```
