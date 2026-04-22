import cv2
import mediapipe as mp
import math
import time
from flask import Flask, render_template, Response
from flask_socketio import SocketIO
from picamera2 import Picamera2

app = Flask(__name__, static_folder='static')
# 非同期処理を安定させるための設定
socketio = SocketIO(app, async_mode='threading')

class VulcanDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
        self.last_spoke_time = 0

    def get_distance(self, p1, p2):
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def process(self, frame):
        results = self.hands.process(frame)
        is_vulcan = False
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                lm = hand_landmarks.landmark
                dist_index_middle = self.get_distance(lm[8], lm[12])
                dist_ring_pinky = self.get_distance(lm[16], lm[20])
                dist_middle_ring = self.get_distance(lm[12], lm[16])

                if dist_index_middle < 0.05 and dist_ring_pinky < 0.05 and dist_middle_ring > 0.08:
                    current_time = time.time()
                    if current_time - self.last_spoke_time > 5: # 再開までの余裕を見て5秒
                        is_vulcan = True
                        self.last_spoke_time = current_time
        return frame, is_vulcan

detector = VulcanDetector()
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)})
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        frame = picam2.capture_array()
        frame, is_vulcan = detector.process(frame)
        
        if is_vulcan:
            # ブラウザへ検知信号を送信
            socketio.emit('vulcan_detected')
            # 音声転送と再生の時間、配信ループを止めて帯域を空ける
            time.sleep(3) 

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# app.py の最後
if __name__ == '__main__':
    # threaded=True を明示し、同時並列処理を強制します
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, log_output=True, allow_unsafe_werkzeug=True)