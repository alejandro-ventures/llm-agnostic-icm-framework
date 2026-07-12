# ocr-folder (human guide)

Turns scanned PDFs into searchable text with a content-hash cache so re-runs are cheap.
Pure pip: the OCR engine (RapidOCR, ONNX) ships in the wheel — no system Tesseract or
poppler install needed, so it runs the same on any machine.

## Set up the venv (first time)
From this workflow folder:

PowerShell (Windows):

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt

bash / zsh (macOS/Linux):

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Run
With the venv active, from this workflow folder:

    python scripts/ocr_folder.py input output

Outputs land in `output/`; both `input/` and `output/` are gitignored. Writes are routed
through `_core/scripts/sandbox.py` and cannot leave the workspace.
