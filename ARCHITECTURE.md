# Architecture

The structure **is** the agent. There is no orchestration framework — the filesystem
encodes it, and any LLM-backed assistant follows it by reading files.

- **Layer 0 — `AGENTS.md`** (model-neutral router). Maps a request to a workflow contract.
- **Layer 1 — `workflows/<name>/.github/<name>/SKILL.md`** (the contract). Inputs, process,
  outputs, and human gates for one workflow.
- **Shared infrastructure — `_core/`**. Conventions, glossary, onboarding, and a structure
  health check that every workflow inherits.
- **Templates — `shared/templates/`**. Copy to scaffold a new workflow.

## Why AGENTS.md instead of CLAUDE.md
The Interpretable Context Methodology (ICM) anchors on a `CLAUDE.md` file and targets Claude
Code. This project uses `AGENTS.md` as a model-neutral Layer-0 anchor so the identical
folder-as-agent structure runs under GitHub Copilot Chat, Claude, Cursor, Codex, or any
assistant — that portability is the contribution of this repository. See Credits in `README.md`.

## Data tiers
Toolkit (committed) / Data (`input/`, gitignored) / Staging (`output/`, gitignored). Cloning the
repo gives a new user the Toolkit; they add their own Data and run.
