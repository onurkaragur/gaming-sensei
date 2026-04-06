"""
Right Panel Widget
Displays the full Japanese sentence and English translation.
"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QFrame, QSizePolicy, QScrollArea
)

logger = logging.getLogger(__name__)


class SentencePanel(QWidget):
    """
    Right panel: displays original Japanese text and English translation.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Section header
        header = QLabel("Sentence & Translation")
        header.setStyleSheet("""
            QLabel {
                color: #7a9fc0;
                font-size: 11px;
                font-family: 'Consolas', monospace;
                letter-spacing: 2px;
                padding: 12px 16px 8px 16px;
                border-bottom: 1px solid #1a2535;
            }
        """)
        layout.addWidget(header)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: #0d1520;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #2a3f5a;
                border-radius: 3px;
            }
        """)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Original Japanese ---
        jp_section_label = _SectionLabel("原文  /  Original")
        content_layout.addWidget(jp_section_label)

        self._japanese_display = _TextBox(
            font_size=20,
            color="#e8f4ff",
            placeholder="Japanese text will appear here...",
            font_family="Noto Serif CJK JP, serif",
        )
        content_layout.addWidget(self._japanese_display)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #1e2f45; margin: 4px 0;")
        content_layout.addWidget(divider)

        # --- English Translation ---
        en_section_label = _SectionLabel("翻訳  /  Translation")
        content_layout.addWidget(en_section_label)

        self._translation_display = _TextBox(
            font_size=15,
            color="#b8d4f0",
            placeholder="English translation will appear here...",
            font_family="Georgia, serif",
            italic=True,
        )
        content_layout.addWidget(self._translation_display)

        # Confidence / metadata area
        self._meta_label = QLabel("")
        self._meta_label.setStyleSheet("""
            QLabel {
                color: #3a5070;
                font-size: 10px;
                font-family: 'Consolas', monospace;
                padding-top: 8px;
            }
        """)
        content_layout.addWidget(self._meta_label)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def display_sentence(self, japanese: str, translation: str, ocr_confidence: float = None):
        """
        Update the displayed sentence and translation.

        Args:
            japanese: Original Japanese text.
            translation: English translation.
            ocr_confidence: Average OCR confidence (optional, for display).
        """
        self._japanese_display.set_text(japanese)
        self._translation_display.set_text(translation)

        if ocr_confidence is not None:
            self._meta_label.setText(f"OCR confidence: {ocr_confidence:.0%}")
        else:
            self._meta_label.setText("")

    def show_loading(self, stage: str = "Processing"):
        """Show a loading/progress message."""
        self._japanese_display.set_text("")
        self._translation_display.set_text(f"⟳ {stage}...")
        self._meta_label.setText("")

    def show_error(self, message: str):
        """Display an error message."""
        self._japanese_display.set_text("")
        self._translation_display.set_text(f"⚠ {message}")
        self._meta_label.setText("")

    def clear(self):
        """Reset to empty state."""
        self._japanese_display.set_text("")
        self._translation_display.set_text("")
        self._meta_label.setText("")


class _SectionLabel(QLabel):
    """Small section header label."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QLabel {
                color: #4a7090;
                font-size: 10px;
                font-family: 'Consolas', monospace;
                letter-spacing: 1px;
            }
        """)


class _TextBox(QLabel):
    """Multi-line text display box with styled background."""

    def __init__(
        self,
        font_size: int,
        color: str,
        placeholder: str,
        font_family: str = "serif",
        italic: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._placeholder = placeholder
        self._font_size = font_size
        self._color = color
        self._font_family = font_family
        self._italic = italic

        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._apply_style(is_placeholder=True)
        self.setText(placeholder)

    def set_text(self, text: str):
        """Update displayed text."""
        if text:
            self.setText(text)
            self._apply_style(is_placeholder=False)
        else:
            self.setText(self._placeholder)
            self._apply_style(is_placeholder=True)

    def _apply_style(self, is_placeholder: bool):
        color = "#3a5070" if is_placeholder else self._color
        italic = "italic" if (self._italic or is_placeholder) else "normal"
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: {self._font_size}px;
                font-family: {self._font_family};
                font-style: {italic};
                background: #131d2b;
                border: 1px solid #1a2a3c;
                border-radius: 6px;
                padding: 12px 14px;
                line-height: 1.6;
            }}
        """)
