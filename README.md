# Odoo TV Dashboard

ระบบ Dashboard แสดงข้อมูลคลังสินค้าและการจัดส่งแบบ Real-time เชื่อมต่อกับ Odoo 18 ผ่าน XML-RPC

---

## หน้าที่มีทั้งหมด

| หน้า | URL | อุปกรณ์ | รีเฟรช |
|------|-----|---------|--------|
| Sales TV | `/sales` | จอ TV | 10 วิ |
| Store TV | `/store` | จอ TV | 10 วิ |
| Transport TV | `/transport` | จอ TV | 10 วิ |
| Mobile รับบิล | `/mobile/receive-bill` | มือถือ (PWA) | manual |
| Tablet ขึ้นรถ | `/tablet/dispatch` | tablet (PWA) | manual |

---

## แต่ละหน้าทำอะไร

### Sales TV (`/sales`)
แสดงรายการ Picking ที่รอออกบิล จัดกลุ่มตาม **เส้นทางจัดส่ง** (กรุงเทพ / สายใน / สายนอก / รับหน้าบริษัท / เซลล์ส่งเอง)
- มี QR code มุมขวาล่างสำหรับสแกนไปหน้ารับบิล
- ไฮไลต์ SO ที่ยอด Pick ≠ Pack (บิลมีปัญหา)

### Store TV (`/store`)
แสดงสถานะงานคลัง 5 column:
- **PICK** — งานที่กำลัง pick อยู่
- **PACK** — งานที่กำลัง pack อยู่
- **DELIVERY** — งานที่รอส่ง
- **รวม SO** — cross-column view พร้อม elapsed time (เขียว/เหลือง/แดง)
- **⚠ Pick≠Pack** — SO ที่มียอดไม่ตรงกัน

### Transport TV (`/transport`)
แสดง Delivery Orders จัดกลุ่มตาม route → ขนส่ง แสดงข้อมูล SO พร้อมจำนวน package และชิ้น

### Mobile รับบิล (`/mobile/receive-bill`) — PWA
สำหรับพนักงาน Store ไปรับบิลจากแผนกเซลล์:
1. เปิดหน้าจาก QR code บน Sales TV
2. ติ้ก SO ที่ได้รับบิล
3. กรอกชื่อ + เซ็นลายมือบน canvas
4. กด "ยืนยันรับบิล" → ระบบ mark `รับบิลแล้ว = True` + แนบ signature ใน Odoo chatter

### Tablet ขึ้นรถ (`/tablet/dispatch`) — PWA
สำหรับพนักงานคลังยืนยันสินค้าขึ้นรถ:
1. เลือกเส้นทาง (ปุ่มใหญ่สีสด)
2. ดูตาราง SO: ลูกค้า / จังหวัด / ขนส่ง / บิลจริง / แพ็ค / ชิ้น / หมายเหตุ
3. ติ้ก SO ที่ขึ้นรถ
4. กรอก ทะเบียนรถ / คนขับ / เวลา → ยืนยัน
5. ระบบ mark `ขึ้นรถจัดส่งแล้ว = True` + post chatter ทุก SO

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Odoo XML-RPC
- **Frontend**: Vanilla HTML/CSS/JS (ไม่มี framework)
- **Database**: ไม่มี — ดึงตรงจาก Odoo ทุกครั้ง
- **Hosting**: Render.com (Docker, Free tier)

---

## โครงสร้างไฟล์

```
odoo-tv-dashboard/
├── backend/
│   ├── config/
│   │   ├── .env                      ← credentials (ไม่ขึ้น git)
│   │   └── .env.example
│   ├── main.py
│   ├── routes/api.py
│   └── services/
│       ├── odoo_client.py
│       ├── sales_service.py
│       ├── store_service.py
│       ├── transport_service.py
│       ├── bill_receipt_service.py
│       └── dispatch_service.py
├── frontend/
│   ├── sales-tv/index.html
│   ├── store-tv/index.html
│   ├── transport-tv/index.html
│   ├── mobile-receive-bill/index.html
│   ├── tablet-dispatch/index.html
│   └── shared/
│       ├── tv.css
│       ├── tv.js
│       ├── qrcode.min.js
│       ├── sw.js                     ← PWA Service Worker
│       ├── manifest-receive-bill.json
│       ├── manifest-dispatch.json
│       ├── icon-receive-bill.svg
│       └── icon-dispatch.svg
├── Dockerfile                        ← สำหรับ Render.com
├── docker/Dockerfile                 ← สำหรับ local / Fly.io
├── docker-compose.yml
├── render.yaml
└── fly.toml
```

---

## ติดตั้งและรันแบบ Local

### 1. ตั้งค่า Environment
```bash
cp backend/config/.env.example backend/config/.env
# แก้ไขค่าใน .env ให้ตรงกับ Odoo server
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

1. Fork / push โค้ดขึ้น GitHub
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
6. (แนะนำ) ตั้ง [UptimeRobot](https://uptimerobot.com) ping `/health` ทุก 5 นาที เพื่อป้องกัน free tier sleep

---

## PWA — ติดตั้งบนมือถือ / tablet

**Android (Chrome):** เปิด URL → แถบที่อยู่มีไอคอน "ติดตั้ง" หรือ ⋮ → เพิ่มลงหน้าจอหลัก

**iOS (Safari):** เปิด URL → Share → "เพิ่มลงหน้าจอหลัก"

ได้ icon + เปิดแบบ fullscreen ไม่มี browser bar

---

## Odoo Field Reference

| Field | Model | ความหมาย |
|-------|-------|-----------|
| `x_studio_selection_field_92b_1jnor75f1` | `sale.order` | เส้นทางการจัดส่ง |
| `x_studio_boolean_field_62d_1jnoq6a7n` | `sale.order` | ทำบิลจริงแล้ว |
| `x_studio_boolean_field_5bd_1jnp0r53i` | `sale.order` | รับบิลแล้ว |
| `x_studio_boolean_field_2dc_1jnrn22ck` | `sale.order` | ขึ้นรถจัดส่งแล้ว |
| `x_studio_char_field_50v_1jnoq3ou3` | `sale.order` | เลขบิล easy-acc |
| `x_studio_datetime_field_is_1jnrfclrr` | `sale.order` | เวลารับบิล |
| `delivery_method` | `sale.order` | วิธีการจัดส่ง |
| `package_level_ids` | `stock.picking` | จำนวน package |
