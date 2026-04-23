import cv2
import mediapipe as mp
import math
import time
import numpy as np
from PIL import ImageFont, ImageDraw, Image
from flask import Flask, render_template, Response
from flask_socketio import SocketIO
from picamera2 import Picamera2

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, async_mode='threading')

FONT_PATH = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
font = ImageFont.truetype(FONT_PATH, 22)

def draw_texts(frame, texts):
    """texts: list of (text, (x, y), rgb_color)"""
    img_pil = Image.fromarray(frame)
    draw = ImageDraw.Draw(img_pil)
    for text, pos, color in texts:
        x, y = pos
        for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
            draw.text((x+dx, y+dy), text, font=font, fill=(0, 0, 0))
        draw.text((x, y), text, font=font, fill=color)
    return np.array(img_pil)

class VulcanDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.last_spoke_time = 0
        self.success_count = 0

    def get_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def process(self, frame):
        results = self.hands.process(frame)
        is_vulcan = False
        is_climax = False
        texts = []

        if results.multi_hand_landmarks:
            for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                lm = hand_landmarks.landmark

                hand_scale = self.get_distance(lm[0], lm[9])
                if hand_scale < 0.01:
                    continue

                d1 = self.get_distance(lm[8], lm[12]) / hand_scale
                d2 = self.get_distance(lm[16], lm[20]) / hand_scale
                d3 = self.get_distance(lm[12], lm[16]) / hand_scale

                # 列のx座標を固定（ラベル / ステータス / 数値）
                X_LABEL  = 10
                X_STATUS = 190
                X_VALUE  = 330
                y_offset = 10 + i * 90

                rows = [
                    ("人差し指と中指", d1 < 0.35,  d1, "近づけて", (255, 220, 0)),
                    ("　薬指　と小指", d2 < 0.35,  d2, "近づけて", (255, 220, 0)),
                    ("　中指　と薬指", d3 > 0.40,  d3, "広げて",   (0, 200, 255)),
                ]
                for j, (label, ok, val, hint, hint_color) in enumerate(rows):
                    y = y_offset + j * 28
                    texts.append((label,              (X_LABEL,  y), (200, 200, 200)))
                    if ok:
                        texts.append(("✓",           (X_STATUS, y), (100, 255, 100)))
                    else:
                        texts.append((hint,           (X_STATUS, y), hint_color))
                    texts.append((f"({val:.2f})",     (X_VALUE,  y), (200, 200, 200)))

                if d1 < 0.35 and d2 < 0.35 and d3 > 0.40:
                    current_time = time.time()
                    if current_time - self.last_spoke_time > 5:
                        is_vulcan = True
                        self.last_spoke_time = current_time
                        self.success_count += 1
                        if self.success_count >= 5:
                            is_climax = True
                            self.success_count = 0

        if texts:
            frame = draw_texts(frame, texts)

        return frame, is_vulcan, is_climax

detector = VulcanDetector()
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)})
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        frame = picam2.capture_array()
        frame, is_vulcan, is_climax = detector.process(frame)

        if is_climax:
            socketio.emit('vulcan_climax')
        elif is_vulcan:
            socketio.emit('vulcan_detected')

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, log_output=True, allow_unsafe_werkzeug=True)
