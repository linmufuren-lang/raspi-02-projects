import cv2
import mediapipe as mp
from flask import Flask, Response
from picamera2 import Picamera2
import numpy as np

app = Flask(__name__)

# MediaPipe 顔検出
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.6
)

# Picamera2 初期化（Pi4 2GB で無理のない解像度）
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"format": 'RGB888', "size": (640, 480)}
)
picam2.configure(config)
picam2.start()

def draw_mask(frame, face_bbox, mask_style='simple'):
    """
    顔の領域にマスクを描画
    
    Args:
        frame: OpenCV フレーム (RGB)
        face_bbox: MediaPipe の face_bbox オブジェクト
        mask_style: 'simple'(矩形) or 'realistic'(多角形)
    """
    h, w = frame.shape[:2]
    
    # face_bbox の正規化座標をピクセル座標に変換
    x_min = int(face_bbox.xmin * w)
    y_min = int(face_bbox.ymin * h)
    x_max = int(face_bbox.xmax * w)
    y_max = int(face_bbox.ymax * h)
    
    # 顔の中央下部（マスク位置）を計算
    face_width = x_max - x_min
    face_height = y_max - y_min
    
    # マスク領域（鼻からあご下まで）
    mask_y_start = y_min + int(face_height * 0.4)  # 鼻あたり
    mask_y_end = y_max  # あご下
    
    if mask_style == 'simple':
        # シンプル矩形マスク
        color = (0, 100, 200)  # オレンジ色 (BGR)
        cv2.rectangle(
            frame,
            (x_min, mask_y_start),
            (x_max, mask_y_end),
            color,
            -1  # 塗りつぶし
        )
        # 枠線
        cv2.rectangle(
            frame,
            (x_min, mask_y_start),
            (x_max, mask_y_end),
            (0, 0, 0),
            2
        )
    
    elif mask_style == 'realistic':
        # より自然なマスク形状（台形）
        pts = np.array([
            [x_min + int(face_width * 0.1), mask_y_start],
            [x_max - int(face_width * 0.1), mask_y_start],
            [x_max - int(face_width * 0.05), mask_y_end],
            [x_min + int(face_width * 0.05), mask_y_end]
        ], np.int32)
        
        color = (0, 100, 200)  # マスク色
        cv2.polylines(frame, [pts], True, (0, 0, 0), 2)  # 枠
        cv2.fillPoly(frame, [pts], color)  # 塗りつぶし
    
    return frame

def generate_frames():
    """フレーム生成ジェネレータ"""
    frame_count = 0
    
    while True:
        # フレーム取得
        frame = picam2.capture_array()
        frame_count += 1
        
        # 処理を軽くするため（オプション）
        frame.flags.writeable = False
        
        # 顔検出
        results = face_detection.process(frame)
        
        # 描画のため書き込み可能に
        frame.flags.writeable = True
        
        # 検出された顔にマスクを描画
        if results.detections:
            for detection in results.detections:
                # マスクを描画
                frame = draw_mask(frame, detection.location_data.relative_bounding_box, mask_style='realistic')
        
        # フレーム番号表示（デバッグ用）
        cv2.putText(
            frame,
            f"Frame: {frame_count}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
        
        # JPEG エンコード
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # ストリーミング出力
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    """Flask ストリーミングエンドポイント"""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

if __name__ == "__main__":
    # ローカルネットワーク内でアクセス可能
    app.run(host='0.0.0.0', port=5000, debug=False)