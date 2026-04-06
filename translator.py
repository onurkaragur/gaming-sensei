"""
Translation Module
Offline Japanese → English translation using MarianMT.
Model: Helsinki-NLP/opus-mt-ja-en

Uses singleton pattern for model loading efficiency.
"""

import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Local cache directory for the model
MODEL_DIR = Path(__file__).parent.parent / "models" / "opus-mt-ja-en"
MODEL_NAME = "Helsinki-NLP/opus-mt-ja-en"


class Translator:
    """
    Singleton MarianMT translator for Japanese → English.

    Features:
    - Lazy model loading (first translate call)
    - Local model caching (no re-download)
    - Simple result caching
    - Graceful error handling
    """

    _instance: Optional["Translator"] = None

    def __new__(cls):
        """Enforce singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._model = None
        self._tokenizer = None
        self._cache: dict = {}
        self._initialized = True
        logger.info("Translator singleton created (lazy load)")

    def _load_model(self):
        """Load MarianMT model and tokenizer from local cache or HuggingFace."""
        if self._model is not None:
            return

        logger.info("Loading MarianMT translation model...")
        t0 = time.time()

        try:
            from transformers import MarianMTModel, MarianTokenizer
        except ImportError:
            logger.error("transformers not installed. Run: pip install transformers sentencepiece")
            raise

        # Try local directory first, then HuggingFace
        model_source = str(MODEL_DIR) if MODEL_DIR.exists() else MODEL_NAME

        if MODEL_DIR.exists():
            logger.info(f"Loading from local cache: {MODEL_DIR}")
        else:
            logger.info(f"Downloading model from HuggingFace: {MODEL_NAME}")
            logger.info("This will take a few minutes on first run...")

        try:
            self._tokenizer = MarianTokenizer.from_pretrained(
                model_source,
                local_files_only=MODEL_DIR.exists(),
            )
            self._model = MarianMTModel.from_pretrained(
                model_source,
                local_files_only=MODEL_DIR.exists(),
            )

            # Save locally if downloaded from HuggingFace
            if not MODEL_DIR.exists():
                logger.info(f"Saving model locally to {MODEL_DIR}")
                MODEL_DIR.mkdir(parents=True, exist_ok=True)
                self._tokenizer.save_pretrained(str(MODEL_DIR))
                self._model.save_pretrained(str(MODEL_DIR))

            elapsed = time.time() - t0
            logger.info(f"Translation model loaded in {elapsed:.1f}s")

        except Exception as e:
            logger.error(f"Failed to load translation model: {e}")
            raise

    def translate(self, text: str, max_length: int = 512) -> str:
        """
        Translate Japanese text to English.

        Args:
            text: Japanese input string.
            max_length: Maximum output token length.

        Returns:
            Translated English string, or error message on failure.
        """
        text = text.strip()
        if not text:
            return ""

        # Check cache
        if text in self._cache:
            logger.debug("Translation cache hit")
            return self._cache[text]

        try:
            self._load_model()
        except Exception as e:
            return f"[Translation unavailable: {e}]"

        try:
            # Tokenize
            inputs = self._tokenizer(
                [text],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            )

            # Generate translation
            translated = self._model.generate(
                **inputs,
                max_length=max_length,
                num_beams=4,
                early_stopping=True,
            )

            # Decode output
            result = self._tokenizer.decode(
                translated[0],
                skip_special_tokens=True,
            )

            # Cache result
            self._cache[text] = result
            logger.info(f"Translated: {text[:30]!r} → {result[:50]!r}")
            return result

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return f"[Translation error: {e}]"

    def is_ready(self) -> bool:
        """True if the model is already loaded (not lazy)."""
        return self._model is not None

    def preload(self):
        """Explicitly load the model (call during app startup for faster first translate)."""
        try:
            self._load_model()
        except Exception as e:
            logger.warning(f"Model preload failed: {e}")

    def clear_cache(self):
        """Clear translation cache."""
        self._cache.clear()
        logger.info("Translation cache cleared")
