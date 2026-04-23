import cv2
import mediapipe as mp
import numpy as np
from picamera2 import Picamera2

# MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# picamera2 カメラ初期化
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (640, 480), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()

print("✓ Camera started")
print("Press 'q' to exit")

frame_count = 0

try:
    while True:
        # フレーム取得
        frame = picam2.capture_array()
        
        # Picamera2 は RGB888 で取得するので変換不要
        image_rgb = frame
        image_rgb.flags.writeable = False
        
        # 姿勢認識
        results = pose.process(image_rgb)
        
        # ランドマーク描画
        image_rgb.flags.writeable = True
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                image_rgb,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS
            )
        
        # フレームカウント
        frame_count += 1
        cv2.putText(image_rgb, f"Frame: {frame_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # --- 修正後（ファイルに保存する） ---
        # 1フレーム分だけ解析結果を保存して終了する例
        output_path = "result.jpg"
        cv2.imwrite(output_path, image_rgb)
        print(f"解析結果を {output_path} に保存しました。")
        # 終了キー
        break

finally:
    picam2.stop()
    cv2.destroyAllWindows()
    pose.close()
    print(f"✓ Processed {frame_count} frames")
