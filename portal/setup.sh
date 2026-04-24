#!/bin/bash
# ポータルの仮想環境セットアップ（初回のみ実行）
set -e
cd "$(dirname "$0")"

echo "=== Pi Portal セットアップ ==="
python3 -m venv env
source env/bin/activate
pip install --upgrade pip -q
pip install flask -q

echo ""
echo "完了！以下のコマンドで起動できます:"
echo "  cd ~/projects/portal && source env/bin/activate && python app.py"
echo ""
echo "自動起動を設定する場合:"
echo "  sudo cp portal.service /etc/systemd/system/"
echo "  sudo systemctl enable --now portal"
