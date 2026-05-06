# Odoo TV Dashboard

ระบบ Dashboard แสดงข้อมูลคลังสินค้าและการจัดส่งแบบ Real-time เชื่อมต่อกับ Odoo 18 ผ่าน XML-RPC  
รองรับทั้งจอ TV, มือถือ (PWA), และ Tablet (PWA)

---

## หน้าที่มีทั้งหมด

| หน้า | URL | อุปกรณ์ | รีเฟรช |
|------|-----|---------|--------|
| **Home** | `/` | ทุกอุปกรณ์ | — |
| **Sales TV** | `/sales` | จอ TV | 10 วิ |
| **Store TV** | `/store` | จอ TV | 10 วิ |
| **Transport TV** | `/transport` | จอ TV | 10 วิ |
| **Mobile รับบิล** | `/mobile/receive-bill` | มือถือ (PWA) | manual |
| **Tablet ขึ้นรถ** | `/tablet/dispatch` | tablet (PWA) | manual |

---

## แต่ละหน้าทำอะไร

### Home (`/`)
หน้าหลักแสดงปุ่มนำทางใหญ่ไปทุกหน้า พร้อมนาฬิกา real-time  
เหมาะสำหรับเปิดบน kiosk หรือแท็บเล็ตตั้งโต๊ะ

### Sales TV (`/sales`)
แสดงรายการ Sale Order ที่พร้อมออกบิล จัดกลุ่มตาม **เส้นทางจัดส่ง**

- ไฮไลต์ SO ที่ยอด Pick ≠ Pack (มีปัญหา)
- มี **QR code** มุมขวาล่าง → สแกนเปิดหน้ารับบิลบนมือถือ
- รีเฟรชทุก 10 วินาที

### Store TV (`/store`)
แสดงสถานะงานคลัง 5 column:

| Column | ความหมาย |
|--------|----------|
| PICK | งานที่กำลัง pick อยู่ |
| PACK | งานที่กำลัง pack อยู่ |
| DELIVERY | งานที่รอส่ง |
| รวม SO | cross-column view + elapsed time (เขียว/เหลือง/แดง) |
| ⚠ Pick≠Pack | SO ที่มียอดไม่ตรงกัน |

### Transport TV (`/transport`)
แสดง Delivery Orders จัดกลุ่มตาม **route → ขนส่ง**  
แสดงข้อมูล SO พร้อมจำนวน package และชิ้น

### Mobile รับบิล (`/mobile/receive-bill`) — PWA

สำหรับพนักงาน Store ไปรับบิลจากแผนกเซลล์:

1. สแกน QR code จากหน้า Sales TV หรือเปิด URL โดยตรง
2. ติ้กเลือก SO ที่ได้รับบิล
3. กรอกชื่อผู้รับ + เซ็นลายมือบน canvas
4. กด **"ยืนยันการรับบิล"**
5. ระบบ:
   - สร้างเอกสาร **Invoice Transfer** (เลขที่ `IT2026/XXXX`) ใน Odoo
   - บันทึกชื่อผู้รับ + ลายเซ็น + เวลา
   - mark `รับบิลแล้ว = True` บนแต่ละ SO
   - แนบลายเซ็นและ post chatter บนแต่ละ SO
6. หน้าจอแสดง **เลขที่เอกสาร** หลัง confirm สำเร็จ

### Tablet ขึ้นรถ (`/tablet/dispatch`) — PWA

สำหรับพนักงานคลังยืนยันสินค้าขึ้นรถ:

1. กดเลือกเส้นทาง (ปุ่มใหญ่ สีต่างกันแต่ละสาย พร้อมจำนวน SO รอ)
2. ดูตาราง SO จัดกลุ่มตามขนส่ง: ลูกค้า / จังหวัด / ขนส่ง / บิลจริง✓ / แพ็ค / ชิ้น / หมายเหตุ
3. ติ้ก SO ที่ขึ้นรถแล้ว (หรือ "เลือกทั้งหมด")
4. กด **"ยืนยันขึ้นรถ"** → กรอก ทะเบียนรถ / คนขับ / เวลา
5. ระบบ mark `ขึ้นรถจัดส่งแล้ว = True` + post chatter ทุก SO

---

## Odoo Data Model

### sale.order — Custom Fields

| Field Name | Type | ความหมาย |
|------------|------|-----------|
| `x_studio_selection_field_92b_1jnor75f1` | selection | เส้นทางการจัดส่ง |
| `x_studio_boolean_field_62d_1jnoq6a7n` | boolean | ทำบิลจริงแล้ว |
| `x_studio_boolean_field_5bd_1jnp0r53i` | boolean | รับบิลแล้ว |
| `x_studio_boolean_field_2dc_1jnrn22ck` | boolean | ขึ้นรถจัดส่งแล้ว |
| `x_studio_char_field_50v_1jnoq3ou3` | char | เลขบิล easy-acc |
| `x_studio_datetime_field_is_1jnrfclrr` | datetime | เวลารับบิล (UTC) |
| `delivery_method` | many2one → delivery.carrier | วิธีการจัดส่ง |
| `package_level_ids` | one2many | จำนวน package |

### x_tv_dashboard_invoice — Invoice Transfer Header

Custom model สำหรับบันทึกแต่ละรอบการรับบิล (1 record = 1 รอบ)

| Field Name | Type | ความหมาย |
|------------|------|-----------|
| `x_name` | char | เลขที่เอกสาร เช่น `IT2026/0001` |
| `x_transfer_datetime` | datetime | วันเวลาที่รับบิล (UTC) |
| `x_signer_name` | char | ชื่อผู้รับบิล |
| `x_signature` | binary (image) | ลายเซ็นผู้รับ (PNG) |
| `x_state` | selection | `draft` / `confirmed` |
| `x_studio_notes` | html | หมายเหตุ |
| `x_tv_dashboard_invoice_line_ids_90795` | one2many → line | รายการ SO ในรอบนี้ |

### x_tv_dashboard_invoice_line_1992d — Invoice Transfer Line

| Field Name | Type | ความหมาย |
|------------|------|-----------|
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

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI |
| Odoo integration | XML-RPC (`xmlrpc.client`) |
| Frontend | Vanilla HTML / CSS / JS (ไม่มี framework) |
| PWA | Service Worker + Web App Manifest |
| Database | ไม่มี — ดึงตรงจาก Odoo ทุกครั้ง |
| Hosting | Render.com (Docker, Free tier, Singapore) |

---

## โครงสร้างไฟล์

```
odoo-tv-dashboard/
├── backend/
│   ├── config/
│   │   ├── .env                         ← Odoo credentials (ไม่ขึ้น git)
│   │   └── .env.example
│   ├── main.py                          ← FastAPI app entry point
│   ├── requirements.txt
│   ├── routes/
│   │   └── api.py                       ← ทุก route และ endpoint
│   └── services/
│       ├── odoo_client.py               ← XML-RPC client (thread-safe)
│       ├── sales_service.py             ← Sales TV logic
│       ├── store_service.py             ← Store TV logic
│       ├── transport_service.py         ← Transport TV logic
│       ├── bill_receipt_service.py      ← รับบิล + Invoice Transfer
│       └── dispatch_service.py          ← ขึ้นรถ logic
├── frontend/
│   ├── home/
│   │   └── index.html                   ← หน้าหลัก
│   ├── sales-tv/
│   │   └── index.html
│   ├── store-tv/
│   │   └── index.html
│   ├── transport-tv/
│   │   └── index.html
│   ├── mobile-receive-bill/
│   │   └── index.html                   ← PWA
│   ├── tablet-dispatch/
│   │   └── index.html                   ← PWA
│   └── shared/
│       ├── tv.css                       ← shared dark theme
│       ├── tv.js                        ← shared utilities
│       ├── qrcode.min.js
│       ├── sw.js                        ← PWA Service Worker
│       ├── manifest-receive-bill.json
│       ├── manifest-dispatch.json
│       ├── icon-receive-bill.svg
│       └── icon-dispatch.svg
├── Dockerfile                           ← สำหรับ Render.com
├── docker/Dockerfile                    ← สำหรับ local / Fly.io
├── docker-compose.yml
├── render.yaml                          ← Render.com config
└── fly.toml                             ← Fly.io config (เก็บไว้)
```

---

## ติดตั้งและรันแบบ Local

### 1. ตั้งค่า Environment

```bash
cp backend/config/.env.example backend/config/.env
# แก้ไขค่าใน .env ให้ตรงกับ Odoo server
```

```env
ODOO_URL=https://your-odoo-server.com
ODOO_DB=your_database_name
ODOO_USERNAME=your@email.com
ODOO_PASSWORD=your_api_key_or_password
```

### 2. รันด้วย Python

```bash
pip install -r backend/requirements.txt
uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

### 3. รันด้วย Docker

```bash
docker compose up -d --build
```

เปิดที่ http://localhost:8000

---

## Deploy บน Render.com

1. Push โค้ดขึ้น GitHub
2. สมัคร [Render.com](https://render.com) → New → Web Service → เลือก repo
3. Render จะอ่าน `render.yaml` อัตโนมัติ
4. ตั้ง Environment Variables ใน Render dashboard:

| Key | ค่า |
|-----|-----|
| `ODOO_URL` | URL ของ Odoo server |
| `ODOO_DB` | ชื่อ database |
| `ODOO_USERNAME` | อีเมล login |
| `ODOO_PASSWORD` | API key หรือรหัสผ่าน |

5. กด **Deploy**
6. ตั้ง [UptimeRobot](https://uptimerobot.com) ping `/health` ทุก 5 นาที เพื่อป้องกัน free tier sleep

---

## PWA — ติดตั้งบนมือถือ / Tablet

**Android (Chrome):**
เปิด URL → แถบที่อยู่มีไอคอน "ติดตั้ง" หรือ ⋮ Menu → เพิ่มลงหน้าจอหลัก

**iOS (Safari):**
เปิด URL → ปุ่ม Share → "เพิ่มลงหน้าจอหลัก"

ได้ icon + เปิดแบบ fullscreen ไม่มี browser bar

---

## API Endpoints

| Method | Path | ความหมาย |
|--------|------|-----------|
| GET | `/` | Home page |
| GET | `/sales` | Sales TV page |
| GET | `/store` | Store TV page |
| GET | `/transport` | Transport TV page |
| GET | `/mobile/receive-bill` | Mobile รับบิล page |
| GET | `/tablet/dispatch` | Tablet ขึ้นรถ page |
| GET | `/health` | Health check (สำหรับ UptimeRobot) |
| GET | `/docs` | FastAPI auto-generated docs |
| GET | `/api/sales/ready-to-invoice` | ดึง SO พร้อมออกบิล |
| GET | `/api/store/pickings` | ดึงงานคลัง |
| GET | `/api/transport/pickings` | ดึง delivery orders |
| GET | `/api/mobile/pending-receipts` | ดึง SO รอรับบิล |
| POST | `/api/mobile/confirm-receipt` | ยืนยันรับบิล (สร้าง Invoice Transfer) |
| GET | `/api/dispatch/routes` | ดึงเส้นทางทั้งหมด |
| GET | `/api/dispatch/route?name=XX` | ดึง SO ตามเส้นทาง |
| POST | `/api/dispatch/confirm` | ยืนยันขึ้นรถ |

---

## Odoo Setup ที่ต้องทำก่อนใช้งาน

### Fields ที่ต้องสร้างใน Odoo Studio (sale.order)
- เส้นทางการจัดส่ง (Selection)
- ทำบิลจริงแล้ว (Boolean)
- รับบิลแล้ว (Boolean)
- ขึ้นรถจัดส่งแล้ว (Boolean)
- เลขบิล easy-acc (Char)
- เวลารับบิล (Datetime)

### Model ที่ต้องสร้างใน Odoo Studio
**TV_dashboard_invoice_tranfer** (`x_tv_dashboard_invoice`)  
ต้องเปิด "Has Mail Thread" เพื่อให้มี chatter

Fields ใน header: `x_name`, `x_signer_name`, `x_signature`, `x_transfer_datetime`, `x_state`  
Fields ใน line (`x_tv_dashboard_invoice_line_1992d`): `x_so_id`

### View Setup
หลังสร้าง fields แล้วต้อง drag เข้า Form View ใน Studio ด้วยตนเอง ไม่งั้น fields จะมีข้อมูลแต่ไม่แสดงใน UI
