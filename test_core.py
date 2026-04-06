"""
Unit Tests for Japanese OCR Translation Assistant
Run with: pytest tests/ -v
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ──────────────────────────────────────────────────────────────────────
# Tokenizer Tests
# ──────────────────────────────────────────────────────────────────────

class TestKatakanaToHiragana:
    """Tests for katakana → hiragana conversion."""

    def test_pure_katakana(self):
        from nlp.tokenizer import katakana_to_hiragana
        assert katakana_to_hiragana("アイウエオ") == "あいうえお"

    def test_mixed_katakana_hiragana(self):
        from nlp.tokenizer import katakana_to_hiragana
        assert katakana_to_hiragana("アあイい") == "ああいい"

    def test_kanji_passthrough(self):
        from nlp.tokenizer import katakana_to_hiragana
        assert katakana_to_hiragana("食べる") == "食べる"

    def test_empty_string(self):
        from nlp.tokenizer import katakana_to_hiragana
        assert katakana_to_hiragana("") == ""

    def test_numbers_passthrough(self):
        from nlp.tokenizer import katakana_to_hiragana
        assert katakana_to_hiragana("123") == "123"

    def test_extended_katakana(self):
        from nlp.tokenizer import katakana_to_hiragana
        result = katakana_to_hiragana("タベル")
        assert result == "たべる"


class TestContainsKanji:
    def test_with_kanji(self):
        from nlp.tokenizer import contains_kanji
        assert contains_kanji("食べる") is True

    def test_pure_hiragana(self):
        from nlp.tokenizer import contains_kanji
        assert contains_kanji("たべる") is False

    def test_pure_katakana(self):
        from nlp.tokenizer import contains_kanji
        assert contains_kanji("テスト") is False

    def test_empty(self):
        from nlp.tokenizer import contains_kanji
        assert contains_kanji("") is False


class TestToken:
    def test_needs_furigana_with_kanji(self):
        from nlp.tokenizer import Token
        t = Token("食べる", "たべる", "たべる", "動詞", "自立", True)
        assert t.needs_furigana() is True

    def test_needs_furigana_pure_kana(self):
        from nlp.tokenizer import Token
        t = Token("たべる", "たべる", "たべる", "動詞", "自立", True)
        assert t.needs_furigana() is False


# ──────────────────────────────────────────────────────────────────────
# Furigana Tests
# ──────────────────────────────────────────────────────────────────────

class TestFuriganaAlignment:
    def test_pure_kana_no_furigana(self):
        from nlp.furigana import FuriganaProcessor
        from nlp.tokenizer import Token
        processor = FuriganaProcessor()
        token = Token("たべる", "たべる", "たべる", "動詞", "自立", True)
        fw = processor._token_to_furigana_word(token)
        assert fw.segments == [("たべる", "")]
        assert not fw.has_kanji

    def test_kanji_word_gets_reading(self):
        from nlp.furigana import FuriganaProcessor
        from nlp.tokenizer import Token
        processor = FuriganaProcessor()
        token = Token("日本語", "にほんご", "にほんご", "名詞", "固有名詞", True)
        fw = processor._token_to_furigana_word(token)
        assert fw.has_kanji
        assert fw.reading == "にほんご"

    def test_mixed_kanji_kana_alignment(self):
        from nlp.furigana import _split_kanji_kana_runs
        runs = _split_kanji_kana_runs("食べる")
        assert runs[0] == ("食", True)
        assert runs[1] == ("べる", False)

    def test_split_pure_kanji(self):
        from nlp.furigana import _split_kanji_kana_runs
        runs = _split_kanji_kana_runs("漢字")
        assert len(runs) == 1
        assert runs[0][1] is True  # is_kanji=True

    def test_split_pure_kana(self):
        from nlp.furigana import _split_kanji_kana_runs
        runs = _split_kanji_kana_runs("たべる")
        assert len(runs) == 1
        assert runs[0][1] is False  # is_kanji=False


class TestFuriganaWord:
    def test_display_reading_empty_for_kana(self):
        from nlp.furigana import FuriganaWord
        fw = FuriganaWord("たべる", "たべる", "たべる", "動詞")
        assert fw.display_reading == ""

    def test_display_reading_for_kanji(self):
        from nlp.furigana import FuriganaWord
        fw = FuriganaWord("食べる", "たべる", "たべる", "動詞")
        assert fw.display_reading == "たべる"


# ──────────────────────────────────────────────────────────────────────
# OCR Engine Tests
# ──────────────────────────────────────────────────────────────────────

class TestOCREngine:
    def test_clean_text_strips_whitespace(self):
        from ocr.ocr_engine import OCREngine
        engine = OCREngine()
        assert engine._clean_text("  テスト  ") == "テスト"

    def test_clean_text_empty(self):
        from ocr.ocr_engine import OCREngine
        engine = OCREngine()
        assert engine._clean_text("") == ""

    def test_clean_text_punctuation_only(self):
        from ocr.ocr_engine import OCREngine
        engine = OCREngine()
        result = engine._clean_text("。、「」")
        assert result == ""

    def test_image_hash_deterministic(self):
        import numpy as np
        from ocr.ocr_engine import OCREngine
        engine = OCREngine()
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        h1 = engine._image_hash(img)
        h2 = engine._image_hash(img)
        assert h1 == h2

    def test_parse_empty_results(self):
        from ocr.ocr_engine import OCREngine
        engine = OCREngine()
        assert engine._parse_results(None) == []
        assert engine._parse_results([None]) == []

    def test_get_combined_text(self):
        from ocr.ocr_engine import OCREngine, OCRResult
        engine = OCREngine()
        results = [
            OCRResult("日本", 0.9),
            OCRResult("語", 0.85),
        ]
        assert engine.get_combined_text(results) == "日本語"


# ──────────────────────────────────────────────────────────────────────
# Dictionary Tests
# ──────────────────────────────────────────────────────────────────────

class TestDictionary:
    def test_lookup_missing_word(self):
        from nlp.dictionary import Dictionary
        d = Dictionary()
        d._loaded = True
        d._index = {"食べる": ["to eat", "to consume"]}
        assert d.lookup("存在しない語") == ""

    def test_lookup_found_word(self):
        from nlp.dictionary import Dictionary
        d = Dictionary()
        d._loaded = True
        d._index = {"食べる": ["to eat", "to consume"]}
        result = d.lookup("食べる")
        assert "to eat" in result

    def test_lookup_all(self):
        from nlp.dictionary import Dictionary
        d = Dictionary()
        d._loaded = True
        d._index = {"猫": ["cat", "kitty"]}
        assert d.lookup_all("猫") == ["cat", "kitty"]

    def test_lookup_with_fallbacks_surface(self):
        from nlp.dictionary import Dictionary
        d = Dictionary()
        d._loaded = True
        d._index = {"食べる": ["to eat"]}
        result = d.lookup_with_fallbacks("食べる", "食べる", "たべる")
        assert result == "to eat"

    def test_format_meaning_truncates(self):
        from nlp.dictionary import Dictionary
        d = Dictionary()
        meanings = ["to eat", "to consume", "to devour", "to ingest"]
        result = d._format_meaning(meanings)
        # Should only include first 2
        assert result == "to eat; to consume"

    def test_format_meaning_empty(self):
        from nlp.dictionary import Dictionary
        d = Dictionary()
        assert d._format_meaning([]) == ""


# ──────────────────────────────────────────────────────────────────────
# Translator Tests (mocked)
# ──────────────────────────────────────────────────────────────────────

class TestTranslator:
    def test_empty_text_returns_empty(self):
        from translation.translator import Translator
        t = Translator()
        # Don't load model, just test empty input guard
        assert t.translate("") == ""

    def test_whitespace_only_returns_empty(self):
        from translation.translator import Translator
        t = Translator()
        assert t.translate("   ") == ""

    def test_cache_hit(self):
        from translation.translator import Translator
        t = Translator()
        t._cache["テスト"] = "test"
        # Load model mock so it uses cache
        t._model = MagicMock()
        t._tokenizer = MagicMock()
        result = t.translate("テスト")
        assert result == "test"

    def test_singleton(self):
        from translation.translator import Translator
        t1 = Translator()
        t2 = Translator()
        assert t1 is t2


# ──────────────────────────────────────────────────────────────────────
# Screen Capture Tests
# ──────────────────────────────────────────────────────────────────────

class TestCaptureRegion:
    def test_valid_region(self):
        from capture.screen_capture import CaptureRegion
        r = CaptureRegion(0, 0, 100, 100)
        assert r.is_valid() is True

    def test_too_small_region(self):
        from capture.screen_capture import CaptureRegion
        r = CaptureRegion(0, 0, 5, 5)
        assert r.is_valid() is False

    def test_mss_dict(self):
        from capture.screen_capture import CaptureRegion
        r = CaptureRegion(10, 20, 300, 200)
        d = r.to_mss_dict()
        assert d == {"left": 10, "top": 20, "width": 300, "height": 200}

    def test_recapture_without_previous(self):
        from capture.screen_capture import ScreenCapture
        sc = ScreenCapture()
        assert sc.recapture_last() is None

    def test_last_region_initially_none(self):
        from capture.screen_capture import ScreenCapture
        sc = ScreenCapture()
        assert sc.last_region is None


# ──────────────────────────────────────────────────────────────────────
# Integration: Pipeline Data Flow
# ──────────────────────────────────────────────────────────────────────

class TestPipelineDataFlow:
    """Verify that data structures are compatible across pipeline stages."""

    def test_token_to_furigana_word_flow(self):
        from nlp.tokenizer import Token
        from nlp.furigana import FuriganaProcessor
        processor = FuriganaProcessor()

        token = Token(
            surface="日本",
            base_form="日本",
            reading="にほん",
            part_of_speech="名詞",
            pos_detail="固有名詞",
            is_content_word=True,
        )
        fw = processor.process([token])

        assert len(fw) == 1
        assert fw[0].surface == "日本"
        assert fw[0].reading == "にほん"
        assert fw[0].has_kanji is True
        assert fw[0].meaning == ""  # Not yet looked up

    def test_furigana_word_meaning_assignment(self):
        from nlp.furigana import FuriganaWord
        fw = FuriganaWord("犬", "いぬ", "犬", "名詞")
        fw.meaning = "dog"
        assert fw.meaning == "dog"
