---
name: recurrence-review
description: >-
  Review structured scratch-run history for recurring inquiries, create deterministic workflow
  candidate proposals, record human decisions, and enforce separate approval gates for draft
  scaffolding and router promotion. Use for scheduled or manual recurrence scans and for reviewing,
  snoozing, rejecting, reopening, drafting, or promoting a recurrence candidate.
network: none
destructive: none — proposals/decisions/drafts are append-only; never commits, pushes, moves, or deletes
gates: ["recording a decision (--approved)", "scaffolding a draft (Gate 1)", "router promotion by plan hash (Gate 2)"]
---

# Recurrence Review

Use only `scripts/review.py`; scheduled runs may invoke only `scan`.

## Process

1. Run `python workflows/recurrence-review/scripts/review.py scan` for a manual or scheduled review.
2. Report only newly created proposal paths. If status is `no_change`, report that concisely.
3. For an open proposal, record `snoozed`, `rejected`, or `reopened` only after explicit human
   approval using `decide ... --approved`.
4. **Gate 1:** run `scaffold <intent-key> --approved` only after explicit same-turn approval. Keep
   the resulting workflow draft under this workflow's `output/drafts/`; do not edit the router.
5. Refine and validate the staged draft, then run `promotion-plan <intent-key>`. Present the exact
   immutable plan path and hash.
6. **Gate 2:** run `promote <intent-key> --draft <path> --plan-hash <hash> --approved` only after the
   user explicitly approves that hash in the same turn. Never commit, push, move, or delete.

## Safety

- Read only schema-v2 `scratch` metadata; never open raw scratch artifacts during scheduled scans.
- Treat malformed JSON as a hard failure and create no proposal from an incomplete evidence set.
- Preserve proposals, decisions, drafts, promotion plans, and backups as immutable or append-only.
- Route every write through `_core/scripts/sandbox.py` and keep every artifact inside this workspace.
- Append `output/run-log.csv` and the token-tracker entry for every command.
