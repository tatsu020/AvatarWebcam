import os
import sys

# Ensure Qt can render without a visible display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import (
    QGuiApplication,
    QPainter,
    QPen,
    QPixmap,
    QColor,
    QPainterPath,
    QFont,
    QFontDatabase,
    QTransform,
)


def _load_icon_font() -> QFont | None:
    # Prefer an explicit font path if provided.
    env_path = os.environ.get("AVATARWEBCAM_ICON_FONT")
    candidates: list[str] = []
    if env_path:
        candidates.append(env_path)

    # Common Windows UI fonts (bold variants).
    win_fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    candidates.extend(
        [
            os.path.join(win_fonts, "segoeuib.ttf"),
            os.path.join(win_fonts, "segoeui.ttf"),
            os.path.join(win_fonts, "arialbd.ttf"),
            os.path.join(win_fonts, "arial.ttf"),
        ]
    )

    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                font = QFont(families[0])
                font.setBold(True)
                font.setHintingPreference(QFont.PreferNoHinting)
                return font

    # Fall back to a system font (may still work fine on most machines).
    font = QFont("Segoe UI")
    font.setBold(True)
    font.setHintingPreference(QFont.PreferNoHinting)
    return font


def _draw_vr_text(painter: QPainter, body: QRect) -> bool:
    font = _load_icon_font()
    if font is None:
        return False

    # Use a vector path to keep the glyphs crisp at multiple sizes.
    font.setPixelSize(100)
    path = QPainterPath()
    path.addText(0, 0, font, "VR")
    bounds = path.boundingRect()
    if bounds.isEmpty():
        return False

    target_w = body.width() * 0.74
    target_h = body.height() * 0.62
    scale = min(target_w / bounds.width(), target_h / bounds.height())

    transform = QTransform()
    transform.translate(body.center().x(), body.center().y())
    transform.scale(scale, scale)
    transform.translate(-bounds.center().x(), -bounds.center().y())

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(17, 17, 27))
    painter.drawPath(transform.map(path))
    return True


def _draw_vr_stroke(painter: QPainter, body: QRect) -> None:
    painter.setBrush(Qt.NoBrush)
    stroke = max(2, int(body.width() / 12))
    painter.setPen(QPen(QColor(17, 17, 27), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

    x = body.x()
    y = body.y()
    w = body.width()
    h = body.height()

    top = y + h * 0.22
    mid = y + h * 0.52
    bottom = y + h * 0.82

    vx1 = x + w * 0.18
    vx2 = x + w * 0.32
    vx3 = x + w * 0.46

    rx1 = x + w * 0.56
    rx2 = x + w * 0.82

    path = QPainterPath()
    path.moveTo(vx1, top)
    path.lineTo(vx2, bottom)
    path.lineTo(vx3, top)

    path.moveTo(rx1, top)
    path.lineTo(rx1, bottom)
    path.moveTo(rx1, top)
    path.lineTo(rx2, top)
    path.lineTo(rx2, mid)
    path.lineTo(rx1, mid)
    path.moveTo(rx1, mid)
    path.lineTo(rx2, bottom)

    painter.drawPath(path)


def _render_icon(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    bg_color = QColor(30, 30, 46)
    accent = QColor(137, 180, 250)

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

    # "VR" text inside camera body (font-based; fallback to strokes).
    if not _draw_vr_text(painter, body):
        _draw_vr_stroke(painter, body)

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
