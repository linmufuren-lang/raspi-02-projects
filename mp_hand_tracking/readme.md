目標：MediaPipe Hands を使った「指さし」検知
骨格、顔と来たら、次は「手」です。手の動き（ジェスチャー）を読み取れるようになると、将来的に「手を振ったらライトがつく」といった高度な操作が可能になります。

ステップ 1：新しい仮想環境の準備（復習）
毎回新しいプロジェクトフォルダを作る習慣は、環境を汚さないための「最強の防御」です。

ディレクトリ作成

Bash
mkdir -p ~/projects/mp_hand_tracking
cd ~/projects/mp_hand_tracking
環境構築

Bash
python -m venv env
source env/bin/activate
sudo apt update && sudo apt install -y libcap-dev  # 以前学んだエラー対策
pip install flask picamera2 opencv-python mediapipe
ステップ 2：プロ仕様の「部品分け」コード
今回は、カメラを担当する部品（クラス）と、AI解析を担当する部品を分けてみましょう。これにより、将来カメラをUSBに変えたい時は、カメラクラスだけを書き換えれば済むようになります。

これを main.py として作成してみてください。

Python
import cv2
import mediapipe as mp
from flask import Flask, Response
from picamera2 import Picamera2

app = Flask(__name__)

# --- 部品1：AI解析担当 (HandDetectorクラス) ---
class HandDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.5)

    def process(self, frame):
        # MediaPipeで解析
        results = self.hands.process(frame)
        # 手が見つかったらアノテーションを描画
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
        return frame

# --- 部品2：カメラ担当 (CameraSourceクラス) ---
class CameraSource:
    def __init__(self):
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)})
        self.picam2.configure(config)
        self.picam2.start()

    def get_frame(self):
        return self.picam2.capture_array()

# --- メインの配信ロジック ---
detector = HandDetector()
camera = CameraSource()

def generate_frames():
    while True:
        frame = camera.get_frame()  # カメラから取得
        frame = detector.process(frame)  # AIで解析
        
        # JPEGに変換して配信
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


## 実行　##
http://192.168.0.19:5000

このコードで学べる「開発力」
カプセル化: CameraSource クラスの中に Picamera2 の複雑な設定を隠しました。外側からは get_frame() と呼ぶだけで画像が手に入ります。

モジュール性: もし「顔検出」に戻したければ、FaceDetector クラスを作って差し替えるだけで、配信側のコードは一切触らずに済みます。

信頼性: min_detection_confidence を高めに設定することで、誤検知を減らす工夫も入れています。