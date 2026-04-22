MediaPipe を使った「関節分析（Skeletal Detection）」


ステップ 1：新しいプロジェクト環境の準備
まずは /projects の下に専用のディレクトリを作り、クリーンな環境を用意します。

ディレクトリの作成と移動

Bash
mkdir -p ~/projects/mp_pose_stream
cd ~/projects/mp_pose_stream
仮想環境の作成と有効化

Bash
python -m venv env
source env/bin/activate
必要なライブラリの一括インストール

Bash
pip install flask picamera2 opencv-python mediapipe
ステップ 2：MediaPipe を組み込んだ stream.py の作成
このコードでは、MediaPipe の処理をひとまとめにして、カメラの種類が変わっても対応しやすい構成にしています。

Python
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

ステップ 3：ライブラリに左右されないようにするには？
「OpenCV や Picamera2 に依存したくない」という考え方は、大規模なシステム開発において非常に重要です。これを実現するには、**「ラッパー（包み紙）」**という考え方を使います。

どういう仕組みか？
カメラから画像を取る部分を「Cameraクラス」、画像に線を引く部分を「Drawerクラス」として独立させます。

カメラを変えたい時: Picamera2Source を USBWebcamSource に差し替えるだけで、メインの解析コード（MediaPipe部分）は 1 行も書き換えずに済みます。

描画ライブラリを変えたい時: OpenCV を使わずに別のライブラリで線を引きたい場合も、その描画クラスだけを差し替えます。

今回のコードで言えば、picam2.capture_array() の部分を「画像データを返す共通の関数」として定義しておくのが第一歩です。

ステップ 4：動作確認の手順
プログラムの実行

Bash
python stream.py
ブラウザで確認
PCのブラウザから http://192.168.0.19:5000 にアクセスしてください。

カメラに映る
自分の体（全身が映るのが理想）をカメラに向けると、リアルタイムで関節に点と線が表示されるはずです。

⚠️ 注意点（ラズパイの負荷）
MediaPipe は CPU をかなり使います。

もし映像がカクつく場合は、config の size を (320, 240) に下げるとスムーズになります。

ラズパイのメモリが気になる場合は、以前設定した ZRAM やスワップファイルが効いていることを確認してください。