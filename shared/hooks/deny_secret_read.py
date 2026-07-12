#!/usr/bin/env python3
"""
Generic PreToolUse guard: deny any tool call that would read a secret file.
================================================================================
A Codex / Claude Code PreToolUse hook. It receives the pending tool call as JSON
on stdin and, if the call would touch a credential/secret path, returns a "deny"
decision so the call never runs. This is the "make the leak impossible, not just
forbidden" layer (see _core/SMALL-MODELS.md rule 5): even if a small model ignores
the workflow contract and tries to `cat` a credential file, the harness refuses.

It does NOT block sanctioned paths — a vetted script that reads its credential
*inside its own process* never puts the danger signals below into a tool call, so
it passes straight through.

Copy this file next to a workflow (workflows/<name>/hooks/) and TUNE the signal
list to that workflow's actual secrets. Substring matching is deliberately blunt:
prefer a false block (the model gets a clear reason and uses the sanctioned path)
over a false allow.

Contract (Claude Code / Codex hook protocol):
  stdin : {"tool_name": "...", "tool_input": {...}, "hookEventName": "PreToolUse"}
  stdout: on block, a JSON permission decision; otherwise nothing.
  exit  : always 0 (a non-zero exit is treated as a hook error, not a deny).
Standard library only.
"""
import json
import sys

# Lowercased substrings that mean "this call touches a secret". Tune per workflow.
DANGER_SIGNALS = (
    ".env",             # dotenv files
    "secrets.",         # secrets.json / secrets.yaml / ...
    "credentials.",     # credentials.json / ...
    "id_rsa",           # SSH private keys
    ".pem",
    "api_key",
    "apikey",
)

REASON = (
    "Blocked: this command would read a credential or secret file. Secrets are read "
    "only inside vetted workflow scripts, never surfaced in a tool call. Use the "
    "workflow's sanctioned script (see its SKILL.md) instead of opening the file."
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Can't parse the call — fail open (don't wedge the harness); other layers still apply.
        return 0

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    # Inspect the ENTIRE serialized tool input, so we catch the danger regardless of
    # which field (cmd / command / file_path / ...) or shell the model used.
    blob = json.dumps(tool_input, ensure_ascii=False).lower()

    if any(sig in blob for sig in DANGER_SIGNALS):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": REASON,
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
