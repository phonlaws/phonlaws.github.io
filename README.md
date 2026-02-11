# RM Alkali Smart Adjuster

ไฟล์ใน repo:
- `index.html`
- `model.json`

## วิธี Deploy (GitHub Pages)
Settings → Pages → Deploy from branch → main → /(root)

## วิธีใช้
1) กรอก Alkali (t, t-1, t-2), Fineness, PV (t/h)
2) กด **บันทึก PV ชั่วโมงนี้** เพื่อสร้าง PV history
3) กด **Predict** หรือ **Smart Recommend**
4) เมื่อปรับจริง กด **ยืนยันว่าปรับแล้ว** เพื่อเริ่ม Pending 3 ชั่วโมง

## PV History
- เก็บใน localStorage ของ browser
- Export/Import ได้เป็น JSON

## Log
- Export ได้เป็น CSV
