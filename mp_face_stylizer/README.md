# mp_face_stylizer

MediaPipe FaceStylizer を使って顔をアート風に変換するプロジェクト。

---

## 共通：起動準備

```bash
cd ~/projects/mp_face_stylizer
source env/bin/activate
```

---

## app.py — ブラウザ撮影モード（推奨）

ライブカメラを見ながらシャッターを押し、変換画像をブラウザのギャラリーに表示する。  
**5枚撮影で自動停止。**

### 起動

```bash
python app.py
```

ブラウザで `http://192.168.0.19:5000` を開く。  
Pi Camera Portal (`http://192.168.0.19:8080`) の **🎨 Face Stylizer** カードからも起動できる。

### 操作

| 操作 | 内容 |
|------|------|
| カメラボタン（●） | 現在フレームをキャプチャしてスタイル変換（約1〜2秒） |
| 右側ギャラリー | 変換済み画像を #1〜#5 で自動表示 |
| 5枚撮影後 | シャッターが無効化されて「✓ 5枚撮影完了」と表示 |

### 画像の保存先

```
~/projects/mp_face_stylizer/captures/
```

ファイル名例: `capture_1714000000000.jpg`  
解像度: 640×480 px（カメラと同サイズにアップスケール）

### モデルの変更

[app.py](app.py) の先頭を編集する：

```python
MODEL_PATH = "face_stylizer_color_sketch.task"   # ← ここを変更
```

| ファイル名 | スタイル |
|-----------|---------|
| `face_stylizer_color_sketch.task` | カラースケッチ（デフォルト） |
| `face_stylizer_color_ink.task` | カラーインク |
| `face_stylizer_oil_painting.task` | 油絵 |

---

## stylize_image.py — 静止画変換モード

画像ファイル1枚を指定してスタイル変換し、ファイルとして保存する。

### 使い方

```bash
# デフォルト（カラースケッチ）
python stylize_image.py --image test_face.jpg

# モデルを指定
python stylize_image.py --image test_face.jpg --model face_stylizer_oil_painting.task

# 出力ファイル名も指定
python stylize_image.py --image test_face.jpg \
  --model face_stylizer_color_ink.task \
  --output output_ink.jpg
```

### オプション

| オプション | デフォルト | 内容 |
|-----------|-----------|------|
| `--image` | （必須） | 入力画像ファイルパス |
| `--model` | `face_stylizer_color_sketch.task` | 使用モデル |
| `--output` | `output_stylized.jpg` | 出力ファイルパス |

### 出力ファイル

| ファイル | 内容 |
|---------|------|
| `output_stylized.jpg` | 元画像サイズに合成した結果 |
| `stylized_only.jpg` | 変換のみの結果（256×256） |

> 顔が検出されなかった場合は元画像をそのまま保存する。

---

## stylize_live.py — ライブプレビューモード（要ディスプレイ）

Picamera2 で映像を取得し、一定間隔でスタイル変換してウィンドウに表示する。  
`cv2.imshow()` を使用するため **HDMI接続のディスプレイが必要**（SSH環境では動作しない）。

### 使い方

```bash
# デフォルト（0.5秒ごとに変換）
python stylize_live.py

# 推論間隔を延ばして CPU 負荷を下げる
python stylize_live.py --interval 1.5

# モデル指定
python stylize_live.py --model face_stylizer_oil_painting.task --interval 2.0
```

### オプション

| オプション | デフォルト | 内容 |
|-----------|-----------|------|
| `--model` | `face_stylizer_color_sketch.task` | 使用モデル |
| `--width` | `640` | カメラ解像度（幅） |
| `--height` | `480` | カメラ解像度（高さ） |
| `--interval` | `0.5` | 推論間隔（秒）。重い場合は `1.0`〜`2.0` を推奨 |

### キー操作

| キー | 内容 |
|------|------|
| `q` | 終了 |
| `s` | スナップショットを `snapshot_<timestamp>.jpg` として保存 |

---

## ディレクトリ構成

```
mp_face_stylizer/
├── app.py                          # ブラウザ撮影モード（Flask）
├── stylize_image.py                # 静止画変換
├── stylize_live.py                 # ライブプレビュー（ディスプレイ必須）
├── captures/                       # ★ app.py の生成画像保存先
│   └── capture_*.jpg
├── face_stylizer_color_sketch.task # モデル: カラースケッチ
├── face_stylizer_color_ink.task    # モデル: カラーインク
├── face_stylizer_oil_painting.task # モデル: 油絵
├── env -> ../mp_object_detector/env  # venv（シンボリックリンク）
└── test_face.jpg                   # テスト用顔画像
```

---

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| 顔が検出されない | 正面向き・明るい環境で撮影。横顔は検出率が低い |
| 変換が遅い | `--interval 2.0` に延ばす、または解像度を 320×240 に下げる |
| `libGL.so` エラー | `sudo apt install -y libgl1` |
| ブラウザで映像が映らない | `python app.py` が起動しているか確認。ポート 5000 が他プロセスと競合していないか確認 |
| `AttributeError: FaceStylizerOptions` | `pip install -U mediapipe` でバージョンを更新 |
