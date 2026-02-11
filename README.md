# RM Alkali Smart Adjuster v2 (ΔPV + constrained signs)

ไฟล์:
- index_v2.html
- model_v2.json

## แนวคิด
- ใช้ ΔPV (การเปลี่ยน PV รายชั่วโมง) ที่เวลา t-lag เทียบ t-(lag+1)
- บังคับทิศทาง: เพิ่ม Feldspar → Alkali เพิ่ม, เพิ่ม Pyro → Alkali ลด
- ตัดช่วง transient ±2h รอบ event ในการเทรน (จากข้อความ event1/event2)

## ต้องมี PV history กี่ชั่วโมง?
- ต้องมี PV ของเวลา t-lag และ t-(lag+1) เพื่อคำนวณ ΔPV
- ถ้า lag=3 ต้องมีอย่างน้อย 4 ชั่วโมงย้อนหลัง

## Deploy
วาง index_v2.html และ model_v2.json ไว้ root ของ repo ที่ GitHub Pages publish
