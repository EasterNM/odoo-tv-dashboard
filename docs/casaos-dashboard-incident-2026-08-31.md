# สรุปโครงการและเหตุการณ์ Odoo TV Dashboard บน CasaOS

วันที่สรุป: 31 สิงหาคม 2026  
เครื่องเซิร์ฟเวอร์: CasaOS / Ubuntu (`10.2.3.23`)  
Repository: `EasterNM/odoo-tv-dashboard`

> เอกสารนี้ไม่เก็บรหัสผ่าน บัญชีล็อกอิน token หรือ secret ใด ๆ

## 1. งานที่ดำเนินการกับโครงการ

- Clone และศึกษาโครงสร้างโครงการ Odoo TV Dashboard
- ลบหน้าและโค้ด Marelli Report ออกจากระบบ
- ตรวจสอบและวิเคราะห์การทำงานของหน้า `/store`
- เพิ่มระบบอัปเดตจาก Git สำหรับเครื่อง CasaOS
  - `deploy/auto-update.sh`
  - `deploy/install-auto-update.sh`
- Deploy เวอร์ชันปัจจุบันบน CasaOS ด้วย Docker Compose
- แก้ Tailscale container ที่ restart loop หลังระบบ/Kernel อัปเดต
- เพิ่มสคริปต์ Windows สำหรับล้าง DNS cache
  - `deploy/windows-flush-dashboard-dns.bat`

## 2. URL ที่ใช้งาน

### URL ผ่านอินเทอร์เน็ต/Tailscale Funnel

```text
https://mtech.tail3a0947.ts.net:8443/store
```

- ใช้ HTTPS
- ใช้ได้ทั้งจากในและนอกองค์กรเมื่อ DNS resolve ได้ถูกต้อง
- Proxy ผ่าน Tailscale Funnel ไปที่ `http://127.0.0.1:8000`

### URL ภายในบริษัท (ทางสำรองปัจจุบัน)

```text
http://10.2.3.23:8000/store
```

- ใช้ได้เฉพาะอุปกรณ์ที่เข้าถึงเครือข่ายภายใน `10.2.3.x`
- ไม่ขึ้นกับ public DNS หรือ Tailscale Funnel
- เป็น HTTP ไม่ใช่ HTTPS จึงควรใช้เฉพาะ LAN ที่เชื่อถือได้

## 3. อาการที่พบ

- ผู้ใช้หลายเครื่องในองค์กรเข้า URL `.ts.net` ไม่ได้พร้อมกัน
- Browser แสดง `ERR_FAILED` หรือไม่สามารถโหลดชื่อโดเมนได้
- เครื่องของผู้ดูแลใช้งานได้หลังเปลี่ยน DNS เป็น Cloudflare
- Dashboard container และ backend ยังคงทำงานตามปกติ

## 4. ผลตรวจสอบเซิร์ฟเวอร์

- Dashboard container: `odoo-tv-dashboard`
- สถานะหลังแก้ไข: `healthy`
- Backend ตอบ `/store` เป็น HTTP 200
- Server IP: `10.2.3.23`
- DNS เดิมของเซิร์ฟเวอร์ยังคงเป็น:
  - Primary: `8.8.8.8`
  - Secondary: `8.8.4.4`
- DNS ของเซิร์ฟเวอร์ไม่ได้ถูกเปลี่ยน

## 5. ปัญหา Tailscale ที่พบและการแก้ไข

หลัง Kernel/ระบบอัปเดต Tailscale container เคยเข้า restart loop เพราะการใช้ TUN แบบเดิมไม่ทำงาน จึงเปลี่ยน entrypoint ของ Tailscale เป็น userspace networking:

```text
tailscaled --tun=userspace-networking --state=...
```

ไฟล์ที่แก้บนเซิร์ฟเวอร์:

```text
/var/lib/casaos/apps/tailscale/docker-compose.yml
```

ไฟล์สำรอง:

```text
/var/lib/casaos/apps/tailscale/docker-compose.yml.bak-20260831
```

หลังแก้:

- Tailscale container ทำงานต่อเนื่อง
- Restart count เป็น 0
- Funnel พอร์ต `8443` ถูกรีเฟรชและประกาศใหม่สำเร็จ
- Funnel status ชี้ไปที่ `http://127.0.0.1:8000`

## 6. ผลตรวจสอบ Ruijie Cloud

Project: `M-TECH AUTO AIR CO.,LTD.`

- Gateway: 1/1 online
- Switch: 4/4 online
- AP: 7/7 online
- Alarm: 0
- Gateway model: `EG406XS`
- WAN egress IP ที่พบ: `171.101.162.149`
- Gateway config status: Synced

เครือข่าย DHCP ที่พบ:

| เครือข่าย | รายละเอียด | Gateway | DHCP pool | Lease time |
|---|---|---|---|---|
| Default VLAN | MANAGE | `10.2.1.1/24` | `10.2.1.2-10.2.1.254` | 30 นาที |
| VLAN 10 | SERVER | `10.2.2.1/24` | `10.2.2.30-10.2.2.254` | 30 นาที |
| VLAN 11 | CLIENT | `10.2.3.1/24` | `10.2.3.21-10.2.3.253` | 30 นาที |
| VLAN 12 | ACCESSPOINT | `10.2.4.1/24` | `10.2.4.2-10.2.4.254` | 30 นาที |

ยังไม่มีการเปลี่ยน DHCP DNS หรือค่าเครือข่ายใน Ruijie Cloud เนื่องจากภายหลังเลือกใช้ URL ผ่าน IP ภายในก่อน

## 7. การวิเคราะห์สาเหตุ

หลักฐานที่พบแยกได้เป็นสองส่วน:

1. Tailscale เคยหยุดทำงานหลังการอัปเดตระบบ ทำให้ Funnel หายไปชั่วคราว
2. หลัง Funnel กลับมา เครื่องลูกข่ายจำนวนมากที่ใช้ DNS เดิมยัง resolve ชื่อ `.ts.net` ไม่ได้ ขณะที่เครื่องที่ใช้ Cloudflare DNS เข้าได้

จึงมีความเป็นไปได้สูงว่า DNS resolver/cache ที่เครื่องลูกข่ายใช้ยังถือผลล้มเหลวเดิม หรือ resolver ตอบ record ของ `.ts.net` ไม่ตรงกัน อย่างไรก็ตามยังไม่ควรระบุว่า Google DNS เป็นสาเหตุเพียงอย่างเดียวจนกว่าจะตรวจ packet/DNS forwarding จาก Gateway เพิ่มเติม

การล้าง DNS cache ช่วยได้เฉพาะกรณี cache อยู่บนเครื่องลูกข่าย หาก upstream DNS ยังตอบผิด การล้าง cache อย่างเดียวจะไม่แก้ปัญหา

## 8. การเปิดใช้งานผ่าน IP ภายใน

เดิม Docker publish port เฉพาะ loopback:

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

เปลี่ยนเป็นเปิดรับจาก LAN:

```yaml
ports:
  - "0.0.0.0:8000:8000"
```

ไฟล์บนเซิร์ฟเวอร์:

```text
/home/jojo/apps/odoo-tv-dashboard/docker-compose.yml
```

ไฟล์สำรองก่อนเปลี่ยน:

```text
/home/jojo/apps/odoo-tv-dashboard/docker-compose.yml.bak-lan-20260831
```

ผลทดสอบจากเครื่องลูกข่าย:

```text
http://10.2.3.23:8000/store -> HTTP 200
```

## 9. สคริปต์ Windows ล้าง DNS cache

ไฟล์:

```text
deploy/windows-flush-dashboard-dns.bat
```

สิ่งที่สคริปต์ทำ:

1. เรียก `ipconfig /flushdns`
2. ตรวจชื่อโดเมนด้วย `nslookup`
3. แสดง URL Tailscale และ URL ภายในเป็นทางสำรอง

วิธีใช้:

1. ส่งไฟล์ไปยังเครื่อง Windows
2. คลิกขวา **Run as administrator**
3. ปิด Browser ทุกหน้าต่างแล้วเปิดใหม่
4. ทดลอง URL `.ts.net` อีกครั้ง

สำหรับการรันทุกเครื่องพร้อมกัน ควรแจกสคริปต์ผ่าน Group Policy, Microsoft Intune หรือระบบ Remote Management ขององค์กร

## 10. ระบบ Auto Update บน CasaOS

โครงการมีสคริปต์สำหรับตรวจ Git และ deploy เวอร์ชันใหม่อัตโนมัติ:

```text
deploy/auto-update.sh
deploy/install-auto-update.sh
```

แนวทางทำงาน:

- ตรวจ branch/commit จาก repository
- เมื่อพบเวอร์ชันใหม่ ให้ pull และ rebuild/recreate Docker container
- ตรวจ health หลัง deploy
- ควรเก็บ log และมี rollback เมื่อ health check ไม่ผ่าน

## 11. วิธี Rollback การเปิดพอร์ต LAN

บนเซิร์ฟเวอร์:

```bash
cd /home/jojo/apps/odoo-tv-dashboard
cp docker-compose.yml.bak-lan-20260831 docker-compose.yml
docker compose up -d
```

หลัง rollback Dashboard จะกลับไปฟังเฉพาะ `127.0.0.1:8000` และ URL ผ่าน IP ภายในจะเข้าไม่ได้

## 12. แนวทางดำเนินงานต่อ

### ระยะสั้น

- ให้ผู้ใช้ภายในบริษัทใช้ `http://10.2.3.23:8000/store`
- ใช้สคริปต์ล้าง DNS cache เมื่อจำเป็น
- ตรวจว่า Client VLAN สามารถเข้าถึง `10.2.3.23:8000` ได้ทุกจุด

### ระยะกลาง

- ให้ vendor ตรวจ DHCP DNS/DNS forwarding ของ Ruijie Gateway
- หากจะเปลี่ยน DNS ที่แจกให้ลูกข่าย ให้บันทึกค่าเดิมก่อนและทดสอบทีละ VLAN
- ตัวเลือก DNS ที่เสนอไว้คือ `1.1.1.1` และ `9.9.9.9`

### ระยะยาว

- ใช้โดเมนบริษัท เช่น `dashboard.<company-domain>`
- ใช้ reverse proxy หรือ Cloudflare Tunnel พร้อม HTTPS
- เพิ่ม health check และแจ้งเตือนเมื่อ Dashboard หรือ Tunnel หยุดทำงาน
- จำกัด firewall ของพอร์ต `8000` ให้เข้าถึงได้เฉพาะ subnet ภายในที่จำเป็น

## 13. สถานะสุดท้าย ณ เวลาจัดทำเอกสาร

- Dashboard container: ทำงานและ healthy
- หน้า `/store`: ตอบ HTTP 200
- URL ภายใน: ใช้งานได้
- Tailscale Funnel: เปิดใช้งานที่พอร์ต 8443
- DNS ของเซิร์ฟเวอร์: คงค่าเดิม
- Ruijie DHCP/DNS: ยังไม่ได้เปลี่ยน
- Marelli Report: ลบออกจากโครงการแล้ว
- Windows DNS flush script: สร้างแล้ว

