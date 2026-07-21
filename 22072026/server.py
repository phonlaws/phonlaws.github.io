import json
import os
import threading
from datetime import datetime, timezone, timedelta

from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, 'status.json')
USERS_FILE = os.path.join(APP_DIR, 'users.json')
LOCK = threading.Lock()

DEPARTMENTS = ["Crusher", "RM1", "RM2", "Petcoke Mill", "Pfister", "Kiln1", "Kiln2"]

app = Flask(__name__, static_folder='.', static_url_path='')

# ----------------------------
# Login / Session settings
# ----------------------------
# แนะนำให้ตั้งค่าเป็น Environment Variable: RW_SECRET_KEY
# Windows CMD: set RW_SECRET_KEY=ใส่ค่ายาวๆสุ่ม
# PowerShell:  $env:RW_SECRET_KEY="ใส่ค่ายาวๆสุ่ม"
app.secret_key = os.environ.get("RW_SECRET_KEY", "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET")

# จำการล็อกอิน 8 ชั่วโมง ตามที่คุณต้องการ
app.permanent_session_lifetime = timedelta(hours=8)

# cookie settings (ใช้ได้ทั้ง LAN/เครื่องกลาง)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# ถ้าคุณยังเข้าเว็บผ่าน http://localhost:8080 อยู่ ห้ามเปิด Secure
# ถ้าวันไหนเข้าผ่าน https อย่างเดียวค่อยเปิด:
# app.config["SESSION_COOKIE_SECURE"] = True


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _default_state():
    return {
        "updatedAt": _now_iso(),
        "overdueMinutes": 120,
        "jobs": []
    }


def load_state():
    if not os.path.exists(DATA_FILE):
        return _default_state()
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'jobs' not in data:
            data['jobs'] = []
        if 'overdueMinutes' not in data:
            if 'overdueHours' in data:
                try:
                    data['overdueMinutes'] = int(data['overdueHours']) * 60
                except Exception:
                    data['overdueMinutes'] = 120
            else:
                data['overdueMinutes'] = 120
        if 'updatedAt' not in data:
            data['updatedAt'] = _now_iso()
        return data
    except Exception:
        return _default_state()


def save_state(state):
    state['updatedAt'] = _now_iso()
    tmp = DATA_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def normalize_point(s: str) -> str:
    return (s or '').strip().lower()


# ----------------------------
# Users / Auth helpers
# ----------------------------
def load_users():
    """
    users.json format:
    [
      {"user":"A","pin_hash":"..."},
      {"user":"B","pin_hash":"..."}
    ]
    """
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def is_logged_in() -> bool:
    return bool(session.get("user"))


def require_login_or_401():
    """Return (json, 401) if not logged in, else None."""
    if not is_logged_in():
        return jsonify({"error": "unauthorized"}), 401
    return None

def get_user_record(username: str):
    users = load_users()
    return next((u for u in users if u.get("user") == username), None)

def is_admin_user(username: str) -> bool:
    rec = get_user_record(username)
    return bool(rec and rec.get("role") == "admin")

# ----------------------------
# Login APIs
# ----------------------------
@app.post('/api/login')
def api_login():
    payload = request.get_json(force=True, silent=True) or {}
    user = (payload.get("user") or "").strip()
    pin = (payload.get("pin") or "").strip()

    if not user or not pin:
        return jsonify({"ok": False, "error": "missing user/pin"}), 400

    # PIN ต้องเป็นตัวเลข 6 หลัก
    if (not pin.isdigit()) or (len(pin) != 6):
        return jsonify({"ok": False, "error": "pin must be 6 digits"}), 400

    users = load_users()
    row = next((u for u in users if u.get("user") == user), None)
    if not row:
        return jsonify({"ok": False, "error": "invalid login"}), 401

    if not check_password_hash(row.get("pin_hash", ""), pin):
        return jsonify({"ok": False, "error": "invalid login"}), 401

    session["user"] = user
    session.permanent = True  # ใช้ lifetime 8 ชั่วโมง
    return jsonify({"ok": True, "user": user})


@app.post('/api/logout')
def api_logout():
    session.pop("user", None)
    return jsonify({"ok": True})


@app.get('/api/me')
def api_me():
    if not is_logged_in():
        return jsonify({"ok": False}), 401
    user = session.get("user")
    role = "admin" if is_admin_user(user) else "user"
    return jsonify({"ok": True, "user": user, "role": role})


# ----------------------------
# Core APIs
# ----------------------------
@app.get('/api/status')
def api_status():
    # ✅ ไม่ล็อก เพื่อให้ kiosk โชว์ได้ตลอด
    with LOCK:
        return jsonify(load_state())


@app.post('/api/config')
def api_config():
    # 1) ต้อง login ก่อน
    guard = require_login_or_401()
    if guard:
        return guard  # ✅ สำคัญมาก ต้อง return

    payload = request.get_json(force=True, silent=True) or {}
    overdue_minutes = payload.get('overdueMinutes', None)

    # 2) (เลือกได้) ถ้าต้องการให้เฉพาะ admin ปรับได้ ให้เปิดส่วนนี้
    current_user = session.get("user")
    if not is_admin_user(current_user):
        return jsonify({"error": "forbidden: admin only"}), 403

    # 3) ตรวจค่า overdueMinutes
    try:
        overdue_minutes = int(str(overdue_minutes).strip())
        overdue_minutes = max(1, min(9999, overdue_minutes))
    except Exception:
        return jsonify({"error": "invalid overdueMinutes"}), 400

    # 4) บันทึกค่า
    with LOCK:
        state = load_state()
        state['overdueMinutes'] = overdue_minutes
        save_state(state)
        return jsonify(state)  # ✅ ต้อง return


@app.post('/api/open')
def api_open():
    # ✅ ล็อก
    guard = require_login_or_401()
    if guard:
        return guard

    payload = request.get_json(force=True, silent=True) or {}

    required = ['riskType', 'department', 'point', 'startedAtISO']
    for k in required:
        if not payload.get(k):
            return jsonify({"error": f"missing {k}"}), 400

    risk_type = payload.get('riskType')
    if risk_type not in ('confined', 'height'):
        return jsonify({"error": "invalid riskType"}), 400

    department = payload.get('department')
    if department not in DEPARTMENTS:
        return jsonify({"error": "invalid department"}), 400

    point = payload.get('point', '').strip()
    control = (payload.get('control') or '').strip()
    requester = (payload.get('requester') or '').strip()
    details = (payload.get('details') or '').strip()
    started_at = payload.get('startedAtISO')

    overdue_minutes = payload.get('overdueMinutes', None)

    with LOCK:
        state = load_state()
        if overdue_minutes is not None:
            try:
                om = int(overdue_minutes)
                state['overdueMinutes'] = max(1, min(9999, om))
            except Exception:
                pass

        pnorm = normalize_point(point)
        for j in state['jobs']:
            if j.get('department') == department and normalize_point(j.get('point')) == pnorm and j.get('riskType') == risk_type:
                return jsonify({"error": "duplicate: เปิดได้ 1 งานต่อประเภท ในหน่วยงาน + จุดงานเดียวกัน"}), 409

        opened_by = session.get("user")  # คนที่ล็อกอิน (ผู้เปิดจริง)

        job_id = payload.get('id') or f"{int(datetime.now().timestamp()*1000)}"
        job = {
            "id": job_id,
            "riskType": risk_type,
            "department": department,
            "point": point,
            "control": control,
            # ✅ ให้ชื่อผู้เปิดงานในงาน = คนที่ล็อกอิน (กันกรอกผิด/กันปลอม)
            "requester": opened_by,
            # ✅ เจ้าของงานตัวจริง
            "openedBy": opened_by,
            "details": details,
            "startedAtISO": started_at
        }
        state['jobs'].insert(0, job)
        save_state(state)
        return jsonify(state)


@app.post('/api/close')
def api_close():
    # ✅ ต้อง login ก่อน (คุณมี require_login_or_401 อยู่แล้ว)
    guard = require_login_or_401()
    if guard:
        return guard

    payload = request.get_json(force=True, silent=True) or {}
    job_id = payload.get('id')
    if not job_id:
        return jsonify({"error": "missing id"}), 400

    current_user = session.get("user")

    with LOCK:
        state = load_state()

        # หา job ที่จะปิด
        job = next((j for j in state.get("jobs", []) if str(j.get("id")) == str(job_id)), None)
        if not job:
            return jsonify({"error": "not found"}), 404

        owner = (job.get("openedBy") or job.get("requester") or "").strip()

        # ✅ admin override
        if (owner != current_user) and (not is_admin_user(current_user)):
            return jsonify({"error": f"forbidden: งานนี้เปิดโดย '{owner}' เท่านั้น (หรือ admin)"}), 403

        # ปิดงาน (ลบออกจากรายการ)
        state['jobs'] = [j for j in state['jobs'] if str(j.get('id')) != str(job_id)]
        save_state(state)
        return jsonify(state)


@app.get('/')
def root():
    return send_from_directory(APP_DIR, 'index.html')


@app.get('/<path:path>')
def static_files(path):
    # กันการโหลดไฟล์สำคัญจาก browser
    if path in ('server.py', 'users.json', 'status.json', 'status.json.tmp'):
        return jsonify({"error": "not found"}), 404
    return send_from_directory(APP_DIR, path)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8080'))
    app.run(host='0.0.0.0', port=port, debug=False)