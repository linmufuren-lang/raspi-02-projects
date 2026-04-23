"""
MediaPipe Object Detector - 静止画モード
使い方: python detect_image.py --image <画像ファイルパス>
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


def run(model_path, image_path, max_results, score_threshold):
    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.ObjectDetectorOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.IMAGE,
        max_results=max_results,
        score_threshold=score_threshold,
    )

    with mp_vision.ObjectDetector.create_from_options(options) as detector:
        mp_image = mp.Image.create_from_file(image_path)
        result = detector.detect(mp_image)

        print(f"検出数: {len(result.detections)}")
        for i, det in enumerate(result.detections):
            cat = det.categories[0]
            print(f"  [{i+1}] {cat.category_name}  スコア: {cat.score:.2f}  "
                  f"Box: ({det.bounding_box.origin_x}, {det.bounding_box.origin_y}, "
                  f"{det.bounding_box.width}x{det.bounding_box.height})")

        image_cv = cv2.imread(image_path)
        annotated = draw_detections(image_cv, result)
        cv2.imwrite("output_image.jpg", annotated)
        print("結果画像を保存しました: output_image.jpg")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="efficientdet_lite0.tflite")
    parser.add_argument("--image", required=True)
    parser.add_argument("--max_results", type=int, default=5)
    parser.add_argument("--score_threshold", type=float, default=0.5)
    args = parser.parse_args()
    run(args.model, args.image, args.max_results, args.score_threshold)
