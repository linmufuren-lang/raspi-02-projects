import cv2
import mediapipe as mp
from flask import Flask, Response
from picamera2 import Picamera2

app = Flask(__name__)

# --- MediaPipe 顔検出の準備 ---
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils
# model_selection=0 は近距離(2m以内)用
face_detection = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

# --- Picamera2 の準備 ---
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)})
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        # 画像を取得
        frame = picam2.capture_array()
        
        # 処理を軽くするため書き込み不可フラグ（任意）
        frame.flags.writeable = False
        # MediaPipeで顔検出実行（入力はRGB）
        results = face_detection.process(frame)
        
        # 描画のために書き込み許可に戻す
        frame.flags.writeable = True
        
        # 検出された顔に枠を描画
        if results.detections:
            for detection in results.detections:
                mp_drawing.draw_detection(frame, detection)
        
        # ブラウザ表示用にJPEGエンコード（色はRGBのまま。前回修正した通りです！）
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)