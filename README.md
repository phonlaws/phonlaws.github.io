# v3-soft: ปรับเบา ๆ + จำกัด Pyro

ตาม requirement:
1) ถ้าเกิน/ต่ำกว่าเป้านิดเดียว (เช่น 0.001) ไม่ควรสั่งปรับแรง
   - ใช้ Deadband (ค่าเริ่มต้น 0.005)
   - ใช้ Soft cap: step_cap = min(max_step, |Error| × gain)
     ค่าเริ่มต้น gain=5 (Error 0.010 → cap 0.05)

2) Pyro ปรับเฉพาะเมื่อ Pred Alkali หลุดช่วง
   - ถ้า 1.50 ≤ Pred ≤ 1.70 → สั่งปรับ Feldspar อย่างเดียว (ΔPyro=0)
   - ต่ำกว่า 1.50 หรือสูงกว่า 1.70 → อนุญาตใช้ Pyro

วิธีติดตั้ง:
- Replace ไฟล์ index_v3_grid_fineness.html ใน repo
- ให้ model_v3.json อยู่โฟลเดอร์เดียวกัน
- Hard refresh (Ctrl+F5) หรือเปิดแบบ incognito
