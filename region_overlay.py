"""
Region Overlay Widget
Full-screen transparent overlay for rubber-band region selection.
"""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor
from PyQt6.QtWidgets import QDialog, QApplication

from capture.screen_capture import CaptureRegion

logger = logging.getLogger(__name__)


class RegionOverlay(QDialog):
    """
    Full-screen semi-transparent overlay for selecting a screen region.
    User clicks and drags to define the capture area.
    """

    OVERLAY_COLOR = QColor(0, 0, 0, 100)        # Semi-transparent black
    SELECTION_COLOR = QColor(100, 180, 255, 50)  # Semi-transparent blue fill
    BORDER_COLOR = QColor(100, 180, 255, 255)    # Solid blue border
    GUIDE_COLOR = QColor(255, 255, 255, 160)     # White guide text

    def __init__(self):
        super().__init__()
        self._origin: Optional[QPoint] = None
        self._current: Optional[QPoint] = None
        self.selected_region: Optional[CaptureRegion] = None
        self._setup_ui()

    def _setup_ui(self):
        """Configure the overlay window."""
        # Full screen, frameless, always on top, transparent
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Cover all screens
        screen_geo = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen_geo)

        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._current = self._origin
            self.update()

    def mouseMoveEvent(self, event):
        if self._origin:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._origin:
            self._current = event.position().toPoint()
            self._finalize_selection()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            logger.info("Region selection cancelled by user")
            self.selected_region = None
            self.reject()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw dark overlay over entire screen
        painter.fillRect(self.rect(), self.OVERLAY_COLOR)

        # Draw selection rectangle
        if self._origin and self._current:
            sel_rect = self._get_selection_rect()

            # Clear (lighter) fill inside selection
            painter.fillRect(sel_rect, self.SELECTION_COLOR)

            # Draw border
            pen = QPen(self.BORDER_COLOR, 2)
            painter.setPen(pen)
            painter.drawRect(sel_rect)

            # Draw size label
            w = sel_rect.width()
            h = sel_rect.height()
            painter.setPen(QPen(self.GUIDE_COLOR))
            label = f"{w} × {h}"
            painter.drawText(sel_rect.bottomRight() + QPoint(6, -4), label)

        # Draw instruction text
        painter.setPen(QPen(QColor(255, 255, 255, 200)))
        font = painter.font()
        font.setPointSize(14)
        painter.setFont(font)
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
            "  Click and drag to select region  |  ESC to cancel  ",
        )

        painter.end()

    def _get_selection_rect(self) -> QRect:
        """Return normalized selection rectangle."""
        if not self._origin or not self._current:
            return QRect()
        return QRect(self._origin, self._current).normalized()

    def _finalize_selection(self):
        """Convert selected rectangle to CaptureRegion and close."""
        rect = self._get_selection_rect()
        if rect.width() > 10 and rect.height() > 10:
            self.selected_region = CaptureRegion(
                x=rect.x(),
                y=rect.y(),
                width=rect.width(),
                height=rect.height(),
            )
            logger.info(f"Region selected: {self.selected_region}")
            self.accept()
        else:
            logger.warning("Selected region too small, ignoring")
            self.selected_region = None
            self.reject()
