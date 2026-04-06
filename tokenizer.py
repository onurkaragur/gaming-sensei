"""
Japanese Tokenizer Module
Uses fugashi (MeCab wrapper) with UniDic for morphological analysis.
Extracts surface form, base form, reading, and POS.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# Katakana → Hiragana conversion range
_KATA_START = 0x30A1  # ァ
_KATA_END = 0x30F6    # ヶ
_HIRA_START = 0x3041  # ぁ


@dataclass
class Token:
    """Represents a single morpheme (word unit) from MeCab analysis."""
    surface: str          # Original text as it appears
    base_form: str        # Dictionary base form (lemma)
    reading: str          # Hiragana reading
    part_of_speech: str   # POS category
    pos_detail: str       # Detailed POS subcategory
    is_content_word: bool = False  # True for nouns, verbs, adjectives, adverbs

    def needs_furigana(self) -> bool:
        """True if the surface form contains kanji."""
        return any("\u4e00" <= c <= "\u9fff" for c in self.surface)

    def __repr__(self):
        return f"Token(surface={self.surface!r}, reading={self.reading!r}, pos={self.part_of_speech!r})"


class JapaneseTokenizer:
    """
    Morphological analyzer wrapping fugashi + UniDic.

    Provides:
    - Surface / base form extraction
    - Reading normalization (katakana → hiragana)
    - Part-of-speech tagging
    - Content-word filtering
    """

    # POS categories considered "content words" (worth translating)
    CONTENT_POS = {"名詞", "動詞", "形容詞", "副詞", "形容動詞"}

    def __init__(self):
        self._tagger = None
        logger.info("JapaneseTokenizer initialized (lazy load)")

    def _load_tagger(self):
        """Lazy-load MeCab tagger via fugashi."""
        if self._tagger is not None:
            return
        try:
            import fugashi
            # Use UniDic if available, fall back to default dict
            try:
                import unidic_lite
                self._tagger = fugashi.Tagger()
                logger.info("MeCab tagger loaded with unidic_lite")
            except ImportError:
                self._tagger = fugashi.Tagger()
                logger.info("MeCab tagger loaded with default dictionary")
        except ImportError:
            logger.error("fugashi not installed. Run: pip install fugashi unidic-lite")
            raise

    def tokenize(self, text: str) -> List[Token]:
        """
        Tokenize Japanese text into morphemes.

        Args:
            text: Japanese input string.

        Returns:
            List of Token objects with readings and POS.
        """
        if not text or not text.strip():
            return []

        self._load_tagger()

        tokens = []
        try:
            for word in self._tagger(text):
                token = self._parse_word(word)
                if token:
                    tokens.append(token)
        except Exception as e:
            logger.error(f"Tokenization failed: {e}")
            return []

        logger.debug(f"Tokenized {len(tokens)} tokens from text: {text[:30]!r}...")
        return tokens

    def _parse_word(self, word) -> Optional[Token]:
        """Parse a single fugashi word object into a Token."""
        try:
            surface = word.surface
            if not surface:
                return None

            feature = word.feature

            # UniDic feature format (csv fields)
            # pos1, pos2, pos3, pos4, cType, cForm, lForm, lemma, orth, pron, orthBase, pronBase, ...
            pos1 = self._safe_feature(feature, 0, "その他")
            pos2 = self._safe_feature(feature, 1, "")
            base_form = self._safe_feature(feature, 7, surface)  # lemma
            reading_kana = self._safe_feature(feature, 9, surface)  # pron

            # Normalize reading to hiragana
            reading = katakana_to_hiragana(reading_kana)

            # If reading is empty or asterisk, use surface
            if not reading or reading in ("*", "＊"):
                reading = surface

            is_content = pos1 in self.CONTENT_POS

            return Token(
                surface=surface,
                base_form=base_form if base_form != "*" else surface,
                reading=reading,
                part_of_speech=pos1,
                pos_detail=pos2,
                is_content_word=is_content,
            )
        except Exception as e:
            logger.warning(f"Failed to parse word {word.surface!r}: {e}")
            # Return minimal token
            return Token(
                surface=word.surface,
                base_form=word.surface,
                reading=word.surface,
                part_of_speech="その他",
                pos_detail="",
                is_content_word=False,
            )

    @staticmethod
    def _safe_feature(feature, index: int, default: str) -> str:
        """Safely access feature field by index."""
        try:
            val = str(feature).split(",")[index].strip()
            return val if val and val != "*" else default
        except (IndexError, AttributeError):
            return default

    def get_content_tokens(self, tokens: List[Token]) -> List[Token]:
        """Filter to content words only (nouns, verbs, adjectives)."""
        return [t for t in tokens if t.is_content_word]


def katakana_to_hiragana(text: str) -> str:
    """
    Convert katakana characters to hiragana.
    Non-katakana characters are passed through unchanged.
    """
    result = []
    for char in text:
        code = ord(char)
        if _KATA_START <= code <= _KATA_END:
            result.append(chr(code - _KATA_START + _HIRA_START))
        else:
            result.append(char)
    return "".join(result)


def contains_kanji(text: str) -> bool:
    """Check if text contains any kanji characters."""
    return any("\u4e00" <= c <= "\u9fff" for c in text)
