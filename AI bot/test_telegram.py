import requests

# ==========================================
# ⚙️ ใส่ข้อมูลของคุณตรงนี้
# ==========================================
TELEGRAM_TOKEN = "8875944703:AAEKAkYJJ_1iz7o8KHHrO_5pXBaS6B4LKM4"
TELEGRAM_CHAT_ID = "8784481128"

MESSAGE = "✅ ทดสอบระบบ: บอทสามารถส่งข้อความเข้า Telegram ได้สำเร็จแล้วครับ! 🤖🚀"

# ==========================================
# 🚀 ระบบส่งข้อความ
# ==========================================
print("กำลังพยายามส่งข้อความเข้า Telegram...")

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
payload = {
    "chat_id": TELEGRAM_CHAT_ID, 
    "text": MESSAGE
}

try:
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("🎉 ส่งข้อความสำเร็จ! ลองเปิดดูในแอป Telegram ได้เลยครับ")
    else:
        print("⚠️ ส่งข้อความไม่สำเร็จ กรุณาตรวจสอบว่า:")
        print("1. ก๊อปปี้ Token มาครบถ้วน ไม่มีเว้นวรรคเกิน")
        print("2. ก๊อปปี้ Chat ID มาถูกต้อง")
        print("3. คุณได้กด /start ทักหาบอทใน Telegram แล้วหรือยัง")
except Exception:
    print("⚠️ เกิดข้อผิดพลาดในการเชื่อมต่ออินเทอร์เน็ตครับ")