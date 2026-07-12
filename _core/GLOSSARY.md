# _core/GLOSSARY.md — Controlled vocabulary

- **Workspace** — this repo; the only place the assistant writes.
- **Reference** — read-only material outside the workspace; copy-in to edit.
- **Router** — `AGENTS.md`; maps a request to a workflow contract.
- **Workflow** — a single repeatable task living under `workflows/<name>/`.
- **Contract (SKILL.md)** — the agent-readable spec for one workflow: inputs, process, outputs, gates.
- **Toolkit / Data / Staging** — the three data tiers; only Toolkit is committed.
- **Human gate** — a mandatory stop where the agent waits for explicit user approval.
- **Guardrail** — `_core/scripts/sandbox.py`; refuses out-of-workspace writes in code (Tier 0).
- **Run log** — `output/run-log.csv`; one line per run for auditability.
- **Token-tracker** — `_core/token-tracker/`; per-run cost/effort log, the business-case substrate.
