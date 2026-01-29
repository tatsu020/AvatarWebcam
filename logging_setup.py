import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_NAME = "AvatarWebCam"
LOG_FILENAME = "vrcambridge.log"
DEFAULT_LEVEL = logging.INFO
MAX_BYTES = 512 * 1024
BACKUP_COUNT = 3


def _get_log_dir() -> Path:
    # 実行ファイル（.exe）と同じ階層、またはスクリプトのある階層の logs フォルダを使用する
    if getattr(sys, "frozen", False) or hasattr(sys, "frozen") or "__compiled__" in globals():
        # exe 実行時
        base_dir = Path(sys.executable).parent
    else:
        # python main.py 実行時
        base_dir = Path(__file__).parent
    
    return base_dir / "logs"


def _parse_level(value: str | None) -> int:
    if not value:
        return DEFAULT_LEVEL
    normalized = value.strip().upper()
    return getattr(logging, normalized, DEFAULT_LEVEL)


def configure_logging() -> None:
    level = _parse_level(os.getenv("AVATARWEBCAM_LOG_LEVEL"))
    log_dir = _get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILENAME

    root = logging.getLogger()
    root.setLevel(level)

    # Reset handlers to avoid duplicate logs when called multiple times.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    try:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except Exception as exc:
        root.warning("Failed to set up file logging: %s", exc)

    # OpenGL_accelerate の通知を抑制（パフォーマンスに影響はなく、単なる通知のため）
    logging.getLogger("OpenGL.acceleratesupport").setLevel(logging.ERROR)
