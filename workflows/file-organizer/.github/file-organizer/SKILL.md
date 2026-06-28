---
name: file-organizer
description: >-
  Analyze a messy folder and propose a reorganization. Produces a reviewable PLAN
  first; only applies changes after explicit user approval. Never deletes.
argument-hint: "Path to a folder to analyze (defaults to workflows/file-organizer/input)"
---

# file-organizer

## Inputs
| Source | Location | Why |
|--------|----------|-----|
| Folder to tidy | `input/` | files to analyze (gitignored) |
| Rules | `references/rules.example.md` | how to group/rename |

## Process
1. Walk the input folder; classify files by type/date/name per the rules.
2. Write a move/rename PLAN to `output/plan.csv` (from -> to). Move nothing yet.
3. **Gate:** show the plan; wait for explicit user "yes".
4. On approval, apply moves (copy-then-verify, never delete originals).
5. Append a run-log line.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Proposed plan | `output/plan.csv` | from,to |

## Gates
- Applying the plan requires explicit user "yes". Originals are never deleted.

## Run log
Append `timestamp,file-organizer,<plan|apply>,<n_items>` to `output/run-log.csv`.
