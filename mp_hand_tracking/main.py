import cv2
import mediapipe as mp
from flask import Flask, Response
from picamera2 import Picamera2

app = Flask(__name__)

# --- 部品1：AI解析担当 (HandDetectorクラス) ---
class HandDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5)

    def process(self, frame):
        # MediaPipeで解析
        results = self.hands.process(frame)
        # 手が見つかったらアノテーションを描画
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
        return frame

# --- 部品2：カメラ担当 (CameraSourceクラス) ---
class CameraSource:
    def __init__(self):
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)})
        self.picam2.configure(config)
        self.picam2.start()

    def get_frame(self):
        return self.picam2.capture_array()

# --- メインの配信ロジック ---
detector = HandDetector()
camera = CameraSource()

def generate_frames():
    while True:
        frame = camera.get_frame()  # カメラから取得
        frame = detector.process(frame)  # AIで解析
        
        # JPEGに変換して配信
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)