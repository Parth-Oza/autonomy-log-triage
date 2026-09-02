from datetime import datetime, timezone
import unittest

from autonomy_log_triage.analyzer import Event, analyze_events


class AnalyzerTests(unittest.TestCase):
    def test_incidents_and_heartbeat_gaps(self) -> None:
        events = [
            Event(datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc), "r1", "mission_started", {}),
            Event(datetime(2026, 1, 1, 0, 0, 8, tzinfo=timezone.utc), "r1", "planning_stall", {"duration_ms": 500}),
            Event(datetime(2026, 1, 1, 0, 0, 50, tzinfo=timezone.utc), "r1", "mission_resumed", {}),
        ]
        report = analyze_events(events, heartbeat_gap_seconds=30)
        self.assertEqual(report["summary"], {"events": 3, "robots": 1, "incidents": 1, "heartbeat_gaps": 1})
        self.assertEqual(report["incidents"][0]["type"], "planning_stall")
        self.assertEqual(report["heartbeat_gaps"][0]["gap_seconds"], 42.0)


if __name__ == "__main__":
    unittest.main()

