"""
Left Panel Widget
Scrollable word breakdown display showing furigana + meanings.
"""

import logging
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea,
    QLabel, QHBoxLayout, QFrame, QSizePolicy
)

from nlp.furigana import FuriganaWord
from ui.components.word_card import WordCard

logger = logging.getLogger(__name__)


class WordBreakdownPanel(QWidget):
    """
    Left panel: displays word-by-word breakdown with furigana and meanings.
    Words are arranged in a wrapping flow layout.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Section header
        header = QLabel("Word Breakdown")
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

        # Scroll area for word cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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

        # Container for cards
        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._cards_layout = FlowLayout(self._container, margin=12, spacing=8)

        scroll.setWidget(self._container)
        layout.addWidget(scroll)

        # Empty state label
        self._empty_label = QLabel("Capture a screen region to begin\nanalysis")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("""
            QLabel {
                color: #3a5070;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self._empty_label, stretch=1)

    def display_words(self, words: List[FuriganaWord], extra_meanings: dict = None):
        """
        Populate the panel with word cards.

        Args:
            words: List of FuriganaWord objects to display.
            extra_meanings: Dict mapping base_form → [str] for tooltips.
        """
        # Clear existing cards
        self._clear_cards()

        if not words:
            self._empty_label.setVisible(True)
            return

        self._empty_label.setVisible(False)

        extra = extra_meanings or {}
        for word in words:
            card = WordCard(
                word=word,
                extra_meanings=extra.get(word.base_form, []),
            )
            self._cards_layout.addWidget(card)

        logger.debug(f"Displayed {len(words)} word cards")

    def _clear_cards(self):
        """Remove all word cards from the layout."""
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def show_loading(self):
        """Show loading state."""
        self._clear_cards()
        self._empty_label.setText("Analyzing...")
        self._empty_label.setVisible(True)

    def show_error(self, message: str):
        """Show error state."""
        self._clear_cards()
        self._empty_label.setText(f"⚠ {message}")
        self._empty_label.setVisible(True)


class FlowLayout(object):
    """
    Simple flow layout that wraps items like words in a paragraph.
    Implemented as a helper that adds items to a QWidget with wrapping HBoxLayouts.
    """

    def __init__(self, parent: QWidget, margin: int = 8, spacing: int = 6):
        self._parent = parent
        self._margin = margin
        self._spacing = spacing
        self._items = []

        self._outer = QVBoxLayout(parent)
        self._outer.setContentsMargins(margin, margin, margin, margin)
        self._outer.setSpacing(spacing)
        self._outer.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._current_row: QHBoxLayout = self._new_row()

    def _new_row(self) -> QHBoxLayout:
        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(self._spacing)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._outer.addWidget(row_widget)
        return row

    def addWidget(self, widget: QWidget):
        # Every 5 cards, start a new row for readability
        if len(self._items) > 0 and len(self._items) % 5 == 0:
            self._current_row = self._new_row()
        self._current_row.addWidget(widget)
        self._items.append(widget)

    def count(self) -> int:
        return len(self._items)

    def takeAt(self, index: int):
        """Remove and return item at index."""
        if 0 <= index < len(self._items):
            widget = self._items.pop(index)

            class FakeItem:
                def __init__(self, w):
                    self._w = w
                def widget(self):
                    return self._w

            return FakeItem(widget)
        return None
