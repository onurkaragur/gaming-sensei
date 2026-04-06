"""
Word Card Widget
Displays a single word with furigana, reading, and English meaning.
Supports hover for extended definition popup.
"""

import logging
from typing import List, Tuple

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QFontMetrics, QPainterPath
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QToolTip, QSizePolicy, QFrame
)

from nlp.furigana import FuriganaWord

logger = logging.getLogger(__name__)


class FuriganaLabel(QWidget):
    """
    Custom widget that renders text with furigana (ruby text) above kanji.
    """

    def __init__(self, word: FuriganaWord, parent=None):
        super().__init__(parent)
        self._word = word
        self._segments = word.segments or [(word.surface, "")]

        # Fonts
        self._surface_font = QFont("Noto Serif CJK JP", 18)
        self._furigana_font = QFont("Noto Serif CJK JP", 9)

        self._surface_metrics = QFontMetrics(self._surface_font)
        self._furigana_metrics = QFontMetrics(self._furigana_font)

        self.setMinimumHeight(52)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        total_w = sum(
            max(
                self._surface_metrics.horizontalAdvance(surf),
                self._furigana_metrics.horizontalAdvance(furi) if furi else 0
            )
            for surf, furi in self._segments
        ) + 8
        return QSize(max(total_w, 40), 52)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        x = 4
        furigana_y = self._furigana_metrics.ascent() + 2
        surface_y = furigana_y + self._furigana_metrics.descent() + 2 + self._surface_metrics.ascent()

        for surface_text, furigana_text in self._segments:
            surf_w = self._surface_metrics.horizontalAdvance(surface_text)
            furi_w = self._furigana_metrics.horizontalAdvance(furigana_text) if furigana_text else 0
            seg_w = max(surf_w, furi_w)

            # Draw furigana (small, above)
            if furigana_text:
                painter.setFont(self._furigana_font)
                painter.setPen(QColor("#8899aa"))
                furi_x = x + (seg_w - furi_w) // 2
                painter.drawText(furi_x, furigana_y, furigana_text)

            # Draw surface text
            painter.setFont(self._surface_font)
            painter.setPen(QColor("#e8e8e8"))
            surf_x = x + (seg_w - surf_w) // 2
            painter.drawText(surf_x, surface_y, surface_text)

            x += seg_w + 2

        painter.end()


class WordCard(QFrame):
    """
    Card widget showing a word with:
    - Furigana reading above kanji
    - POS badge
    - English meaning
    - Hover tooltip with extended meanings
    """

    clicked = pyqtSignal(str)  # Emits base_form on click

    # POS color map
    POS_COLORS = {
        "名詞": "#4a9eff",    # Noun → blue
        "動詞": "#ff6b6b",    # Verb → red
        "形容詞": "#ffd93d",  # Adjective → yellow
        "副詞": "#6bffb8",    # Adverb → green
        "助詞": "#888888",    # Particle → gray
        "助動詞": "#aaaaaa",  # Auxiliary → light gray
        "接続詞": "#cc99ff",  # Conjunction → purple
    }
    DEFAULT_POS_COLOR = "#666666"

    def __init__(self, word: FuriganaWord, extra_meanings: List[str] = None, parent=None):
        super().__init__(parent)
        self._word = word
        self._extra_meanings = extra_meanings or []
        self._setup_ui()
        self._setup_tooltip()

    def _setup_ui(self):
        self.setObjectName("wordCard")
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Furigana + surface
        furigana_label = FuriganaLabel(self._word)
        layout.addWidget(furigana_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # POS badge
        pos_color = self.POS_COLORS.get(self._word.part_of_speech, self.DEFAULT_POS_COLOR)
        pos_label = QLabel(self._word.part_of_speech or "—")
        pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pos_label.setStyleSheet(f"""
            QLabel {{
                color: {pos_color};
                font-size: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                border: 1px solid {pos_color}44;
                border-radius: 3px;
                padding: 1px 4px;
            }}
        """)
        layout.addWidget(pos_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # English meaning
        meaning = self._word.meaning or "—"
        meaning_label = QLabel(meaning)
        meaning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meaning_label.setWordWrap(True)
        meaning_label.setStyleSheet("""
            QLabel {
                color: #b0c4de;
                font-size: 12px;
                font-style: italic;
            }
        """)
        layout.addWidget(meaning_label)

        self.setStyleSheet("""
            QFrame#wordCard {
                background: #1e2a3a;
                border: 1px solid #2a3f5a;
                border-radius: 8px;
            }
            QFrame#wordCard:hover {
                border: 1px solid #4a9eff;
                background: #243040;
            }
        """)
        self.setFixedWidth(120)

    def _setup_tooltip(self):
        """Build rich tooltip with extended meanings."""
        if self._extra_meanings:
            tip_lines = [f"<b>{self._word.surface}</b> ({self._word.reading})<br>"]
            tip_lines += [f"• {m}" for m in self._extra_meanings[:5]]
            self.setToolTip("<br>".join(tip_lines))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._word.base_form)
        super().mousePressEvent(event)
