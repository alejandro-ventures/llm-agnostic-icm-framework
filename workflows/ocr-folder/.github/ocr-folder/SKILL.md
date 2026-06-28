---
name: ocr-folder
description: >-
  Make a folder of scanned or image-only PDFs text-searchable. Adds a text layer
  and writes a per-file content-hash cache so unchanged files are skipped on re-runs.
argument-hint: "Path to a folder of PDFs (defaults to workflows/ocr-folder/input)"
---

# ocr-folder

## Inputs
| Source | Location | Why |
|--------|----------|-----|
| PDFs to OCR | `input/` | source documents (gitignored) |

## Process
1. List PDFs in the input folder; report count and total size to the user.
2. For each file, compute a SHA-256 hash; skip if already in `output/.ocr_cache`.
3. OCR each remaining file to searchable text/PDF in `output/`.
4. **Gate:** if any file would overwrite an existing output, stop and ask for explicit "yes".
5. Append a run-log line.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Searchable text | `output/<name>.txt` | UTF-8 |
| Cache | `output/.ocr_cache` | hash list |

## Gates
- Overwriting any existing output requires an explicit user "yes".

## Run log
Append `timestamp,ocr-folder,ocr,<n_processed>` to `output/run-log.csv`.
