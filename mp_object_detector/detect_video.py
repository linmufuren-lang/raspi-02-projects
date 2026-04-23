"""
MediaPipe Object Detector - 動画ファイルモード
使い方: python detect_video.py --video <動画ファイルパス>
終了:  'q' キー
"""

import argparse
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision


def draw_detections(image, detection_result):
    for detection in detection_result.detections:
        bbox = detection.bounding_box
        start = (bbox.origin_x, bbox.origin_y)
        end = (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height)
        cv2.rectangle(image, start, end, (0, 165, 255), 3)

        category = detection.categories[0]
        label = f"{category.category_name} ({category.score:.2f})"
        cv2.putText(image, label,
                    (bbox.origin_x + 10, bbox.origin_y + 30),
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 0), 1, cv2.LINE_AA)
    return image


def run(model_path, video_path, max_results, score_threshold):
    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.ObjectDetectorOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        max_results=max_results,
        score_threshold=score_threshold,
    )

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    print(f"動画FPS: {fps}")

    with mp_vision.ObjectDetector.create_from_options(options) as detector:
        frame_index = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_ms = int(frame_index * (1000 / fps))
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            result = detector.detect_for_video(mp_image, timestamp_ms)
            annotated = draw_detections(frame, result)
            cv2.imshow("Object Detector - Video", annotated)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            frame_index += 1

    cap.release()
    cv2.destroyAllWindows()
    print("終了しました")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="efficientdet_lite0.tflite")
    parser.add_argument("--video", required=True)
    parser.add_argument("--max_results", type=int, default=5)
    parser.add_argument("--score_threshold", type=float, default=0.5)
    args = parser.parse_args()
    run(args.model, args.video, args.max_results, args.score_threshold)
