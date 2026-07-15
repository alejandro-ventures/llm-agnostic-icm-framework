---
name: rss-digest
description: >-
  Read a list of public RSS/Atom feeds and produce a dated markdown digest of new
  items. Read-only against the network; writes only a local markdown file.
argument-hint: "A feeds list (defaults to references/feeds.example.md)"
requires-python: "3.9+"
network: outbound HTTPS to the user-listed feeds only, read-only
destructive: none — writes a new dated digest file
gates: ["adding a feed not already in the user's list"]
---

# rss-digest

## Environment
Runs in its own venv at `.venv/` (gitignored); deps pinned in `requirements.txt`. From this
workflow folder:
- Windows PowerShell: `python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt`
- macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

## Inputs
| Source | Location | Why |
|--------|----------|-----|
| Feed URLs | `references/feeds.example.md` | which public feeds to read |

## Process
1. Parse the feed list; fetch each public feed (read-only).
2. Collect items newer than the last run (state in `output/.last_run`).
3. Write `output/digest-<date>.md` via `_core/scripts/sandbox.py` (`guard_write`).
4. Append a run-log line and a token-tracker entry. (Emailing/sending is out of scope and
   left to the user.)

## Outputs
| Artifact | Location | Format |
|--------|----------|--------|
| Digest | `output/digest-<date>.md` | Markdown |

## Gates
- None: read-only on the network, writes a single local file. Sending is the user's manual step.

## Run log
Append `timestamp,rss-digest,digest,<n_items>` to `output/run-log.csv`, then log the run:
`python _core/token-tracker/tracker.py log --workflow rss-digest --action digest --source local`.
