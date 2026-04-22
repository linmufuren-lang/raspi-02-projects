import cv2
import mediapipe as mp
import time
from flask import Flask, render_template, Response
from flask_socketio import SocketIO
from picamera2 import Picamera2

app = Flask(__name__)
# eventletを使用することで並列処理を安定させます
socketio = SocketIO(app, async_mode='eventlet')

class VulcanDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
        self.last_time = 0

    def process(self, frame):
        results = self.hands.process(frame)
        is_vulcan = False
        if results.multi_hand_landmarks:
            for lm in results.multi_hand_landmarks:
                pts = lm.landmark
                # ヴァルカンサインの判定
                d1 = ((pts[8].x-pts[12].x)**2 + (pts[8].y-pts[12].y)**2)**0.5
                d2 = ((pts[16].x-pts[20].x)**2 + (pts[16].y-pts[20].y)**2)**0.5
                d3 = ((pts[12].x-pts[16].x)**2 + (pts[12].y-pts[16].y)**2)**0.5
                if d1 < 0.05 and d2 < 0.05 and d3 > 0.08:
                    if time.time() - self.last_time > 5:
                        is_vulcan = True
                        self.last_time = time.time()
        return is_vulcan

detector = VulcanDetector()
picam2 = Picamera2()
# 解像度を 320x240 に下げて通信量を抑える
config = picam2.create_preview_configuration(main={"format": 'RGB888', "size": (320, 240)})
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        frame = picam2.capture_array()
        is_vulcan = detector.process(frame)
        
        if is_vulcan:
            # ブラウザに検知を通知
            socketio.emit('vulcan_detected')
            # サーバー側でも配信ループを4秒止めて、音声転送用の「空き」を作る
            socketio.sleep(4) 
        
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index(): return render_template('index.html')

@app.route('/video_feed')
def video_feed(): return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)