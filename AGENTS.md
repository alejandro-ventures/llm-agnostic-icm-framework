# AGENTS.md — Workspace Router (Layer 0)

Model-agnostic entry point. Any LLM-backed assistant (Codex, Claude, GitHub Copilot Chat, a
local model, a CLI) reads this file FIRST to learn where it is and how to route. The `CLAUDE.md`
and `.github/copilot-instructions.md` files are one-line shims that redirect here — this file is
the single source of truth. The rules that keep this workspace LLM- and harness-agnostic (what each
harness reads, integrations-as-adapters, no Copilot-only `applyTo`) live in `PORTABILITY.md`.

## How to use this workspace
1. Read this file, then `_core/CONVENTIONS.md`.
2. Match the user's request to a workflow in the routing table below. If no specialized workflow
   fits, route to `scratch` — the catch-all fallback (last row). Never improvise a write location.
3. Open that workflow's `SKILL.md` contract and follow it exactly.
4. Do NOT load workflow folders that don't match the request (keeps context small — this matters
   for small local-model windows; see `_core/SMALL-MODELS.md`).
5. Stop at every irreversible step for explicit human approval (CONVENTIONS rules 4–6).

## The one hard boundary
Write ONLY inside this workspace. Anything outside it is read-only reference. To change an
outside file, copy it into a workflow's `input/` first, then work on the copy. The original is
never touched.

## Routing table
| Workflow | Use when the user wants to… | Contract |
|----------|------------------------------|----------|
| `ocr-folder` | make scanned / image-only PDFs text-searchable | `workflows/ocr-folder/.github/ocr-folder/SKILL.md` |
| `file-organizer` | analyze a messy folder and reorganize it from a reviewable plan (copies, never deletes) | `workflows/file-organizer/.github/file-organizer/SKILL.md` |
| `rss-digest` | turn public RSS/Atom feeds into a dated markdown digest | `workflows/rss-digest/.github/rss-digest/SKILL.md` |
| `scratch` | **(fallback)** do anything that matches none of the workflows above — general input/output under the same write-boundary, gates, and logging | `workflows/scratch/.github/scratch/SKILL.md` |

## Data tiers (see `_core/CONVENTIONS.md`)
- **Toolkit** — generic, committed: this file, `_core/`, `shared/`, every `SKILL.md` and script.
- **Data** — user-supplied inputs (`workflows/*/input/`). Gitignored.
- **Staging** — transient outputs and caches (`workflows/*/output/`, `*_cache/`, `run-log.csv`). Gitignored.

## Execution environments (per-workflow venv)
- Every workflow runs inside its own Python virtual environment at `workflows/<name>/.venv/`.
- `.gitignore` excludes `.venv/` and `venv/`: the env lives on-device only and never enters git history.
- Each workflow pins its own dependencies in `workflows/<name>/requirements.txt` and installs them
  into that venv. A stdlib-only workflow still keeps a `requirements.txt` (with a note) for consistency.
- Set up / activate, run from the workflow folder:
  - Windows PowerShell: `python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt`
  - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- **A venv isolates dependencies, not the system.** It is NOT a security sandbox: code inside a venv
  still runs with your full user permissions and full network/filesystem access. Two layers add real
  protection: (1) every workflow script routes its writes through `_core/scripts/sandbox.py`, which
  refuses to write outside the workspace or to any secret file; (2) for unvetted code or sensitive
  material, run it in a disposable Windows Sandbox VM via `_core/scripts/new-sandbox.ps1`. Both are
  documented in `_core/SANDBOXING.md`, with the human gates in CONVENTIONS rules 4–6 as the control
  that works on every device.

## Adding a workflow
Copy `shared/templates/` into `workflows/<name>/`, fill in its `SKILL.md` + `docs/README.md`, create
its `.venv` and `requirements.txt`, and add one row to the routing table above. Any script that writes
must import `_core/scripts/sandbox.py` and route its output through `sandbox.guard_write(...)` (see
SANDBOXING.md → Tier 0). Only if you introduce a new *required* file, update
`_core/scripts/health_check.py`. Everything else stays local to the workflow folder, so workflows
never interfere with each other.
