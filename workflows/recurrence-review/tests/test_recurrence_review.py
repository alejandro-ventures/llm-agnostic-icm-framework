from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]
WORKFLOW = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


review = load_module("recurrence_review", WORKFLOW / "scripts" / "review.py")
tracker = load_module("token_tracker", WORKSPACE / "_core" / "token-tracker" / "tracker.py")
analyze = load_module("token_analyze", WORKSPACE / "_core" / "token-tracker" / "analyze.py")


class WorkspaceTempCase(unittest.TestCase):
    def setUp(self):
        root = WORKFLOW / "output" / "test-tmp"
        root.mkdir(parents=True, exist_ok=True)
        self.temp = Path(tempfile.mkdtemp(prefix="recurrence-", dir=root))

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def write_jsonl(self, path: Path, entries: list[dict]):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries),
            encoding="utf-8",
        )

    @staticmethod
    def evidence(timestamp: datetime, key: str, *, outcome="success", summary="Repeated task", minutes=5):
        return {
            "schema_version": 2,
            "run_id": f"run-{timestamp.timestamp()}-{key}",
            "timestamp": timestamp.isoformat(),
            "workflow": "scratch",
            "action": "test-action",
            "source": "local",
            "tokens": 0,
            "minutes_saved": minutes,
            "outcome": outcome,
            "summary": summary,
            "notes": "",
            "intent_key": key,
        }

    def scan(self, entries: list[dict], *, now: datetime, minimum_count=3, minimum_days=2):
        usage = self.temp / "usage.jsonl"
        decisions = self.temp / "decisions.jsonl"
        output = self.temp / "output"
        workspace = self.temp / "workspace"
        (workspace / "workflows").mkdir(parents=True, exist_ok=True)
        self.write_jsonl(usage, entries)
        result = review.scan(
            usage_log=usage,
            decisions_path=decisions,
            output_dir=output,
            workspace_root=workspace,
            current_time=now,
            minimum_count=minimum_count,
            minimum_days=minimum_days,
        )
        return result, usage, decisions, output, workspace


class TrackerTests(WorkspaceTempCase):
    def test_tracker_v2_fields_and_scratch_validation(self):
        original_log = tracker.LOG
        tracker.LOG = self.temp / "usage.jsonl"
        try:
            entry = tracker.log_usage(
                "scratch",
                "test",
                source="local",
                outcome="success",
                summary="Compared recurring report formats",
                intent_key="compare-report-formats",
            )
            self.assertEqual(entry["schema_version"], 2)
            self.assertTrue(entry["run_id"])
            self.assertEqual(entry["intent_key"], "compare-report-formats")
            with self.assertRaises(ValueError):
                tracker.log_usage("scratch", "test", summary="Missing key")
            with self.assertRaises(ValueError):
                tracker.log_usage(
                    "scratch", "test", summary="Valid summary", intent_key="Bad_Key"
                )
            with self.assertRaises(ValueError):
                tracker.log_usage(
                    "scratch", "test", summary="x" * 161, intent_key="valid-test-key"
                )
        finally:
            tracker.LOG = original_log

    def test_analyzer_accepts_old_and_new_entries(self):
        old = {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "workflow": "email-read",
            "tokens": 2,
            "minutes_saved": 3,
        }
        new = {
            **old,
            "schema_version": 2,
            "run_id": "00000000-0000-0000-0000-000000000001",
            "tokens": 4,
            "minutes_saved": 5,
            "intent_key": "",
        }
        path = self.temp / "usage.jsonl"
        self.write_jsonl(path, [old, new])
        original_log = analyze.LOG
        analyze.LOG = path
        try:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(analyze.main(), 0)
            rendered = output.getvalue()
            self.assertIn("email-read", rendered)
            self.assertIn("TOTAL", rendered)
        finally:
            analyze.LOG = original_log


class ScanTests(WorkspaceTempCase):
    def setUp(self):
        super().setUp()
        self.now = datetime(2026, 7, 14, 10, 0, tzinfo=timezone.utc)

    def test_threshold_failures_and_success(self):
        two = [
            self.evidence(self.now - timedelta(days=2), "build-report-workflow"),
            self.evidence(self.now - timedelta(days=1), "build-report-workflow"),
        ]
        result, *_ = self.scan(two, now=self.now)
        self.assertEqual(result["status"], "no_change")

        same_day = [
            self.evidence(self.now - timedelta(hours=3 - index), "same-day-work")
            for index in range(3)
        ]
        result, *_ = self.scan(same_day, now=self.now)
        self.assertEqual(result["status"], "no_change")

        qualifying = two + [self.evidence(self.now, "build-report-workflow")]
        result, _, _, output, _ = self.scan(qualifying, now=self.now)
        self.assertEqual(result["status"], "new_candidates")
        self.assertEqual(len(result["new_candidates"]), 1)
        self.assertEqual(result["new_candidate_details"][0]["successful_occurrences"], 3)
        self.assertEqual(result["new_candidate_details"][0]["distinct_zurich_dates"], 3)
        self.assertTrue((output / "proposals" / "build-report-workflow" / "initial.md").is_file())

    def test_failed_old_and_other_keys_do_not_count(self):
        entries = [
            self.evidence(self.now - timedelta(days=3), "repeat-one-task"),
            self.evidence(self.now - timedelta(days=2), "repeat-one-task", outcome="failed"),
            self.evidence(self.now - timedelta(days=1), "repeat-two-task"),
            self.evidence(self.now - timedelta(days=91), "repeat-one-task"),
        ]
        result, *_ = self.scan(entries, now=self.now)
        self.assertEqual(result["status"], "no_change")

    def test_ninety_day_boundary_is_inclusive(self):
        entries = [
            self.evidence(self.now - timedelta(days=90), "boundary-test-case"),
            self.evidence(self.now - timedelta(days=1), "boundary-test-case"),
            self.evidence(self.now, "boundary-test-case"),
        ]
        result, *_ = self.scan(entries, now=self.now)
        self.assertEqual(result["status"], "new_candidates")

    def test_zurich_dates_not_utc_dates(self):
        entries = [
            self.evidence(datetime(2026, 7, 13, 22, 30, tzinfo=timezone.utc), "zurich-day-test"),
            self.evidence(datetime(2026, 7, 13, 23, 30, tzinfo=timezone.utc), "zurich-day-test"),
            self.evidence(datetime(2026, 7, 14, 0, 30, tzinfo=timezone.utc), "zurich-day-test"),
        ]
        result, *_ = self.scan(entries, now=self.now)
        self.assertEqual(result["status"], "no_change")

    def test_malformed_json_fails_without_proposal(self):
        usage = self.temp / "usage.jsonl"
        usage.write_text('{"schema_version": 2}\nnot-json\n', encoding="utf-8")
        output = self.temp / "output"
        workspace = self.temp / "workspace"
        (workspace / "workflows").mkdir(parents=True)
        with self.assertRaises(review.ReviewError):
            review.scan(
                usage_log=usage,
                decisions_path=self.temp / "decisions.jsonl",
                output_dir=output,
                workspace_root=workspace,
                current_time=self.now,
            )
        self.assertFalse((output / "proposals").exists())

    def test_scan_is_idempotent(self):
        entries = [
            self.evidence(self.now - timedelta(days=2), "idempotent-test-case"),
            self.evidence(self.now - timedelta(days=1), "idempotent-test-case"),
            self.evidence(self.now, "idempotent-test-case"),
        ]
        result, usage, decisions, output, workspace = self.scan(entries, now=self.now)
        self.assertEqual(result["status"], "new_candidates")
        again = review.scan(
            usage_log=usage,
            decisions_path=decisions,
            output_dir=output,
            workspace_root=workspace,
            current_time=self.now,
        )
        self.assertEqual(again["status"], "no_change")
        self.assertEqual(len(list((output / "proposals").rglob("*.md"))), 1)

    def test_promoted_key_is_suppressed(self):
        key = "promoted-key-test"
        entries = [
            self.evidence(self.now - timedelta(days=2), key),
            self.evidence(self.now - timedelta(days=1), key),
            self.evidence(self.now, key),
        ]
        usage = self.temp / "usage.jsonl"
        decisions = self.temp / "decisions.jsonl"
        output = self.temp / "output"
        workspace = self.temp / "workspace-promoted"
        marker = workspace / "workflows" / "active-workflow" / ".recurrence-review.json"
        marker.parent.mkdir(parents=True)
        marker.write_text(json.dumps({"recurrence_key": key}), encoding="utf-8")
        self.write_jsonl(usage, entries)
        result = review.scan(
            usage_log=usage,
            decisions_path=decisions,
            output_dir=output,
            workspace_root=workspace,
            current_time=self.now,
        )
        self.assertEqual(result["status"], "no_change")
        self.assertEqual(result["qualified_intent_keys"], [key])
        self.assertFalse((output / "proposals").exists())

    def test_snooze_reject_and_reopen(self):
        key = "decision-state-test"
        entries = [
            self.evidence(self.now - timedelta(days=2), key),
            self.evidence(self.now - timedelta(days=1), key),
            self.evidence(self.now, key),
        ]
        _, usage, decisions, output, workspace = self.scan(entries, now=self.now)
        review.decide(
            intent_key=key,
            decision="snoozed",
            decisions_path=decisions,
            current_time=self.now,
            approved=True,
            snooze_days=10,
        )
        quiet = review.scan(
            usage_log=usage,
            decisions_path=decisions,
            output_dir=output,
            workspace_root=workspace,
            current_time=self.now + timedelta(days=5),
        )
        self.assertEqual(quiet["status"], "no_change")
        resurfaced = review.scan(
            usage_log=usage,
            decisions_path=decisions,
            output_dir=output,
            workspace_root=workspace,
            current_time=self.now + timedelta(days=11),
        )
        self.assertEqual(resurfaced["status"], "new_candidates")
        review.decide(
            intent_key=key,
            decision="rejected",
            decisions_path=decisions,
            current_time=self.now + timedelta(days=12),
            approved=True,
        )
        rejected = review.scan(
            usage_log=usage,
            decisions_path=decisions,
            output_dir=output,
            workspace_root=workspace,
            current_time=self.now + timedelta(days=13),
        )
        self.assertEqual(rejected["status"], "no_change")
        review.decide(
            intent_key=key,
            decision="reopened",
            decisions_path=decisions,
            current_time=self.now + timedelta(days=14),
            approved=True,
        )
        reopened = review.scan(
            usage_log=usage,
            decisions_path=decisions,
            output_dir=output,
            workspace_root=workspace,
            current_time=self.now + timedelta(days=15),
        )
        self.assertEqual(reopened["status"], "new_candidates")


class GateTests(WorkspaceTempCase):
    def setUp(self):
        super().setUp()
        self.now = datetime(2026, 7, 14, 10, 0, tzinfo=timezone.utc)
        self.key = "promote-test-workflow"
        entries = [
            self.evidence(self.now - timedelta(days=2), self.key),
            self.evidence(self.now - timedelta(days=1), self.key),
            self.evidence(self.now, self.key),
        ]
        _, self.usage, self.decisions, self.output, _ = self.scan(entries, now=self.now)
        self.proposal = self.output / "proposals" / self.key / "initial.md"

    def test_gate_one_and_gate_two(self):
        with self.assertRaises(review.ReviewError):
            review.scaffold_draft(
                intent_key=self.key,
                proposal=self.proposal,
                output_dir=self.output,
                decisions_path=self.decisions,
                current_time=self.now,
                approved=False,
            )
        staged = review.scaffold_draft(
            intent_key=self.key,
            proposal=self.proposal,
            output_dir=self.output,
            decisions_path=self.decisions,
            current_time=self.now,
            approved=True,
        )
        draft = Path(staged["draft"])
        self.assertTrue(draft.is_dir())

        workspace = self.temp / "promotion-workspace"
        (workspace / "workflows").mkdir(parents=True)
        agents_text = """# Router

| Workflow | Use when | Contract |
|---|---|---|
| `scratch` | fallback | `workflows/scratch/.github/scratch/SKILL.md` |
"""
        (workspace / "AGENTS.md").write_text(agents_text, encoding="utf-8")
        plan = review.create_promotion_plan(
            intent_key=self.key,
            draft=draft,
            output_dir=self.output,
            workspace_root=workspace,
            current_time=self.now,
        )
        self.assertEqual((workspace / "AGENTS.md").read_text(encoding="utf-8"), agents_text)
        self.assertFalse((workspace / "workflows" / self.key).exists())
        with self.assertRaises(review.ReviewError):
            review.apply_promotion(
                intent_key=self.key,
                draft=draft,
                plan_hash=plan["draft_hash"],
                output_dir=self.output,
                decisions_path=self.decisions,
                workspace_root=workspace,
                current_time=self.now,
                approved=False,
                run_health_check=False,
            )
        promoted = review.apply_promotion(
            intent_key=self.key,
            draft=draft,
            plan_hash=plan["draft_hash"],
            output_dir=self.output,
            decisions_path=self.decisions,
            workspace_root=workspace,
            current_time=self.now,
            approved=True,
            run_health_check=False,
        )
        self.assertEqual(promoted["status"], "promoted")
        destination = workspace / "workflows" / self.key
        self.assertTrue((destination / ".github" / self.key / "SKILL.md").is_file())
        self.assertTrue((destination / ".recurrence-review.json").is_file())
        self.assertTrue(draft.exists(), "promotion must copy, not move, the staged draft")
        updated_agents = (workspace / "AGENTS.md").read_text(encoding="utf-8")
        self.assertLess(updated_agents.index(f"| `{self.key}` |"), updated_agents.index("| `scratch` |"))

    def test_stale_hash_is_rejected(self):
        staged = review.scaffold_draft(
            intent_key=self.key,
            proposal=self.proposal,
            output_dir=self.output,
            decisions_path=self.decisions,
            current_time=self.now,
            approved=True,
        )
        draft = Path(staged["draft"])
        workspace = self.temp / "stale-workspace"
        (workspace / "workflows").mkdir(parents=True)
        (workspace / "AGENTS.md").write_text(
            "| `scratch` | fallback | `workflows/scratch/.github/scratch/SKILL.md` |\n",
            encoding="utf-8",
        )
        plan = review.create_promotion_plan(
            intent_key=self.key,
            draft=draft,
            output_dir=self.output,
            workspace_root=workspace,
            current_time=self.now,
        )
        (draft / "docs" / "README.md").write_text("changed after plan\n", encoding="utf-8")
        with self.assertRaises(review.ReviewError):
            review.apply_promotion(
                intent_key=self.key,
                draft=draft,
                plan_hash=plan["draft_hash"],
                output_dir=self.output,
                decisions_path=self.decisions,
                workspace_root=workspace,
                current_time=self.now,
                approved=True,
                run_health_check=False,
            )
        self.assertFalse((workspace / "workflows" / self.key).exists())


if __name__ == "__main__":
    unittest.main()
