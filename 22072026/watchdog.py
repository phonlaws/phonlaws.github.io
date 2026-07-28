import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
LOCAL_HEALTH_URL = "http://127.0.0.1:8080/api/health"
PUBLIC_HEALTH_URL = os.environ.get("RW_PUBLIC_HEALTH_URL", "").strip()
BOT_TOKEN = os.environ.get("RW_TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("RW_TELEGRAM_CHAT_ID", "").strip()

CHECK_INTERVAL_SECONDS = 30
FAILURE_THRESHOLD = 3
REQUEST_TIMEOUT_SECONDS = 10

STATE_FILE = APP_DIR / "watchdog_state.json"
LOG_FILE = APP_DIR / "watchdog.log"


def now_text():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def log(message):
    line = f"[{now_text()}] {message}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def default_state():
    return {
        "internet": {"status": "unknown", "failures": 0, "down_since": None},
        "local": {"status": "unknown", "failures": 0, "down_since": None},
        "public": {"status": "unknown", "failures": 0, "down_since": None},
        "pending_messages": []
    }


def load_state():
    state = default_state()
    if not STATE_FILE.exists():
        return state
    try:
        saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        for key in ("internet", "local", "public"):
            if isinstance(saved.get(key), dict):
                state[key].update(saved[key])
        if isinstance(saved.get("pending_messages"), list):
            state["pending_messages"] = saved["pending_messages"]
    except Exception as e:
        log(f"อ่าน state ไม่สำเร็จ: {e}")
    return state


def save_state(state):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def request_url(url, expect_json=False):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "RiskWork-Watchdog/1.0",
            "Cache-Control": "no-cache"
        })
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as res:
            code = res.getcode()
            body = res.read().decode("utf-8", errors="replace")
        if code != 200:
            return False, f"HTTP {code}"
        if expect_json:
            data = json.loads(body)
            if data.get("ok") is not True:
                return False, 'ไม่พบค่า "ok": true'
        return True, "ตอบสนองปกติ"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)


def check_internet():
    for url in ("https://api.telegram.org", "https://www.cloudflare.com/cdn-cgi/trace"):
        ok, detail = request_url(url)
        if ok:
            return True, "เชื่อมต่ออินเทอร์เน็ตได้"
    return False, detail


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        return False, "ยังตั้งค่า Telegram ไม่ครบ"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": "true"
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as res:
            result = json.loads(res.read().decode("utf-8", errors="replace"))
        return (True, "sent") if result.get("ok") else (False, str(result))
    except Exception as e:
        return False, str(e)


def queue_message(state, message):
    if message not in state["pending_messages"]:
        state["pending_messages"].append(message)
        log("บันทึกข้อความรอส่ง")


def send_or_queue(state, message, internet_ok):
    if not internet_ok:
        queue_message(state, message)
        return
    ok, detail = send_telegram(message)
    if ok:
        log("ส่ง Telegram สำเร็จ")
    else:
        log(f"ส่ง Telegram ไม่สำเร็จ: {detail}")
        queue_message(state, message)


def flush_pending(state):
    if not state["pending_messages"]:
        return
    remaining = []
    for message in state["pending_messages"]:
        ok, detail = send_telegram(message)
        if ok:
            log("ส่งข้อความค้างสำเร็จ")
            time.sleep(1)
        else:
            log(f"ส่งข้อความค้างไม่สำเร็จ: {detail}")
            remaining.append(message)
    state["pending_messages"] = remaining


def update_status(state, key, name, ok, detail, internet_ok):
    item = state[key]
    previous = item["status"]

    if ok:
        item["failures"] = 0
        if previous == "down":
            message = (
                f"🟢 {name} กลับมาปกติ\n\n"
                f"เริ่มมีปัญหา: {item.get('down_since') or 'ไม่ทราบ'}\n"
                f"กลับมาปกติ: {now_text()}\n"
                f"รายละเอียด: {detail}"
            )
            log(f"{name}: DOWN -> UP")
            send_or_queue(state, message, internet_ok)
        item["status"] = "up"
        item["down_since"] = None
        return

    item["failures"] += 1
    log(f"{name}: ไม่ผ่าน {item['failures']}/{FAILURE_THRESHOLD} - {detail}")
    if item["failures"] < FAILURE_THRESHOLD or previous == "down":
        return

    item["status"] = "down"
    item["down_since"] = now_text()
    message = (
        f"🔴 {name} มีปัญหา\n\n"
        f"ตรวจพบเมื่อ: {item['down_since']}\n"
        f"ตรวจไม่ผ่านต่อเนื่อง: {FAILURE_THRESHOLD} ครั้ง\n"
        f"รายละเอียด: {detail}\n\n"
        f"กรุณาเข้าตรวจสอบเครื่องกลางด้วยตนเอง"
    )
    log(f"{name}: UP -> DOWN")
    send_or_queue(state, message, internet_ok)


def validate_config():
    missing = []
    if not BOT_TOKEN:
        missing.append("RW_TELEGRAM_BOT_TOKEN")
    if not CHAT_ID:
        missing.append("RW_TELEGRAM_CHAT_ID")
    if not PUBLIC_HEALTH_URL:
        missing.append("RW_PUBLIC_HEALTH_URL")
    if missing:
        log("ยังตั้งค่าไม่ครบ: " + ", ".join(missing))
        return False
    return True


def main():
    log("=" * 60)
    log("Risk Work Watchdog เริ่มทำงาน")
    log(f"Local: {LOCAL_HEALTH_URL}")
    log(f"Public: {PUBLIC_HEALTH_URL or 'ยังไม่ได้กำหนด'}")
    log(f"ตรวจทุก {CHECK_INTERVAL_SECONDS} วินาที ยืนยันปัญหาหลัง {FAILURE_THRESHOLD} ครั้ง")
    validate_config()
    state = load_state()

    while True:
        try:
            internet_ok, internet_detail = check_internet()
            update_status(state, "internet", "อินเทอร์เน็ตเครื่องกลาง",
                          internet_ok, internet_detail, internet_ok)

            if internet_ok:
                flush_pending(state)

            local_ok, local_detail = request_url(LOCAL_HEALTH_URL, expect_json=True)
            update_status(state, "local", "Flask Server ในเครื่อง",
                          local_ok, local_detail, internet_ok)

            if internet_ok and PUBLIC_HEALTH_URL:
                public_ok, public_detail = request_url(PUBLIC_HEALTH_URL, expect_json=True)
                update_status(state, "public", "Cloudflare Public URL",
                              public_ok, public_detail, internet_ok)
            else:
                log("ข้าม Public URL เพราะอินเทอร์เน็ตไม่พร้อมหรือยังไม่มี URL")

            save_state(state)
            time.sleep(CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            log("Watchdog ถูกหยุดโดยผู้ใช้งาน")
            save_state(state)
            break
        except Exception as e:
            log(f"Watchdog error: {e}")
            save_state(state)
            time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
