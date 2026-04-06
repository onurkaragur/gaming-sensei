"""
Main Application Window
Orchestrates all UI components and the processing pipeline.
"""

import logging
from typing import Optional

import numpy as np
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QSplitter, QFrame
)

from capture.screen_capture import ScreenCapture, RegionSelector, pil_to_numpy
from ocr.ocr_engine import OCREngine
from nlp.tokenizer import JapaneseTokenizer
from nlp.furigana import FuriganaProcessor
from nlp.dictionary import Dictionary
from translation.translator import Translator
from ui.components.toolbar import Toolbar, StatusBar
from ui.components.left_panel import WordBreakdownPanel
from ui.components.right_panel import SentencePanel
from ui.worker import ProcessingWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Root application window.

    Layout:
    ┌─────────────────────────────────────────┐
    │              Toolbar                     │
    ├────────────────────┬────────────────────┤
    │   Word Breakdown   │  Sentence +        │
    │   (Left Panel)     │  Translation       │
    │                    │  (Right Panel)     │
    ├─────────────────────────────────────────┤
    │              Status Bar                  │
    └─────────────────────────────────────────┘
    """

    MIN_WIDTH = 960
    MIN_HEIGHT = 600
    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 720

    def __init__(self):
        super().__init__()
        self._worker: Optional[ProcessingWorker] = None
        self._current_image: Optional[np.ndarray] = None

        # Initialize pipeline components (lazy loading inside each)
        self._screen_capture = ScreenCapture()
        self._region_selector = RegionSelector()
        self._ocr_engine = OCREngine()
        self._tokenizer = JapaneseTokenizer()
        self._furigana_processor = FuriganaProcessor()
        self._dictionary = Dictionary()
        self._translator = Translator()

        self._setup_window()
        self._setup_ui()
        self._connect_signals()

        logger.info("MainWindow initialized")

    # ──────────────────────────────────────────────────────────────────
    # Window Setup
    # ──────────────────────────────────────────────────────────────────

    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle("Japanese OCR Translation Assistant")
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self.setStyleSheet(self._global_stylesheet())

    def _global_stylesheet(self) -> str:
        return """
            QMainWindow {
                background: #0d1520;
            }
            QWidget {
                background: #0d1520;
                color: #c8d8e8;
                font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
            }
            QSplitter::handle {
                background: #1a2535;
                width: 1px;
            }
            QToolTip {
                background: #0f1b28;
                color: #90c8ff;
                border: 1px solid #2a4a6a;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
        """

    # ──────────────────────────────────────────────────────────────────
    # UI Construction
    # ──────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        """Build the complete UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Toolbar (top)
        self._toolbar = Toolbar()
        root_layout.addWidget(self._toolbar)

        # Main content area (splitter)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left panel: word breakdown
        self._left_panel = WordBreakdownPanel()
        self._left_panel.setMinimumWidth(360)
        splitter.addWidget(self._left_panel)

        # Thin separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #1a2535;")
        splitter.addWidget(sep)

        # Right panel: sentence + translation
        self._right_panel = SentencePanel()
        self._right_panel.setMinimumWidth(360)
        splitter.addWidget(self._right_panel)

        # 55 / 45 split
        splitter.setSizes([int(self.DEFAULT_WIDTH * 0.55), 1, int(self.DEFAULT_WIDTH * 0.44)])
        root_layout.addWidget(splitter, stretch=1)

        # Status bar (bottom)
        self._status_bar = StatusBar()
        root_layout.addWidget(self._status_bar)

    # ──────────────────────────────────────────────────────────────────
    # Signal Connections
    # ──────────────────────────────────────────────────────────────────

    def _connect_signals(self):
        self._toolbar.capture_requested.connect(self._on_select_area)
        self._toolbar.recapture_requested.connect(self._on_recapture)

    # ──────────────────────────────────────────────────────────────────
    # Capture Flow
    # ──────────────────────────────────────────────────────────────────

    def _on_select_area(self):
        """Handle 'Select Area' button click."""
        self._status_bar.set_status("Select a screen region…", "processing")

        # Minimize so the overlay can see other windows
        self.showMinimized()

        # Launch region selector overlay
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        region = self._region_selector.select()

        # Restore window
        self.showNormal()
        self.raise_()
        self.activateWindow()

        if region is None:
            self._status_bar.set_status("Selection cancelled", "info", temporary=True)
            return

        # Capture the selected region
        self._status_bar.set_status("Capturing region…", "processing")
        image = self._screen_capture.capture_region(region)

        if image is None:
            self._status_bar.set_status("Screen capture failed", "error", temporary=True)
            return

        self._current_image = pil_to_numpy(image)
        self._toolbar.enable_recapture(True)
        self._start_processing()

    def _on_recapture(self):
        """Re-capture the last selected region without re-selecting."""
        image = self._screen_capture.recapture_last()
        if image is None:
            self._status_bar.set_status("No previous region to recapture", "warning", temporary=True)
            return

        self._current_image = pil_to_numpy(image)
        self._start_processing()

    # ──────────────────────────────────────────────────────────────────
    # Processing Pipeline
    # ──────────────────────────────────────────────────────────────────

    def _start_processing(self):
        """Start background processing worker."""
        if self._current_image is None:
            return

        # Abort previous worker if still running
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)

        # Show loading states in both panels
        self._left_panel.show_loading()
        self._right_panel.show_loading("Running OCR")
        self._toolbar.set_processing(True)

        # Build and start worker
        self._worker = ProcessingWorker(
            image=self._current_image,
            ocr_engine=self._ocr_engine,
            tokenizer=self._tokenizer,
            furigana_processor=self._furigana_processor,
            dictionary=self._dictionary,
            translator=self._translator,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

        self._status_bar.set_status("Processing…", "processing")

    def _on_progress(self, stage: str):
        """Update status bar with current pipeline stage."""
        self._status_bar.set_status(stage, "processing")
        self._right_panel.show_loading(stage)

    def _on_finished(self, result):
        """Handle successful pipeline completion."""
        self._toolbar.set_processing(False)

        if not result.success:
            self._on_error(result.error)
            return

        # Update word breakdown panel
        self._left_panel.display_words(result.words, result.extra_meanings)

        # Update sentence panel
        self._right_panel.display_sentence(
            japanese=result.raw_text,
            translation=result.translation,
            ocr_confidence=result.avg_confidence,
        )

        word_count = len(result.words)
        self._status_bar.set_status(
            f"Done — {word_count} words analyzed",
            "success",
            temporary=True,
        )
        logger.info(f"Pipeline finished: {word_count} words, translation ready")

    def _on_error(self, message: str):
        """Handle pipeline error."""
        self._toolbar.set_processing(False)
        self._left_panel.show_error(message)
        self._right_panel.show_error(message)
        self._status_bar.set_status(f"Error: {message}", "error")
        logger.error(f"Pipeline error: {message}")

    # ──────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Clean up background threads on close."""
        if self._worker and self._worker.isRunning():
            logger.info("Stopping background worker...")
            self._worker.quit()
            self._worker.wait(3000)
        event.accept()
