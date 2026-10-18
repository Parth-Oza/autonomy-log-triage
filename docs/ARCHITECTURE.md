# Architecture

## Goal

Autonomy Log Triage provides a small, auditable analysis core between raw robot events and downstream incident-review tools. The repository deliberately avoids transport-specific code so the same logic can be exercised with synthetic data, unit tests, CI artifacts, or adapters maintained elsewhere.

## Processing stages

1. `load_jsonl` reads non-empty lines and reports malformed input with its line number.
2. `iter_mcap_events` streams records in file order, validates CRCs, decodes JSON or ROS 2 CDR, and attaches source metadata.
3. `Event.from_mapping` normalizes timestamps, identifiers, event names, and details.
4. `analyze_events` sorts transport-neutral input or consumes a declared-ordered stream in one pass.
5. Known incident types are mapped to explicit severity levels.
6. Adjacent per-robot timestamps are checked for heartbeat gaps.
7. A stable dictionary is returned for JSON serialization or programmatic reuse.

## MCAP reliability model

- `mcap.reader.make_reader` handles seekable files and chunk decompression.
- `log_time_order=False` prevents the reader from retaining a non-indexed recording merely to sort it.
- ROS 2 CDR decoding uses the schema embedded in the recording and does not require a ROS installation.
- Topic, schema, exact log time, and exact publish time survive normalization under `details.mcap`.
- The ordered analyzer retains only counters, previous per-robot state, and report output—not raw messages.
- A timestamp regression for any robot fails explicitly because heartbeat gaps would otherwise be unreliable.
- Empty recordings produce an empty report; malformed containers and payloads include recording, record, and topic context.

## Public extension points

- Add adapters for rosbag2 SQLite, databases, or live telemetry streams using the documented event contract.
- Add event types to `INCIDENT_EVENTS` with tests that demonstrate the intended severity.
- Consume `analyze_events` directly from a service, notebook, or batch workflow.
- Send the JSON report to a dashboard or retain it as a CI artifact.

## Deliberate boundaries

- No network access or persistent storage.
- No hidden scoring model or probabilistic classification.
- No employer schemas, operational data, maps, missions, or facility identifiers.
- No assumption that timestamps arrive in order.

## Reliability properties

- Frozen event records prevent accidental mutation.
- Sorting uses robot identifier and timestamp for repeatable analysis.
- JSONL and MCAP parser failures are explicit rather than silently dropping data.
- Core logic is separated from argument parsing and printing.
