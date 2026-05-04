# Odoo TV Dashboard

ระบบแสดงผลข้อมูลจาก Odoo 18.1E บน TV แบบ Realtime สำหรับ 2 แผนก

## หน้าจอ TV แต่ละแผนก

### 1. Sales TV (`/frontend/sales-tv`)
แสดงรายการบิล (Stock Picking) ที่จัดสินค้าเสร็จแล้ว (สถานะ Done) รอให้ฝ่ายขายออกบิลให้ลูกค้า

### 2. Store TV (`/frontend/store-tv`)
แสดงสถานะใบ Pick / Pack / Delivery แยกตาม custom field "ขนส่งท้องถิ่น" ใน Odoo

## Tech Stack

- **Backend**: Python (FastAPI) + Odoo XML-RPC/JSON-RPC API
- **Frontend**: HTML/CSS/JavaScript (Vanilla - เหมาะกับ TV display)
- **Real-time**: WebSocket (FastAPI)
- **Deployment**: Docker Compose

## โครงสร้าง Project

```
odoo-tv-dashboard/
├── backend/
│   ├── config/         # Odoo connection config, env vars
│   ├── services/       # Odoo API service (xmlrpc)
│   ├── routes/         # FastAPI endpoints
│   └── utils/          # helpers
├── frontend/
│   ├── sales-tv/       # หน้าจอฝ่ายขาย
│   ├── store-tv/       # หน้าจอ Store / คลังสินค้า
│   └── shared/         # CSS, JS, components ร่วมกัน
├── docker/             # Dockerfile, docker-compose
└── docs/               # เอกสาร API, field mapping
```

## Quick Start

```bash
cp backend/config/.env.example backend/config/.env
# แก้ไข .env ใส่ข้อมูล Odoo server
docker-compose up -d
```

## URLs
- Sales TV : http://localhost:8000/sales
- Store TV  : http://localhost:8000/store
- API Docs  : http://localhost:8000/docs
