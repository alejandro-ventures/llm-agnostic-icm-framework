#!/usr/bin/env python3
"""Leak gate — refuse to publish credentials or private terms. Stdlib only.

Scans git-tracked text (default: working tree; --history: every blob in every commit,
decoding UTF-8/UTF-16 so nothing hides behind an encoding) for:

  1. credential patterns (API keys, bearer tokens, private-key blocks, JWTs);
  2. email addresses outside the allowlist below;
  3. private terms from an optional, NEVER-COMMITTED terms file — one case-insensitive
     term per line, `#` comments allowed. Default location: `.leakscan.local` at the repo
     root (gitignored), or set env LEAK_TERMS_FILE. This is how a public repo gets checked
     against a private vocabulary (employer names, client names, internal hosts) without
     that vocabulary ever appearing in the repo itself.

Exit 0 = GO, 1 = findings, 2 = usage error. Wire it as CI step and/or pre-push hook:

    python _core/scripts/leak_scan.py             # tree scan (fast, every push)
    python _core/scripts/leak_scan.py --history   # full-history scan (before going public)
"""
from __future__ import annotations
import os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EMAIL_ALLOWLIST = {"alejandro.ventures@pm.me", "noreply@anthropic.com"}
EMAIL_RE = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CRED_RES = [re.compile(p) for p in (
    rb"ut_[A-Za-z0-9_-]{20,}",            # AFFiNE-style user tokens
    rb"sk-[A-Za-z0-9_-]{20,}",            # OpenAI/Anthropic-style keys
    rb"ghp_[A-Za-z0-9]{30,}",             # GitHub PATs
    rb"gho_[A-Za-z0-9]{30,}",
    rb"AKIA[0-9A-Z]{16}",                 # AWS access keys
    rb"AIza[A-Za-z0-9_-]{30,}",           # Google API keys
    rb"xox[bpars]-[A-Za-z0-9-]{10,}",     # Slack tokens
    rb"eyJ[A-Za-z0-9_-]{40,}\.eyJ",       # JWTs
    rb"-----BEGIN [A-Z ]*PRIVATE KEY-----",
)]


def load_private_terms() -> list[bytes]:
    path = Path(os.environ.get("LEAK_TERMS_FILE", ROOT / ".leakscan.local"))
    if not path.is_file():
        return []
    terms = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line.encode())
    return terms


def decodings(raw: bytes) -> list[bytes]:
    """The raw bytes plus a UTF-8 re-encoding of any UTF-16 content, so BOM'd or wide
    text can't hide a match from byte-level regexes."""
    out = [raw]
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in raw[:200]:
        try:
            out.append(raw.decode("utf-16").encode("utf-8"))
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
    return out


def scan_bytes(raw: bytes, label: str, terms: list[bytes]) -> list[str]:
    findings = []
    for text in decodings(raw):
        low = text.lower()
        for term in terms:
            if term.lower() in low:
                findings.append(f"{label}: private term {term.decode()!r}")
        for cre in CRED_RES:
            m = cre.search(text)
            if m:
                findings.append(f"{label}: credential pattern {m.group()[:12].decode(errors='replace')}…")
        for m in EMAIL_RE.finditer(text):
            email = m.group().decode(errors="replace").lower()
            if email not in EMAIL_ALLOWLIST:
                findings.append(f"{label}: unlisted email {email}")
    return findings


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def main(argv: list[str]) -> int:
    terms = load_private_terms()
    findings: list[str] = []
    if "--history" in argv:
        lines = git("rev-list", "--all", "--objects").decode().splitlines()
        for line in lines:
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1]:
                findings += scan_bytes(git("cat-file", "-p", parts[0]), f"history:{parts[1]}", terms)
    else:
        for rel in git("ls-files").decode().splitlines():
            p = ROOT / rel
            if p.is_file():
                findings += scan_bytes(p.read_bytes(), rel, terms)
    findings = sorted(set(findings))
    if findings:
        print(f"HOLD - {len(findings)} potential leak(s):")
        for f in findings[:50]:
            print(f"  FAIL: {f}")
        return 1
    mode = "history" if "--history" in argv else "tree"
    print(f"GO - leak scan clean ({mode}; {len(terms)} private terms loaded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
