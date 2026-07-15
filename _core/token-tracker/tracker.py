#!/usr/bin/env python3
"""Append-only token / effort logger (harness-agnostic — Python stdlib only).

Every workflow run appends one JSON line to usage-log.jsonl, the data substrate for the
"automation cost (tokens) vs human effort (minutes)" business case. Works from any harness:

  python _core/token-tracker/tracker.py log --workflow pdf-ocr --action ocr \
      --source local --tokens 1200 --minutes-saved 15 --outcome success --summary "12 PDFs"

Or import it:  from tracker import log_usage;  log_usage(workflow="pdf-ocr", action="ocr", ...)
"""
from __future__ import annotations
import argparse, json, re, sys, uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sandbox import safe_open_w  # noqa: E402

LOG = Path(__file__).resolve().parent / "usage-log.jsonl"
SCHEMA_VERSION = 2
INTENT_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+){1,4}$")


def _validate_intent_key(intent_key: str) -> str:
    if not intent_key:
        return ""
    if len(intent_key) > 64 or not INTENT_KEY_RE.fullmatch(intent_key):
        raise ValueError(
            "intent_key must be <=64 characters and contain 2-5 lowercase "
            "kebab-case parts"
        )
    return intent_key


def _validate_run_id(run_id: str) -> str:
    if not run_id:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(run_id))
    except ValueError as exc:
        raise ValueError("run_id must be a UUID") from exc


def log_usage(workflow, action, *, model="", source="", tokens=0,
              minutes_saved=0, outcome="success", summary="", notes="",
              intent_key="", run_id=""):
    """Append one entry. `source` is the privacy axis: 'local' (on-device) vs 'cloud'."""
    intent_key = _validate_intent_key(str(intent_key))
    summary = str(summary)
    if workflow == "scratch":
        if not intent_key:
            raise ValueError("scratch runs require --intent-key")
        if not summary or len(summary) > 160 or "\n" in summary or "\r" in summary:
            raise ValueError(
                "scratch summaries must be redacted, single-line, non-empty, and <=160 characters"
            )
    entry = {
        "schema_version": SCHEMA_VERSION,
        "run_id": _validate_run_id(str(run_id)),
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
        "intent_key": intent_key,
    }
    with safe_open_w(LOG, "a", encoding="utf-8") as fh:
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
    lg.add_argument(
        "--intent-key", default="",
        help="2-5-part lowercase kebab-case key; required for scratch runs",
    )
    lg.add_argument("--run-id", default="", help="optional UUID for caller-supplied identity")
    a = p.parse_args(argv)
    try:
        entry = log_usage(
            a.workflow, a.action, model=a.model, source=a.source, tokens=a.tokens,
            minutes_saved=a.minutes_saved, outcome=a.outcome, summary=a.summary,
            notes=a.notes, intent_key=a.intent_key, run_id=a.run_id,
        )
    except ValueError as exc:
        p.error(str(exc))
    print(json.dumps(entry, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
