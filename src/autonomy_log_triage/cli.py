"""Command-line interface."""

from __future__ import annotations

import argparse
import json

from .analyzer import analyze_events, load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Triage synthetic robot autonomy event logs")
    parser.add_argument("path", help="JSON Lines event log")
    parser.add_argument("--heartbeat-gap", type=float, default=30.0, help="Gap threshold in seconds")
    args = parser.parse_args()
    report = analyze_events(load_jsonl(args.path), heartbeat_gap_seconds=args.heartbeat_gap)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

