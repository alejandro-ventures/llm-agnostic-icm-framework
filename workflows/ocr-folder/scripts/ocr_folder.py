#!/usr/bin/env python3
"""OCR a folder of PDFs to searchable text using RapidOCR (ONNX), with a content-hash cache.

Per-page routing: a page that already has enough embedded ("native") text keeps that text;
a page without it (scanned / image-only) is rendered and passed to the OCR engine. Pure pip —
no system Tesseract binary and no poppler required, so it runs the same on any machine.
Usage: python ocr_folder.py [input_dir] [output_dir]"""
from __future__ import annotations
import csv, hashlib, sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_core" / "scripts"))
import sandbox  # filesystem guardrail — see _core/SANDBOXING.md

DPI = 200
MIN_NATIVE_CHARS = 100              # a page with >= this many native chars skips OCR
SCALE = DPI / 72.0

def file_token(path: Path) -> str:
    """Cache token: file content hash + engine params, so changing the engine re-runs."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return f"{h.hexdigest()}|rapidocr|dpi{DPI}|min{MIN_NATIVE_CHARS}"

def main(in_dir: str, out_dir: str) -> int:
    src = Path(in_dir)
    dst = sandbox.guard_write(out_dir)          # refuse to write outside the workspace
    dst.mkdir(parents=True, exist_ok=True)
    cache = dst / ".ocr_cache"
    seen = set(filter(None, cache.read_text().split("\n"))) if cache.exists() else set()

    try:
        import pypdfium2 as pdfium
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as e:
        print(f"Install deps first (pip install -r requirements.txt): {e}")
        return 1

    pdfs = sorted(src.glob("*.pdf"))
    print(f"Found {len(pdfs)} PDF(s) in {src}")
    ocr = None                                  # built lazily — only if a page actually needs OCR
    processed = 0

    for pdf_path in pdfs:
        token = file_token(pdf_path)
        if token in seen:
            print(f"  skip (cached): {pdf_path.name}")
            continue
        out = dst / (pdf_path.stem + ".txt")
        if out.exists():
            print(f"  GATE: {out.name} exists. Re-run with explicit approval to overwrite. Skipping.")
            continue

        doc = pdfium.PdfDocument(str(pdf_path))
        pages_text, ocr_pages = [], 0
        for i in range(len(doc)):
            page = doc[i]
            native = (page.get_textpage().get_text_range() or "").strip()
            if len(native) >= MIN_NATIVE_CHARS:
                pages_text.append(native)
            else:
                if ocr is None:
                    ocr = RapidOCR()
                img = page.render(scale=SCALE).to_pil().convert("RGB")
                res, _ = ocr(np.array(img))
                pages_text.append("\n".join(line[1] for line in res) if res else "")
                ocr_pages += 1
        out.write_text("\n\n".join(pages_text), encoding="utf-8")
        seen.add(token)
        processed += 1
        print(f"  ocr: {pdf_path.name} -> {out.name}  ({len(doc)} pages, {ocr_pages} via OCR)")

    cache.write_text("\n".join(sorted(seen)))
    with (dst / "run-log.csv").open("a", newline="") as fh:
        csv.writer(fh).writerow([datetime.datetime.now().isoformat(timespec="seconds"),
                                 "ocr-folder", "ocr", processed])
    print(f"Done. {processed} file(s) processed.")
    return 0

if __name__ == "__main__":
    wf = sandbox.workflow_dir(__file__)
    a = sys.argv[1:] or [str(wf / "input"), str(wf / "output")]
    raise SystemExit(main(a[0], a[1] if len(a) > 1 else str(wf / "output")))
