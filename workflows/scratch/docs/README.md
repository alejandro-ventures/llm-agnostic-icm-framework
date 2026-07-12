# scratch

Human guide for the catch-all workflow. `scratch` is where a task lands when it matches none of the
specialized workflows — a general home for input/output that still obeys the workspace's write
boundary, gates, and logging. It ships no fixed script; you (or the assistant) write task-specific
code into `scripts/` as needed.

## Set up the venv (first time)
From this workflow folder:

PowerShell (Windows):

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt

bash / zsh (macOS/Linux):

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

If activation is blocked on Windows, allow it for the current shell only:
`Set-ExecutionPolicy -Scope Process RemoteSigned`.

## Run
There is no single entry script. Put material to work on in `input/`, write results to `output/`, and
run whatever ad-hoc script the task needs from this folder:

    python scripts/<script>.py [args]

Any script that writes must route its output through `_core/scripts/sandbox.py`.

## Requirements
`requirements.txt` starts stdlib-only. When a task needs a third-party package, install it into this
venv and pin it in `requirements.txt` so the run stays reproducible.

## When to graduate
If you keep coming back to `scratch` for the same kind of task, that's the signal to turn it into its
own workflow: copy `shared/templates/` into `workflows/<name>/` and add a routing-table row.
