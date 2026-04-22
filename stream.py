import cv2
import numpy as np
from flask import Flask, Response
from picamera2 import Picamera2

app = Flask(__name__)

# Picamera2の初期化
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)})
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        # Picamera2から1フレーム取得（numpy配列として取得）
        frame = picam2.capture_array()
        
        # OpenCV形式（BGR）に変換（MediaPipeで使う際もこの変換が必要です）
        # frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # JPEGにエンコードしてストリーミング
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)