# background-remove

Removes backgrounds from portrait and general images, saving them as PNG files with transparent alpha channels.

## Prerequisites
- Python 3.10+ installed
- Install dependencies: `pip install -r requirements.txt` (from repo root; pulls in `rembg`, `Pillow`)
- First run downloads the U²-Net model (~50 MB) into `~/.u2net/` automatically.

## How to use
1. Drop your images into `workflows/background-remove/input/`. Supported formats: PNG, JPG, JPEG, BMP, WEBP.
2. Run from the repo root:
   ```
   python workflows/background-remove/scripts/remove_bg.py input output
   ```
   Or simply:
   ```
   python workflows/background-remove/scripts/remove_bg.py
   ```
   which defaults to `input/` and `output/` relative to the script location.
3. Find transparent-background PNGs in `workflows/background-remove/output/`.

## Notes
- Output is always PNG with alpha transparency, regardless of input format.
- Re-running skips already-processed images (content-hash cache).
- Existing output files are **not** overwritten without explicit approval.
