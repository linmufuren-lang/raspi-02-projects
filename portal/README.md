# Pi Camera Portal

ブラウザからカメラプロジェクトを起動・停止できるランチャーです。  
アクセス先: `http://192.168.0.19:8080`

---

## 通常の使い方

Pi の電源を入れてブラウザで `http://192.168.0.19:8080` を開くだけです。  
ポータルは自動で起動しています。

- **▶ 起動** → カメラ + AI 処理が始まります
- **🔗 開く** → カメラ映像を別タブで表示します（`http://192.168.0.19:5000`）
- **■ 停止** → カメラが止まり、負荷がゼロに戻ります

> **負荷について:** ポータル自体の常時起動は CPU・メモリへの影響はほぼありません。  
> 重い処理（カメラ + AI）は「▶ 起動」を押した時だけ動きます。

---

## 起動状態の確認

```bash
sudo systemctl status portal
```

`active (running)` と表示されれば正常です。

---

## ポータルを停止したい場合

```bash
sudo systemctl stop portal
```

再起動するまで止まります（次回 Pi 起動時には自動で戻ります）。

---

## 自動起動を無効にしたい場合

```bash
sudo systemctl disable portal
```

以後は Pi を再起動しても自動では起動しません。

---

## 手動で起動したい場合

自動起動を無効にした後、使いたい時だけ以下を実行します。

```bash
cd ~/projects/portal
source env/bin/activate
python app.py
```

終了するには `Ctrl + C` を押します。

---

## 自動起動に戻したい場合

```bash
sudo systemctl enable --now portal
```

---

## 新しいプロジェクトを追加する場合

1. `~/projects/<プロジェクト名>/` に `env/` と `app.py`（または `main.py` / `stream.py`）を置く
2. ポータルのページをブラウザでリロードする

カードが自動で追加されます。設定ファイルの変更は不要です。

アイコン・説明文をカスタマイズしたい場合は `portal/app.py` の `PROJECT_META` に1行追加してください。

---

## 不要なプロジェクトをカードから消す場合

フォルダ名の先頭に `_` をつけるとポータルが自動で無視します。

```bash
mv ~/projects/mp_XXX ~/projects/_mp_XXX
```

---

## ファイル構成

```
portal/
├── app.py              # Flask バックエンド（プロセス管理）
├── setup.sh            # 初回セットアップ用スクリプト
├── portal.service      # systemd サービス定義
├── README.md           # このファイル
└── templates/
    └── index.html      # ブラウザ表示用 UI
```
