"""
Japanese OCR Translation Assistant
Entry point for the application.
"""

import sys
import logging
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.app import MainWindow
from utils.logger import setup_logger


def main():
    """Application entry point."""
    # Initialize logging
    logger = setup_logger("japanese_ocr", level=logging.INFO)
    logger.info("Starting Japanese OCR Translation Assistant")

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Japanese OCR Assistant")
    app.setOrganizationName("JapaneseOCR")

    # High DPI support
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    # Launch main window
    window = MainWindow()
    window.show()

    logger.info("Application window launched")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
