# Odoo TV Dashboard

ระบบแสดงผลข้อมูลจาก Odoo 18 บน TV แบบ Realtime สำหรับ 3 แผนก ได้แก่ ฝ่ายขาย, คลังสินค้า, และขนส่ง

---

## หน้าจอ TV

| URL | แผนก | เนื้อหา |
|-----|------|---------|
| `/sales` | ฝ่ายขาย | SO ที่จัดสินค้าเสร็จแล้ว รอออกบิล จัดกลุ่มตามเส้นทาง |
| `/store` | คลังสินค้า | สถานะ PICK / PACK / DELIVERY พร้อมแจ้งเตือนยอดไม่ตรง |
| `/transport` | ขนส่ง | Delivery จัดกลุ่มตามเส้นทางการจัดส่ง → วิธีการจัดส่ง |

---

## Tech Stack

- **Backend**: Python 3.12 + FastAPI + Odoo XML-RPC
- **Frontend**: HTML / CSS / JavaScript (Vanilla — เหมาะกับ TV display)
- **Deployment**: Docker Compose
- **Refresh**: Frontend polling ทุก 10 วินาที

---

## โครงสร้าง Project

```
odoo-tv-dashboard/
├── backend/
│   ├── config/
│   │   └── .env                  # Odoo credentials + app config
│   ├── services/
│   │   ├── odoo_client.py        # XML-RPC client (thread-safe)
│   │   ├── sales_service.py      # Logic หน้า Sales TV
│   │   ├── store_service.py      # Logic หน้า Store TV
│   │   └── transport_service.py  # Logic หน้า Transport TV
│   ├── routes/
│   │   └── api.py                # FastAPI endpoints
│   └── main.py                   # App entry point
├── frontend/
│   ├── sales-tv/
│   │   └── index.html
│   ├── store-tv/
│   │   └── index.html
│   ├── transport-tv/
│   │   └── index.html
│   └── shared/
│       ├── tv.css                # Global dark-theme styles
│       └── tv.js                 # Shared JS (clock, etc.)
├── docker/
│   └── Dockerfile
├── docker-compose.yml
└── docs/
    └── odoo-fields.md            # Field mapping reference
```

---

## Quick Start

```bash
# 1. คัดลอก config
cp backend/config/.env.example backend/config/.env

# 2. แก้ไข .env ใส่ข้อมูล Odoo server
nano backend/config/.env

# 3. รัน
docker compose up -d --build
```

หน้าจอพร้อมใช้งานที่ http://localhost:8000

---

## Environment Variables (`.env`)

```env
ODOO_URL=https://your-odoo.com/odoo   # URL ของ Odoo server
ODOO_DB=your-database-name            # ชื่อ database
ODOO_USERNAME=user@example.com        # username
ODOO_PASSWORD=your_api_key_or_password

APP_HOST=0.0.0.0
APP_PORT=8000
REFRESH_INTERVAL=10                   # ดึงข้อมูลทุกกี่วินาที (frontend)
```

---

## Logic แต่ละหน้า

---

### 1. Sales TV (`/sales`)

**วัตถุประสงค์**: แสดง SO ที่จัดสินค้าเสร็จแล้ว (หยิบแล้ว > 0) รอฝ่ายขายออกบิลให้ลูกค้า

**แหล่งข้อมูล**: `sale.order`

**เงื่อนไขการดึงข้อมูล**:
- `order_line.x_studio_picked > 0` — มีสินค้าที่หยิบแล้วอย่างน้อย 1 รายการ
- `date_order >= 2026-05-01` — เฉพาะ SO ตั้งแต่ 1 พ.ค. 2569 เป็นต้นไป
- ซ่อน SO ที่ `ทำบิลจริงแล้ว = True` และ `write_date` เกิน 24 ชั่วโมง

**การจัดกลุ่ม**: แยก column ตาม **เส้นทางการจัดส่ง**
```
กรุงเทพ → สายใน → สายนอก → รับหน้าบริษัท → เซลล์ส่งเอง → ยังไม่ระบุ
```

**Column พิเศษ (⚠ บิลมีปัญหา)**: แสดง SO ที่ยอด PICK (done) ≠ PACK (done)
- ดึง `stock.move` ของ PICK/PACK ที่ `state = done`
- หักยอด Return picking ออก (ตรวจจาก origin มีคำว่า "การส่งคืนของ" หรือ "Return of")
- Return PACK ตัดออกทั้งก้อน (ไม่นับเป็น error)
- เรียงตาม diff มากสุดก่อน

**Odoo Fields ที่ใช้**:

| Field | Model | หมายเหตุ |
|-------|-------|---------|
| `x_studio_picked` | `sale.order.line` | จำนวนที่หยิบแล้ว |
| `x_studio_selection_field_92b_1jnor75f1` | `sale.order` | เส้นทางการจัดส่ง |
| `x_studio_char_field_50v_1jnoq3ou3` | `sale.order` | เลขที่บิล easy-acc |
| `x_studio_boolean_field_62d_1jnoq6a7n` | `sale.order` | ทำบิลจริงแล้ว |
| `picking_type_id = 3` | `stock.picking` | PICK (คลังสินค้าหลัก) |
| `picking_type_id = 4` | `stock.picking` | PACK (คลังสินค้าหลัก) |

---

### 2. Store TV (`/store`)

**วัตถุประสงค์**: แสดงสถานะงานคลังสินค้า แบ่งเป็น 5 column

**แหล่งข้อมูล**: `stock.picking` (คลังสินค้าหลัก + คลังของเคลม)

**เงื่อนไขการดึงข้อมูล**:
- `state not in [cancel, done]` — เฉพาะที่ยังไม่เสร็จ
- `create_date >= 2026-05-01` — เฉพาะตั้งแต่ 1 พ.ค. 2569
- `picking_type_id in [2, 3, 4]` — คลังหลัก (Delivery, Pick, Pack)
- คลังเคลม (`picking_type_id = 18`) ดึงมาด้วย **เฉพาะลูกค้าที่มีของออกจากคลังหลักด้วย**

**Picking Type IDs (คลังสินค้าหลัก)**:

| ID | ชื่อ | Column |
|----|------|--------|
| 3 | Pick | PICK |
| 4 | Pack | PACK |
| 2 | Delivery Orders | DELIVERY |
| 18 | Delivery Orders (คลังของเคลม) | DELIVERY |

**5 Column ที่แสดง**:

| Column | สี | เนื้อหา |
|--------|----|---------|
| **PICK** | น้ำเงิน | SO ที่มี picking type = Pick ยังไม่เสร็จ |
| **PACK** | เหลือง | SO ที่มี picking type = Pack ยังไม่เสร็จ |
| **DELIVERY** | เขียว | SO ที่มี picking type = Delivery ยังไม่เสร็จ (รวมคลังเคลม) |
| **รวม SO** | ม่วง | แต่ละ SO แสดง PICK+PACK+DEL ในการ์ดเดียว เรียงตามเวลาค้างนานสุด |
| **⚠ Pick ≠ Pack** | แดง | SO ที่ยอด PICK done ≠ PACK done (reuse logic จาก Sales TV) |

**เวลาค้าง (Elapsed Time)**:
- คำนวณจาก `create_date` ของ picking เก่าสุดของ SO นั้น
- สี: เขียว (< 4 ชม.) / เหลือง (4–8 ชม.) / แดง (> 8 ชม.)

**Logic คลังเคลม**:
1. Query คลังหลัก → เก็บ `partner_id` ที่มีของออก
2. Query คลังเคลม โดย filter `partner_id in [...]` — ดึงเฉพาะลูกค้าที่มีของคลังหลักด้วย
3. ถ้าไม่มี `origin` (SO) ใช้ชื่อเอกสาร (`name`) เป็น key แทน

---

### 3. Transport TV (`/transport`)

**วัตถุประสงค์**: แสดง Delivery Order จัดกลุ่มตามเส้นทาง และวิธีการจัดส่ง

**แหล่งข้อมูล**: `stock.picking` (Delivery คลังหลัก) + `sale.order` (route, carrier)

**เงื่อนไขการดึงข้อมูล**:
- `picking_type_id = 2` — Delivery Orders คลังสินค้าหลัก
- `state not in [cancel, done]`
- `create_date >= 2026-05-01`
- มี `origin` (SO) เท่านั้น

**การจัดกลุ่ม**:
```
เส้นทางการจัดส่ง
  └── วิธีการจัดส่ง (carrier)
        └── SO cards
```

เส้นทางเรียงตามลำดับ:
```
กรุงเทพ → สายใน → สายนอก → รับหน้าบริษัท → เซลล์ส่งเอง → ยังไม่ระบุเส้นทาง
```

วิธีการจัดส่งเรียง A–Z, "ยังไม่ระบุวิธีส่ง" ไว้ท้าย

**Odoo Fields ที่ใช้**:

| Field | Model | หมายเหตุ |
|-------|-------|---------|
| `x_studio_selection_field_92b_1jnor75f1` | `sale.order` | เส้นทางการจัดส่ง |
| `carrier_id` | `sale.order` | วิธีการจัดส่ง → `delivery.carrier` |

**หมายเหตุ**: field เส้นทางและ carrier ต้องกรอกใน Sale Order ก่อน ถึงจะแสดงในหน้านี้ได้ถูกต้อง

---

## API Endpoints

| Method | Path | คำอธิบาย |
|--------|------|---------|
| GET | `/sales` | หน้า Sales TV (HTML) |
| GET | `/store` | หน้า Store TV (HTML) |
| GET | `/transport` | หน้า Transport TV (HTML) |
| GET | `/api/sales/ready-to-invoice` | JSON: SO รอออกบิล |
| GET | `/api/store/pickings` | JSON: picking data 5 column |
| GET | `/api/transport/pickings` | JSON: delivery จัดกลุ่มเส้นทาง |
| GET | `/docs` | Swagger UI |

---

## Odoo Connection

ใช้ **XML-RPC** ผ่าน `xmlrpc.client` (Python standard library)

- `odoo_client.py` เป็น thread-safe โดยใช้ `threading.local()` สำหรับ `ServerProxy`
- Authenticate ครั้งเดียว cache `uid` ไว้ใน instance

```python
# ตัวอย่างการ query
from services.odoo_client import odoo

records = odoo.search_read(
    "stock.picking",
    [("state", "=", "assigned")],
    ["name", "partner_id", "origin"],
    limit=100
)
```

---

## การเพิ่มหน้า TV ใหม่

1. สร้าง `backend/services/<name>_service.py`
2. เพิ่ม endpoint ใน `backend/routes/api.py`
3. สร้าง `frontend/<name>-tv/index.html`
4. Rebuild: `docker compose up -d --build`
