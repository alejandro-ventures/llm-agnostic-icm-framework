---
name: scratch
description: >-
  Catch-all fallback for a task that matches no specialized workflow. Gives general input/output a
  home under the same write-boundary, logging, and human gates as every other workflow.
argument-hint: "The task, plus any files to work on (default workflows/scratch/input)"
---
# scratch
Route here ONLY when no specialized workflow in the routing table fits. "General" loosens the task
type, never the rules: every CONVENTIONS rule (write-boundary, copy-in-to-edit, dry-run, human gates,
no secrets, logging) still applies here in full.
## MUST-DO checklist — verify each item BEFORE finishing, none are optional
- [ ] Inputs were COPIED into `input/` (never read other workflows' folders or references in place).
- [ ] Every write went through `_core/scripts/sandbox.py` (`sandbox.guard_write` / `safe_open_w`).
- [ ] Any third-party import is installed in `.venv` AND pinned in `requirements.txt`.
- [ ] One line appended to `output/run-log.csv` AND one token-tracker entry logged.
## Inputs
| Source | Location | Why |
|--------|----------|-----|
| User data | `input/` | material to work on (copy reference files here first — never edit the original) |
| Reference | (read-only material outside the workspace) | context, pulled minimally |
## Process
1. **Confirm the fallback.** If any specialized workflow matches, stop and route there instead.
2. Put user-provided files in `input/`; write every artifact to `output/`. Nothing leaves the workspace.
3. Ad-hoc code goes in `scripts/`; any write must route through `_core/scripts/sandbox.py`
   (`sandbox.guard_write(...)`). Install packages into `.venv` and pin them in `requirements.txt`.
4. **Gate:** any destructive/irreversible step (delete, overwrite, send, move) needs a reviewable
   plan first and an explicit "yes" in the same turn.
5. Append run-log + log to the token-tracker.
6. **Graduation:** if this kind of task recurs, promote it into its own workflow via
   `shared/templates/` rather than letting `scratch` become a junk drawer.
## Outputs
| Artifact | Location | Format |
|--------|----------|--------|
| Result | `output/` | whatever the task needs (readable/plain-text where possible) |
## Gates
- Destructive/irreversible actions need an explicit "yes" (see CONVENTIONS).
## Run log
`timestamp,scratch,<action>,<result>` to `output/run-log.csv`, then
`python _core/token-tracker/tracker.py log --workflow scratch --action <action> --source <local|cloud>`.
