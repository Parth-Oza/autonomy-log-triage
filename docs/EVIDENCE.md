# Evidence record

## Verified synthetic scenario

Command:

```bash
autonomy-triage examples/synthetic_events.jsonl
```

Expected summary:

```json
{
  "events": 8,
  "robots": 3,
  "incidents": 5,
  "heartbeat_gaps": 2
}
```

The rules identify one critical recovery failure, two high-severity conditions, and two medium-severity conditions. Adjacent events for `robot-07` expose 35-second and 32-second heartbeat gaps when the threshold is 30 seconds.

## Test record

The test suite verifies isolated heartbeat arithmetic and locks the complete public synthetic scenario to the documented `8 / 3 / 5 / 2` summary.

Run:

```bash
python -m unittest discover -s tests -v
```

## Interpretation boundary

This project demonstrates deterministic event analysis, not causal diagnosis. It does not yet ingest ROS 2 diagnostics or MCAP directly, correlate traces, estimate probabilistic confidence, or operate a live fleet dashboard. Those capabilities are defined as future work in the Autonomy Flight Recorder roadmap.
