"""
Furigana Module
Aligns hiragana readings with kanji characters.
Produces structured word data for UI display.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from nlp.tokenizer import Token, contains_kanji, katakana_to_hiragana

logger = logging.getLogger(__name__)


@dataclass
class FuriganaWord:
    """
    A word with its furigana annotation and meaning.
    Ready for UI display.
    """
    surface: str          # Original text (may contain kanji)
    reading: str          # Full hiragana reading
    base_form: str        # Dictionary form
    part_of_speech: str   # POS label
    meaning: str = ""     # English meaning (filled by dictionary lookup)
    segments: List[Tuple[str, str]] = field(default_factory=list)
    # segments: list of (text_chunk, reading_chunk) pairs
    # e.g. [("食", "た"), ("べる", "")]  — kanji+reading, kana+empty

    @property
    def has_kanji(self) -> bool:
        return contains_kanji(self.surface)

    @property
    def display_reading(self) -> str:
        """Reading to show as furigana (empty if surface is already kana)."""
        if not self.has_kanji:
            return ""
        return self.reading


class FuriganaProcessor:
    """
    Converts tokenized words into furigana-annotated structures.

    Strategy:
    - If a word is pure kana, no furigana needed.
    - If a word contains kanji, align the reading over the kanji portion.
    - Uses a character-by-character alignment heuristic.
    """

    def process(self, tokens: List[Token]) -> List[FuriganaWord]:
        """
        Convert a list of Token objects to FuriganaWord objects.

        Args:
            tokens: Tokenized Japanese morphemes.

        Returns:
            List of FuriganaWord ready for display.
        """
        words = []
        for token in tokens:
            fw = self._token_to_furigana_word(token)
            words.append(fw)
        return words

    def _token_to_furigana_word(self, token: Token) -> FuriganaWord:
        """Convert a single Token to a FuriganaWord."""
        surface = token.surface
        reading = token.reading

        # Normalize reading
        reading = katakana_to_hiragana(reading)
        if not reading or reading == surface:
            reading = surface

        segments = self._align_furigana(surface, reading)

        return FuriganaWord(
            surface=surface,
            reading=reading,
            base_form=token.base_form,
            part_of_speech=token.part_of_speech,
            segments=segments,
        )

    def _align_furigana(
        self, surface: str, reading: str
    ) -> List[Tuple[str, str]]:
        """
        Align furigana reading with surface text.

        Returns list of (surface_segment, reading_segment) tuples.
        Pure kana segments get empty reading; kanji segments get their reading.

        Example:
            surface="食べる", reading="たべる"
            → [("食", "た"), ("べる", "")]
        """
        if not contains_kanji(surface):
            return [(surface, "")]

        segments = []
        try:
            segments = self._align_recursive(surface, reading)
        except Exception as e:
            logger.warning(f"Furigana alignment failed for {surface!r}: {e}")
            # Fallback: entire word with full reading
            segments = [(surface, reading)]

        return segments if segments else [(surface, reading)]

    def _align_recursive(
        self, surface: str, reading: str
    ) -> List[Tuple[str, str]]:
        """
        Recursively align kana/kanji segments with the reading string.

        Algorithm:
        1. Split surface into runs of (kanji) and (kana).
        2. For each kana run, find it in reading string to anchor.
        3. Everything between anchors goes to the kanji run.
        """
        if not surface:
            return []
        if not reading:
            return [(surface, "")]

        # Split into alternating kanji/kana runs
        runs = _split_kanji_kana_runs(surface)

        if len(runs) == 1:
            run_text, is_kanji = runs[0]
            if is_kanji:
                return [(run_text, reading)]
            else:
                return [(run_text, "")]

        segments = []
        remaining_reading = reading

        for i, (run_text, is_kanji) in enumerate(runs):
            if not is_kanji:
                # Kana run: consume matching kana from front of remaining_reading
                kana_reading = katakana_to_hiragana(run_text)
                if remaining_reading.startswith(kana_reading):
                    remaining_reading = remaining_reading[len(kana_reading):]
                segments.append((run_text, ""))
            else:
                # Kanji run: figure out how much reading to consume
                # Look ahead to next kana run for anchor
                if i + 1 < len(runs):
                    next_kana, _ = runs[i + 1]
                    next_kana_h = katakana_to_hiragana(next_kana)
                    # Find next_kana in remaining_reading
                    idx = remaining_reading.find(next_kana_h)
                    if idx > 0:
                        kanji_reading = remaining_reading[:idx]
                        remaining_reading = remaining_reading[idx:]
                        segments.append((run_text, kanji_reading))
                    else:
                        # Can't find anchor, assign all remaining
                        segments.append((run_text, remaining_reading))
                        remaining_reading = ""
                else:
                    # Last run is kanji, assign all remaining reading
                    segments.append((run_text, remaining_reading))
                    remaining_reading = ""

        return segments


def _split_kanji_kana_runs(text: str) -> List[Tuple[str, bool]]:
    """
    Split text into alternating runs of (kanji, True) and (kana/other, False).

    Example: "食べる" → [("食", True), ("べる", False)]
    """
    if not text:
        return []

    runs = []
    current = text[0]
    current_is_kanji = _is_kanji(text[0])

    for char in text[1:]:
        char_is_kanji = _is_kanji(char)
        if char_is_kanji == current_is_kanji:
            current += char
        else:
            runs.append((current, current_is_kanji))
            current = char
            current_is_kanji = char_is_kanji

    runs.append((current, current_is_kanji))
    return runs


def _is_kanji(char: str) -> bool:
    """Check if a character is a CJK kanji."""
    return "\u4e00" <= char <= "\u9fff"
