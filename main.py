"""
AvatarWebcam - Entry Point
VRChatのSpoutカメラ出力を受け取り、仮想カメラとして出力するアプリ
"""

import sys


def main():
    """アプリケーションのエントリーポイント"""
    # Windows DPIスケーリング対応
    # PySide6 (Qt6) はデフォルトでDPI対応しているため、
    # 手動で設定すると競合して "Access Denied" になる場合があります。
    # そのため、手動設定は削除します。
    # try:
    #     from ctypes import windll
    #     windll.shcore.SetProcessDpiAwareness(1)
    # except Exception:
    #     pass

    from logging_setup import configure_logging
    configure_logging()

    from ui import run_app
    run_app()


if __name__ == "__main__":
    main()
