# _core/CONVENTIONS.md — Behavioral rules for every workflow

These rules apply workspace-wide. A workflow's `SKILL.md` may add to them but never override them.

## Routing & context
1. **One router.** `AGENTS.md` is the only routing table. Read it first, every session.
2. **Load narrowly.** Open only the matched workflow folder. Less irrelevant context = better output.
3. **One stage, one job.** Each workflow does one thing. If a request spans two, run them in sequence.

## Safety
4. **Human gates are non-negotiable.** No destructive or irreversible action (delete, overwrite,
   send, move) runs without an explicit user "yes" in the same turn.
5. **Dry-run first.** Any workflow that changes files produces a reviewable *plan* before it acts.
6. **No secrets, ever.** Never read, print, or commit `.env`, keys, tokens, or credentials.

## Data discipline
7. **Three tiers.** Toolkit (committed), Data (`input/`, gitignored), Staging (`output/`, gitignored).
8. **Generic content only.** Commit only reusable code and synthetic examples — never private or proprietary data.
9. **Plain text as the interface.** Stages hand off through readable files a human can open and edit.

## Reproducibility
10. **Pinned deps.** `requirements.txt` declares dependencies; keep it current.
11. **Path-independent.** Scripts derive paths from their own location, not a hardcoded machine path.
12. **Every run leaves a trail.** Workflows append one line to `output/run-log.csv` (timestamp, workflow, action, result).

## Documentation
13. **Canonical sources.** Each fact has one home; other files point to it, never copy it.
14. **Docs over outputs.** Agents learn how to build from `docs/` and `references/`, not from prior outputs.
15. **Contracts are short.** A `SKILL.md` fits on a screen: what it reads, what it does, what it writes.
