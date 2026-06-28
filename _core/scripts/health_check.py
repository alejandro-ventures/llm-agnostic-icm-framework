#!/usr/bin/env python3
"""Generic structure validator for the _AI-workflows-style workspace.
Cross-platform, no third-party deps. Exit 0 = GO, 1 = HOLD."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
fails: list[str] = []

# Required toolkit files
for rel in ["AGENTS.md",
            "_core/CONVENTIONS.md", "_core/GLOSSARY.md", "_core/ONBOARDING.md",
            "requirements.txt"]:
    if not (ROOT / rel).is_file():
        fails.append(f"missing required file: {rel}")

# Every workflow folder must carry a contract and a human guide
wf_root = ROOT / "workflows"
if not wf_root.is_dir():
    fails.append("missing workflows/ directory")
else:
    for wf in sorted(p for p in wf_root.iterdir() if p.is_dir()):
        name = wf.name
        if not (wf / ".github" / name / "SKILL.md").is_file():
            fails.append(f"{name}: missing .github/{name}/SKILL.md contract")
        if not (wf / "docs" / "README.md").is_file():
            fails.append(f"{name}: missing docs/README.md")

# Nothing sensitive should be tracked
for bad in ["**/.env", "**/secrets.json", "**/credentials.json", "**/state.json"]:
    hits = [p for p in ROOT.glob(bad) if p.is_file()]
    if hits:
        fails.append(f"sensitive file present: {hits[0].relative_to(ROOT)}")

if fails:
    print("HOLD - structure check failed")
    for f in fails:
        print(f"  FAIL: {f}")
    sys.exit(1)
print("GO - structure check passed")
sys.exit(0)
