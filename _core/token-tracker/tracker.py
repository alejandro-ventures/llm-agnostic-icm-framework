#!/usr/bin/env python3
"""Append-only token / effort logger (harness-agnostic — Python stdlib only).

Every workflow run appends one JSON line to usage-log.jsonl, the data substrate for the
"automation cost (tokens) vs human effort (minutes)" business case. Works from any harness:

  python _core/token-tracker/tracker.py log --workflow pdf-ocr --action ocr \
      --source local --tokens 1200 --minutes-saved 15 --outcome success --summary "12 PDFs"

Or import it:  from tracker import log_usage;  log_usage(workflow="pdf-ocr", action="ocr", ...)
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

LOG = Path(__file__).resolve().parent / "usage-log.jsonl"


def log_usage(workflow, action, *, model="", source="", tokens=0,
              minutes_saved=0, outcome="success", summary="", notes=""):
    """Append one entry. `source` is the privacy axis: 'local' (on-device) vs 'cloud'."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workflow": workflow,
        "action": action,
        "model": model,
        "source": source,
        "tokens": int(tokens),
        "minutes_saved": float(minutes_saved),
        "outcome": outcome,
        "summary": summary,
        "notes": notes,
    }
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _cli(argv=None):
    p = argparse.ArgumentParser(description="append a token/effort log entry")
    sub = p.add_subparsers(dest="cmd", required=True)
    lg = sub.add_parser("log", help="append one run entry")
    lg.add_argument("--workflow", required=True)
    lg.add_argument("--action", required=True)
    lg.add_argument("--model", default="")
    lg.add_argument("--source", default="", help="local | cloud")
    lg.add_argument("--tokens", type=int, default=0)
    lg.add_argument("--minutes-saved", type=float, default=0)
    lg.add_argument("--outcome", default="success")
    lg.add_argument("--summary", default="")
    lg.add_argument("--notes", default="")
    a = p.parse_args(argv)
    print(json.dumps(log_usage(
        a.workflow, a.action, model=a.model, source=a.source, tokens=a.tokens,
        minutes_saved=a.minutes_saved, outcome=a.outcome, summary=a.summary, notes=a.notes),
        ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
