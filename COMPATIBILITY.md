# COMPATIBILITY.md — tested clients, honestly labeled

"Model-agnostic" is a design goal; this file is the evidence ledger for it. Every client below
is labeled with what has actually been demonstrated — nothing is claimed as universal.

## Status vocabulary
- **Verified** — real workflows have been routed and completed end-to-end under this client.
- **Experimental** — routing works in smoke tests; no systematic pass across all workflows.
- **Conceptual** — expected to work by design (the entry point is plain markdown), not yet run.
- **Unsupported** — known not to work, or requires features this workspace refuses to depend on.

## Client matrix
| Client | Entry point | Status | Notes |
|--------|-------------|--------|-------|
| GitHub Copilot Chat (VS Code) | `.github/copilot-instructions.md` → `AGENTS.md` | **Verified** | Primary development harness for this repo. |
| Claude Code (CLI / desktop) | `CLAUDE.md` → `AGENTS.md` | **Verified** | Shim auto-loads; hooks in `shared/hooks/` are written for its PreToolUse interface. |
| OpenAI Codex CLI | `AGENTS.md` (native) | **Experimental** | `AGENTS.md` is Codex's native convention; smoke-tested routing, no systematic pass. |
| Small local models, 7–35B (LM Studio, Ollama) | `AGENTS.md` via harness | **Experimental** | The design rules in `_core/SMALL-MODELS.md` were each earned by testing against small models; a published all-workflow matrix does not exist yet. |
| Any other assistant that reads a markdown entry point | `AGENTS.md` | **Conceptual** | Nothing here requires more than reading files and running Python. |

## What compatibility requires of a client
1. Read `AGENTS.md` first (natively or by being told to) and follow file references.
2. Run Python 3.9+ scripts and report their output.
3. Respect stop-and-ask gates (CONVENTIONS rules 4–6) — a client that cannot pause for human
   approval must not run destructive steps.

## What is deliberately NOT required
Harness-specific config formats, MCP servers, or vendor extensions. Integrations are defined
once in `_core/integrations/servers.json` and *projected* into native configs by
`_core/scripts/gen-harness-config.py` — the workspace never depends on any one harness's format
(`PORTABILITY.md` has the rules).

## Promotion policy
A client moves to **Verified** only when every workflow in the routing table has been exercised
under it end-to-end (route → contract → gates → run-log). Until then it stays honestly labeled.
