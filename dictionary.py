"""
Dictionary Module
Offline Japanese-English dictionary using JMdict.
Provides fast word lookup via in-memory index.
"""

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default path for JMdict JSON (converted from XML)
DEFAULT_DICT_PATH = Path(__file__).parent.parent / "data" / "jmdict.json"
FALLBACK_DICT_PATH = Path(__file__).parent.parent / "data" / "jmdict_e.xml"


class Dictionary:
    """
    Offline Japanese-English dictionary powered by JMdict.

    Supports:
    - Lookup by kanji form
    - Lookup by kana form (reading)
    - Lookup by base/lemma form
    - Short meaning extraction (first gloss only)
    """

    def __init__(self, dict_path: Optional[Path] = None):
        self._path = dict_path or DEFAULT_DICT_PATH
        self._index: Dict[str, List[str]] = {}  # word → [meanings]
        self._loaded = False
        logger.info(f"Dictionary configured (path={self._path})")

    def _ensure_loaded(self):
        """Lazy-load the dictionary on first access."""
        if self._loaded:
            return
        self._load()

    def _load(self):
        """Load JMdict from JSON or XML into memory."""
        json_path = self._path
        xml_path = FALLBACK_DICT_PATH

        if json_path.exists():
            self._load_json(json_path)
        elif xml_path.exists():
            logger.info("Loading JMdict XML (this takes ~10s on first run)...")
            self._load_xml(xml_path)
            # Save JSON cache for fast future loads
            self._save_json(json_path)
        else:
            logger.warning(
                "JMdict not found. Run setup script to download. "
                "Dictionary lookups will return empty results."
            )
            self._index = {}

        self._loaded = True
        logger.info(f"Dictionary loaded: {len(self._index)} entries")

    def _load_json(self, path: Path):
        """Load pre-converted JSON dictionary."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._index = json.load(f)
            logger.info(f"Dictionary loaded from JSON: {path}")
        except Exception as e:
            logger.error(f"Failed to load JSON dictionary: {e}")
            self._index = {}

    def _load_xml(self, path: Path):
        """Parse JMdict XML and build lookup index."""
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            self._index = {}

            for entry in root.findall("entry"):
                # Collect all kanji forms
                kanji_forms = [k.findtext("keb", "") for k in entry.findall("k_ele")]

                # Collect all kana forms
                kana_forms = [r.findtext("reb", "") for r in entry.findall("r_ele")]

                # Collect English glosses (first sense only for brevity)
                meanings = []
                for sense in entry.findall("sense"):
                    glosses = [g.text for g in sense.findall("gloss") if g.text]
                    if glosses:
                        meanings.extend(glosses[:3])  # max 3 per sense
                    if meanings:
                        break  # Only use first sense

                if not meanings:
                    continue

                # Index by all forms
                for form in kanji_forms + kana_forms:
                    if form:
                        if form not in self._index:
                            self._index[form] = meanings
        except ET.ParseError as e:
            logger.error(f"Failed to parse JMdict XML: {e}")
            self._index = {}

    def _save_json(self, path: Path):
        """Cache the loaded dictionary as JSON for fast future loads."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, separators=(",", ":"))
            logger.info(f"Dictionary cached to JSON: {path}")
        except Exception as e:
            logger.warning(f"Failed to save JSON cache: {e}")

    def lookup(self, word: str) -> str:
        """
        Look up a word and return its primary English meaning.

        Args:
            word: Japanese word (kanji or kana form).

        Returns:
            Short English meaning string, or empty string if not found.
        """
        self._ensure_loaded()

        if not word or not self._index:
            return ""

        # Direct lookup
        meanings = self._index.get(word)
        if meanings:
            return self._format_meaning(meanings)

        return ""

    def lookup_all(self, word: str) -> List[str]:
        """
        Look up a word and return all English meanings.

        Returns:
            List of meaning strings, empty list if not found.
        """
        self._ensure_loaded()

        if not word or not self._index:
            return []

        return self._index.get(word, [])

    def _format_meaning(self, meanings: List[str]) -> str:
        """Format a list of meanings into a concise display string."""
        if not meanings:
            return ""
        # Return first 2 meanings separated by semicolon
        return "; ".join(m for m in meanings[:2] if m)

    def lookup_with_fallbacks(self, surface: str, base_form: str, reading: str) -> str:
        """
        Look up with multiple fallback strategies.

        Tries: surface → base_form → reading (kana)

        Args:
            surface: Word as it appears in text.
            base_form: Lemma/dictionary form.
            reading: Hiragana reading.

        Returns:
            Best available English meaning.
        """
        self._ensure_loaded()

        for candidate in [surface, base_form, reading]:
            if candidate:
                result = self.lookup(candidate)
                if result:
                    return result

        return ""

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def entry_count(self) -> int:
        return len(self._index)
