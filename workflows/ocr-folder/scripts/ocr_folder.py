#!/usr/bin/env python3
"""OCR a folder of PDFs to searchable text with a content-hash cache.
Generic example workflow. Usage: python ocr_folder.py <input_dir> <output_dir>"""
from __future__ import annotations
import csv, hashlib, sys, datetime
from pathlib import Path

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main(in_dir: str, out_dir: str) -> int:
    src, dst = Path(in_dir), Path(out_dir)
    dst.mkdir(parents=True, exist_ok=True)
    cache = dst / ".ocr_cache"
    seen = set(cache.read_text().split()) if cache.exists() else set()
    try:
        import pdfplumber, pytesseract            # noqa: F401
        from PIL import Image                      # noqa: F401
        import io
    except ImportError:
        print("Install deps first: pip install -r requirements.txt"); return 1

    pdfs = sorted(src.glob("*.pdf"))
    print(f"Found {len(pdfs)} PDF(s) in {src}")
    processed = 0
    for pdf in pdfs:
        digest = sha256(pdf)
        if digest in seen:
            print(f"  skip (cached): {pdf.name}"); continue
        out = dst / (pdf.stem + ".txt")
        if out.exists():
            print(f"  GATE: {out.name} exists. Re-run with explicit approval to overwrite."); continue
        import pdfplumber, pytesseract, io
        from PIL import Image
        text = []
        with pdfplumber.open(pdf) as doc:
            for page in doc.pages:
                layer = page.extract_text() or ""
                if layer.strip():
                    text.append(layer)
                else:
                    img = page.to_image(resolution=200).original
                    text.append(pytesseract.image_to_string(img))
        out.write_text("\n".join(text), encoding="utf-8")
        seen.add(digest); processed += 1
        print(f"  ocr: {pdf.name} -> {out.name}")
    cache.write_text("\n".join(sorted(seen)))
    with (dst / "run-log.csv").open("a", newline="") as fh:
        csv.writer(fh).writerow([datetime.datetime.now().isoformat(timespec="seconds"),
                                 "ocr-folder", "ocr", processed])
    print(f"Done. {processed} file(s) processed.")
    return 0

if __name__ == "__main__":
    a = sys.argv[1:] or ["input", "output"]
    raise SystemExit(main(a[0], a[1] if len(a) > 1 else "output"))
