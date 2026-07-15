#!/usr/bin/env python3
"""Regenerate provenance.manifest.sha256 — SHA-256 of every git-tracked file.

Stdlib only (shells out to git). Hashes each file's COMMITTED BLOB content — not working-tree
bytes — so the manifest is identical on every platform regardless of line-ending checkout
(a CRLF working copy on Windows must not change the hash). Two derived artifacts are excluded:
the manifest itself and its OpenTimestamps proof (.ots) — neither can contain its own hash.
The combined root hash is the SHA-256 of the sorted entry lines ("<hash>  <path>\\n" each), so
anyone can re-derive and verify it from a clone. Run from anywhere inside the repo:

    python _core/scripts/make_provenance.py          # rewrite the manifest
    python _core/scripts/make_provenance.py --check  # verify, exit 1 on drift
"""
from __future__ import annotations
import hashlib, subprocess, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "provenance.manifest.sha256"


def sha256_blob(sha: str) -> str:
    blob = subprocess.run(
        ["git", "cat-file", "blob", sha], cwd=ROOT, capture_output=True, check=True
    ).stdout
    return hashlib.sha256(blob).hexdigest()


def build() -> tuple[str, str]:
    """Return (entries_text, root_hash) from the index (staged/committed blobs)."""
    tracked = subprocess.run(
        ["git", "ls-files", "-s"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split("\n")
    files = {}
    for line in tracked:
        if not line:
            continue
        meta, rel = line.split("\t", 1)
        files[rel] = meta.split()[1]
    derived = {MANIFEST.name, MANIFEST.name + ".ots"}
    entries = []
    for rel in sorted(files):
        if rel in derived:
            continue
        entries.append(f"{sha256_blob(files[rel])}  {rel}\n")
    entries_text = "".join(entries)
    root = hashlib.sha256(entries_text.encode("utf-8")).hexdigest()
    return entries_text, root


def render(entries_text: str, root: str, date: str) -> str:
    return (
        "# Content manifest — LLM-agnostic ICM framework\n"
        f"# Generated {date}. SHA-256 of each git-tracked file's blob content\n"
        "# (manifest and its .ots proof excluded; hashes are line-ending independent).\n"
        f"# Combined root hash (SHA-256 of the entry lines below): {root}\n"
        "# Regenerate / verify: python _core/scripts/make_provenance.py [--check]\n"
        "\n"
        f"{entries_text}"
    )


def main(argv: list[str]) -> int:
    entries_text, root = build()
    if "--check" in argv:
        if not MANIFEST.exists():
            print("HOLD - no manifest present"); return 1
        current = MANIFEST.read_text(encoding="utf-8")
        if current.split("\n\n", 1)[-1] != entries_text:
            print("HOLD - manifest is stale; regenerate with make_provenance.py"); return 1
        print(f"GO - manifest matches index blobs (root {root[:16]}…)")
        return 0
    date = datetime.date.today().isoformat()
    MANIFEST.write_text(render(entries_text, root, date), encoding="utf-8", newline="\n")
    print(f"Wrote {MANIFEST.name}: {entries_text.count(chr(10))} files, root {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
