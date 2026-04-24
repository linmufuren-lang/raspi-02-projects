"""
MediaPipe Face Stylizer - 静止画モード
画像ファイル1枚を変換して保存する。

使い方:
  python stylize_image.py --image <画像パス>
  python stylize_image.py --image test.jpg --model face_stylizer_oil_painting.task
"""

import argparse
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision


def blend_stylized(original: np.ndarray, stylized_rgb: np.ndarray) -> np.ndarray:
    """
    スタイル変換結果(256x256)を元画像の顔領域に合成する。
    FaceStylizer の出力は常に 256x256 なので元画像中央にリサイズ配置。
    """
    h, w = original.shape[:2]
    # stylized は RGB → BGR に変換
    stylized_bgr = cv2.cvtColor(stylized_rgb, cv2.COLOR_RGB2BGR)
    # 元画像の短辺に合わせてリサイズ
    size = min(h, w)
    stylized_resized = cv2.resize(stylized_bgr, (size, size))
    # 中央に配置
    result = original.copy()
    y_off = (h - size) // 2
    x_off = (w - size) // 2
    result[y_off:y_off + size, x_off:x_off + size] = stylized_resized
    return result


def run(model_path: str, image_path: str, output_path: str):
    base_options = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.FaceStylizerOptions(base_options=base_options)

    with mp_vision.FaceStylizer.create_from_options(options) as stylizer:
        image_bgr = cv2.imread(image_path)
        if image_bgr is None:
            print(f"エラー: 画像を読み込めませんでした: {image_path}")
            return

        # BGR → RGB 変換 (MediaPipe は RGB を期待)
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

        print("スタイル変換中...")
        stylized = stylizer.stylize(mp_image)

        if stylized is None:
            print("顔が検出されませんでした。元画像を保存します。")
            cv2.imwrite(output_path, image_bgr)
            return

        stylized_rgb = stylized.numpy_view()
        print(f"スタイル変換結果サイズ: {stylized_rgb.shape}")  # (256, 256, 3)

        result = blend_stylized(image_bgr, stylized_rgb)
        cv2.imwrite(output_path, result)
        print(f"結果を保存しました: {output_path}")

        # 変換のみの画像も保存 (デバッグ用)
        stylized_bgr = cv2.cvtColor(stylized_rgb, cv2.COLOR_RGB2BGR)
        cv2.imwrite("stylized_only.jpg", stylized_bgr)
        print("スタイル変換のみの画像: stylized_only.jpg")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="face_stylizer_color_sketch.task",
                        help="モデルファイルパス")
    parser.add_argument("--image", required=True,
                        help="入力画像ファイルパス")
    parser.add_argument("--output", default="output_stylized.jpg",
                        help="出力画像ファイルパス")
    args = parser.parse_args()

    run(args.model, args.image, args.output)
