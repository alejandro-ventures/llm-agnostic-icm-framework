# _core/ONBOARDING.md — Stand this up in ten minutes

1. **Clone** the repo and open the folder in your editor.
2. **Verify structure:** `python _core/scripts/health_check.py` — expect `GO`.
3. **Self-test the guardrail:** `python _core/scripts/sandbox.py` — it should allow an
   in-workspace path and block an escape + a secret file.
4. **Open your assistant.** Codex reads `AGENTS.md` natively; Claude Code and Copilot are
   redirected there by one-line shims; for anything else, tell it to read `AGENTS.md`.
5. **Ask in plain English**, e.g. *"OCR the PDFs in workflows/ocr-folder/input."* The agent
   routes via the table, reads the matching `SKILL.md`, and walks the stages, pausing at each
   human gate. Each workflow sets up its own venv from its own `requirements.txt` on first use
   (see `AGENTS.md` → Execution environments).
6. **Your data stays local.** Put inputs in a workflow's `input/`; results land in `output/`.
   Both are gitignored, as are the run logs and the token-tracker's `usage-log.jsonl`.
7. **Optional — MCP connectors:** define servers once in `_core/integrations/servers.json`,
   then generate your harness's native config: `python _core/scripts/gen-harness-config.py all`.
8. **After a run:** `python _core/token-tracker/analyze.py` shows runs, tokens, and
   human-minutes saved per workflow — the automation business case, from day one.
