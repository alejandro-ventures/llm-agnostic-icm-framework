#!/usr/bin/env python3
"""Deterministic recurrence review and human-gated workflow promotion."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

WORKFLOW_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = WORKFLOW_DIR / "output"
USAGE_LOG = WORKSPACE_ROOT / "_core" / "token-tracker" / "usage-log.jsonl"
DECISIONS = OUTPUT_DIR / "decisions.jsonl"
INTENT_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+){1,4}$")
DECISION_TYPES = {"snoozed", "rejected", "reopened", "draft_approved", "promoted"}

sys.path.insert(0, str(WORKSPACE_ROOT / "_core" / "scripts"))
from sandbox import guard_write, safe_open_w  # noqa: E402


class ReviewError(RuntimeError):
    """Raised when evidence or a gated transition is unsafe or invalid."""


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def parse_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ReviewError(f"{label}: missing timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewError(f"{label}: invalid timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        raise ReviewError(f"{label}: timestamp must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def validate_intent_key(value: str) -> str:
    if len(value) > 64 or not INTENT_KEY_RE.fullmatch(value):
        raise ReviewError(
            "intent key must be <=64 characters and contain 2-5 lowercase kebab-case parts"
        )
    return value


def _last_sunday(year: int, month: int) -> date:
    if month == 12:
        first_next = date(year + 1, 1, 1)
    else:
        first_next = date(year, month + 1, 1)
    day = first_next - timedelta(days=1)
    return day - timedelta(days=(day.weekday() + 1) % 7)


def zurich_date(value: datetime) -> date:
    """Return Europe/Zurich date with a stdlib-only Windows fallback."""
    value = value.astimezone(timezone.utc)
    try:
        from zoneinfo import ZoneInfo

        return value.astimezone(ZoneInfo("Europe/Zurich")).date()
    except Exception:
        start = datetime.combine(
            _last_sunday(value.year, 3), datetime.min.time(), timezone.utc
        ) + timedelta(hours=1)
        end = datetime.combine(
            _last_sunday(value.year, 10), datetime.min.time(), timezone.utc
        ) + timedelta(hours=1)
        offset = 2 if start <= value < end else 1
        return (value + timedelta(hours=offset)).date()


def load_jsonl(path: Path, label: str, *, missing_ok: bool = True) -> list[dict]:
    if not path.exists():
        if missing_ok:
            return []
        raise ReviewError(f"missing {label}: {path}")
    records: list[dict] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ReviewError(f"{label} line {number}: malformed JSON") from exc
        if not isinstance(value, dict):
            raise ReviewError(f"{label} line {number}: expected a JSON object")
        records.append(value)
    return records


def load_evidence(
    usage_log: Path,
    *,
    current_time: datetime,
    window_days: int,
) -> dict[str, list[dict]]:
    cutoff = current_time - timedelta(days=window_days)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for index, entry in enumerate(load_jsonl(usage_log, "usage log"), start=1):
        if int(entry.get("schema_version", 0) or 0) < 2:
            continue
        if entry.get("workflow") != "scratch":
            continue
        key = entry.get("intent_key", "")
        if not key:
            continue
        validate_intent_key(str(key))
        timestamp = parse_timestamp(entry.get("timestamp"), f"usage log record {index}")
        summary = entry.get("summary", "")
        if not isinstance(summary, str) or not summary or len(summary) > 160:
            raise ReviewError(f"usage log record {index}: invalid redacted summary")
        if timestamp < cutoff or timestamp > current_time:
            continue
        normalized = dict(entry)
        normalized["_timestamp"] = timestamp
        grouped[str(key)].append(normalized)
    return grouped


def load_decision_state(path: Path) -> dict[str, dict]:
    states: dict[str, dict] = {}
    for index, entry in enumerate(load_jsonl(path, "decision log"), start=1):
        key = validate_intent_key(str(entry.get("intent_key", "")))
        decision = str(entry.get("decision", ""))
        if decision not in DECISION_TYPES:
            raise ReviewError(f"decision log record {index}: unsupported decision {decision!r}")
        parse_timestamp(entry.get("timestamp"), f"decision log record {index}")
        if decision == "snoozed":
            parse_timestamp(entry.get("until"), f"decision log record {index} snooze")
        states[key] = entry
    return states


def promoted_keys(workspace_root: Path) -> set[str]:
    result: set[str] = set()
    workflow_root = workspace_root / "workflows"
    if not workflow_root.exists():
        return result
    for marker in workflow_root.glob("*/.recurrence-review.json"):
        try:
            value = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ReviewError(f"invalid promoted-workflow marker: {marker}") from exc
        key = validate_intent_key(str(value.get("recurrence_key", "")))
        result.add(key)
    return result


def proposal_generation(state: dict | None, current_time: datetime) -> str | None:
    if state is None:
        return "initial"
    decision = state["decision"]
    if decision in {"rejected", "draft_approved", "promoted"}:
        return None
    stamp = parse_timestamp(state["timestamp"], "decision").strftime("%Y%m%dT%H%M%SZ")
    if decision == "snoozed":
        if current_time < parse_timestamp(state["until"], "snooze until"):
            return None
        return f"after-snooze-{stamp}"
    if decision == "reopened":
        return f"after-reopen-{stamp}"
    raise ReviewError(f"unsupported decision state: {decision}")


def _md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def routing_description(intent_key: str) -> str:
    return f"handle recurring {intent_key.replace('-', ' ')} requests through a reviewed workflow"


def render_proposal(
    intent_key: str,
    attempts: list[dict],
    successes: list[dict],
    *,
    current_time: datetime,
    window_days: int,
    minimum_count: int,
    minimum_days: int,
) -> str:
    ordered = sorted(successes, key=lambda item: item["_timestamp"])
    total_minutes = sum(float(item.get("minutes_saved", 0) or 0) for item in ordered)
    days = sorted({zurich_date(item["_timestamp"]) for item in ordered})
    rows = [
        f"| {_md(zurich_date(item['_timestamp']))} | {_md(item.get('action', ''))} | "
        f"{_md(item.get('summary', ''))} | {float(item.get('minutes_saved', 0) or 0):g} |"
        for item in ordered
    ]
    return "\n".join(
        [
            f"# Workflow candidate: `{intent_key}`",
            "",
            f"Generated: {iso_utc(current_time)}",
            "",
            "## Qualification",
            "",
            f"- Successful occurrences: {len(ordered)} (minimum {minimum_count})",
            f"- Distinct Europe/Zurich dates: {len(days)} (minimum {minimum_days})",
            f"- Review window: {window_days} days",
            f"- Total attempts recorded in window: {len(attempts)}",
            f"- Estimated minutes saved across successful occurrences: {total_minutes:g}",
            f"- First / latest success: {iso_utc(ordered[0]['_timestamp'])} / {iso_utc(ordered[-1]['_timestamp'])}",
            "",
            "## Evidence",
            "",
            "| Zurich date | Action | Redacted summary | Minutes saved |",
            "|---|---|---|---:|",
            *rows,
            "",
            "## Suggested workflow",
            "",
            f"- Proposed slug: `{intent_key}`",
            f"- Proposed router description: {routing_description(intent_key)}",
            "- Contract: define stable inputs, deterministic process, reviewable outputs, human gates, and run logging.",
            "- Gate 1 evidence review: inspect only explicitly approved scratch artifacts needed to complete the draft.",
            "",
            "## Draft contract outline",
            "",
            "1. Confirm the repeated request boundary represented by the intent key.",
            "2. Derive the smallest stable input/process/output interface from approved evidence.",
            "3. Make file changes dry-run-first and route writes through the workspace sandbox helper.",
            "4. Preserve irreversible actions behind explicit same-turn approval.",
            "5. Validate the draft before proposing router activation.",
            "",
            "## Risks to resolve at Gate 1",
            "",
            "- Confirm the intent key does not combine materially different request variants.",
            "- Confirm summaries contain no raw prompts, message bodies, file contents, personal data, or secrets.",
            "- Confirm a new workflow is preferable to extending an existing specialized workflow.",
            "",
        ]
    )


def scan(
    *,
    usage_log: Path,
    decisions_path: Path,
    output_dir: Path,
    workspace_root: Path,
    current_time: datetime,
    window_days: int = 90,
    minimum_count: int = 3,
    minimum_days: int = 2,
) -> dict:
    if window_days < 1 or minimum_count < 1 or minimum_days < 1:
        raise ReviewError("scan thresholds must be positive")
    evidence = load_evidence(usage_log, current_time=current_time, window_days=window_days)
    states = load_decision_state(decisions_path)
    active_keys = promoted_keys(workspace_root)
    created: list[str] = []
    created_details: list[dict] = []
    qualified: list[str] = []
    for key in sorted(evidence):
        attempts = evidence[key]
        successes = [item for item in attempts if item.get("outcome") == "success"]
        distinct_days = {zurich_date(item["_timestamp"]) for item in successes}
        if len(successes) < minimum_count or len(distinct_days) < minimum_days:
            continue
        qualified.append(key)
        if key in active_keys:
            continue
        generation = proposal_generation(states.get(key), current_time)
        if generation is None:
            continue
        proposal = output_dir / "proposals" / key / f"{generation}.md"
        try:
            with safe_open_w(proposal, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    render_proposal(
                        key,
                        attempts,
                        successes,
                        current_time=current_time,
                        window_days=window_days,
                        minimum_count=minimum_count,
                        minimum_days=minimum_days,
                    )
                )
        except FileExistsError:
            continue
        created.append(str(proposal.resolve()))
        created_details.append(
            {
                "intent_key": key,
                "proposal": str(proposal.resolve()),
                "successful_occurrences": len(successes),
                "distinct_zurich_dates": len(distinct_days),
            }
        )
    return {
        "status": "new_candidates" if created else "no_change",
        "new_candidates": created,
        "new_candidate_details": created_details,
        "qualified_intent_keys": qualified,
    }


def append_decision(
    decisions_path: Path,
    *,
    intent_key: str,
    decision: str,
    current_time: datetime,
    until: datetime | None = None,
    proposal: str = "",
    draft_hash: str = "",
) -> dict:
    validate_intent_key(intent_key)
    if decision not in DECISION_TYPES:
        raise ReviewError(f"unsupported decision: {decision}")
    entry = {
        "timestamp": iso_utc(current_time),
        "intent_key": intent_key,
        "decision": decision,
    }
    if until is not None:
        entry["until"] = iso_utc(until)
    if proposal:
        entry["proposal"] = proposal
    if draft_hash:
        entry["draft_hash"] = draft_hash
    with safe_open_w(decisions_path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def latest_proposal(output_dir: Path, intent_key: str) -> Path:
    proposals = list((output_dir / "proposals" / intent_key).glob("*.md"))
    if not proposals:
        raise ReviewError(f"no proposal exists for {intent_key}")
    return max(proposals, key=lambda path: path.stat().st_mtime_ns)


def hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise ReviewError(f"draft contains no files: {root}")
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def scaffold_draft(
    *,
    intent_key: str,
    proposal: Path,
    output_dir: Path,
    decisions_path: Path,
    current_time: datetime,
    approved: bool,
) -> dict:
    validate_intent_key(intent_key)
    if not approved:
        raise ReviewError("Gate 1 requires explicit approval and --approved")
    if not proposal.is_file() or proposal.parent.name != intent_key:
        raise ReviewError("proposal must be an existing proposal for this intent key")
    draft = output_dir / "drafts" / intent_key / proposal.stem
    skill = draft / ".github" / intent_key / "SKILL.md"
    if skill.exists():
        raise ReviewError(f"draft already exists: {draft}")
    description = (
        f"Handle recurring {intent_key.replace('-', ' ')} requests through a reviewed, reproducible "
        "workflow. Use after recurrence-review Gate 1 approves this candidate for drafting."
    )
    skill_text = f"""---
name: {intent_key}
description: >-
  {description}
---
# {intent_key}

## Process
1. Confirm the request matches this workflow's reviewed boundary.
2. Define and validate the required inputs before processing.
3. Run the deterministic implementation and write reviewable outputs only inside this workflow.
4. Stop before every destructive or irreversible action for explicit same-turn approval.
5. Append the workflow run log and token-tracker entry.

## Gate
- Do not activate this draft until recurrence-review Gate 2 approves its promotion plan hash.
"""
    readme = f"""# {intent_key}

Review draft generated from `{proposal.name}`. Before Gate 2, replace this paragraph with the human
guide for the stable inputs, command, outputs, dependencies, safety gates, and validation steps.
"""
    metadata = {
        "schema_version": 1,
        "recurrence_key": intent_key,
        "routing_description": routing_description(intent_key),
        "proposal": proposal.relative_to(output_dir).as_posix(),
    }
    files: dict[Path, str] = {
        skill: skill_text,
        draft / "docs" / "README.md": readme,
        draft / "requirements.txt": "# Standard library only until the reviewed draft requires otherwise.\n",
        draft / ".recurrence-review.json": json.dumps(metadata, indent=2) + "\n",
        draft / "input" / ".gitkeep": "",
        draft / "output" / ".gitkeep": "",
        draft / "scripts" / ".gitkeep": "",
    }
    for path, content in files.items():
        with safe_open_w(path, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    draft_hash = hash_tree(draft)
    append_decision(
        decisions_path,
        intent_key=intent_key,
        decision="draft_approved",
        current_time=current_time,
        proposal=proposal.relative_to(output_dir).as_posix(),
        draft_hash=draft_hash,
    )
    return {"status": "draft_created", "draft": str(draft.resolve()), "draft_hash": draft_hash}


def decide(
    *,
    intent_key: str,
    decision: str,
    decisions_path: Path,
    current_time: datetime,
    approved: bool,
    snooze_days: int = 90,
) -> dict:
    if not approved:
        raise ReviewError("recording a human decision requires explicit approval and --approved")
    if decision not in {"snoozed", "rejected", "reopened"}:
        raise ReviewError("decision must be snoozed, rejected, or reopened")
    if snooze_days < 1:
        raise ReviewError("snooze days must be positive")
    until = current_time + timedelta(days=snooze_days) if decision == "snoozed" else None
    return append_decision(
        decisions_path,
        intent_key=intent_key,
        decision=decision,
        current_time=current_time,
        until=until,
    )


def latest_draft(output_dir: Path, intent_key: str) -> Path:
    roots = [path for path in (output_dir / "drafts" / intent_key).glob("*") if path.is_dir()]
    if not roots:
        raise ReviewError(f"no approved draft exists for {intent_key}")
    return max(roots, key=lambda path: path.stat().st_mtime_ns)


def draft_metadata(draft: Path, intent_key: str) -> dict:
    marker = draft / ".recurrence-review.json"
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewError(f"invalid draft metadata: {marker}") from exc
    if value.get("recurrence_key") != intent_key:
        raise ReviewError("draft recurrence key does not match requested intent key")
    required = [
        draft / ".github" / intent_key / "SKILL.md",
        draft / "docs" / "README.md",
        draft / "requirements.txt",
        draft / "input" / ".gitkeep",
        draft / "output" / ".gitkeep",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ReviewError("draft is incomplete: " + ", ".join(missing))
    return value


def router_row(intent_key: str, description: str) -> str:
    safe_description = str(description).replace("|", "/").replace("\r", " ").replace("\n", " ")
    return (
        f"| `{intent_key}` | {safe_description} | "
        f"`workflows/{intent_key}/.github/{intent_key}/SKILL.md` |"
    )


def create_promotion_plan(
    *,
    intent_key: str,
    draft: Path,
    output_dir: Path,
    workspace_root: Path,
    current_time: datetime,
) -> dict:
    metadata = draft_metadata(draft, intent_key)
    destination = workspace_root / "workflows" / intent_key
    if destination.exists():
        raise ReviewError(f"destination workflow already exists: {destination}")
    draft_hash = hash_tree(draft)
    row = router_row(intent_key, metadata["routing_description"])
    files = [path.relative_to(draft).as_posix() for path in sorted(draft.rglob("*")) if path.is_file()]
    plan = output_dir / "promotion-plans" / intent_key / f"{draft_hash}.md"
    content = "\n".join(
        [
            f"# Promotion plan: `{intent_key}`",
            "",
            f"Generated: {iso_utc(current_time)}",
            f"Draft: `{draft.resolve()}`",
            f"Draft hash: `{draft_hash}`",
            f"Destination: `{destination.resolve()}`",
            "",
            "## Planned copies",
            "",
            *[f"- `{name}`" for name in files],
            "",
            "## Planned router row",
            "",
            row,
            "",
            "## Gate 2",
            "",
            "Approve this exact hash in the same turn before applying. Applying copies the draft,",
            "backs up and updates AGENTS.md, runs the health check, and records promotion. It never",
            "commits, pushes, moves, or deletes files.",
            "",
        ]
    )
    try:
        with safe_open_w(plan, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except FileExistsError:
        pass
    return {"status": "promotion_plan_ready", "plan": str(plan.resolve()), "draft_hash": draft_hash}


def _copy_draft(draft: Path, destination: Path) -> None:
    for source in sorted(path for path in draft.rglob("*") if path.is_file()):
        target = guard_write(destination / source.relative_to(draft))
        with safe_open_w(target, "xb") as output:
            output.write(source.read_bytes())


def apply_promotion(
    *,
    intent_key: str,
    draft: Path,
    plan_hash: str,
    output_dir: Path,
    decisions_path: Path,
    workspace_root: Path,
    current_time: datetime,
    approved: bool,
    run_health_check: bool = True,
) -> dict:
    if not approved:
        raise ReviewError("Gate 2 requires explicit same-turn approval and --approved")
    metadata = draft_metadata(draft, intent_key)
    actual_hash = hash_tree(draft)
    if actual_hash != plan_hash:
        raise ReviewError("draft changed after planning; generate and approve a new promotion hash")
    plan = output_dir / "promotion-plans" / intent_key / f"{plan_hash}.md"
    if not plan.is_file():
        raise ReviewError("matching immutable promotion plan does not exist")
    destination = workspace_root / "workflows" / intent_key
    if destination.exists():
        raise ReviewError(f"destination workflow already exists: {destination}")
    agents = workspace_root / "AGENTS.md"
    original = agents.read_text(encoding="utf-8")
    if f"| `{intent_key}` |" in original:
        raise ReviewError("router already contains this workflow")
    scratch_marker = "| `scratch` |"
    marker_index = original.find(scratch_marker)
    if marker_index < 0:
        raise ReviewError("could not find scratch row in AGENTS.md")
    line_start = original.rfind("\n", 0, marker_index) + 1
    row = router_row(intent_key, metadata["routing_description"]) + "\n"
    updated = original[:line_start] + row + original[line_start:]
    backup = output_dir / "backups" / f"AGENTS-before-{plan_hash}.md"
    try:
        with safe_open_w(backup, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(original)
    except FileExistsError:
        pass
    _copy_draft(draft, destination)
    with safe_open_w(agents, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)
    health_output = "not run"
    if run_health_check:
        result = subprocess.run(
            [sys.executable, str(workspace_root / "_core" / "scripts" / "health_check.py")],
            cwd=workspace_root,
            text=True,
            capture_output=True,
            check=False,
        )
        health_output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            raise ReviewError(f"promotion copied files but health check failed: {health_output}")
    append_decision(
        decisions_path,
        intent_key=intent_key,
        decision="promoted",
        current_time=current_time,
        draft_hash=actual_hash,
    )
    return {
        "status": "promoted",
        "workflow": str(destination.resolve()),
        "health_check": health_output,
    }


def audit(action: str, result: str, *, current_time: datetime, outcome: str = "success") -> None:
    run_log = OUTPUT_DIR / "run-log.csv"
    with safe_open_w(run_log, "a", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerow([iso_utc(current_time), "recurrence-review", action, result])
    command = [
        sys.executable,
        str(WORKSPACE_ROOT / "_core" / "token-tracker" / "tracker.py"),
        "log",
        "--workflow",
        "recurrence-review",
        "--action",
        action,
        "--source",
        "local",
        "--outcome",
        outcome,
        "--summary",
        result[:240],
    ]
    completed = subprocess.run(command, cwd=WORKSPACE_ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise ReviewError(f"token-tracker audit failed: {(completed.stderr or completed.stdout).strip()}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="review recurring scratch inquiries")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_parser = sub.add_parser("scan", help="create proposals for newly qualifying intent keys")
    scan_parser.add_argument("--window-days", type=int, default=90)
    scan_parser.add_argument("--minimum-count", type=int, default=3)
    scan_parser.add_argument("--minimum-days", type=int, default=2)

    decide_parser = sub.add_parser("decide", help="record snooze, reject, or reopen")
    decide_parser.add_argument("intent_key")
    decide_parser.add_argument("decision", choices=["snoozed", "rejected", "reopened"])
    decide_parser.add_argument("--days", type=int, default=90)
    decide_parser.add_argument("--approved", action="store_true")

    scaffold_parser = sub.add_parser("scaffold", help="Gate 1: create a staged workflow draft")
    scaffold_parser.add_argument("intent_key")
    scaffold_parser.add_argument("--proposal", type=Path)
    scaffold_parser.add_argument("--approved", action="store_true")

    plan_parser = sub.add_parser("promotion-plan", help="write an immutable Gate 2 plan")
    plan_parser.add_argument("intent_key")
    plan_parser.add_argument("--draft", type=Path)

    promote_parser = sub.add_parser("promote", help="Gate 2: activate an approved draft")
    promote_parser.add_argument("intent_key")
    promote_parser.add_argument("--draft", type=Path, required=True)
    promote_parser.add_argument("--plan-hash", required=True)
    promote_parser.add_argument("--approved", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    current_time = now_utc()
    try:
        if args.command == "scan":
            result = scan(
                usage_log=USAGE_LOG,
                decisions_path=DECISIONS,
                output_dir=OUTPUT_DIR,
                workspace_root=WORKSPACE_ROOT,
                current_time=current_time,
                window_days=args.window_days,
                minimum_count=args.minimum_count,
                minimum_days=args.minimum_days,
            )
            audit("scan", f"new={len(result['new_candidates'])}", current_time=current_time)
        elif args.command == "decide":
            result = decide(
                intent_key=args.intent_key,
                decision=args.decision,
                decisions_path=DECISIONS,
                current_time=current_time,
                approved=args.approved,
                snooze_days=args.days,
            )
            audit("decide", f"{args.intent_key}:{args.decision}", current_time=current_time)
        elif args.command == "scaffold":
            proposal = args.proposal or latest_proposal(OUTPUT_DIR, args.intent_key)
            result = scaffold_draft(
                intent_key=args.intent_key,
                proposal=proposal.resolve(),
                output_dir=OUTPUT_DIR,
                decisions_path=DECISIONS,
                current_time=current_time,
                approved=args.approved,
            )
            audit("scaffold", args.intent_key, current_time=current_time)
        elif args.command == "promotion-plan":
            draft = (args.draft or latest_draft(OUTPUT_DIR, args.intent_key)).resolve()
            result = create_promotion_plan(
                intent_key=args.intent_key,
                draft=draft,
                output_dir=OUTPUT_DIR,
                workspace_root=WORKSPACE_ROOT,
                current_time=current_time,
            )
            audit("promotion-plan", args.intent_key, current_time=current_time)
        else:
            result = apply_promotion(
                intent_key=args.intent_key,
                draft=args.draft.resolve(),
                plan_hash=args.plan_hash,
                output_dir=OUTPUT_DIR,
                decisions_path=DECISIONS,
                workspace_root=WORKSPACE_ROOT,
                current_time=current_time,
                approved=args.approved,
            )
            audit("promote", args.intent_key, current_time=current_time)
    except (ReviewError, OSError, ValueError) as exc:
        try:
            audit(args.command, str(exc)[:160], current_time=current_time, outcome="failed")
        except Exception:
            pass
        parser.exit(2, f"ERROR: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
