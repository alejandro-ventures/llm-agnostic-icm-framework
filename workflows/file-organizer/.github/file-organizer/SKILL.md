---
name: file-organizer
description: >-
  Analyze a messy folder and propose a reorganization. Produces a reviewable PLAN
  first; only applies changes after explicit user approval. Never deletes.
argument-hint: "Path to a folder to analyze (defaults to workflows/file-organizer/input)"
requires-python: "3.9+"
network: none
destructive: none — copies only, never deletes; apply step requires approval
gates: ["applying the reorganization plan"]
---

# file-organizer

## Environment
Runs in its own venv at `.venv/` (gitignored); standard library only — `requirements.txt`
says so. From this workflow folder:
- Windows PowerShell: `python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt`
- macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

## Inputs
| Source | Location | Why |
|--------|----------|-----|
| Folder to tidy | `input/` | files to analyze (gitignored) |
| Rules | `references/rules.example.md` | how to group/rename |

## Process
1. Walk the input folder; classify files by type/date/name per the rules.
2. Write a move/rename PLAN to `output/plan.csv` (from -> to). Move nothing yet.
3. **Gate:** show the plan; wait for explicit user "yes".
4. On approval, apply moves (copy-then-verify, never delete originals). Every destination
   is checked by `_core/scripts/sandbox.py` (`guard_write`) — it cannot leave the workspace.
5. Append a run-log line and a token-tracker entry.

## Outputs
| Artifact | Location | Format |
|--------|----------|--------|
| Proposed plan | `output/plan.csv` | from,to |

## Gates
- Applying the plan requires explicit user "yes". Originals are never deleted.

## Run log
Append `timestamp,file-organizer,<plan|apply>,<n_items>` to `output/run-log.csv`, then log the run:
`python _core/token-tracker/tracker.py log --workflow file-organizer --action <plan|apply> --source local`.
