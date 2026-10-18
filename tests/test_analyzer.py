import unittest
from datetime import datetime, timezone
from pathlib import Path

from autonomy_log_triage.analyzer import Event, analyze_events, load_jsonl


class AnalyzerTests(unittest.TestCase):
    def test_missing_required_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "robot_id and event"):
            Event.from_mapping({"timestamp": "2026-01-01T00:00:00Z", "event": "fault"})

    def test_ordered_stream_is_consumed_in_one_pass(self) -> None:
        events = (
            Event(
                datetime(2026, 1, 1, 0, 0, second, tzinfo=timezone.utc),
                "r1",
                "heartbeat",
                {},
            )
            for second in (0, 5, 10)
        )

        report = analyze_events(events, events_are_ordered=True)

        self.assertEqual(report["summary"]["events"], 3)

    def test_ordered_stream_rejects_timestamp_regression(self) -> None:
        events = [
            Event(
                datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc),
                "r1",
                "heartbeat",
                {},
            ),
            Event(
                datetime(2026, 1, 1, 0, 0, 4, tzinfo=timezone.utc),
                "r1",
                "heartbeat",
                {},
            ),
        ]

        with self.assertRaisesRegex(ValueError, "nondecreasing timestamp order"):
            analyze_events(events, events_are_ordered=True)

    def test_incidents_and_heartbeat_gaps(self) -> None:
        events = [
            Event(
                datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                "r1",
                "mission_started",
                {},
            ),
            Event(
                datetime(2026, 1, 1, 0, 0, 8, tzinfo=timezone.utc),
                "r1",
                "planning_stall",
                {"duration_ms": 500},
            ),
            Event(
                datetime(2026, 1, 1, 0, 0, 50, tzinfo=timezone.utc),
                "r1",
                "mission_resumed",
                {},
            ),
        ]
        report = analyze_events(events, heartbeat_gap_seconds=30)
        self.assertEqual(
            report["summary"],
            {"events": 3, "robots": 1, "incidents": 1, "heartbeat_gaps": 1},
        )
        self.assertEqual(report["incidents"][0]["type"], "planning_stall")
        self.assertEqual(report["heartbeat_gaps"][0]["gap_seconds"], 42.0)

    def test_public_synthetic_scenario_matches_documented_evidence(self) -> None:
        example = Path(__file__).parents[1] / "examples" / "synthetic_events.jsonl"
        report = analyze_events(load_jsonl(example), heartbeat_gap_seconds=30)

        self.assertEqual(
            report["summary"],
            {"events": 8, "robots": 3, "incidents": 5, "heartbeat_gaps": 2},
        )
        self.assertEqual(
            [gap["gap_seconds"] for gap in report["heartbeat_gaps"]],
            [35.0, 32.0],
        )
        self.assertEqual(report["incidents"][0]["type"], "recovery_failed")
        self.assertEqual(report["incidents"][0]["details"]["attempts"], 3)


if __name__ == "__main__":
    unittest.main()
