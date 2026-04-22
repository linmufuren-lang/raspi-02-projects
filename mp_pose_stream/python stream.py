import cv2
import mediapipe as mp
from flask import Flask, Response
from picamera2 import Picamera2

app = Flask(__name__)

# --- MediaPipe の準備 ---
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
# 負荷を軽くするため、検出精度と追跡精度のバランスを調整
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# --- カメラの準備 (Picamera2) ---
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)})
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        # 1. カメラから画像を取得 (RGB形式)
        frame = picam2.capture_array()
        
        # 2. MediaPipe で骨格検知を実行
        # 入力は RGB である必要があるため、Picamera2 の生データがそのまま使えます
        results = pose.process(frame)
        
        # 3. 検知結果を画像に描き込む
        # ここで OpenCV の描画機能を使いますが、描画対象はメモリ上の画像データです
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                frame, 
                results.pose_landmarks, 
                mp_pose.POSE_CONNECTIONS
            )
        
        # 4. ブラウザ表示用に JPEG へ変換
        # ブラウザは RGB そのままだと表示できないため、ここで JPEG に固めます
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    # 5000番ポートで公開
    app.run(host='0.0.0.0', port=5000)