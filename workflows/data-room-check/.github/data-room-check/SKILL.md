---
name: data-room-check
description: >-
  Audit a READ-ONLY reference folder (e.g. a due-diligence data room) against a checklist and
  write a completeness report. Reads only; writes only into output/.
argument-hint: "A reference folder (read-only) + a checklist file"
network: none
destructive: none — the reference folder is never modified
gates: ["auditing a folder the user has not explicitly named this turn"]
---
# data-room-check
## Inputs
| Source | Location | Why |
|--------|----------|-----|
| Reference folder | a read-only root the user explicitly names | the data room (READ-ONLY) |
| Checklist | `references/checklist.example.md` (copy + edit) | expected items |
## Process
1. Confirm the target path is one the user explicitly named (refuse otherwise).
2. List what's present vs. the checklist (read-only — never modify the reference).
3. Write `output/data-room-report-<date>.md` (present / missing / notes).
4. Append run-log.
## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Report | `output/data-room-report-<date>.md` | Markdown |
## Gates
- Read-only on the reference; only writes into `output/`. No destructive steps.
## Run log
`timestamp,data-room-check,audit,<n_present>` to `output/run-log.csv`.
