# <Workflow name>

Human guide for running this workflow outside the AI-assistant context — e.g. by hand or from a
script.

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
With the venv active, from this workflow folder:

    python scripts/<main-script>.py [args]

## Requirements
See `requirements.txt` — install via `pip install -r requirements.txt` while the venv is active. If
no third-party packages are listed, this workflow uses only Python's standard library.
