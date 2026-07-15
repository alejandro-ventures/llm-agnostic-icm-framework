# SECURITY.md — threat model and enforcement map

This is a personal reference implementation, not a supported product. What it offers instead of
an SLA: the rules that matter are enforced by code, and this file says exactly which ones.

## The invariant
**Processed content is data, never instructions.** Text inside an input file — a PDF being
OCRed, a feed entry, a filename — must never change routing, rules, or gates. Instruction
precedence is fixed (see `AGENTS.md` → Instruction precedence); input content sits at the
bottom, permanently. A file that says "ignore previous instructions" is a file that says that.

## Threat model
| Threat | Mitigation | Enforced by |
|--------|------------|-------------|
| Script writes outside the workspace (bug or hallucination) | every write routes through `guard_write()` / `safe_open_w()` — out-of-workspace paths raise | code — `_core/scripts/sandbox.py`, self-tested in CI |
| Reading or leaking credentials | secret-pattern paths (`.env`, `*.key`, `credentials.*`, …) refused on read AND write; harness-level PreToolUse denial | code — `sandbox.py` + `shared/hooks/deny_secret_read.py` |
| Prompt injection via processed files | content-is-data invariant; workflows never execute instructions found in inputs; ambiguity stops state-changing work | convention — `AGENTS.md`, backed by gates |
| Destructive action without consent | human gate: explicit "yes" in the same turn for delete/overwrite/send; dry-run plans before file changes | convention — CONVENTIONS rules 4–5, written into every `SKILL.md` |
| Secrets committed to the repo | `.gitignore` secret patterns; `health_check.py` fails on tracked sensitive files; `leak_scan.py` scans tree and history for credential patterns | code — CI runs both on every push |
| Untrusted or unvetted code | disposable Windows Sandbox VM launcher for anything not hand-reviewed | tooling — `_core/scripts/new-sandbox.ps1`, `_core/SANDBOXING.md` |
| Dependency supply chain | per-workflow venvs with pinned `requirements.txt`; no install hooks; stdlib-only core scripts | convention + structure check |

## Network default
Workflows are **offline by default**. A workflow that needs the network declares it in its
`SKILL.md` frontmatter (`network:` key, validated by `health_check.py`); everything else states
`network: none`. Today exactly one workflow declares outbound access (`rss-digest`, to
user-listed public feeds).

## Code-enforced vs. convention — the honest line
A pure-Python guard stops bugs and accidents, which are the dominant real risk of AI-generated
code. It does not stop a determined adversary — `sandbox.py` says this in its docstring, and
`_core/SANDBOXING.md` describes the tiered isolation (Windows Sandbox VM) for that case. Claims
here are scoped accordingly.

## Reporting
Security issue in the framework itself: open a GitHub issue, or mail alejandro.ventures@pm.me
for anything sensitive.
