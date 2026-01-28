"""
AvatarWebcam - GUI
PySide6を使用したユーザーインターフェース (Modern Dark Design)
"""

from __future__ import annotations

from queue import Empty, Queue
import subprocess
import logging
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QRect,
    QSize,
    QEasingCurve,
    QAbstractNativeEventFilter,
    QCoreApplication,
    QSharedMemory,
)
from PySide6.QtGui import (
    QFont,
    QIcon,
    QImage,
    QPixmap,
    QColor,
    QPainter,
    QPainterPath,
    QBrush,
    QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QPushButton,
    QComboBox,
    QCheckBox,
    QRadioButton,
    QButtonGroup,
    QSystemTrayIcon,
    QMenu,
    QSizePolicy,
    QGraphicsDropShadowEffect,
    QMessageBox,
)

from bridge import BridgeState, BridgeStatus, SpoutBridge

logger = logging.getLogger(__name__)

# Resolve checkmark asset for QSS (Qt doesn't always load data: URLs)
CHECKMARK_SVG_PATH = Path(__file__).resolve().parent / "assets" / "checkmark.svg"
# Qt style sheets handle absolute paths better than file:// on Windows.
CHECKMARK_URL = CHECKMARK_SVG_PATH.as_posix().replace(" ", "%20")

# --- Modern Light Theme QSS (Catppuccin Latte inspired) ---
APP_QSS = """
QWidget {
    font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
    font-size: 14px;
    color: #4c4f69; /* Text */
}

QWidget#root {
    background-color: #eff1f5; /* Base Light */
}

/* --- Typography --- */
QLabel#headerTitle {
    font-size: 20px;
    font-weight: 700;
    color: #179299; /* Teal */
}
QLabel#headerSubtitle {
    font-size: 12px;
    color: #9ca0b0; /* Subtext */
}
QLabel#sectionTitle {
    font-size: 13px;
    font-weight: 600;
    color: #7287fd; /* Lavender/Blue */
    margin-bottom: 4px;
}
QLabel#statusLabel {
    font-weight: 600;
}

/* --- Cards --- */
QFrame[class="card"] {
    background-color: #ffffff;
    border: 1px solid #ccd0da;
    border-radius: 12px;
}

/* --- Buttons --- */
QPushButton {
    background-color: #e6e9ef;
    border: 1px solid #bcc0cc;
    border-radius: 8px;
    padding: 8px 16px;
    color: #4c4f69;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #dce0e8;
    border-color: #acb0be;
}
QPushButton:pressed {
    background-color: #eff1f5;
}

/* Hero Button (Start/Stop) */
QPushButton#heroButton {
    background-color: #1e66f5; /* Blue */
    color: #ffffff;
    border: none;
    font-size: 16px;
    font-weight: 800;
    border-radius: 12px;
}
QPushButton#heroButton:hover {
    background-color: #1754e6; /* Darker Blue */
}
QPushButton#heroButton[active="true"] {
    background-color: #d20f39; /* Red */
    color: #ffffff;
}
QPushButton#heroButton[active="true"]:hover {
    background-color: #b00c30;
}

QPushButton#iconButton {
    padding: 4px;
    border-radius: 6px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    background-color: transparent;
    border: 1px solid transparent;
}
QPushButton#iconButton:hover {
    background-color: #e6e9ef;
    border-color: #bcc0cc;
}

/* --- Inputs --- */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #ccd0da;
    border-radius: 8px;
    padding: 8px 12px;
    color: #4c4f69;
}
QComboBox:hover {
    border-color: #1e66f5; /* Focus Blue */
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border: none;
    width: 0; 
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #6c6f85;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #ccd0da;
    selection-background-color: #eff1f5;
    selection-color: #1e66f5;
    outline: none;
}

/* --- Checkbox / Radio --- */
QCheckBox, QRadioButton {
    spacing: 8px;
    color: #4c4f69;
    min-height: 22px;
}
QCheckBox:hover, QRadioButton:hover {
    color: #1e66f5;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #9ca0b0;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #1e66f5;
    border-color: #1e66f5;
    /* White checkmark from local asset */
    image: url("__CHECKMARK_URL__");
}
QCheckBox::indicator:hover {
    border-color: #1e66f5;
}
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #9ca0b0;
    background: #ffffff;
}
QRadioButton::indicator:checked {
    background-color: #1e66f5;
    border: 1px solid #1e66f5;
    image: none;
}
QRadioButton::indicator:hover {
    border-color: #1e66f5;
}

/* --- Preview Area --- */
QLabel#previewCanvas {
    background-color: #e6e9ef; /* Lighter preview bg */
    border-radius: 8px;
    color: #9ca0b0;
    font-size: 11px;
}
"""

APP_QSS = APP_QSS.replace("__CHECKMARK_URL__", CHECKMARK_URL)

class StatusBadge(QFrame):
    """Custom Status Indicator Widget"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = QColor("#585b70") # Default gray

    def set_color(self, color_str: str):
        self._color = QColor(color_str)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(2, 2, 8, 8)


class _WindowsShutdownFilter(QAbstractNativeEventFilter):
    """Detect Windows shutdown/logoff to avoid close-to-tray interception."""

    _WM_QUERYENDSESSION = 0x0011
    _WM_ENDSESSION = 0x0016

    def __init__(self, on_shutdown):
        super().__init__()
        self._on_shutdown = on_shutdown

    def nativeEventFilter(self, event_type, message):
        if os.name != "nt":
            return False, 0
        if event_type not in ("windows_generic_MSG", "windows_dispatcher_MSG"):
            return False, 0
        try:
            import ctypes
            from ctypes import wintypes

            msg = wintypes.MSG.from_address(int(message))
            if msg.message in (self._WM_QUERYENDSESSION, self._WM_ENDSESSION):
                self._on_shutdown()
        except Exception:
            pass
        return False, 0


class AvatarWebcamApp(QWidget):
    """AvatarWebcam Main Window"""

    PREVIEW_SIZE = (384, 216)  # 16:9, slightly more compact to fit 720p screens
    AUTOSTART_ARG = "--autostart"
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    RUN_VALUE_NAME = "AvatarWebcam"
    RESOLUTION_CHOICES = [
        ("480p", "480p"),
        ("720p", "720p"),
        ("1080p", "1080p"),
        ("1440p (2K)", "1440p"),
        ("2160p (4K)", "2160p"),
        ("VRCカメラと同じ", "source"),
    ]

    def __init__(self):
        super().__init__()

        self.setObjectName("root")
        self.setWindowTitle("AvatarWebcam")
        self.resize(480, 620) # More compact window
        self.setWindowIcon(self._build_app_icon())

        # Logic State
        self._state_queue: Queue[BridgeState] = Queue()
        self._bridge = SpoutBridge(state_callback=self._on_bridge_state)
        self._preview_pixmap: Optional[QPixmap] = None
        
        # Settings
        settings = self._load_settings()
        self._auto_start_enabled = bool(settings.get("auto_start_enabled", True))
        self._windows_autostart_enabled = self._is_windows_autostart_enabled()
        legacy_start_in_tray = bool(settings.get("start_in_tray", False))
        self._start_in_tray_on_launch_enabled = bool(
            settings.get("start_in_tray_on_launch", legacy_start_in_tray)
        )
        self._close_to_tray_enabled = bool(
            settings.get("close_to_tray", legacy_start_in_tray)
        )
        self._resolution_value = settings.get("resolution", "source")
        if self._resolution_value not in [v for _, v in self.RESOLUTION_CHOICES]:
            self._resolution_value = "source"

        self._monitor_interval_idle_ms = 60000
        self._monitor_interval_active_ms = 10000
        self._started_from_autostart = self.AUTOSTART_ARG in sys.argv
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._tray_menu: Optional[QMenu] = None
        self._auto_monitor_timer: Optional[QTimer] = None
        self._has_shown = False
        self._start_hidden_in_tray = False
        self._allow_exit = False
        self._shutdown_requested = False
        self._native_event_filter: Optional[QAbstractNativeEventFilter] = None
        self._state_timer_interval_running_ms = 100
        self._state_timer_interval_idle_visible_ms = 250
        self._state_timer_interval_idle_hidden_ms = 500
        self._vrchat_running_cache: Optional[bool] = None
        self._vrchat_last_check = 0.0
        self._vrchat_cache_ttl_idle_s = 30.0
        self._vrchat_cache_ttl_active_s = 10.0

        # Build UI
        self._build_ui()
        self._apply_settings_to_controls()
        self._refresh_sources()
        self._update_auto_controls()
        self._update_startup_controls()

        # Timers
        self._state_timer = QTimer(self)
        self._state_timer.timeout.connect(self._update_state)
        self._update_state_timer_interval()
        self._state_timer.start()

        # Startup Logic
        self._install_shutdown_handler()
        self._maybe_start_in_tray()
        if self._auto_start_enabled and self._is_auto_detect_selected():
            self._start_auto_monitor()

    def showEvent(self, event):
        super().showEvent(event)
        if self._start_hidden_in_tray:
            self._start_hidden_in_tray = False
            QTimer.singleShot(0, self._hide_to_tray)
            return
        self._update_state_timer_interval()

    def closeEvent(self, event):
        if self._shutdown_requested:
            self._shutdown_requested = False
            self._stop_bridge()
            self._stop_auto_monitor()
            self._stop_tray_icon()
            event.accept()
            QCoreApplication.quit()
            return
        if self._allow_exit:
            self._allow_exit = False
            self._stop_bridge()
            self._stop_auto_monitor()
            self._stop_tray_icon()
            event.accept()
            QCoreApplication.quit()
            return
        if self._close_to_tray_enabled and QSystemTrayIcon.isSystemTrayAvailable():
            self._hide_to_tray()
            event.ignore()
            return
        # Stop everything gracefully
        self._stop_bridge()
        self._stop_auto_monitor()
        self._stop_tray_icon()
        event.accept()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(14)

        # --- Header ---
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_group = QWidget()
        title_layout = QVBoxLayout(title_group)
        title_layout.setContentsMargins(0,0,0,0)
        title_layout.setSpacing(2)
        
        title = QLabel("AvatarWebcam")
        title.setObjectName("headerTitle")
        subtitle = QLabel("Spoutカメラ出力を仮想カメラへ")
        subtitle.setObjectName("headerSubtitle")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        # Status Badge (Top Right)
        status_container = QFrame()
        status_container.setObjectName("statusContainer")
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        
        self._status_badge = StatusBadge()
        self._status_text = QLabel("準備完了")
        self._status_text.setObjectName("statusLabel")
        self._status_text.setStyleSheet("color: #9ca0b0; font-size: 13px;")

        status_layout.addStretch()
        status_layout.addWidget(self._status_badge)
        status_layout.addWidget(self._status_text)

        header_layout.addWidget(title_group)
        header_layout.addWidget(status_container)
        
        root_layout.addWidget(header)

        # --- Preview & Main Action ---
        main_card = QFrame()
        main_card.setProperty("class", "card")
        main_layout = QVBoxLayout(main_card)
        main_layout.setContentsMargins(12, 12, 12, 16)
        main_layout.setSpacing(12)

        # Preview Area
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0,0,0,0)
        preview_layout.setSpacing(8)
        
        lbl_preview = QLabel("プレビュー")
        lbl_preview.setObjectName("sectionTitle")
        preview_layout.addWidget(lbl_preview)

        self._preview_label = QLabel("信号なし")
        self._preview_label.setObjectName("previewCanvas")
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setFixedSize(*self.PREVIEW_SIZE)
        
        # Add shadow to preview
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self._preview_label.setGraphicsEffect(shadow)

        # Wrap preview in a centering layout
        p_center = QHBoxLayout()
        p_center.addStretch()
        p_center.addWidget(self._preview_label)
        p_center.addStretch()
        preview_layout.addLayout(p_center)
        
        main_layout.addWidget(preview_container)
        
        # Source Control
        src_label = QLabel("映像ソース")
        src_label.setObjectName("sectionTitle")
        main_layout.addWidget(src_label)

        src_row = QHBoxLayout()
        self._source_combo = QComboBox()
        self._source_combo.addItem("自動検出 (VRChat)")
        self._source_combo.currentTextChanged.connect(self._on_source_change)
        self._source_combo.setMinimumHeight(42)
        self._source_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._refresh_btn = QPushButton("↻")
        self._refresh_btn.setObjectName("iconButton")
        self._refresh_btn.setToolTip("ソースリスト更新")
        self._refresh_btn.clicked.connect(self._refresh_sources)

        src_row.addWidget(self._source_combo)
        src_row.addWidget(self._refresh_btn)
        main_layout.addLayout(src_row)

        # Hero Button
        self._start_btn = QPushButton("仮想カメラ開始")
        self._start_btn.setObjectName("heroButton")
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.setFixedHeight(50)
        self._start_btn.clicked.connect(self._toggle_bridge)
        main_layout.addWidget(self._start_btn)
        
        root_layout.addWidget(main_card)

        # --- Settings Panel ---
        self._settings_card = QFrame()
        self._settings_card.setProperty("class", "card")
        stg_layout = QVBoxLayout(self._settings_card)
        stg_layout.setContentsMargins(16, 12, 16, 12)
        stg_layout.setSpacing(8)

        stg_title = QLabel("設定")
        stg_title.setObjectName("sectionTitle")
        stg_layout.addWidget(stg_title)

        # Resolution
        res_row = QHBoxLayout()
        res_row.setSpacing(10)
        res_label = QLabel("解像度:")
        res_label.setStyleSheet("color: #a6adc8;")
        res_row.addWidget(res_label)
        
        self._resolution_combo = QComboBox()
        for label, value in self.RESOLUTION_CHOICES:
            self._resolution_combo.addItem(label, value)
        self._resolution_combo.currentIndexChanged.connect(self._on_resolution_change)
        self._resolution_combo.setMinimumWidth(160)
        res_row.addWidget(self._resolution_combo)
        res_row.addStretch()
        stg_layout.addLayout(res_row)
        
        # Checkboxes
        self._auto_start_checkbox = QCheckBox("Spoutカメラ検出時に自動開始")
        self._auto_start_checkbox.toggled.connect(self._on_auto_start_toggle)
        stg_layout.addWidget(self._auto_start_checkbox)

        self._windows_autostart_checkbox = QCheckBox("PC起動時に自動実行")
        self._windows_autostart_checkbox.toggled.connect(self._on_windows_autostart_toggle)
        stg_layout.addWidget(self._windows_autostart_checkbox)

        self._start_in_tray_on_launch_checkbox = QCheckBox("起動時にトレイに格納")
        self._start_in_tray_on_launch_checkbox.toggled.connect(
            self._on_start_in_tray_on_launch_toggle
        )
        stg_layout.addWidget(self._start_in_tray_on_launch_checkbox)

        self._close_to_tray_checkbox = QCheckBox("アプリ終了時にトレイに格納")
        self._close_to_tray_checkbox.toggled.connect(self._on_close_to_tray_toggle)
        stg_layout.addWidget(self._close_to_tray_checkbox)

        root_layout.addWidget(self._settings_card)
        root_layout.addStretch()
        
        # Footer Info
        footer = QHBoxLayout()
        self._fps_label = QLabel("")
        self._fps_label.setStyleSheet("color: #585b70; font-size: 11px;")
        footer.addStretch()
        footer.addWidget(self._fps_label)
        root_layout.addLayout(footer)

    def _make_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        # Deprecated helper, kept for interface comp if needed, but not used in new build
        pass

    # --- Properties Sync ---
    def _apply_settings_to_controls(self):
        self._auto_start_checkbox.blockSignals(True)
        self._auto_start_checkbox.setChecked(self._auto_start_enabled)
        self._auto_start_checkbox.blockSignals(False)

        self._windows_autostart_checkbox.blockSignals(True)
        self._windows_autostart_checkbox.setChecked(self._windows_autostart_enabled)
        self._windows_autostart_checkbox.blockSignals(False)

        self._start_in_tray_on_launch_checkbox.blockSignals(True)
        self._start_in_tray_on_launch_checkbox.setChecked(
            self._start_in_tray_on_launch_enabled
        )
        self._start_in_tray_on_launch_checkbox.blockSignals(False)

        self._close_to_tray_checkbox.blockSignals(True)
        self._close_to_tray_checkbox.setChecked(self._close_to_tray_enabled)
        self._close_to_tray_checkbox.blockSignals(False)

        self._resolution_combo.blockSignals(True)
        for i in range(self._resolution_combo.count()):
            if self._resolution_combo.itemData(i) == self._resolution_value:
                self._resolution_combo.setCurrentIndex(i)
                break
        self._resolution_combo.blockSignals(False)

    # --- Actions ---
    def _toggle_bridge(self):
        if self._bridge.is_running():
            self._stop_bridge()
        else:
            self._start_bridge()

    def _start_bridge(self):
        source = self._source_combo.currentText().strip()
        # "Auto Detect" -> "自動検出"
        if source == "" or "自動検出" in source or "Auto Detect" in source or "VRChat" in source:
            self._bridge.set_target_source(None) # Auto
        else:
            self._bridge.set_target_source(source)

        self._bridge.set_resolution(self._resolution_value)
        self._set_running_ui(True)
        self._bridge.start()

    def _stop_bridge(self):
        self._bridge.stop()
        self._set_running_ui(False)
        self._clear_preview()

    def _set_running_ui(self, running: bool):
        if running:
            self._start_btn.setText("仮想カメラ停止")
            self._start_btn.setProperty("active", True)
            self._source_combo.setEnabled(False)
            self._refresh_btn.setEnabled(False)
            self._settings_card.setEnabled(False) # Lock settings while running
            self._settings_card.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=0)) # visual cue
            self._settings_card.setStyleSheet("QFrame[class='card'] { background-color: #e6e9ef; border: 1px solid #bcc0cc; }")
        else:
            self._start_btn.setText("仮想カメラ開始")
            self._start_btn.setProperty("active", False)
            self._source_combo.setEnabled(True)
            self._refresh_btn.setEnabled(True)
            self._settings_card.setEnabled(True)
            self._settings_card.setStyleSheet("") # Reset

        # Reflow styles
        self._start_btn.style().unpolish(self._start_btn)
        self._start_btn.style().polish(self._start_btn)
        self._update_state_timer_interval()
    
    def _update_state_timer_interval(self):
        if not hasattr(self, "_state_timer"):
            return
        if self._bridge.is_running():
            interval = self._state_timer_interval_running_ms
        elif self.isVisible():
            interval = self._state_timer_interval_idle_visible_ms
        else:
            interval = self._state_timer_interval_idle_hidden_ms
        if self._state_timer.interval() != interval:
            self._state_timer.setInterval(interval)

    def _on_bridge_state(self, state: BridgeState):
        self._state_queue.put(state)

    def _update_state(self):
        try:
            while True:
                state = self._state_queue.get_nowait()
                self._apply_state(state)
        except Empty:
            pass

    def _apply_state(self, state: BridgeState):
        self._status_text.setText(state.message)

        # Colors from palette (Latte)
        colors = {
            BridgeStatus.STOPPED: "#9ca0b0", # Gray
            BridgeStatus.WAITING: "#df8e1d", # Yellow
            BridgeStatus.RUNNING: "#40a02b", # Green
            BridgeStatus.ERROR: "#d20f39",   # Red
        }
        color = colors.get(state.status, "#9ca0b0")
        self._status_badge.set_color(color)
        self._status_text.setStyleSheet(f"color: {color}; font-weight: 600;")

        if state.fps > 0:
            self._fps_label.setText(f"FPS: {state.fps:.1f}")
        else:
             self._fps_label.setText("")

        if state.frame is not None:
            self._update_preview(state.frame)
        
        if state.status == BridgeStatus.STOPPED:
            self._set_running_ui(False)
            self._clear_preview()

    def _update_preview(self, frame: np.ndarray):
        try:
            if not frame.flags["C_CONTIGUOUS"]:
                frame = np.ascontiguousarray(frame)
            height, width, _ = frame.shape
            image = QImage(frame.data, width, height, 3 * width, QImage.Format_RGB888).copy()

            target_w, target_h = self.PREVIEW_SIZE
            scaled = image.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Draw rounded frame
            canvas = QPixmap(target_w, target_h)
            canvas.fill(Qt.transparent)
             
            # Center image
            x = (target_w - scaled.width()) // 2
            y = (target_h - scaled.height()) // 2
            
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Create rounded path
            path = QPainterPath()
            path.addRoundedRect(0, 0, target_w, target_h, 8, 8)
            painter.setClipPath(path)
            
            # Draw black bg then image
            painter.fillRect(0,0,target_w, target_h, QColor("#000000"))
            painter.drawImage(x, y, scaled)
            painter.end()

            self._preview_pixmap = canvas
            self._preview_label.setPixmap(self._preview_pixmap)
            self._preview_label.setText("")
        except Exception:
            pass

    def _clear_preview(self):
        self._preview_label.setPixmap(QPixmap())
        self._preview_label.setText("信号なし")
        self._preview_pixmap = None

    def _refresh_sources(self):
        sources = ["自動検出 (VRChat)"]
        try:
            sender_list = self._bridge.get_sender_list()
            sources.extend(sender_list)
        except Exception:
            pass

        current = self._source_combo.currentText()
        self._source_combo.blockSignals(True)
        self._source_combo.clear()
        self._source_combo.addItems(sources)
        if current in sources:
            self._source_combo.setCurrentText(current)
        else:
            self._source_combo.setCurrentIndex(0)
        self._source_combo.blockSignals(False)
        self._update_auto_controls()

    # --- Settings Logic (Same as before) ---
    def _settings_path(self) -> Path:
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "AvatarWebcam" / "settings.json"
        return Path.home() / "AppData" / "Roaming" / "AvatarWebcam" / "settings.json"

    def _load_settings(self) -> dict:
        path = self._settings_path()
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to load settings: %s", e)
        return {}

    def _save_settings(self):
        path = self._settings_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "auto_start_enabled": self._auto_start_enabled,
                "windows_autostart_enabled": self._windows_autostart_enabled,
                "start_in_tray_on_launch": self._start_in_tray_on_launch_enabled,
                "close_to_tray": self._close_to_tray_enabled,
                "start_in_tray": self._start_in_tray_on_launch_enabled or self._close_to_tray_enabled,
                "resolution": self._resolution_value,
            }
            path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save settings: %s", e)

    def _is_auto_detect_selected(self) -> bool:
        text = self._source_combo.currentText()
        return "Auto Detect" in text or "自動検出" in text

    def _update_auto_controls(self):
        auto_detect = self._is_auto_detect_selected()
        if not auto_detect:
            if self._auto_start_enabled:
                self._auto_start_enabled = False
                self._auto_start_checkbox.blockSignals(True)
                self._auto_start_checkbox.setChecked(False)
                self._auto_start_checkbox.blockSignals(False)
                self._stop_auto_monitor()
                self._save_settings()
            self._auto_start_checkbox.setEnabled(False)
            return
        self._auto_start_checkbox.setEnabled(True)

    def _on_source_change(self, _value: str):
        self._update_auto_controls()

    def _on_auto_start_toggle(self, checked: bool):
        self._auto_start_enabled = checked
        if checked:
            if self._is_auto_detect_selected():
                self._start_auto_monitor()
            else:
                self._auto_start_enabled = False
                self._auto_start_checkbox.setChecked(False)
        else:
            self._stop_auto_monitor()
        self._update_auto_controls()
        self._save_settings()

    def _on_windows_autostart_toggle(self, checked: bool):
        if not self._set_windows_autostart(checked):
            self._windows_autostart_checkbox.blockSignals(True)
            self._windows_autostart_checkbox.setChecked(not checked) # Revert
            self._windows_autostart_checkbox.blockSignals(False)
            return
        self._windows_autostart_enabled = checked
        self._update_startup_controls()
        self._save_settings()

    def _on_start_in_tray_on_launch_toggle(self, checked: bool):
        self._start_in_tray_on_launch_enabled = checked
        self._update_startup_controls()
        self._save_settings()

    def _on_close_to_tray_toggle(self, checked: bool):
        self._close_to_tray_enabled = checked
        self._update_startup_controls()
        self._save_settings()

    def _on_resolution_change(self):
        self._resolution_value = self._resolution_combo.currentData()
        self._save_settings()
        # If running, we might want to restart bridge or just let it apply next time?
        # Current logic doesn't dynamic update resolution while running, which is fine.

    def _start_auto_monitor(self):
        if self._auto_monitor_timer is None:
            self._auto_monitor_timer = QTimer(self)
            self._auto_monitor_timer.setSingleShot(True)
            self._auto_monitor_timer.timeout.connect(self._check_vrc_source)
        if not self._auto_monitor_timer.isActive():
            self._check_vrc_source()

    def _stop_auto_monitor(self):
        if self._auto_monitor_timer:
            self._auto_monitor_timer.stop()

    def _check_vrc_source(self):
        if not self._auto_start_enabled or not self._is_auto_detect_selected():
            self._stop_auto_monitor()
            return

        vrc_running = self._is_vrchat_running_cached()
        interval = self._monitor_interval_active_ms if vrc_running else self._monitor_interval_idle_ms
        
        if not vrc_running:
            if self._auto_monitor_timer:
                self._auto_monitor_timer.start(interval)
            return

        if not self._bridge.is_running():
            sources = []
            try:
                sources = self._bridge.get_sender_list()
            except: pass
            
            # Simple check for any source if Auto
            if sources:
                self._start_bridge()

        if self._auto_monitor_timer:
            self._auto_monitor_timer.start(interval)

    def _is_vrchat_running_cached(self) -> bool:
        now = time.monotonic()
        ttl = self._vrchat_cache_ttl_active_s if self._bridge.is_running() else self._vrchat_cache_ttl_idle_s
        if self._vrchat_running_cache is not None and (now - self._vrchat_last_check) < ttl:
            return self._vrchat_running_cache
        result = self._is_vrchat_running()
        self._vrchat_running_cache = result
        self._vrchat_last_check = now
        return result

    def _is_vrchat_running(self) -> bool:
        try:
            # Simple faster check using tasklist
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq VRChat.exe", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return "VRChat.exe" in result.stdout
        except Exception:
            pass
        return False

    def _update_startup_controls(self):
        tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        if not tray_available:
            self._start_in_tray_on_launch_checkbox.setEnabled(False)
            self._close_to_tray_checkbox.setEnabled(False)
            return
        self._start_in_tray_on_launch_checkbox.setEnabled(True)
        self._close_to_tray_checkbox.setEnabled(True)

    def _autostart_command(self) -> str:
        exe_path = Path(sys.executable).resolve()
        # If running as python script
        if exe_path.name.lower().startswith("python"):
            script_path = Path(sys.argv[0]).resolve().parent / "main.py"
            return f'"{exe_path}" "{script_path}" {self.AUTOSTART_ARG}'
        # If frozen exe
        return f'"{exe_path}" {self.AUTOSTART_ARG}'

    def _is_windows_autostart_enabled(self) -> bool:
        if os.name != "nt": return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.RUN_KEY, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, self.RUN_VALUE_NAME)
            return bool(value)
        except:
            return False

    def _set_windows_autostart(self, enabled: bool) -> bool:
        if os.name != "nt": return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, self.RUN_VALUE_NAME, 0, winreg.REG_SZ, self._autostart_command())
                else:
                    try:
                        winreg.DeleteValue(key, self.RUN_VALUE_NAME)
                    except FileNotFoundError: pass
            return True
        except Exception as e:
            logger.warning("Failed to set autostart: %s", e)
            return False

    def _maybe_start_in_tray(self):
        if not self._start_in_tray_on_launch_enabled:
            return
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._start_tray_icon()
        self._start_hidden_in_tray = True
        self.setWindowOpacity(0.0)

    def _start_tray_icon(self):
        if self._tray_icon is not None: return
        
        menu = QMenu()
        menu.setStyleSheet(APP_QSS) # Attempt to style menu
        
        show_action = menu.addAction("AvatarWebcam を表示")
        show_action.triggered.connect(self._restore_window)
        
        menu.addSeparator()
        
        exit_action = menu.addAction("終了")
        exit_action.triggered.connect(self._on_tray_exit)
        
        self._tray_menu = menu
        self._tray_icon = QSystemTrayIcon(self._build_app_icon(), self)
        self._tray_icon.setToolTip("AvatarWebcam")
        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _install_shutdown_handler(self):
        if os.name != "nt":
            return
        if QCoreApplication.instance() is None:
            return
        if self._native_event_filter is None:
            self._native_event_filter = _WindowsShutdownFilter(self._on_system_shutdown)
            QCoreApplication.instance().installNativeEventFilter(self._native_event_filter)

    def _on_system_shutdown(self):
        if self._shutdown_requested:
            return
        self._shutdown_requested = True
        self._allow_exit = True
        self.close()

    def _stop_tray_icon(self):
        if self._tray_icon:
            self._tray_icon.hide()
            self._tray_icon = None

    def _build_app_icon(self) -> QIcon:
        # Simple icon: camera body with a "V" cutout
        size = 128
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        bg_color = QColor(30, 30, 46)
        accent = QColor(137, 180, 250)
        accent_dark = QColor(17, 17, 27)

        # Background Container (Rounded Square)
        rect = QRect(8, 8, size - 16, size - 16)
        painter.setBrush(bg_color)
        painter.setPen(QPen(accent, 6))
        painter.drawRoundedRect(rect, 22, 22)

        # Camera body (big, simple)
        painter.setPen(Qt.NoPen)
        painter.setBrush(accent)
        body = QRect(24, 50, 80, 44)
        painter.drawRoundedRect(body, 10, 10)
        painter.drawRoundedRect(QRect(48, 40, 32, 12), 6, 6)  # top bump

        # "VR" text inside camera body
        painter.setPen(accent_dark)
        font = QFont("Segoe UI", 28, QFont.Bold)
        painter.setFont(font)
        painter.drawText(body, Qt.AlignCenter, "VR")

        painter.end()
        return QIcon(pixmap)

    def _hide_to_tray(self):
        self.hide()
        if not self._tray_icon:
            self._start_tray_icon()
        
        if self._tray_icon:
            self._tray_icon.showMessage(
                "AvatarWebcam",
                "バックグラウンドで実行中",
                QSystemTrayIcon.Information,
                2000
            )
        self._update_state_timer_interval()

    def _restore_window(self):
        self.show()
        self.setWindowOpacity(1.0)
        self.activateWindow()
        self._has_shown = True
        self._update_state_timer_interval()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self._restore_window()

    def _on_tray_exit(self):
        self._allow_exit = True
        self.close()

    def _on_close(self):
        pass # Handle in closeEvent

def run_app():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AvatarWebcam")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_QSS)

    # Single Instance Check
    shared_mem = QSharedMemory("AvatarWebcam_Unique_Key_2026")
    if not shared_mem.create(1):
        # Already running
        msg = QMessageBox()
        msg.setWindowTitle("AvatarWebcam")
        msg.setText("アプリは既に起動しています。")
        msg.setInformativeText("既に起動しているインスタンスを使用してください。")
        msg.setIcon(QMessageBox.Warning)
        msg.exec()
        sys.exit(0)

    # Store shared_mem in app to keep it alive
    app._single_instance_lock = shared_mem

    window = AvatarWebcamApp()
    app.setWindowIcon(window.windowIcon())
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    run_app()
