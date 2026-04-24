"""
MediaPipe Face Stylizer - ライブプレビューモード (Picamera2版)
カメラ映像を取得して一定間隔でスタイル変換して表示する。

注意: FaceStylizer は IMAGE モードのみ対応のため、
      フレームをバッファリングして非同期で処理する。
      Raspberry Pi 4 では 1-3 fps 程度が現実的。

使い方:
  python stylize_live.py
  python stylize_live.py --model face_stylizer_oil_painting.task --interval 1.5
終了: 'q' キー / 's' でスナップショット保存
"""

import argparse
import time
import threading
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from picamera2 import Picamera2

# グローバル状態
STYLIZED_RESULT = None   # 最新のスタイル変換済みフレーム (BGR numpy)
PROCESSING = False       # 推論中フラグ
LOCK = threading.Lock()
PROCESS_INTERVAL = 0.5  # 推論間隔 (秒)


def stylize_worker(stylizer, frame_rgb: np.ndarray):
    """バックグラウンドスレッドでスタイル変換を実行する"""
    global STYLIZED_RESULT, PROCESSING

    try:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)  # RGB 直接渡し

        stylized = stylizer.stylize(mp_image)

        if stylized is not None:
            # 出力は RGB (256x256) → imshow 用に BGR に変換
            stylized_rgb = stylized.numpy_view()
            stylized_bgr = cv2.cvtColor(stylized_rgb, cv2.COLOR_RGB2BGR)
            with LOCK:
                STYLIZED_RESULT = stylized_bgr
    except Exception as e:
        print(f"[Worker] エラー: {e}")
    finally:
        with LOCK:
            PROCESSING = False


def overlay_stylized(frame: np.ndarray, stylized: np.ndarray,
                     alpha: float = 0.85) -> np.ndarray:
    """スタイル変換結果 (256x256) をフレームの右下にプレビュー表示する"""
    h, w = frame.shape[:2]
    preview_size = min(256, h // 3, w // 3)
    stylized_resized = cv2.resize(stylized, (preview_size, preview_size))

    margin = 10
    y1 = h - preview_size - margin
    x1 = w - preview_size - margin
    y2 = y1 + preview_size
    x2 = x1 + preview_size

    result = frame.copy()
    roi = result[y1:y2, x1:x2]
    blended = cv2.addWeighted(roi, 1 - alpha, stylized_resized, alpha, 0)
    result[y1:y2, x1:x2] = blended

    cv2.rectangle(result, (x1, y1), (x2, y2), (255, 255, 0), 2)
    cv2.putText(result, "Stylized", (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    return result


def run(model_path: str, width: int, height: int, process_interval: float):
    global PROCESSING

    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.FaceStylizerOptions(base_options=base_options)

    # Picamera2 初期化
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (width, height), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(0.5)  # カメラウォームアップ待ち

    print(f"カメラ起動: {width}x{height}  モデル: {model_path}")
    print("'q' で終了 / 's' でスナップショット保存")
    print(f"推論間隔: {process_interval}秒 (変更: --interval オプション)")

    last_process_time = 0
    fps_counter = 0
    fps_start = time.time()
    fps_display = 0.0

    with mp_vision.FaceStylizer.create_from_options(options) as stylizer:
        while True:
            # Picamera2 は RGB888 で取得。MediaPipe へは RGB 直接渡し
            frame_rgb = picam2.capture_array()
            # imshow は BGR を期待するため表示用のみ変換
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            now = time.time()

            with LOCK:
                is_processing = PROCESSING

            if not is_processing and (now - last_process_time) >= process_interval:
                with LOCK:
                    PROCESSING = True
                last_process_time = now
                t = threading.Thread(
                    target=stylize_worker,
                    args=(stylizer, frame_rgb.copy()),  # RGB のまま渡す
                    daemon=True
                )
                t.start()

            display = frame_bgr.copy()

            with LOCK:
                result = STYLIZED_RESULT

            if result is not None:
                display = overlay_stylized(display, result)

            fps_counter += 1
            if fps_counter >= 30:
                fps_display = fps_counter / (time.time() - fps_start)
                fps_counter = 0
                fps_start = time.time()

            cv2.putText(display, f"Camera FPS: {fps_display:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            status = "Stylizing..." if is_processing else "Waiting"
            cv2.putText(display, status, (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

            cv2.imshow("Face Stylizer - Live", display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                snap_path = f"snapshot_{int(time.time())}.jpg"
                cv2.imwrite(snap_path, display)
                print(f"スナップショット保存: {snap_path}")

    picam2.stop()
    cv2.destroyAllWindows()
    print("終了しました")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="face_stylizer_color_sketch.task",
                        help="モデルファイル (.task)")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--interval", type=float, default=PROCESS_INTERVAL,
                        help="推論間隔(秒)。重い場合は 1.0〜2.0 を推奨")
    args = parser.parse_args()

    run(args.model, args.width, args.height, args.interval)
