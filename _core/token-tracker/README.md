# token-tracker

The data substrate for the "automation cost vs human effort" business case: every workflow run
appends one JSON line to `usage-log.jsonl` (gitignored — local only). Harness-agnostic, stdlib only.

## Log a run
From any harness or script:
```
python _core/token-tracker/tracker.py log --workflow pdf-ocr --action ocr \
    --source local --tokens 1200 --minutes-saved 15 --outcome success --summary "12 PDFs"
```
Or import: `from tracker import log_usage; log_usage(workflow="pdf-ocr", action="ocr", source="local")`.

`scratch` runs additionally require a redacted, single-line summary of at most 160 characters and a
stable 2-5-part lowercase kebab-case intent key:
```
python _core/token-tracker/tracker.py log --workflow scratch --action research \
    --source local --outcome success --summary "Compared recurring vendor-report formats" \
    --intent-key compare-vendor-reports
```
Reuse the same intent key for the same kind of request. Never put prompts, message bodies, file
contents, personal data, or secrets in the summary or intent key.

## See the summary
```
python _core/token-tracker/analyze.py
```
Per-workflow runs, total tokens, and human-minutes saved.

## Entry schema (one JSON object per line)
| field | meaning |
|-------|---------|
| `schema_version` / `run_id` | schema revision and UUID for new entries (older entries remain valid) |
| `timestamp` | UTC ISO-8601 |
| `workflow` / `action` | which workflow, what it did |
| `model` | model id used (optional) |
| `source` | `local` (on-device) or `cloud` — the privacy axis |
| `tokens` | token cost proxy (best estimate) |
| `minutes_saved` | human effort avoided |
| `outcome` | `success` / `partial` / `failed` |
| `summary` / `notes` | free text |
| `intent_key` | optional normalized request kind; required for new `scratch` entries |
