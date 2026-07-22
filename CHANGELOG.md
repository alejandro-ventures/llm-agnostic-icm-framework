# Changelog

All notable changes to this project are documented here.

## [Unreleased]
### Changed
- `README.md` — added an "At a glance" ASCII architecture diagram: shims → router →
  workflow folders → code-enforced guardrails.
- `NOTICE` — replaced the conditional attribution placeholder with a definitive statement:
  no upstream ICM reference-implementation files are included; MIT notice reproduction is
  required only if that ever changes.

## [2.1.0] - 2026-07-15
Evidence and contracts: honest compatibility claims, a written threat model, machine-checked
workflow contracts, a leak gate — and four new real-use workflows.

### Added
- `COMPATIBILITY.md` — per-client evidence ledger (Verified / Experimental / Conceptual /
  Unsupported); the README's "any LLM-backed assistant" claim narrowed to what's demonstrated.
- `SECURITY.md` — threat model and enforcement map; states the core invariant (processed
  content is data, never instructions) and the honest code-vs-convention line.
- `AGENTS.md` → Instruction precedence — fixed 5-level precedence order, deterministic routing,
  and stop-on-ambiguity for state-changing work.
- SKILL.md contract keys — every workflow's frontmatter now declares `network`, `destructive`,
  and `gates`; `health_check.py` fails the build if any key is missing.
- `_core/scripts/leak_scan.py` — publication gate: scans tree or full history (UTF-16-aware)
  for credential patterns, unlisted emails, and a private terms file that never enters the repo
  (`.leakscan.local`, gitignored). Wired into CI.
- CI now also runs on `windows-latest` (the workspace is PowerShell-heavy; test where it runs).
- New workflows from real use: `transcribe` (fully local ASR + diarization, offline-enforced),
  `background-remove` (documented model decision tree), `data-room-check` (read-only checklist
  audit), `recurrence-review` (mines scratch history, human-gated workflow promotion — ships
  with its own test suite).
- Token-tracker v2 — schema v2 with validated intent keys; writes routed through the sandbox
  guard (`safe_open_w`).

### Changed
- `make_provenance.py` now hashes committed blob content instead of working-tree bytes,
  so the manifest is platform-independent (a CRLF working copy on Windows no longer
  produces a different hash than a CI checkout).
- `PROVENANCE.md` — manifest scope clarified: git-tracked source and docs only; dependencies
  and generated outputs are not covered.

## [2.0.0] - 2026-07-12
From concept demo to hardened workspace: the framework's rules are now enforced by code, not
just documented.

### Added
- `_core/scripts/sandbox.py` — Tier-0 filesystem guardrail: every workflow script routes writes
  through `guard_write(...)`, which refuses out-of-workspace paths and secret files. Ships with a
  self-test (`python _core/scripts/sandbox.py`).
- `_core/SANDBOXING.md` — honest isolation story: explicit threat model, venv-is-not-a-sandbox
  correction, and three isolation tiers (guardrail / disposable Windows Sandbox VM / Docker).
- `_core/scripts/new-sandbox.ps1` — Tier-1 launcher: generates a per-workflow Windows Sandbox
  `.wsb` config that maps only the workspace, networking disabled by default.
- `_core/token-tracker/` — per-run cost accounting (tokens, local-vs-cloud source, human-minutes
  saved) with an aggregating `analyze.py`; the substrate for the automation business case.
- `_core/integrations/` + `_core/scripts/gen-harness-config.py` — MCP connectors defined once in
  a neutral `servers.json`, projected into Codex / Claude / VS Code native config formats.
- `_core/SMALL-MODELS.md` — design rules for workflows that stay safe under small local models:
  route-by-trying, one-command defaults, preflight gates, no improvised paths, enforcement over
  instruction.
- `shared/hooks/deny_secret_read.py` — PreToolUse guard template: denies secret-reading tool
  calls at the harness level (Codex / Claude Code hook protocol).
- `PORTABILITY.md` — the five agnosticism rules and the harness entry-point/MCP-config matrix.
- `workflows/scratch` — routing fallback: tasks that match no specialized workflow get a home
  under the same write-boundary, gates, and logging, instead of an improvised location.
- Per-workflow venvs: each workflow pins its own `requirements.txt`; root `requirements.txt` is
  now tooling-only.
- CI: GitHub Actions runs the structure check and the guardrail self-test on every push/PR.

### Changed
- `ocr-folder` switched to a pure-pip OCR stack (pypdfium2 + RapidOCR/ONNX) — no system
  Tesseract or poppler install needed; per-page routing keeps native text layers and OCRs only
  image pages.
- All example workflow scripts route writes through the sandbox guardrail and log to the
  token-tracker in addition to the per-workflow run log.
- `AGENTS.md`, `ARCHITECTURE.md`, `_core/CONVENTIONS.md`, glossary, onboarding, and templates
  updated for the mechanism layer, the fallback route, and per-workflow venvs.
- `health_check.py` now validates the mechanism layer and per-workflow `requirements.txt`.

## [1.0.0] - 2026-06-28
- Initial public release: `AGENTS.md` router, `_core/` conventions, and three example
  workflows (ocr-folder, file-organizer, rss-digest).
- Tool-agnostic routing: `AGENTS.md` is the single source of truth, with one-line `CLAUDE.md`
  and `.github/copilot-instructions.md` shims.
