"""
Screen Capture Module
Handles region selection and screen capture using mss.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class CaptureRegion:
    """Represents a screen capture region."""
    x: int
    y: int
    width: int
    height: int

    def to_mss_dict(self) -> dict:
        return {"left": self.x, "top": self.y, "width": self.width, "height": self.height}

    def is_valid(self) -> bool:
        return self.width > 10 and self.height > 10


class ScreenCapture:
    """
    Handles screen region capture using mss (fast, cross-platform).
    Supports both full-region capture and on-demand re-capture.
    """

    def __init__(self):
        self._last_region: Optional[CaptureRegion] = None
        logger.info("ScreenCapture initialized")

    def capture_region(self, region: CaptureRegion) -> Optional[Image.Image]:
        """
        Capture a specific screen region.

        Args:
            region: CaptureRegion specifying coordinates and size.

        Returns:
            PIL Image of the captured region, or None on failure.
        """
        try:
            import mss
            with mss.mss() as sct:
                monitor = region.to_mss_dict()
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                self._last_region = region
                logger.debug(f"Captured region: {region}")
                return img
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return None

    def recapture_last(self) -> Optional[Image.Image]:
        """Re-capture the previously selected region."""
        if self._last_region is None:
            logger.warning("No previous region to recapture")
            return None
        return self.capture_region(self._last_region)

    def capture_full_screen(self, monitor_index: int = 1) -> Optional[Image.Image]:
        """Capture the entire screen (or a specific monitor)."""
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[monitor_index]
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                return img
        except Exception as e:
            logger.error(f"Full screen capture failed: {e}")
            return None

    @property
    def last_region(self) -> Optional[CaptureRegion]:
        return self._last_region


class RegionSelector:
    """
    Interactive screen region selector using PyQt overlay.
    Presents a transparent full-screen overlay for rubber-band selection.
    """

    def select(self) -> Optional[CaptureRegion]:
        """
        Launch interactive region selection.

        Returns:
            CaptureRegion if user selected a region, None if cancelled.
        """
        from PyQt6.QtWidgets import QApplication
        from ui.components.region_overlay import RegionOverlay

        app = QApplication.instance()
        if app is None:
            logger.error("No QApplication instance found")
            return None

        overlay = RegionOverlay()
        overlay.exec()

        region = overlay.selected_region
        if region and region.is_valid():
            logger.info(f"Region selected: {region}")
            return region
        else:
            logger.info("Region selection cancelled or invalid")
            return None


def pil_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array (for PaddleOCR)."""
    return np.array(image)
