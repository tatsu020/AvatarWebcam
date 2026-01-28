import os
import sys

# Ensure Qt can render without a visible display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QGuiApplication, QPainter, QPen, QPixmap, QColor, QFont


def _render_icon(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    bg_color = QColor(30, 30, 46)
    accent = QColor(137, 180, 250)
    accent_dark = QColor(17, 17, 27)

    margin = max(4, size // 16)
    rect = QRect(margin, margin, size - margin * 2, size - margin * 2)
    pen_width = max(2, size // 21)
    corner = max(8, size // 6)

    painter.setBrush(bg_color)
    painter.setPen(QPen(accent, pen_width))
    painter.drawRoundedRect(rect, corner, corner)

    painter.setPen(Qt.NoPen)
    painter.setBrush(accent)

    body = QRect(
        int(size * 0.1875),
        int(size * 0.390625),
        int(size * 0.625),
        int(size * 0.34375),
    )
    body_radius = int(size * 0.078125)
    painter.drawRoundedRect(body, body_radius, body_radius)

    bump = QRect(
        int(size * 0.375),
        int(size * 0.3125),
        int(size * 0.25),
        int(size * 0.09375),
    )
    bump_radius = int(size * 0.046875)
    painter.drawRoundedRect(bump, bump_radius, bump_radius)

    painter.setPen(accent_dark)
    font_size = max(8, int(size * 0.21875))
    painter.setFont(QFont("Segoe UI", font_size, QFont.Bold))
    painter.drawText(body, Qt.AlignCenter, "VR")

    painter.end()
    return pixmap


def main() -> int:
    app = QGuiApplication(sys.argv)
    _ = app  # keep reference alive for Qt resources

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    ico_path = os.path.join(repo_root, "icon.ico")
    png_path = os.path.join(repo_root, "icon.png")

    pixmap = _render_icon(256)

    if not pixmap.save(png_path, "PNG"):
        print("Failed to write icon.png")
        return 1

    if not pixmap.save(ico_path, "ICO"):
        # Leave the PNG so builds can still use it.
        if os.path.exists(ico_path):
            try:
                os.remove(ico_path)
            except OSError:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
