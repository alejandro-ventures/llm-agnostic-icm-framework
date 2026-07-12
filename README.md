# LLM-agnostic ICM framework

A personal, **model-agnostic** adaptation of the Interpretable Context Methodology (ICM):
folder structure as agent architecture, runnable under Codex, Claude, GitHub Copilot Chat, a
local model, or any LLM-backed assistant. No orchestration framework — the filesystem is the
architecture, and the rules that matter are enforced by code, not just prose.

This repository contains only generic, reusable framework code, documentation, and synthetic
examples — no private data, credentials, or secrets.

## Quick start
```bash
python _core/scripts/health_check.py        # structure check: expect GO
python _core/scripts/sandbox.py             # guardrail self-test: escape + secret blocked
```
Then open your assistant (Codex reads `AGENTS.md` natively; for others, tell them to read it) and
ask in plain English, e.g. *"OCR the PDFs in workflows/ocr-folder/input."* The single source of
truth is `AGENTS.md`; from there it follows the matching `SKILL.md`. One-line `CLAUDE.md` and
`.github/copilot-instructions.md` shims just redirect Claude Code and Copilot to `AGENTS.md`.
Each workflow runs in its own venv with its own pinned `requirements.txt` (see `AGENTS.md` →
Execution environments).

## What's inside
- `AGENTS.md` — Layer-0 router (model-neutral), with a `scratch` fallback so no task ever
  improvises a write location.
- `PORTABILITY.md` — the five rules that keep the workspace LLM- and harness-agnostic.
- `_core/` — conventions, glossary, onboarding, and the mechanism layer:
  - `scripts/sandbox.py` — filesystem guardrail: out-of-workspace writes and secret files are
    refused *in code*, not just forbidden in prose (`_core/SANDBOXING.md` has the full threat
    model and the tiered isolation story, including a disposable Windows Sandbox VM launcher).
  - `token-tracker/` — every run logs tokens, local-vs-cloud source, and human-minutes saved;
    `analyze.py` turns the log into the automation business case.
  - `integrations/` — MCP connectors defined once, neutrally; `gen-harness-config.py` projects
    them into Codex / Claude / VS Code native configs.
  - `SMALL-MODELS.md` — design rules that make the same workflows safe under small local models.
- `workflows/` — example workflows, each venv-isolated and guardrail-wired:
  - `ocr-folder` — make scanned PDFs searchable (pure-pip ONNX OCR, content-hash cache).
  - `file-organizer` — plan-then-apply folder tidy; never deletes.
  - `rss-digest` — public RSS/Atom feeds into a dated markdown digest.
  - `scratch` — the routing fallback: general tasks under the same boundary, gates, and logging.
- `shared/templates/` — scaffolding for new workflows; `shared/hooks/` — PreToolUse guard
  template that denies secret-reading tool calls at the harness level.
- See `ARCHITECTURE.md` for the design and `_core/CONVENTIONS.md` for the rules.

## Credits & Prior Art

This project is a model-agnostic, VS Code / Copilot Chat-runnable adaptation of the
**Interpretable Context Methodology (ICM)** introduced by Jake Van Clief and David McDermott.
Where ICM uses `CLAUDE.md` as the Layer-0 anchor and targets Claude Code, this work uses
`AGENTS.md` as a model-neutral router so the same folder-as-agent structure runs under any
LLM-backed coding assistant.

- Methodology: Van Clief, J. & McDermott, D. (2026). *Interpretable Context Methodology:
  Folder Structure as Agentic Architecture.* arXiv:2603.16021.
- Reference implementation (MIT): https://github.com/RinDig/Interpreted-Context-Methdology

## License
Apache-2.0 — see `LICENSE`. Attribution and prior-art notes in `NOTICE` and `PROVENANCE.md`.
