#!/usr/bin/env python3
"""Summarize usage-log.jsonl: per-workflow runs, tokens, and human-minutes saved.
The local, agnostic counterpart of the work version's business-case analyzer. Stdlib only.
Usage: python _core/token-tracker/analyze.py"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

LOG = Path(__file__).resolve().parent / "usage-log.jsonl"


def main() -> int:
    if not LOG.exists():
        print(f"no usage log yet: {LOG}")
        return 0
    agg = defaultdict(lambda: {"runs": 0, "tokens": 0, "minutes_saved": 0.0})
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        a = agg[e.get("workflow", "?")]
        a["runs"] += 1
        a["tokens"] += int(e.get("tokens", 0) or 0)
        a["minutes_saved"] += float(e.get("minutes_saved", 0) or 0)

    tot = {"runs": 0, "tokens": 0, "minutes_saved": 0.0}
    print(f"{'workflow':<24}{'runs':>6}{'tokens':>12}{'min_saved':>12}")
    print("-" * 54)
    for wf in sorted(agg):
        a = agg[wf]
        for k in tot:
            tot[k] += a[k]
        print(f"{wf:<24}{a['runs']:>6}{a['tokens']:>12}{a['minutes_saved']:>12.0f}")
    print("-" * 54)
    print(f"{'TOTAL':<24}{tot['runs']:>6}{tot['tokens']:>12}{tot['minutes_saved']:>12.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
