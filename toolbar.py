"""
Toolbar and Status Components
Top toolbar with action buttons and bottom status bar.
"""

import logging
from typing import Callable, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFrame, QSizePolicy
)

logger = logging.getLogger(__name__)


class Toolbar(QWidget):
    """
    Top toolbar with action buttons.
    Emits signals on button clicks.
    """

    capture_requested = pyqtSignal()
    translate_requested = pyqtSignal()
    recapture_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # App title
        title = QLabel("日本語 OCR")
        title.setStyleSheet("""
            QLabel {
                color: #4a9eff;
                font-size: 16px;
                font-family: 'Noto Serif CJK JP', serif;
                font-weight: bold;
            }
        """)
        layout.addWidget(title)

        subtitle = QLabel("Translation Assistant")
        subtitle.setStyleSheet("""
            QLabel {
                color: #3a5070;
                font-size: 11px;
                font-family: 'Consolas', monospace;
                padding-left: 4px;
            }
        """)
        layout.addWidget(subtitle)
        layout.addStretch()

        # Recapture button (re-use last region)
        self._recapture_btn = _ToolButton(
            text="↺  Recapture",
            tooltip="Re-capture the previously selected region",
            style="secondary",
        )
        self._recapture_btn.clicked.connect(self.recapture_requested)
        self._recapture_btn.setEnabled(False)
        layout.addWidget(self._recapture_btn)

        # Select Area button
        self._capture_btn = _ToolButton(
            text="⊞  Select Area",
            tooltip="Click and drag to select a screen region for OCR",
            style="primary",
        )
        self._capture_btn.clicked.connect(self.capture_requested)
        layout.addWidget(self._capture_btn)

        self.setStyleSheet("""
            QWidget {
                background: #0f1b28;
                border-bottom: 1px solid #1a2535;
            }
        """)

    def enable_recapture(self, enabled: bool = True):
        """Enable/disable the recapture button."""
        self._recapture_btn.setEnabled(enabled)

    def set_processing(self, processing: bool):
        """Update button states during processing."""
        self._capture_btn.setEnabled(not processing)
        self._recapture_btn.setEnabled(not processing and self._recapture_btn.isEnabled())


class StatusBar(QWidget):
    """
    Bottom status bar showing current operation status.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._clear_temp)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        # Status indicator dot
        self._dot = QLabel("●")
        self._dot.setFixedWidth(12)
        self._dot.setStyleSheet("color: #2a4060; font-size: 8px;")
        layout.addWidget(self._dot)

        # Status message
        self._status_label = QLabel("Ready — select a screen region to begin")
        self._status_label.setStyleSheet("""
            QLabel {
                color: #3a5070;
                font-size: 11px;
                font-family: 'Consolas', monospace;
            }
        """)
        layout.addWidget(self._status_label)
        layout.addStretch()

        # Version label
        version = QLabel("v1.0.0")
        version.setStyleSheet("color: #1e3050; font-size: 10px; font-family: 'Consolas', monospace;")
        layout.addWidget(version)

        self.setFixedHeight(32)
        self.setStyleSheet("""
            QWidget {
                background: #080f18;
                border-top: 1px solid #1a2535;
            }
        """)

    def set_status(self, message: str, status_type: str = "info", temporary: bool = False):
        """
        Update status message.

        Args:
            message: Status text.
            status_type: One of "info", "success", "warning", "error", "processing"
            temporary: If True, revert to "Ready" after 3 seconds.
        """
        colors = {
            "info": ("#3a5070", "#3a5070"),
            "success": ("#4aff9e", "#2a9060"),
            "warning": ("#ffd93d", "#a08020"),
            "error": ("#ff6b6b", "#902020"),
            "processing": ("#4a9eff", "#1a4080"),
        }
        dot_color, text_color = colors.get(status_type, colors["info"])

        self._dot.setStyleSheet(f"color: {dot_color}; font-size: 8px;")
        self._status_label.setText(message)
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: 11px;
                font-family: 'Consolas', monospace;
            }}
        """)

        if temporary:
            self._timer.start(3000)

    def _clear_temp(self):
        self.set_status("Ready", "info")


class _ToolButton(QPushButton):
    """Styled toolbar button."""

    PRIMARY_STYLE = """
        QPushButton {
            background: #1a4a8a;
            color: #90c8ff;
            border: 1px solid #2a6aaa;
            border-radius: 5px;
            padding: 6px 16px;
            font-size: 12px;
            font-family: 'Consolas', monospace;
        }
        QPushButton:hover {
            background: #1e5aaa;
            border-color: #4a9eff;
            color: #c0e0ff;
        }
        QPushButton:pressed { background: #0f3060; }
        QPushButton:disabled { background: #0a1a2a; color: #2a3f55; border-color: #1a2535; }
    """
    SECONDARY_STYLE = """
        QPushButton {
            background: #0f1b28;
            color: #3a6080;
            border: 1px solid #1e3048;
            border-radius: 5px;
            padding: 6px 16px;
            font-size: 12px;
            font-family: 'Consolas', monospace;
        }
        QPushButton:hover { background: #162535; border-color: #2a5070; color: #5a90b0; }
        QPushButton:pressed { background: #0a1520; }
        QPushButton:disabled { background: #080f18; color: #1a2535; border-color: #0f1b28; }
    """

    def __init__(self, text: str, tooltip: str = "", style: str = "primary", parent=None):
        super().__init__(text, parent)
        self.setToolTip(tooltip)
        self.setStyleSheet(self.PRIMARY_STYLE if style == "primary" else self.SECONDARY_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
