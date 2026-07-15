#!/usr/bin/env python3
"""Audit a READ-ONLY reference folder against a checklist; write a report.
Usage: python audit_folder.py "<reference_folder>" <checklist.md> <output_dir>
Read-only on the reference folder. Writes only into output_dir."""
from __future__ import annotations
import csv, datetime, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_core" / "scripts"))
import sandbox  # filesystem guardrail — see _core/SANDBOXING.md

def items(md: Path):
    return [l.strip("-* ").strip() for l in md.read_text(encoding="utf-8").splitlines()
            if l.strip().startswith(("-", "*"))]

def main(ref: str, checklist: str, out_dir: str) -> int:
    ref_p = Path(ref)
    if not ref_p.is_dir():
        print(f"Reference folder not found (must be a read-only reference root the user explicitly named): {ref}")
        return 1
    names = " \n".join(p.name.lower() for p in ref_p.rglob("*") if p.is_file())
    checks = items(Path(checklist))
    rows = []
    for c in checks:
        kw = re.sub(r"[^a-z0-9]+", " ", c.lower()).split()
        hit = any(k in names for k in kw if len(k) > 3)
        rows.append((c, "present" if hit else "MISSING"))
    out = sandbox.guard_write(out_dir); out.mkdir(parents=True, exist_ok=True)  # writes stay inside the workspace
    today = datetime.date.today().isoformat()
    lines = [f"# Data-room report — {today}", f"Reference: {ref}", ""]
    lines += [f"- [{'x' if s=='present' else ' '}] {c} — {s}" for c, s in rows]
    (out / f"data-room-report-{today}.md").write_text("\n".join(lines), encoding="utf-8")
    n = sum(1 for _, s in rows if s == "present")
    with (out / "run-log.csv").open("a", newline="") as fh:
        csv.writer(fh).writerow([datetime.datetime.now().isoformat(timespec="seconds"),
                                 "data-room-check", "audit", n])
    print(f"Wrote report ({n}/{len(rows)} present). Reference folder was not modified.")
    return 0

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        print('Usage: python audit_folder.py "<reference_folder>" <checklist.md> [output_dir]'); raise SystemExit(2)
    raise SystemExit(main(a[0], a[1], a[2] if len(a) > 2 else str(sandbox.workflow_dir(__file__) / "output")))
