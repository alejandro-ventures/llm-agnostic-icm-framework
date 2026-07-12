#!/usr/bin/env python3
"""Plan (and optionally apply) a folder reorganization. Never deletes.
Phase 1:  python plan_reorg.py <input_dir> <plan.csv>
Phase 2:  python plan_reorg.py --apply <plan.csv>"""
from __future__ import annotations
import csv, shutil, sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_core" / "scripts"))
import sandbox  # filesystem guardrail — see _core/SANDBOXING.md

def plan(in_dir: str, plan_path: str) -> int:
    src = Path(in_dir); rows = []
    for f in sorted(p for p in src.rglob("*") if p.is_file()):
        bucket = (f.suffix.lower().lstrip(".") or "no-ext")
        rows.append((str(f), str(src / bucket / f.name)))
    plan_path = str(sandbox.guard_write(plan_path))   # refuse to write outside _AI-workflows/
    Path(plan_path).parent.mkdir(parents=True, exist_ok=True)
    with open(plan_path, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["from", "to"]); w.writerows(rows)
    print(f"Planned {len(rows)} move(s) -> {plan_path}. Review before applying.")
    return 0

def apply(plan_path: str) -> int:
    moved = 0
    with open(plan_path, newline="") as fh:
        for row in csv.DictReader(fh):
            frm, to = Path(row["from"]), Path(row["to"])
            if not frm.exists():
                continue
            to = sandbox.guard_write(to)          # refuse destinations outside _AI-workflows/
            to.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(frm, to)                 # copy, then verify; originals kept
            if to.exists() and to.stat().st_size == frm.stat().st_size:
                moved += 1
    log = Path(plan_path).parent / "run-log.csv"
    with log.open("a", newline="") as fh:
        csv.writer(fh).writerow([datetime.datetime.now().isoformat(timespec="seconds"),
                                 "file-organizer", "apply", moved])
    print(f"Applied {moved} move(s). Originals left in place for you to remove manually.")
    return 0

if __name__ == "__main__":
    wf = sandbox.workflow_dir(__file__)
    args = sys.argv[1:]
    if args and args[0] == "--apply":
        raise SystemExit(apply(args[1]))
    raise SystemExit(plan(args[0] if args else str(wf / "input"),
                          args[1] if len(args) > 1 else str(wf / "output" / "plan.csv")))
