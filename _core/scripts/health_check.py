#!/usr/bin/env python3
"""Generic structure validator for the workspace.
Cross-platform, no third-party deps. Exit 0 = GO, 1 = HOLD."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
fails: list[str] = []

# Required toolkit files
for rel in ["AGENTS.md", "PORTABILITY.md", "COMPATIBILITY.md", "SECURITY.md",
            "_core/CONVENTIONS.md", "_core/GLOSSARY.md", "_core/ONBOARDING.md",
            "_core/SANDBOXING.md", "_core/scripts/sandbox.py",
            "_core/scripts/gen-harness-config.py", "_core/integrations/servers.json",
            "_core/token-tracker/tracker.py", "_core/token-tracker/analyze.py",
            "requirements.txt"]:
    if not (ROOT / rel).is_file():
        fails.append(f"missing required file: {rel}")

# Every workflow folder must carry a contract, a human guide, and pinned deps.
# The SKILL.md frontmatter must also declare the machine-checkable contract keys:
# name, description, and the capability declarations network / destructive / gates.
CONTRACT_KEYS = ("name", "description", "network", "destructive", "gates")


def frontmatter_keys(skill: Path) -> set[str]:
    lines = skill.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return set()
    keys = set()
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line and not line[0].isspace() and ":" in line:
            keys.add(line.split(":", 1)[0].strip())
    return keys


wf_root = ROOT / "workflows"
if not wf_root.is_dir():
    fails.append("missing workflows/ directory")
else:
    for wf in sorted(p for p in wf_root.iterdir() if p.is_dir()):
        name = wf.name
        skill = wf / ".github" / name / "SKILL.md"
        if not skill.is_file():
            fails.append(f"{name}: missing .github/{name}/SKILL.md contract")
        else:
            missing = [k for k in CONTRACT_KEYS if k not in frontmatter_keys(skill)]
            if missing:
                fails.append(f"{name}: SKILL.md frontmatter missing contract keys: {', '.join(missing)}")
        if not (wf / "docs" / "README.md").is_file():
            fails.append(f"{name}: missing docs/README.md")
        if not (wf / "requirements.txt").is_file():
            fails.append(f"{name}: missing requirements.txt (per-workflow venv convention)")

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
