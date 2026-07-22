# LLM-agnostic ICM framework

A personal, **model-agnostic** adaptation of the Interpretable Context Methodology (ICM):
folder structure as agent architecture. Verified today under GitHub Copilot Chat and Claude
Code, experimental under Codex CLI and small local models — `COMPATIBILITY.md` is the honest
ledger of what has actually been demonstrated, per client. No orchestration framework — the
filesystem is the architecture, and the rules that matter are enforced by code, not just prose.

This repository contains only generic, reusable framework code, documentation, and synthetic
examples — no private data, credentials, or secrets.

## At a glance

```text
GitHub Copilot ──► .github/copilot-instructions.md ─┐
Claude Code ─────► CLAUDE.md ───────────────────────┤  one-line shims —
Codex CLI ───────► (reads AGENTS.md natively) ──────┘  one source of truth
                                                    │
                  ┌─────────────────────────────────┴───┐
                  │ AGENTS.md — Layer-0 router          │
                  │ fixed instruction precedence,       │
                  │ deterministic routing               │
                  └──────────────────┬──────────────────┘
                                     │  "OCR the PDFs in …/input"
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
  workflows/ocr-folder/     workflows/transcribe/     workflows/scratch/
  ├ SKILL.md (contract)     + 5 more, same shape:     the routed fallback —
  ├ own venv, pinned deps   contract, venv, gates,    unplanned tasks land
  └ input/ ──► output/      logs — one folder each    here, same gates + logs
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     ▼
             enforced in code, not prose — on every run:
             sandbox.py      out-of-workspace writes & secret files refused
             shared/hooks/   secret-reading tool calls denied at the harness
             token-tracker   tokens, local-vs-cloud source, minutes saved
```

The filesystem is the architecture: one router file, one folder per workflow, and the rules
that matter enforced by scripts every run has to pass through.

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
- `AGENTS.md` — Layer-0 router (model-neutral), with fixed instruction precedence, deterministic
  routing, and a `scratch` fallback so no task ever improvises a write location.
- `PORTABILITY.md` — the five rules that keep the workspace LLM- and harness-agnostic.
- `COMPATIBILITY.md` — which clients are Verified / Experimental / Conceptual, and what each
  status actually means.
- `SECURITY.md` — the threat model and the map of which rules are enforced by code vs. convention.
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
  - `transcribe` — call recordings into speaker-labeled transcripts, fully local (whisper +
    pyannote, offline-enforced after a one-time gated model download).
  - `background-remove` — image backgrounds removed to transparent PNGs, with a documented
    model decision tree.
  - `data-room-check` — audit a read-only folder against a checklist; report only, never touches
    the reference.
  - `recurrence-review` — mine `scratch` run history for recurring tasks and propose new
    workflows, with two human gates (scaffold, then hash-pinned router promotion).
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
