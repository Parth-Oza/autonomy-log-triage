import tempfile
import unittest
from pathlib import Path

from mcap_ros2.writer import Writer

from autonomy_log_triage.mcap_adapter import McapInputError, iter_mcap_events

EVENT_SCHEMA = """string robot_id
string event
string details_json
"""


class McapAdapterTests(unittest.TestCase):
    def test_streams_ros2_event_and_preserves_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.mcap"
            writer = Writer(str(path))
            schema = writer.register_msgdef("autonomy_msgs/msg/Event", EVENT_SCHEMA)
            writer.write_message(
                topic="/autonomy/events",
                schema=schema,
                message={
                    "robot_id": "robot-07",
                    "event": "planning_stall",
                    "details_json": '{"duration_ms":840}',
                },
                log_time=1_700_000_000_123_456_789,
                publish_time=1_700_000_000_123_450_000,
                sequence=42,
            )
            writer.finish()

            events = iter_mcap_events(path, topics=["/autonomy/events"])
            self.assertNotIsInstance(events, list)
            event = next(events)
            self.assertEqual(event.robot_id, "robot-07")
            self.assertEqual(event.event, "planning_stall")
            self.assertEqual(event.details["duration_ms"], 840)
            self.assertEqual(
                event.details["mcap"],
                {
                    "topic": "/autonomy/events",
                    "log_time_ns": 1_700_000_000_123_456_789,
                    "publish_time_ns": 1_700_000_000_123_450_000,
                    "schema": "autonomy_msgs/msg/Event",
                },
            )
            with self.assertRaises(StopIteration):
                next(events)

    def test_empty_recording_yields_no_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.mcap"
            writer = Writer(str(path))
            writer.finish()

            self.assertEqual(list(iter_mcap_events(path)), [])

    def test_malformed_recording_has_contextual_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.mcap"
            path.write_bytes(b"not-an-mcap")

            with self.assertRaisesRegex(McapInputError, "Invalid MCAP recording"):
                list(iter_mcap_events(path))

    def test_invalid_event_payload_identifies_record_and_topic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid-event.mcap"
            writer = Writer(str(path))
            schema = writer.register_msgdef("autonomy_msgs/msg/Event", EVENT_SCHEMA)
            writer.write_message(
                topic="/autonomy/events",
                schema=schema,
                message={"robot_id": "", "event": "fault", "details_json": "{}"},
                log_time=1,
                publish_time=1,
            )
            writer.finish()

            with self.assertRaisesRegex(
                McapInputError,
                r"message 1 on topic '/autonomy/events'",
            ):
                list(iter_mcap_events(path))


if __name__ == "__main__":
    unittest.main()
