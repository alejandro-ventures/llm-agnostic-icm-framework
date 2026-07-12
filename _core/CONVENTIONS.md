# _core/CONVENTIONS.md — Behavioral rules for every workflow

Workspace-wide. A `SKILL.md` may add to these but never override them.

## Sandbox boundary (non-negotiable)
1. **Write only inside the workspace.** Never create, edit, move, or delete any file outside
   this repo. Everything outside is read-only reference.
2. **Read reference material minimally.** Pull only what a task needs (irrelevant context hurts
   output and overruns small local-model windows). When using a CLOUD model, be deliberate before
   reading sensitive files — they leave your machine; a LOCAL model keeps everything on-device.
3. **Copy-in to edit.** To change a reference file, copy it into the workflow's `input/` first,
   then work on the copy. The original is never touched.

## Safety
4. **Human gates.** No destructive/irreversible action (delete, overwrite, send, move) without an
   explicit user "yes" in the same turn.
5. **Dry-run first.** Any workflow that changes files writes a reviewable plan before acting.
6. **No secrets.** Never read, print, or commit `.env`, keys, tokens, or credentials.

## Data discipline
7. **Three tiers.** Toolkit (committed) / Data (`input/`, gitignored) / Staging (`output/`, gitignored).
8. **Generic content only.** Commit only reusable code and synthetic examples — never private or
   proprietary data.
9. **Plain text interface.** Stages hand off through readable files a human can open and edit.

## Reproducibility & logging
10. **Per-workflow venv + pinned deps.** Each workflow runs in its own `.venv/` (gitignored) with
    dependencies pinned in its own `requirements.txt`. A venv isolates dependencies, not the system —
    it is not a security sandbox (see `AGENTS.md` → Execution environments and `_core/SANDBOXING.md`).
11. **Path-independent** scripts (derive paths from their own location).
12. **Every run leaves a trail.** Append one line to the workflow's `output/run-log.csv`
    (timestamp, workflow, action, result), AND one entry to the token-tracker:
    `python _core/token-tracker/tracker.py log --workflow <name> --action <action> --source <local|cloud>`
    (see `_core/token-tracker/README.md`). The token log is the business-case substrate; treat it as
    part of finishing a run, not optional.

## Docs
13. **Canonical sources** — each fact has one home; others point to it.
14. **Short contracts** — a `SKILL.md` fits on a screen.
