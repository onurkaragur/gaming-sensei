"""
Model Download Helper
Downloads and caches all required models for offline use.
Run once before using the app: python utils/download_models.py
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger("setup")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Paths
ROOT = Path(__file__).parent.parent
MODEL_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"


def download_marian_model():
    """Download Helsinki-NLP/opus-mt-ja-en from HuggingFace."""
    dest = MODEL_DIR / "opus-mt-ja-en"
    if dest.exists():
        logger.info("✓ MarianMT model already present")
        return

    logger.info("Downloading MarianMT (opus-mt-ja-en)...")
    try:
        from transformers import MarianMTModel, MarianTokenizer
        dest.mkdir(parents=True, exist_ok=True)
        tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-ja-en")
        model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-ja-en")
        tokenizer.save_pretrained(str(dest))
        model.save_pretrained(str(dest))
        logger.info(f"✓ MarianMT saved to {dest}")
    except Exception as e:
        logger.error(f"✗ MarianMT download failed: {e}")


def download_paddleocr_models():
    """Trigger PaddleOCR model download (it auto-downloads on first use)."""
    logger.info("Initializing PaddleOCR (will download models if needed)...")
    try:
        from paddleocr import PaddleOCR
        # This triggers the model download
        ocr = PaddleOCR(use_angle_cls=True, lang="japan", show_log=False, use_gpu=False)
        logger.info("✓ PaddleOCR models ready")
    except Exception as e:
        logger.error(f"✗ PaddleOCR initialization failed: {e}")


def download_jmdict():
    """
    Download JMdict XML dictionary.
    Source: http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz
    """
    dest = DATA_DIR / "jmdict_e.xml"
    if dest.exists():
        logger.info("✓ JMdict already present")
        return

    logger.info("Downloading JMdict (Japanese-English dictionary)...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    import urllib.request
    import gzip
    import shutil

    url = "http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz"
    gz_path = DATA_DIR / "jmdict_e.gz"

    try:
        logger.info(f"Fetching {url} ...")
        urllib.request.urlretrieve(url, gz_path)

        logger.info("Decompressing...")
        with gzip.open(gz_path, "rb") as f_in, open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        gz_path.unlink()  # Clean up .gz file
        logger.info(f"✓ JMdict saved to {dest}")
        logger.info("  (JSON cache will be built on first app launch)")
    except Exception as e:
        logger.error(f"✗ JMdict download failed: {e}")
        logger.info("  You can manually download from: http://ftp.edrdg.org/pub/Nihongo/")


def check_mecab():
    """Verify MeCab/fugashi are working."""
    try:
        import fugashi
        tagger = fugashi.Tagger()
        result = list(tagger("テスト"))
        logger.info(f"✓ MeCab/fugashi working (test: {[w.surface for w in result]})")
    except Exception as e:
        logger.error(f"✗ MeCab/fugashi not working: {e}")
        logger.info("  Run: pip install fugashi unidic-lite")


def check_unidic():
    """Check UniDic installation."""
    try:
        import unidic_lite
        logger.info(f"✓ unidic_lite found at {unidic_lite.DICDIR}")
    except ImportError:
        logger.warning("⚠ unidic_lite not found (fallback dict will be used)")
        logger.info("  Run: pip install unidic-lite")


def main():
    logger.info("=" * 50)
    logger.info("Japanese OCR Translation Assistant — Setup")
    logger.info("=" * 50)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("\n[1/5] Checking MeCab / fugashi...")
    check_mecab()

    logger.info("\n[2/5] Checking UniDic...")
    check_unidic()

    logger.info("\n[3/5] Downloading JMdict...")
    download_jmdict()

    logger.info("\n[4/5] Pre-loading PaddleOCR models...")
    download_paddleocr_models()

    logger.info("\n[5/5] Downloading MarianMT translation model...")
    download_marian_model()

    logger.info("\n" + "=" * 50)
    logger.info("Setup complete. Run:  python main.py")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
