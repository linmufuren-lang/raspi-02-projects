from flask import Flask, render_template, jsonify
import subprocess
import pathlib
import socket
import time

app = Flask(__name__)

BASE_DIR = pathlib.Path("/home/rasaicam/projects")

# プロジェクトの表示名・アイコン・説明（自動検出の補足情報）
PROJECT_META = {
    "mp_face_mask":       {"icon": "😷",  "name": "Face Mask",         "desc": "顔マスク描画"},
    "mp_face_mesh":       {"icon": "🕸️",  "name": "Face Mesh",         "desc": "顔メッシュランドマーク"},
    "mp_object_detector": {"icon": "🔍",  "name": "Object Detector",   "desc": "物体検出 (EfficientDet)"},
    "mp_Vulcan_salute":   {"icon": "🖖",  "name": "Vulcan Salute",     "desc": "バルカン敬礼ジェスチャー"},
    "mp_face_stylizer":   {"icon": "🎨",  "name": "Face Stylizer",     "desc": "顔をアートに変換・5枚撮影"},
}

ENTRY_NAMES = ["app.py", "main.py", "stream.py"]
SKIP_DIRS   = {"portal", "mediapipe-vision"}

# 起動中プロセス管理: project_key -> Popen
_running: dict[str, subprocess.Popen] = {}


def _find_entry(project_dir: pathlib.Path):
    for name in ENTRY_NAMES:
        p = project_dir / name
        if p.exists():
            return p
    return None


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def discover_projects():
    projects = []
    for d in sorted(BASE_DIR.iterdir()):
        if not d.is_dir() or d.name in SKIP_DIRS or d.name.startswith((".", "_")):
            continue
        if not (d / "env" / "bin" / "python").exists():
            continue
        if not _find_entry(d):
            continue
        meta = PROJECT_META.get(d.name, {})
        projects.append({
            "key":  d.name,
            "name": meta.get("name", d.name),
            "icon": meta.get("icon", "🔧"),
            "desc": meta.get("desc", ""),
        })
    return projects


@app.route("/")
def index():
    return render_template("index.html", projects=discover_projects())


@app.route("/api/status")
def api_status():
    result = {}
    for key, proc in list(_running.items()):
        if proc.poll() is None:
            result[key] = "running"
        else:
            del _running[key]
    return jsonify(result)


@app.route("/api/start/<key>", methods=["POST"])
def api_start(key):
    if key in _running and _running[key].poll() is None:
        return jsonify({"ok": False, "msg": "already running"})

    project_dir = BASE_DIR / key
    python_bin  = project_dir / "env" / "bin" / "python"
    entry       = _find_entry(project_dir)

    if not entry:
        return jsonify({"ok": False, "msg": "entry point not found"})
    if not python_bin.exists():
        return jsonify({"ok": False, "msg": "venv not found"})

    proc = subprocess.Popen(
        [str(python_bin), str(entry)],
        cwd=str(project_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    time.sleep(1.0)
    if proc.poll() is not None:
        err = proc.stderr.read().decode(errors="replace").strip()
        return jsonify({"ok": False, "msg": err or f"process exited (code {proc.returncode})"})
    _running[key] = proc
    return jsonify({"ok": True, "pid": proc.pid})


@app.route("/api/stop/<key>", methods=["POST"])
def api_stop(key):
    if key not in _running:
        return jsonify({"ok": False, "msg": "not running"})

    proc = _running.pop(key)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
