# Changelog

All notable changes to this project are documented here.

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
