import os
import sys
import subprocess
import ctypes
from pathlib import Path

def launch():
    # Nuitka onefile の場合、sys.executable は Temp フォルダを指す。
    # オリジナル EXE の場所は NUITKA_ONEFILE_BINARY 環境変数に入っている。
    exe_path = os.environ.get("NUITKA_ONEFILE_BINARY")
    if not exe_path:
        # 環境変数がない場合は sys.argv[0] を試す（フォールバック）
        exe_path = sys.argv[0]
    
    base_dir = Path(exe_path).parent.absolute()
    real_exe = base_dir / "_internal" / "AvatarWebCam_internal.exe"
    
    if not real_exe.exists():
        ctypes.windll.user32.MessageBoxW(
            0, 
            f"システム本体が見つかりません。\n場所: {real_exe}", 
            "AvatarWebCam 起動エラー", 
            0x10
        )
        return

    # 本物のEXEを起動
    try:
        # カレントディレクトリを base_dir (ルート) に設定して起動
        subprocess.Popen([str(real_exe)] + sys.argv[1:], cwd=str(base_dir))
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(
            0, 
            f"アプリの起動に失敗しました。\nエラー: {e}", 
            "AvatarWebCam 起動エラー", 
            0x10
        )

if __name__ == "__main__":
    launch()
