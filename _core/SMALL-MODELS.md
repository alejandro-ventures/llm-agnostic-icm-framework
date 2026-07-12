# _core/SMALL-MODELS.md — designing workflows small local models can't break

Harness-agnostic includes model-agnostic: the same workspace must run under a frontier cloud
model AND a small local model (7B–35B) with a limited context window. Small models fail
differently — they hallucinate tools, misjudge their own capability, and improvise when a
step errors. Every rule below was earned by testing workflows against small local models and
watching where they broke. None of these rules hurt a strong model; all of them save a weak one.

## 1. Route by trying, never by self-assessment
Never write "if you are a capable model, do X; otherwise Y." A model cannot reliably judge its
own capability — and that misjudgment is exactly what small models get wrong. Decide
mechanically instead: attempt the richer path with **one real test call**; if the probe errors
or the model can't emit it, drop to the fallback. Capability is demonstrated, not declared.

## 2. Default to the one-command path
Every workflow that touches anything risky should have a single vetted command that does the
whole job (`python scripts/<main>.py`), and the contract should present it as the default.
A small model that runs one known-good script is safe; a small model improvising against an
open-ended toolbox is not. The rich interactive path (MCP tools, iterative search) is the
*upgrade*, gated by rule 1 — not the baseline.

## 3. Close the improvisation door
Contracts enumerate Path A (rich) and Path B (one command) — and then say explicitly: **never
invent a Path C.** If A is unusable and B fails, the correct behavior is to STOP and report,
not to hand-roll the protocol the vetted script encapsulates (raw IMAP, raw HTTP, ad-hoc file
surgery). Small models treat silence as permission; deny the invented path in writing.

## 4. Preflight gates — check mechanically before acting expensively
Put a cheap, deterministic check in front of every expensive or risky stage: config present,
port open, disk space, input not truncated. Preflights fail with *instructions* ("start the
service, then re-run"), never with questions — a small model given a question mid-run will
answer it itself, wrongly. The pattern: `scripts/preflight.py` runs in seconds, exits nonzero
with a one-line fix, and the contract says to run it whenever the main path fails.

## 5. Enforcement beats instruction
A rule that only lives in the prompt can be ignored by a model that doesn't read carefully —
so back the critical rules with mechanism:
- **Write boundary** → `_core/scripts/sandbox.py` refuses out-of-workspace writes in code.
- **Secret reads** → a `PreToolUse` hook (`shared/hooks/deny_secret_read.py`) inspects every
  pending tool call at the harness level and *denies* any that would read a credential file,
  before it runs. Even if the model ignores the contract, the harness refuses.
Make the failure impossible, not just forbidden. Instructions are the fallback layer, not the
only layer.

## 6. Vetted scripts, not inline code
No heredocs, no `python -c` blobs, no regenerating logic that a `scripts/` file already
encapsulates. Inline code re-derives solved problems (quoting, protocol quirks, encoding) and
is where small models spend their error budget. If a task needs new code, it goes into a file
in `scripts/`, gets reviewed, and becomes part of the workflow.

## 7. Context discipline
Small windows overflow fast, and an overflowed model silently forgets its rules. This is why
the router says *load only the matched workflow folder*, why contracts must fit on a screen,
and why stages hand off through plain-text files instead of conversation memory. Token
frugality is not an optimization here — it is a correctness requirement.

## Author checklist for a new workflow
- [ ] One-command default path exists and is first in the contract.
- [ ] Richer path is gated by a mechanical probe (rule 1), not capability language.
- [ ] "Never invent a Path C — stop and report" appears verbatim.
- [ ] Preflight script covers every external dependency the main path needs.
- [ ] Secrets are read only *inside* vetted scripts, never surfaced to the model; a deny-hook
      covers the credential paths.
- [ ] Every write routes through `sandbox.guard_write`.
- [ ] The contract fits on one screen.
