"""
Processing Worker
Runs OCR, NLP, and Translation in a background QThread
to keep the UI responsive.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from nlp.furigana import FuriganaWord

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Complete result from the processing pipeline."""
    raw_text: str = ""
    words: List[FuriganaWord] = field(default_factory=list)
    translation: str = ""
    avg_confidence: float = 0.0
    extra_meanings: dict = field(default_factory=dict)  # base_form → [str]
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class ProcessingWorker(QThread):
    """
    Background worker that runs the full OCR → NLP → Translation pipeline.
    Communicates results via Qt signals.
    """

    # Signals
    progress = pyqtSignal(str)          # Stage description
    finished = pyqtSignal(object)       # ProcessingResult
    error = pyqtSignal(str)             # Error message

    def __init__(
        self,
        image: np.ndarray,
        ocr_engine,
        tokenizer,
        furigana_processor,
        dictionary,
        translator,
    ):
        super().__init__()
        self._image = image
        self._ocr = ocr_engine
        self._tokenizer = tokenizer
        self._furigana = furigana_processor
        self._dictionary = dictionary
        self._translator = translator

    def run(self):
        """Execute the full processing pipeline."""
        try:
            result = self._process()
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Processing pipeline error: {e}", exc_info=True)
            self.error.emit(str(e))

    def _process(self) -> ProcessingResult:
        result = ProcessingResult()

        # Stage 1: OCR
        self.progress.emit("Running OCR...")
        logger.info("Pipeline: OCR stage")
        ocr_results = self._ocr.extract_text(self._image)

        if not ocr_results:
            result.error = "No text detected in the selected region"
            return result

        raw_text = self._ocr.get_combined_text(ocr_results)
        result.raw_text = raw_text
        result.avg_confidence = sum(r.confidence for r in ocr_results) / len(ocr_results)
        logger.info(f"OCR result: {raw_text!r}")

        # Stage 2: Tokenization
        self.progress.emit("Tokenizing text...")
        logger.info("Pipeline: Tokenization stage")
        tokens = self._tokenizer.tokenize(raw_text)

        if not tokens:
            result.error = "Failed to tokenize extracted text"
            return result

        # Stage 3: Furigana processing
        self.progress.emit("Processing furigana...")
        logger.info("Pipeline: Furigana stage")
        words = self._furigana.process(tokens)

        # Stage 4: Dictionary lookup
        self.progress.emit("Looking up meanings...")
        logger.info("Pipeline: Dictionary lookup stage")
        extra_meanings = {}
        for word in words:
            meaning = self._dictionary.lookup_with_fallbacks(
                word.surface, word.base_form, word.reading
            )
            word.meaning = meaning

            all_meanings = self._dictionary.lookup_all(word.base_form)
            if all_meanings:
                extra_meanings[word.base_form] = all_meanings

        result.words = words
        result.extra_meanings = extra_meanings

        # Stage 5: Translation
        self.progress.emit("Translating...")
        logger.info("Pipeline: Translation stage")
        translation = self._translator.translate(raw_text)
        result.translation = translation

        logger.info("Pipeline complete")
        return result
