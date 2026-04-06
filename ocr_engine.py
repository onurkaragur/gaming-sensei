"""
OCR Engine Module
Wraps PaddleOCR for Japanese text extraction.
Implements lazy loading and result caching.
"""

import logging
import hashlib
from typing import List, Optional, Tuple
from dataclasses import dataclass

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Single OCR text detection result."""
    text: str
    confidence: float
    bounding_box: Optional[List] = None  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]

    def __repr__(self):
        return f"OCRResult(text={self.text!r}, conf={self.confidence:.2f})"


class OCREngine:
    """
    PaddleOCR wrapper configured for Japanese text extraction.

    Features:
    - Lazy model loading (first-use initialization)
    - Image preprocessing for better OCR accuracy
    - Noise filtering via confidence threshold
    - Result normalization and cleaning
    """

    DEFAULT_CONFIDENCE_THRESHOLD = 0.5
    DEFAULT_LANGUAGE = "japan"

    def __init__(
        self,
        language: str = DEFAULT_LANGUAGE,
        use_angle_cls: bool = True,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ):
        self._language = language
        self._use_angle_cls = use_angle_cls
        self._confidence_threshold = confidence_threshold
        self._engine = None  # Lazy loaded
        self._last_image_hash: Optional[str] = None
        self._last_results: Optional[List[OCRResult]] = None
        logger.info(f"OCREngine configured (lang={language}, angle_cls={use_angle_cls})")

    def _load_engine(self):
        """Lazy-load PaddleOCR model (only on first use)."""
        if self._engine is not None:
            return

        logger.info("Loading PaddleOCR model (this may take a moment)...")
        try:
            from paddleocr import PaddleOCR
            self._engine = PaddleOCR(
                use_angle_cls=self._use_angle_cls,
                lang=self._language,
                show_log=False,
                use_gpu=False,  # CPU for maximum compatibility
            )
            logger.info("PaddleOCR model loaded successfully")
        except ImportError:
            logger.error("PaddleOCR not installed. Run: pip install paddleocr")
            raise
        except Exception as e:
            logger.error(f"Failed to load PaddleOCR: {e}")
            raise

    def _image_hash(self, image: np.ndarray) -> str:
        """Compute hash to detect duplicate images (for caching)."""
        return hashlib.md5(image.tobytes()).hexdigest()

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results.
        Scales up small images, converts if needed.
        """
        from PIL import Image, ImageEnhance
        pil_img = Image.fromarray(image)

        # Scale up if too small (PaddleOCR works better on larger images)
        min_dim = 600
        w, h = pil_img.size
        if w < min_dim or h < min_dim:
            scale = max(min_dim / w, min_dim / h)
            new_w, new_h = int(w * scale), int(h * scale)
            pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
            logger.debug(f"Upscaled image from ({w},{h}) to ({new_w},{new_h})")

        # Mild contrast enhancement
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(1.2)

        return np.array(pil_img)

    def extract_text(
        self,
        image: np.ndarray,
        use_cache: bool = True,
    ) -> List[OCRResult]:
        """
        Extract Japanese text from an image.

        Args:
            image: numpy array (H, W, C) in RGB format.
            use_cache: Return cached results if same image is re-submitted.

        Returns:
            List of OCRResult objects, sorted top-to-bottom.
        """
        self._load_engine()

        # Check cache
        img_hash = self._image_hash(image)
        if use_cache and img_hash == self._last_image_hash and self._last_results:
            logger.debug("Returning cached OCR results")
            return self._last_results

        # Preprocess
        processed = self._preprocess_image(image)

        # Run OCR
        logger.info("Running OCR inference...")
        try:
            raw_results = self._engine.ocr(processed, cls=self._use_angle_cls)
        except Exception as e:
            logger.error(f"OCR inference failed: {e}")
            return []

        # Parse results
        results = self._parse_results(raw_results)

        # Cache
        self._last_image_hash = img_hash
        self._last_results = results

        logger.info(f"OCR extracted {len(results)} text blocks")
        return results

    def _parse_results(self, raw_results) -> List[OCRResult]:
        """Parse PaddleOCR raw output into OCRResult objects."""
        results = []

        if not raw_results or raw_results[0] is None:
            return results

        for page in raw_results:
            if page is None:
                continue
            for line in page:
                try:
                    bbox = line[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                    text, confidence = line[1]

                    # Filter low confidence results
                    if confidence < self._confidence_threshold:
                        logger.debug(f"Filtered low-confidence result: {text!r} ({confidence:.2f})")
                        continue

                    # Clean text
                    text = self._clean_text(text)
                    if not text:
                        continue

                    results.append(OCRResult(
                        text=text,
                        confidence=confidence,
                        bounding_box=bbox,
                    ))
                except (IndexError, TypeError) as e:
                    logger.warning(f"Failed to parse OCR line: {e}")
                    continue

        # Sort top-to-bottom by y-coordinate of first point
        results.sort(key=lambda r: r.bounding_box[0][1] if r.bounding_box else 0)
        return results

    def _clean_text(self, text: str) -> str:
        """Remove noise characters from OCR output."""
        if not text:
            return ""
        # Strip excessive whitespace
        text = text.strip()
        # Remove standalone punctuation-only results
        stripped = text.strip("。、「」『』【】・…―ー～！？　 ")
        if not stripped:
            return ""
        return text

    def get_combined_text(self, results: List[OCRResult]) -> str:
        """Combine all OCR results into a single string."""
        return "".join(r.text for r in results)
