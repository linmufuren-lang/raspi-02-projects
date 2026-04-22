プロジェクト別仮想環境（venv）構築手順書
このドキュメントでは、プロジェクトごとに独立した Python 実行環境を作成し、ライブラリの衝突を防ぐための標準的な手順を記述します。

1. プロジェクトディレクトリの作成と移動
新しい開発を始める際は、まず専用のフォルダを作成してその中に入ります。

Bash
mkdir -p ~/projects/my_new_project
cd ~/projects/my_new_project
2. 仮想環境の作成
フォルダ内に env という名前で仮想環境を作成します。

Bash
python -m venv env
※ env という名前は慣習ですが、.gitignore などで除外設定しやすいため推奨されます。

3. 仮想環境の有効化
作成した環境に切り替えます。

Bash
source env/bin/activate
有効になると、ターミナルの左端に (env) と表示されます。

4. ライブラリのインストール
そのプロジェクトに必要なライブラリだけをインストールします。

Bash
pip install flask picamera2 opencv-python mediapipe

5. 環境の書き出し（バックアップ・移行用）
インストール済みのライブラリ一覧をテキストファイルに保存しておくと、別の端末や新しいディスクでの復元が容易になります。

Bash
pip freeze > requirements.txt
※ 復元時は pip install -r requirements.txt で一括インストール可能です。

6. VS Code での選択手順
VS Code でプロジェクトフォルダを開いた後、以下の操作で作成した環境を紐付けます。

Ctrl + Shift + P を押す。

「Python: Select Interpreter」と入力して選択。

リストから ./env/bin/python を選ぶ。

これにより、VS Code のターミナル起動時に自動で source env/bin/activate が実行されるようになります。

7. # 仮想環境の無効化

python -m venv env

