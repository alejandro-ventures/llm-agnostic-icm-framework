# ocr-folder (human guide)

Turns scanned PDFs into searchable text with a content-hash cache so re-runs are cheap.

## Prerequisites
- `pip install -r ../../requirements.txt`
- Tesseract OCR installed and on PATH (open-source; install separately).

## Run manually
```bash
python scripts/ocr_folder.py input output
```
Outputs land in `output/`; both `input/` and `output/` are gitignored.
