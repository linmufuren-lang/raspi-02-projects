"""
MediaPipe Face Stylizer - Flask ブラウザ版
ライブカメラをブラウザで確認しながらシャッターでスタイル変換 → ギャラリー表示
5枚撮影で自動停止。生成画像は captures/ フォルダに保存。
"""

import os
import time
import threading
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from picamera2 import Picamera2
from flask import Flask, Response, render_template_string, jsonify, send_from_directory

# ── 設定 ──────────────────────────────────────────────────
MODEL_PATH   = "face_stylizer_color_sketch.task"
CAPTURES_DIR = os.path.join(os.path.dirname(__file__), "captures")
MAX_CAPTURES = 5
WIDTH, HEIGHT = 640, 480
# ──────────────────────────────────────────────────────────

os.makedirs(CAPTURES_DIR, exist_ok=True)
app = Flask(__name__)

# ── 共有状態 ──────────────────────────────────────────────
latest_frame  = None        # RGB numpy, カメラスレッドが常時更新
frame_lock    = threading.Lock()

capture_count = 0
captures_list = []          # 保存済みファイル名リスト
is_capturing  = False       # 推論中フラグ
is_done       = False       # 5枚完了フラグ
state_lock    = threading.Lock()

# ── カメラ起動 ─────────────────────────────────────────────
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
))
picam2.start()
time.sleep(0.5)


def camera_reader():
    global latest_frame
    while True:
        with frame_lock:
            latest_frame = picam2.capture_array()  # RGB888 のまま保持


threading.Thread(target=camera_reader, daemon=True).start()


# ── MJPEG ストリーム ───────────────────────────────────────
def generate_frames():
    while True:
        with frame_lock:
            frame = latest_frame
        if frame is None:
            time.sleep(0.05)
            continue
        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ok:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                   + buf.tobytes() + b'\r\n')
        time.sleep(1 / 15)   # 15fps に制限して Pi の負荷を抑える


# ── スタイル変換ワーカー ───────────────────────────────────
def do_stylize(frame_rgb):
    global capture_count, captures_list, is_capturing, is_done

    try:
        base_opts = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        opts = mp_vision.FaceStylizerOptions(base_options=base_opts)

        with mp_vision.FaceStylizer.create_from_options(opts) as stylizer:
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)  # RGB 直接渡し
            result = stylizer.stylize(mp_img)

        if result is not None:
            stylized_rgb = result.numpy_view()                    # (256,256,3) RGB
            stylized_bgr = cv2.cvtColor(stylized_rgb, cv2.COLOR_RGB2BGR)  # imwrite 用に BGR へ

            # 元フレームサイズにアップスケールして保存
            out = cv2.resize(stylized_bgr, (WIDTH, HEIGHT),
                             interpolation=cv2.INTER_LANCZOS4)

            filename = f"capture_{int(time.time() * 1000)}.jpg"
            cv2.imwrite(os.path.join(CAPTURES_DIR, filename), out,
                        [cv2.IMWRITE_JPEG_QUALITY, 95])

            with state_lock:
                capture_count += 1
                captures_list.append(filename)
                is_capturing = False
                if capture_count >= MAX_CAPTURES:
                    is_done = True

            print(f"[OK] 保存: {filename}  ({capture_count}/{MAX_CAPTURES})")
        else:
            print("[NG] 顔が検出されませんでした")
            with state_lock:
                is_capturing = False

    except Exception as e:
        print(f"[ERR] {e}")
        with state_lock:
            is_capturing = False


# ── Flask ルート ──────────────────────────────────────────
@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/capture', methods=['POST'])
def capture():
    global is_capturing

    with state_lock:
        if is_done:
            return jsonify({'ok': False, 'reason': '撮影完了済み'})
        if is_capturing:
            return jsonify({'ok': False, 'reason': '変換中です'})
        is_capturing = True

    with frame_lock:
        frame = latest_frame.copy() if latest_frame is not None else None

    if frame is None:
        with state_lock:
            is_capturing = False
        return jsonify({'ok': False, 'reason': 'カメラ未準備'})

    threading.Thread(target=do_stylize, args=(frame,), daemon=True).start()
    return jsonify({'ok': True})


@app.route('/status')
def status():
    with state_lock:
        return jsonify({
            'count':     capture_count,
            'max':       MAX_CAPTURES,
            'capturing': is_capturing,
            'captures':  captures_list[:],
            'done':      is_done,
        })


@app.route('/captures/<path:filename>')
def serve_capture(filename):
    return send_from_directory(CAPTURES_DIR, filename)


# ── HTML テンプレート ─────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Face Stylizer</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #111; color: #eee; font-family: sans-serif; min-height: 100vh; }

  h1 { text-align: center; padding: 14px 0 10px; font-size: 1.1rem;
       letter-spacing: 0.15em; color: #ddd; border-bottom: 1px solid #333; }

  #layout { display: flex; flex-wrap: wrap; gap: 20px;
            padding: 16px; justify-content: center; }

  /* 左カラム: ライブビュー + シャッター */
  #left { display: flex; flex-direction: column; align-items: center; gap: 12px; }

  #stream { width: 640px; max-width: 90vw;
            border: 2px solid #444; border-radius: 6px; display: block; }

  #controls { display: flex; flex-direction: column; align-items: center; gap: 6px; }

  #shutter {
    width: 100px; height: 100px; border-radius: 50%;
    background: #cc2222; border: 5px solid #fff;
    font-size: 2rem; cursor: pointer;
    transition: background 0.15s, transform 0.1s;
    display: flex; align-items: center; justify-content: center;
  }
  #shutter:hover:not(:disabled) { background: #991111; transform: scale(1.06); }
  #shutter:active:not(:disabled) { transform: scale(0.96); }
  #shutter:disabled { background: #444; border-color: #666; cursor: not-allowed; }

  #counter { font-size: 1.3rem; font-weight: bold; color: #aaa; }
  #status-msg { font-size: 0.85rem; color: #ffcc00; min-height: 1.2em; }
  #done-msg {
    font-size: 1rem; color: #33ff88; font-weight: bold;
    display: none; padding: 6px 14px;
    border: 1px solid #33ff88; border-radius: 20px;
  }

  /* 右カラム: ギャラリー */
  #right { width: 420px; max-width: 90vw; }
  #gallery-title { font-size: 0.9rem; color: #888;
                   border-bottom: 1px solid #333; padding-bottom: 6px;
                   margin-bottom: 10px; }
  #grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          gap: 10px; }

  .card { background: #1e1e1e; border-radius: 6px; overflow: hidden;
          border: 1px solid #333; }
  .card img { width: 100%; display: block; aspect-ratio: 4/3; object-fit: cover; }
  .card .label { text-align: center; font-size: 0.75rem; color: #888;
                 padding: 4px 0; }

  #empty-msg { color: #555; font-size: 0.85rem; }
</style>
</head>
<body>
<h1>&#127775; Face Stylizer</h1>

<div id="layout">
  <!-- ライブビュー -->
  <div id="left">
    <img id="stream" src="/video_feed" alt="live">
    <div id="controls">
      <button id="shutter" onclick="doCapture()">&#128247;</button>
      <div id="counter">0 / 5</div>
      <div id="status-msg"></div>
      <div id="done-msg">&#10003; 5枚撮影完了</div>
    </div>
  </div>

  <!-- ギャラリー -->
  <div id="right">
    <div id="gallery-title">生成画像 &#8212; captures/</div>
    <div id="grid">
      <span id="empty-msg">まだ画像がありません</span>
    </div>
  </div>
</div>

<script>
  let prevCount = -1;

  async function doCapture() {
    document.getElementById('shutter').disabled = true;
    document.getElementById('status-msg').textContent = '変換中...';
    try {
      const r = await fetch('/capture', { method: 'POST' });
      const j = await r.json();
      if (!j.ok) {
        document.getElementById('status-msg').textContent = j.reason || 'エラー';
        document.getElementById('shutter').disabled = false;
      }
    } catch(e) {
      document.getElementById('status-msg').textContent = '通信エラー';
      document.getElementById('shutter').disabled = false;
    }
  }

  async function poll() {
    try {
      const r = await fetch('/status');
      const s = await r.json();

      document.getElementById('counter').textContent = s.count + ' / ' + s.max;

      if (s.done) {
        document.getElementById('shutter').disabled = true;
        document.getElementById('done-msg').style.display = 'inline-block';
        document.getElementById('status-msg').textContent = '';
      } else if (!s.capturing) {
        document.getElementById('shutter').disabled = false;
        if (document.getElementById('status-msg').textContent === '変換中...') {
          document.getElementById('status-msg').textContent = '';
        }
      }

      if (s.captures.length !== prevCount) {
        prevCount = s.captures.length;
        renderGallery(s.captures);
      }
    } catch(e) { /* 無視 */ }
  }

  function renderGallery(files) {
    const grid = document.getElementById('grid');
    grid.innerHTML = '';
    if (files.length === 0) {
      grid.innerHTML = '<span id="empty-msg">まだ画像がありません</span>';
      return;
    }
    files.forEach((f, i) => {
      const card = document.createElement('div');
      card.className = 'card';
      const img = document.createElement('img');
      img.src = '/captures/' + f + '?t=' + Date.now();
      img.alt = '#' + (i + 1);
      const label = document.createElement('div');
      label.className = 'label';
      label.textContent = '#' + (i + 1);
      card.appendChild(img);
      card.appendChild(label);
      grid.appendChild(card);
    });
  }

  setInterval(poll, 800);
  poll();
</script>
</body>
</html>"""


if __name__ == '__main__':
    print(f"起動: http://192.168.0.19:5000")
    print(f"モデル: {MODEL_PATH}")
    print(f"保存先: {CAPTURES_DIR}")
    app.run(host='0.0.0.0', port=5000, threaded=True)
