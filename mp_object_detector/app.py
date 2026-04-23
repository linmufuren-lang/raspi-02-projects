"""
MediaPipe Object Detector - Flask ライブストリーミングモード
picamera2 でキャプチャ → EfficientDet-Lite0 で物体推論 → MJPEG 配信

ブラウザ: http://192.168.0.19:5000
"""

import time
import threading
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from flask import Flask, Response
from picamera2 import Picamera2

MODEL_PATH = "efficientdet_lite0.tflite"
WIDTH, HEIGHT = 640, 480
MAX_RESULTS = 5
SCORE_THRESHOLD = 0.5

app = Flask(__name__)

# 最新の検出結果をスレッド間で共有
detection_lock = threading.Lock()
latest_result = None
det_running = False
fps_counter = 0
fps_value = 0.0
fps_start = time.time()


def on_detection(result, output_image: mp.Image, timestamp_ms: int):
    global latest_result, det_running, fps_counter, fps_value, fps_start
    with detection_lock:
        latest_result = result
        det_running = False
        fps_counter += 1
        if fps_counter % 10 == 0:
            fps_value = 10 / (time.time() - fps_start)
            fps_start = time.time()


def draw_detections(frame, result):
    if result is None:
        return frame
    for detection in result.detections:
        bbox = detection.bounding_box
        x1, y1 = bbox.origin_x, bbox.origin_y
        x2, y2 = x1 + bbox.width, y1 + bbox.height
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)

        cat = detection.categories[0]
        label = f"{cat.category_name} {cat.score:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), (0, 165, 255), -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return frame


def generate_frames():
    global det_running

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()

    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.ObjectDetectorOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.LIVE_STREAM,
        max_results=MAX_RESULTS,
        score_threshold=SCORE_THRESHOLD,
        result_callback=on_detection,
    )

    with mp_vision.ObjectDetector.create_from_options(options) as detector:
        while True:
            frame = picam2.capture_array()  # RGB888

            with detection_lock:
                running = det_running

            if not running:
                with detection_lock:
                    det_running = True
                frame.flags.writeable = False
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
                detector.detect_async(mp_image, time.time_ns() // 1_000_000)
                frame.flags.writeable = True

            with detection_lock:
                result = latest_result
                fps = fps_value

            annotated = draw_detections(frame, result)

            # 検出数と FPS を表示
            n = len(result.detections) if result else 0
            cv2.putText(annotated, f"FPS:{fps:.1f}  Objects:{n}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 255, 0), 2, cv2.LINE_AA)

            _, jpeg = cv2.imencode(".jpg", annotated)
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")


@app.route("/")
def index():
    return """<!DOCTYPE html>
<html>
<head>
  <title>Object Detector</title>
  <style>
    body { background:#111; color:#eee; font-family:sans-serif; text-align:center; margin:0; padding:20px; }
    h1 { font-size:1.4em; margin-bottom:12px; }
    img { border:2px solid #444; max-width:100%; }
  </style>
</head>
<body>
  <h1>MediaPipe Object Detector</h1>
  <img src="/video_feed">
</body>
</html>"""


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
