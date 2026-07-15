---
name: ocr-folder
description: >-
  Make a folder of scanned or image-only PDFs text-searchable. Per-page routing keeps
  existing text layers and OCRs only image pages; a content-hash cache skips unchanged
  files on re-runs. Pure pip — no system OCR binary needed.
argument-hint: "Path to a folder of PDFs (defaults to workflows/ocr-folder/input)"
requires-python: "3.9+"
network: none
destructive: none — outputs are new files; overwrite requires a gate
gates: ["overwriting any existing output"]
---

# ocr-folder

## Environment
Runs in its own venv at `.venv/` (gitignored). From this workflow folder:
- Windows PowerShell: `python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt`
- macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

A venv isolates dependencies, not the system (see `_core/SANDBOXING.md`).

## Inputs
| Source | Location | Why |
|--------|----------|-----|
| PDFs to OCR | `input/` | source documents (gitignored) |

## Process
1. List PDFs in the input folder; report count and total size to the user.
2. For each file, compute a content-hash cache token; skip if already in `output/.ocr_cache`.
3. Per page: keep a sufficient native text layer as-is; render and OCR image-only pages.
4. **Gate:** if any file would overwrite an existing output, stop and ask for explicit "yes".
5. Writes go through `_core/scripts/sandbox.py` (`guard_write`) — they cannot leave the workspace.
6. Append a run-log line and a token-tracker entry.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Searchable text | `output/<name>.txt` | UTF-8 |
| Cache | `output/.ocr_cache` | hash list |

## Gates
- Overwriting any existing output requires an explicit user "yes".

## Run log
Append `timestamp,ocr-folder,ocr,<n_processed>` to `output/run-log.csv`, then log the run:
`python _core/token-tracker/tracker.py log --workflow ocr-folder --action ocr --source local`.
