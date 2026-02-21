import json
import os
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, 'status.json')
LOCK = threading.Lock()

DEPARTMENTS = ["Crusher","RM1","RM2","Petcoke Mill","Pfister","Kiln1","Kiln2"]

app = Flask(__name__, static_folder='.', static_url_path='')


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


@app.get('/api/status')
def api_status():
    with LOCK:
        return jsonify(load_state())


@app.post('/api/config')
def api_config():
    payload = request.get_json(force=True, silent=True) or {}
    overdue_minutes = payload.get('overdueMinutes', None)
    try:
        overdue_minutes = int(overdue_minutes)
        overdue_minutes = max(1, min(9999, overdue_minutes))
    except Exception:
        return jsonify({"error": "invalid overdueMinutes"}), 400

    with LOCK:
        state = load_state()
        state['overdueMinutes'] = overdue_minutes
        save_state(state)
        return jsonify(state)


@app.post('/api/open')
def api_open():
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

        job_id = payload.get('id') or f"{int(datetime.now().timestamp()*1000)}"
        job = {
            "id": job_id,
            "riskType": risk_type,
            "department": department,
            "point": point,
            "control": control,
            "requester": requester,
            "details": details,
            "startedAtISO": started_at
        }
        state['jobs'].insert(0, job)
        save_state(state)
        return jsonify(state)


@app.post('/api/close')
def api_close():
    payload = request.get_json(force=True, silent=True) or {}
    job_id = payload.get('id')
    if not job_id:
        return jsonify({"error": "missing id"}), 400

    with LOCK:
        state = load_state()
        state['jobs'] = [j for j in state['jobs'] if str(j.get('id')) != str(job_id)]
        save_state(state)
        return jsonify(state)


@app.get('/')
def root():
    return send_from_directory(APP_DIR, 'index.html')


@app.get('/<path:path>')
def static_files(path):
    if path in ('server.py', 'status.json', 'status.json.tmp'):
        return jsonify({"error": "not found"}), 404
    return send_from_directory(APP_DIR, path)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8080'))
    app.run(host='0.0.0.0', port=port, debug=False)
