# AvatarWebcam

VRChatのSpoutカメラ出力を受け取り、仮想カメラとして出力するアプリケーション。
OBSを起動せずにDiscord等でアバターをカメラとして使えます。

## ダウンロード

👉 **[最新版をダウンロード](https://github.com/tatsu020/AvatarWebcam/releases/latest)**

Windows用のexeファイルをダウンロードして、そのまま実行できます。

> ⚠️ **事前準備**  
> [OBS Studio](https://obsproject.com/) をインストールしてください（仮想カメラドライバが自動で登録されます）。

## 機能

- **自動検出**: VRChatのSpoutソースを自動的に検出
- **リアルタイムプレビュー**: 配信映像をGUI上で確認可能
- **軽量動作**: OBS本体を起動せずに仮想カメラのみを利用可能

## 使い方

1. VRChatの設定で「Spout出力を有効にする」にチェックを入れます。
2. AvatarWebcamを起動します。
3. 自動的にVRChatの映像がキャプチャされ、プレビューが表示されます。
4. DiscordやZoom等のカメラ設定から「OBS Virtual Camera」を選択します。

## トラブルシューティング

### 「仮想カメラの初期化に失敗しました」と表示される

OBS Virtual Cameraがインストールされていない可能性があります。

1. OBS Studioをインストール
2. OBSを起動して一度閉じる（初回セットアップのため）

### VRChatのSpoutカメラが検出されない

1. VRChatでSpoutカメラが有効になっているか確認
2. 「↻」ボタンでソースを再スキャン
3. 手動でドロップダウンからソースを選択


## 開発者向け

### 必要要件

- Python 3.9.x
- Windows 10/11
- [OBS Studio](https://obsproject.com/)

### 起動・ビルド

```bash
# 依存関係のインストール
pip install -r requirements.txt

# アプリの起動
python main.py

# 配布用exeの作成
build.bat
```

## ライセンス / 謝辞

本プロジェクトは **GPL v2** で公開されています。  
ソースコード: https://github.com/tatsu020/AvatarWebcam

