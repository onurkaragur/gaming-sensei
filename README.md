# 日本語 OCR Translation Assistant

A fully **offline** desktop application that captures a region of your screen, extracts Japanese text with OCR, performs word-by-word morphological analysis with furigana, and translates the full sentence — all locally on your machine.

---

## Features

| Feature | Technology |
|---|---|
| Screen region selection | PyQt6 overlay |
| Screen capture | `mss` (fast, cross-platform) |
| Japanese OCR | PaddleOCR |
| Morphological analysis | `fugashi` + UniDic (MeCab) |
| Furigana / readings | Custom alignment engine |
| Dictionary lookup | JMdict (offline) |
| Sentence translation | MarianMT (`opus-mt-ja-en`) |
| UI | PyQt6 |

---

## Project Structure

```
japanese_ocr/
│
├── main.py                        # Entry point
├── requirements.txt
│
├── capture/
│   └── screen_capture.py          # ScreenCapture, RegionSelector, CaptureRegion
│
├── ocr/
│   └── ocr_engine.py              # OCREngine (PaddleOCR wrapper)
│
├── nlp/
│   ├── tokenizer.py               # JapaneseTokenizer (fugashi/MeCab)
│   ├── furigana.py                # FuriganaProcessor, FuriganaWord
│   └── dictionary.py              # Dictionary (JMdict offline lookup)
│
├── translation/
│   └── translator.py              # Translator (MarianMT singleton)
│
├── ui/
│   ├── app.py                     # MainWindow (root Qt window)
│   ├── worker.py                  # ProcessingWorker (QThread pipeline)
│   └── components/
│       ├── toolbar.py             # Toolbar, StatusBar
│       ├── left_panel.py          # WordBreakdownPanel
│       ├── right_panel.py         # SentencePanel
│       ├── word_card.py           # WordCard, FuriganaLabel
│       └── region_overlay.py      # RegionOverlay (screen selection)
│
├── utils/
│   ├── logger.py                  # Logging setup
│   └── download_models.py         # One-time model download script
│
├── models/
│   └── opus-mt-ja-en/             # MarianMT model (auto-downloaded)
│
├── data/
│   ├── jmdict_e.xml               # JMdict XML (downloaded by setup)
│   └── jmdict.json                # JSON index (built on first run)
│
└── logs/
    └── japanese_ocr.log
```

---

## System Requirements

- **Python** 3.10 or higher
- **OS**: Windows 10+, macOS 12+, or Ubuntu 20.04+
- **RAM**: 4 GB minimum, 8 GB recommended (for MarianMT + PaddleOCR in memory)
- **Storage**: ~4 GB for all models
- **Internet**: Required only for initial model download (app runs fully offline after)

---

## Installation

### Step 1 — Clone / Download

```bash
git clone https://github.com/yourname/japanese-ocr-assistant.git
cd japanese-ocr-assistant
```

### Step 2 — Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note for macOS (Apple Silicon):** PaddlePaddle has limited M-series support.
> You may need to install via Rosetta or use the CPU-only wheel:
> ```bash
> pip install paddlepaddle==2.5.2
> ```

> **Note for GPU (NVIDIA):** Replace `torch>=2.0.0` in requirements.txt with:
> ```
> torch>=2.0.0+cu118  --extra-index-url https://download.pytorch.org/whl/cu118
> ```

### Step 4 — Download Models & Dictionary (one-time setup)

```bash
python utils/download_models.py
```

This will:
1. Verify MeCab/fugashi installation
2. Check UniDic dictionary
3. Download **JMdict** (~50 MB, from edrdg.org)
4. Download **PaddleOCR** Japanese models (~400 MB)
5. Download **MarianMT** opus-mt-ja-en (~300 MB, from HuggingFace)

All models are saved locally and reused on subsequent runs.

### Step 5 — Launch

```bash
python main.py
```

---

## Usage

1. **Click "⊞ Select Area"** — your screen dims and a crosshair cursor appears.
2. **Click and drag** to draw a rectangle around the Japanese text you want to analyze (e.g., a game window, manga panel, website).
3. Press **ESC** to cancel selection.
4. The app captures the region, runs OCR, and processes the text.
5. **Left panel** shows each word with furigana and English meaning.
6. **Right panel** shows the full sentence and English translation.
7. **Hover** over a word card to see extended dictionary definitions.
8. Click **"↺ Recapture"** to re-analyze the same region (useful for on-demand refresh).

---

## Model Details

### PaddleOCR
- Language model: `japan` (Japanese)
- Angle classification: enabled (handles rotated text)
- Mode: CPU inference
- Models auto-downloaded to `~/.paddleocr/`

### MarianMT (Helsinki-NLP/opus-mt-ja-en)
- Architecture: Marian Neural Machine Translation
- Trained on: OPUS multilingual corpus
- Inference: CPU (beam search, 4 beams)
- Local cache: `models/opus-mt-ja-en/`

### JMdict
- Source: Electronic Dictionary Research and Development Group (EDRDG)
- License: Creative Commons Attribution-ShareAlike 4.0
- Entries: ~200,000+ Japanese words
- First-run: XML parsed and cached as JSON for fast lookup

### MeCab + UniDic (via fugashi)
- `fugashi`: Python wrapper for MeCab morphological analyzer
- `unidic-lite`: Lightweight version of the UniDic dictionary
- Provides: surface form, lemma, reading (katakana → hiragana), POS tags

---

## Extending the Application

### Add a new UI component
1. Create a new file in `ui/components/`
2. Subclass `QWidget`
3. Add to `ui/app.py` layout

### Swap OCR engine
Replace `ocr/ocr_engine.py` with a new class exposing:
```python
def extract_text(self, image: np.ndarray) -> List[OCRResult]: ...
def get_combined_text(self, results: List[OCRResult]) -> str: ...
```

### Swap translation model
Replace `translation/translator.py` with any class exposing:
```python
def translate(self, text: str) -> str: ...
```

### Use a different dictionary
Replace `nlp/dictionary.py` with any class exposing:
```python
def lookup(self, word: str) -> str: ...
def lookup_all(self, word: str) -> List[str]: ...
def lookup_with_fallbacks(self, surface, base_form, reading) -> str: ...
```

---

## Troubleshooting

### "No text detected"
- Ensure the selected region actually contains Japanese text.
- Try selecting a higher-resolution area or zooming the source window.
- Increase image contrast in your source application.

### MeCab / fugashi errors
```bash
pip install fugashi unidic-lite
```
On Windows, you may need the MeCab binary installed separately:
```
https://github.com/ikegami-yukino/mecab/releases
```

### MarianMT slow on first run
The model is ~300 MB and takes 5–15 seconds to load into memory. Subsequent translations in the same session are fast due to caching.

### PaddleOCR model download fails
If `python utils/download_models.py` fails for PaddleOCR, models will be downloaded automatically on first use. Ensure you have ~400 MB free space.

### PyQt6 not found
```bash
pip install PyQt6
```

---

## Architecture Notes

- **Lazy loading**: OCR, tokenizer, and translator models are only loaded on first use.
- **Singleton translator**: The `Translator` class uses `__new__` to ensure only one model instance exists in memory.
- **QThread worker**: All heavy processing runs in `ProcessingWorker` (a `QThread`) to keep the UI responsive.
- **Result caching**: OCR results are cached by image hash; translations are cached by text.
- **Modular pipeline**: Each stage (capture → OCR → NLP → translate) is independently testable.

---

## License

MIT License — see `LICENSE` file.

JMdict is used under the Creative Commons Attribution-ShareAlike 4.0 License.
MarianMT model weights are available under CC-BY 4.0.
