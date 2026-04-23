import os
import time
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image
from flask import Flask, Response, render_template, request
from picamera2 import Picamera2

app = Flask(__name__)

GIF_DIR = os.path.join(os.path.dirname(__file__), 'templates')
GIF_NAMES = ['laughing_man', 'laughing_cat', 'piyopiyo', 'totoro']
STYLES = ['surgical', 'circle', 'oval'] + GIF_NAMES


# --- GIF アニメーション読み込み ---
class GifLoader:
    """GIFの全フレームをRGBAで保持し、経過時間でフレームを進める"""
    def __init__(self, path):
        self.frames = []
        self.durations = []
        gif = Image.open(path)
        try:
            while True:
                self.frames.append(np.array(gif.convert('RGBA')))
                self.durations.append(gif.info.get('duration', 100) / 1000.0)
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass
        self.idx = 0
        self.last = time.time()

    def get_frame(self):
        now = time.time()
        if now - self.last >= self.durations[self.idx]:
            self.idx = (self.idx + 1) % len(self.frames)
            self.last = now
        return self.frames[self.idx]  # RGBA numpy array


# 起動時に全 GIF を読み込む
gifs = {}
for name in GIF_NAMES:
    path = os.path.join(GIF_DIR, f'{name}.gif')
    if os.path.exists(path):
        gifs[name] = GifLoader(path)


def overlay_rgba(base, rgba, x, y, w, h):
    """RGBA画像をRGBフレームのbbox位置に透過合成する"""
    if w <= 0 or h <= 0:
        return base
    bh, bw = base.shape[:2]
    resized = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_LINEAR)
    rgb   = resized[:, :, :3].astype(float)
    alpha = resized[:, :, 3:4].astype(float) / 255.0

    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(bw, x + w), min(bh, y + h)
    if x1 >= x2 or y1 >= y2:
        return base

    ox1, oy1 = x1 - x, y1 - y
    ox2, oy2 = ox1 + (x2 - x1), oy1 + (y2 - y1)

    roi = base[y1:y2, x1:x2].astype(float)
    ov  = rgb  [oy1:oy2, ox1:ox2]
    al  = alpha[oy1:oy2, ox1:ox2]
    base[y1:y2, x1:x2] = (ov * al + roi * (1 - al)).astype(np.uint8)
    return base


# --- 部品1：AI解析担当 (FaceMaskDetector クラス) ---
class FaceMaskDetector:
    def __init__(self):
        mp_face_detection = mp.solutions.face_detection
        self.face_detection = mp_face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.6
        )

    def process(self, frame, style):
        frame.flags.writeable = False
        results = self.face_detection.process(frame)
        frame.flags.writeable = True

        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                frame = self._draw_mask(frame, bbox, style)

        return frame

    def _draw_mask(self, frame, bbox, style):
        h, w = frame.shape[:2]

        x_min = max(0, int(bbox.xmin * w))
        y_min = max(0, int(bbox.ymin * h))
        x_max = min(w, int((bbox.xmin + bbox.width) * w))
        y_max = min(h, int((bbox.ymin + bbox.height) * h))

        face_w = x_max - x_min
        face_h = y_max - y_min
        cx = x_min + face_w // 2
        cy = y_min + face_h // 2

        if style == 'surgical':
            my_start = y_min + int(face_h * 0.45)
            my_end   = min(h - 1, y_max + int(face_h * 0.05))
            pts = np.array([
                [x_min + int(face_w * 0.08), my_start],
                [x_max - int(face_w * 0.08), my_start],
                [x_max - int(face_w * 0.02), my_end],
                [x_min + int(face_w * 0.02), my_end],
            ], np.int32)
            cv2.fillPoly(frame, [pts], (200, 100, 0))
            cv2.polylines(frame, [pts], True, (0, 0, 0), 2)

        elif style == 'circle':
            radius = max(face_w, face_h) // 2 + 10
            cv2.circle(frame, (cx, cy), radius, (0, 210, 255), -1)
            cv2.circle(frame, (cx, cy), radius, (0, 0, 0), 3)

        elif style == 'oval':
            axes = (face_w // 2 + 15, face_h // 2 + 20)
            for angle in range(0, 360, 10):
                cv2.ellipse(frame, (cx, cy), axes, 0, angle, angle + 8,
                            (180, 200, 80), 4)

        elif style in gifs:
            # 顔全体にGIFを透過合成（少し余白を持たせる）
            pad = int(max(face_w, face_h) * 0.15)
            gx = x_min - pad
            gy = y_min - pad
            gw = face_w + pad * 2
            gh = face_h + pad * 2
            gif_frame = gifs[style].get_frame()
            frame = overlay_rgba(frame, gif_frame, gx, gy, gw, gh)

        return frame


# --- 部品2：カメラ担当 (CameraSource クラス) ---
class CameraSource:
    def __init__(self):
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )
        self.picam2.configure(config)
        self.picam2.start()

    def get_frame(self):
        return self.picam2.capture_array()


# --- メインの配信ロジック ---
detector = FaceMaskDetector()
camera = CameraSource()

def generate_frames(style):
    while True:
        frame = camera.get_frame()
        frame = detector.process(frame, style)

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    style = request.args.get('style', 'surgical')
    if style not in STYLES:
        style = 'surgical'
    return render_template('index.html', style=style, styles=STYLES)

@app.route('/video_feed')
def video_feed():
    style = request.args.get('style', 'surgical')
    if style not in STYLES:
        style = 'surgical'
    return Response(
        generate_frames(style),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
