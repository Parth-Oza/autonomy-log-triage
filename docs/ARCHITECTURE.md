# Architecture

## Goal

Autonomy Log Triage provides a small, auditable analysis core between raw robot events and downstream incident-review tools. The repository deliberately avoids transport-specific code so the same logic can be exercised with synthetic data, unit tests, CI artifacts, or adapters maintained elsewhere.

## Processing stages

1. `load_jsonl` reads non-empty lines and reports malformed input with its line number.
2. `Event.from_mapping` normalizes timestamps, identifiers, event names, and details.
3. `analyze_events` sorts deterministically, groups by robot, and counts event types.
4. Known incident types are mapped to explicit severity levels.
5. Adjacent per-robot timestamps are checked for heartbeat gaps.
6. A stable dictionary is returned for JSON serialization or programmatic reuse.

## Public extension points

- Add an external adapter that converts MCAP, ROS2 bag, database, or streaming records into the documented event contract.
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
- Parser failures are explicit rather than silently dropping data.
- Core logic is separated from argument parsing and printing.
