# AGENTS.md — Workspace Router (Layer 0)

Model-agnostic entry point. Any LLM-backed coding assistant (GitHub Copilot Chat,
Claude, Cursor, Codex, etc.) reads this file FIRST to learn where it is and how to route.
This is the model-neutral equivalent of a `CLAUDE.md` anchor.

## How to use this workspace
1. Read this file, then `_core/CONVENTIONS.md`.
2. Match the user's request to a workflow in the routing table.
3. Open that workflow's contract and follow it exactly.
4. Do NOT load workflow folders that don't match the request (keeps context small).
5. Stop at every irreversible step for explicit human approval.

## Routing table
| Workflow | Use when the user wants to… | Contract |
|----------|------------------------------|----------|
| `ocr-folder` | make a folder of scanned / image-only PDFs text-searchable | `workflows/ocr-folder/.github/ocr-folder/SKILL.md` |
| `file-organizer` | analyze and reorganize a messy folder with a reviewable plan | `workflows/file-organizer/.github/file-organizer/SKILL.md` |
| `rss-digest` | turn public RSS/Atom feeds into a scheduled markdown digest | `workflows/rss-digest/.github/rss-digest/SKILL.md` |

## Data tiers (see `_core/CONVENTIONS.md`)
- **Toolkit** — generic, exportable: this file, `_core/`, `shared/`, every `SKILL.md` and script. Committed.
- **Data** — user-specific inputs you supply locally (`workflows/*/input/`). Gitignored.
- **Staging** — transient outputs and caches (`workflows/*/output/`, `*_cache/`). Gitignored.

## Adding or removing a workflow
Copy `shared/templates/` into `workflows/<name>/`, add one row above, and (only if you
introduce a new required file) update `_core/scripts/health_check.py`. Everything else is
local to the workflow folder, so workflows never interfere with each other.
