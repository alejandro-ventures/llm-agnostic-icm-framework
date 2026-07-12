# PORTABILITY.md — staying LLM- and harness-agnostic

The north star: this workspace runs the same whether driven by a local model, Codex, Claude,
GitHub Copilot, or a plain CLI. ICM's reference implementation anchors on Claude Code; this
framework is deliberately anchored on nothing. The rules below are how it stays that way.

## What each harness reads
| Harness | Entry point it auto-loads | MCP config it reads |
|---------|---------------------------|---------------------|
| Codex | `AGENTS.md` (native) | `~/.codex/config.toml` |
| Claude | `CLAUDE.md` shim -> `AGENTS.md` | `.mcp.json` |
| GitHub Copilot | `.github/copilot-instructions.md` shim -> `AGENTS.md` | `.vscode/mcp.json` |
| Local model / CLI | told to read `AGENTS.md` | n/a or harness-specific |

`AGENTS.md` is the single source of truth. `CLAUDE.md` and `.github/copilot-instructions.md` are
one-line shims that redirect to it and contain no rules of their own.

## The five agnosticism rules
1. **One router, thin shims.** All routing lives in `AGENTS.md`. Never put behavioral rules in a
   shim — a rule that only Copilot or only Claude sees breaks parity.
2. **No harness-only routing magic.** Copilot can auto-attach skills via `applyTo:` frontmatter
   globs. Do NOT adopt that here — route via the `AGENTS.md` table, which every harness reads.
   Skills are found by the router, not by an editor feature.
3. **Tooling in Python, not PowerShell.** `health_check.py`, `sandbox.py`, `tracker.py`,
   `gen-harness-config.py` are stdlib Python so they run under any harness and OS. Reserve PowerShell
   for genuinely OS-specific extras (the Windows Sandbox launcher), never for core logic.
4. **Integrations are adapters, not lock-in.** Define MCP servers / connectors once in
   `_core/integrations/servers.json`; generate each harness's native config with
   `_core/scripts/gen-harness-config.py`. The repo stays neutral; each harness gets a generated adapter.
5. **Model-neutral, secrets externalized.** Choose local vs cloud per task on the privacy axis
   (the token-tracker `source` field) — never hard-code a model. Secrets live in `.env`, referenced
   by name; never inlined into a committed config.

## Adding a new harness
Add a row to the table above, add a shim if it auto-loads one (pointing at `AGENTS.md`), and add an
emitter to `gen-harness-config.py` for its MCP config format. Nothing else should need to change —
if it does, that's a portability leak worth fixing.
