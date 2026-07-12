# Architecture

The structure **is** the agent. There is no orchestration framework — the filesystem
encodes it, and any LLM-backed assistant follows it by reading files.

- **Layer 0 — `AGENTS.md`** (model-neutral router). Maps a request to a workflow contract;
  ends in a `scratch` fallback row so no task ever improvises a write location.
- **Layer 1 — `workflows/<name>/.github/<name>/SKILL.md`** (the contract). Inputs, process,
  outputs, and human gates for one workflow.
- **Shared infrastructure — `_core/`**. Conventions, glossary, onboarding, and the mechanism
  layer described below.
- **Templates — `shared/templates/`**. Copy to scaffold a new workflow. `shared/hooks/` holds
  harness-level guard templates (PreToolUse deny hooks).

## Why AGENTS.md instead of CLAUDE.md
The Interpretable Context Methodology (ICM) anchors on a `CLAUDE.md` file and targets Claude
Code. This project uses `AGENTS.md` as a model-neutral Layer-0 anchor so the identical
folder-as-agent structure runs under GitHub Copilot Chat, Claude, Cursor, Codex, or any
assistant — that portability is the contribution of this repository. `PORTABILITY.md` holds
the rules that keep it that way. See Credits in `README.md`.

## The mechanism layer (`_core/`)
Rules that only live in prose can be ignored by a model that doesn't read carefully, so the
critical ones are backed by code:

- **Write boundary → `_core/scripts/sandbox.py`.** Every workflow script imports it and routes
  write destinations through `guard_write(...)`, which refuses paths outside the workspace and
  secret files. Tiered isolation above that (disposable Windows Sandbox VM, Docker) is
  documented in `_core/SANDBOXING.md`, threat model included.
- **Secret reads → `shared/hooks/deny_secret_read.py`.** A PreToolUse hook that denies
  credential-touching tool calls at the harness level.
- **Cost accounting → `_core/token-tracker/`.** Every run logs tokens, local-vs-cloud source,
  and human-minutes saved; `analyze.py` turns the log into the automation business case.
- **Connectors → `_core/integrations/servers.json`.** MCP servers defined once, neutrally;
  `gen-harness-config.py` projects them into each harness's native config format.
- **Small-model robustness → `_core/SMALL-MODELS.md`.** Design rules (route-by-trying,
  one-command defaults, preflight gates, no improvised paths) that make the same workflows
  safe under 7B-class local models.

## Execution model
Each workflow runs in its own venv with its own pinned `requirements.txt` (a venv isolates
dependencies, not the system — see SANDBOXING.md). Stages hand off through plain-text files;
every run appends to a run log and the token-tracker. Destructive steps stop at human gates.

## Data tiers
Toolkit (committed) / Data (`input/`, gitignored) / Staging (`output/`, gitignored). Cloning the
repo gives a new user the Toolkit; they add their own Data and run.
