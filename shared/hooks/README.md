# shared/hooks — harness-level guards (PreToolUse)

`deny_secret_read.py` is a **PreToolUse hook** (Codex / Claude Code protocol): it inspects
every pending tool call and **denies** any whose input mentions a secret path — reading the
file, discovering its location, or piping it anywhere. This is the enforcement layer behind
`_core/SMALL-MODELS.md` rule 5: even if a model ignores the workflow contract, the harness
refuses the call. Sanctioned scripts that read their credential inside their own process pass
through untouched — their tool calls never contain the danger signals.

The file here is a **template**: copy it into a workflow (`workflows/<name>/hooks/`) and tune
`DANGER_SIGNALS` to that workflow's real secrets (a mailbox workflow adds its credential
filename and the raw-protocol modules a model might improvise with, e.g. `imaplib`).

## Wiring — Codex (machine-local, one-time)
The wiring carries a machine-specific absolute path, so it lives outside this repo:
1. Create `~/.codex/hooks.json` with a `PreToolUse` entry pointing at the hook script.
2. Close the Codex app, reference it from `~/.codex/config.toml`: `hooks = "hooks.json"`.
3. Reopen Codex and approve the one-time hook-trust prompt. Codex records a `trusted_hash`;
   re-approve only if the hook changes.

## Wiring — Claude Code
Same hook shape: point a `PreToolUse` hook at the same script in `.claude/settings.json`
(project) or `~/.claude/settings.json` (user). The script itself is harness-agnostic
(stdin JSON in, permission decision out).

## Verify
Ask the assistant to read a file matching a danger signal — the call should be blocked with
the hook's reason — then run the workflow's sanctioned script, which should work normally.
