# recurrence-review

Deterministically review structured `scratch` history and suggest a specialized workflow after three
successful occurrences on at least two Europe/Zurich dates in a rolling 90-day window. Evidence,
proposals, decisions, and drafts remain device-local and gitignored.

## Commands

From the workspace root, using this workflow's virtual environment:

    python -m venv workflows/recurrence-review/.venv
    workflows/recurrence-review/.venv/Scripts/python -m pip install -r workflows/recurrence-review/requirements.txt
    workflows/recurrence-review/.venv/Scripts/python workflows/recurrence-review/scripts/review.py scan

Human decisions require an explicit approval flag and the matching same-turn user approval:

    ... review.py decide <intent-key> snoozed --days 90 --approved
    ... review.py decide <intent-key> rejected --approved
    ... review.py decide <intent-key> reopened --approved
    ... review.py scaffold <intent-key> --approved
    ... review.py promotion-plan <intent-key>
    ... review.py promote <intent-key> --draft <path> --plan-hash <hash> --approved

Gate 1 writes only under `output/drafts/`. Gate 2 copies the reviewed draft into `workflows/`, backs
up and updates `AGENTS.md`, runs the health check, and records promotion. It never commits, pushes,
moves, or deletes.

## Schedulers

Codex is the primary adapter: use a standalone local-project task in the main checkout every Monday
at 09:00 Europe/Zurich. Its prompt must run only `review.py scan`, report new proposal paths, and
return a terse no-change result otherwise. Local scheduling requires the computer and desktop app to
be running; every run remains visible in Scheduled.

The Windows adapter is disabled by default. Preview it without changing Task Scheduler:

    powershell -ExecutionPolicy Bypass -File workflows/recurrence-review/scripts/install_windows_task.ps1

Install or uninstall only after explicit approval:

    ... install_windows_task.ps1 -Mode Install -Approved
    ... install_windows_task.ps1 -Mode Uninstall -Approved

Task Scheduler uses the machine's local timezone and invokes the same venv and `scan` command.

## Requirements

Standard library only; see `requirements.txt`.
