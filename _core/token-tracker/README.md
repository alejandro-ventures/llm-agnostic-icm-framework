# token-tracker

The data substrate for the "automation cost vs human effort" business case: every workflow run
appends one JSON line to `usage-log.jsonl` (gitignored — local only). Harness-agnostic, stdlib only.

## Log a run
From any harness or script:
```
python _core/token-tracker/tracker.py log --workflow ocr-folder --action ocr \
    --source local --tokens 1200 --minutes-saved 15 --outcome success --summary "12 PDFs"
```
Or import: `from tracker import log_usage; log_usage(workflow="ocr-folder", action="ocr", source="local")`.

## See the summary
```
python _core/token-tracker/analyze.py
```
Per-workflow runs, total tokens, and human-minutes saved.

## Entry schema (one JSON object per line)
| field | meaning |
|-------|---------|
| `timestamp` | UTC ISO-8601 |
| `workflow` / `action` | which workflow, what it did |
| `model` | model id used (optional) |
| `source` | `local` (on-device) or `cloud` — the privacy axis |
| `tokens` | token cost proxy (best estimate) |
| `minutes_saved` | human effort avoided |
| `outcome` | `success` / `partial` / `failed` |
| `summary` / `notes` | free text |
