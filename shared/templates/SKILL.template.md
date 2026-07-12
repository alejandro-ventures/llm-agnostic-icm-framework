---
name: <workflow-name>
description: >-
  <one line: what it does and when to use it>
argument-hint: "<what to provide>"
requires-python: "3.9+"
---
# <Workflow name>

## Environment
This workflow runs in its own venv at `.venv/` (gitignored — it never enters git history). Set up
from this workflow folder:
- Windows PowerShell: `python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt`
- macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

A `requirements.txt` is always present; if the workflow uses only the standard library, it says so in
a comment. A venv isolates dependencies, not the system — it is not a security sandbox (see
`_core/SANDBOXING.md` before running unvetted code or touching sensitive data).

## Inputs
| Source | Location | Why |
|--------|----------|-----|
| User data | `input/` | material to process |
| Reference | (read-only material outside the workspace) | context, pulled minimally |

## Process
1. <step — mark human gates explicitly>

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| <artifact> | `output/` | <format> |

## Gates
- <destructive/irreversible steps need an explicit "yes">

## Run log
Append `timestamp,<workflow>,<action>,<result>` to `output/run-log.csv`, then log the run to the
token-tracker (see CONVENTIONS):
`python _core/token-tracker/tracker.py log --workflow <name> --action <action> --source <local|cloud>`.
