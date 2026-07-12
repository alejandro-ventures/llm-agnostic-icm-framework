#!/usr/bin/env python3
"""Filesystem guardrail for workspace scripts (Tier 0 — see _core/SANDBOXING.md).

Converts the "write only inside the workspace" convention into code. A workflow script
imports this and routes its write destinations through `guard_write()` (or `safe_open_w()`).
Reads outside the workspace stay allowed (reference material is read-only) EXCEPT secrets.

This is a guardrail against bugs and accidents — the dominant real risk for AI-generated
code — NOT a security jail. A determined or malicious script can bypass a pure-Python check.
For untrusted code or sensitive data, run inside Windows Sandbox (the per-workflow .wsb
configs) — see `_core/SANDBOXING.md`.
"""
from __future__ import annotations
from pathlib import Path

# This file lives at  <workspace>/_core/scripts/sandbox.py
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]

# Secret patterns that must never be opened by a workflow (mirrors .gitignore "Secrets").
_SECRET_GLOBS = (".env", ".env.*", "secrets.*", "credentials.*", "*.key", "*.pem")


class SandboxError(Exception):
    """Raised when a path escapes the workspace or names a secret."""


def _is_secret(path: Path) -> bool:
    return any(path.match(glob) for glob in _SECRET_GLOBS)


def inside_workspace(path) -> bool:
    """True if `path` resolves to a location inside the workspace root."""
    try:
        Path(path).resolve().relative_to(WORKSPACE_ROOT)
        return True
    except ValueError:
        return False


def guard_write(path) -> Path:
    """Return a resolved Path, or raise SandboxError if it is outside the workspace or
    names a secret. Call this on any write/delete destination before touching it."""
    p = Path(path).resolve()
    if not inside_workspace(p):
        raise SandboxError(
            f"refusing to write outside the workspace: {p}\n"
            f"  the one hard boundary is: writes stay inside {WORKSPACE_ROOT}"
        )
    if _is_secret(p):
        raise SandboxError(f"refusing to write to a secret file: {p}")
    return p


def guard_read(path) -> Path:
    """Return a resolved Path for reading, or raise if it names a secret. Reads are allowed
    anywhere (reference material is read-only); only secrets are off-limits."""
    p = Path(path).resolve()
    if _is_secret(p):
        raise SandboxError(f"refusing to read a secret file: {p}")
    return p


def safe_open_w(path, mode: str = "w", **kwargs):
    """open() for writing, guarded. Creates parent dirs. Refuses read-only modes."""
    if not any(m in mode for m in ("w", "a", "x", "+")):
        raise ValueError("safe_open_w is for writing; use guard_read + open() for reads")
    p = guard_write(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return open(p, mode, **kwargs)


def workflow_dir(script_file) -> Path:
    """The workflow folder for a script at workflows/<name>/scripts/<x>.py.
    Use to derive default input/output paths (CONVENTIONS: path-independent)."""
    return Path(script_file).resolve().parents[1]


if __name__ == "__main__":
    # Tiny self-test: prove the guard blocks an escape and allows an in-workspace path.
    # Exits non-zero on any unexpected allow, so CI can run it as a check.
    import sys as _sys
    failed = False
    print(f"WORKSPACE_ROOT = {WORKSPACE_ROOT}")
    ok = WORKSPACE_ROOT / "workflows" / "ocr-folder" / "output"
    print(f"in-workspace allowed: {guard_write(ok)}")
    for bad in (Path.home() / "evil.txt", WORKSPACE_ROOT / ".env"):
        try:
            guard_write(bad)
            print(f"  UNEXPECTED: allowed {bad}")
            failed = True
        except SandboxError as e:
            print(f"  blocked as expected: {str(e).splitlines()[0]}")
    _sys.exit(1 if failed else 0)
