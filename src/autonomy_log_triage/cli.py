"""Command-line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyzer import analyze_events, load_jsonl
from .mcap_adapter import iter_mcap_events


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Triage synthetic robot autonomy event logs"
    )
    parser.add_argument("path", help="JSON Lines event log or MCAP recording")
    parser.add_argument(
        "--input-format",
        choices=("auto", "jsonl", "mcap"),
        default="auto",
        help="Input format; auto selects MCAP for a .mcap extension",
    )
    parser.add_argument(
        "--topic",
        action="append",
        dest="topics",
        help="MCAP topic to include; repeat to select multiple topics",
    )
    parser.add_argument(
        "--heartbeat-gap", type=float, default=30.0, help="Gap threshold in seconds"
    )
    args = parser.parse_args()
    input_format = args.input_format
    if input_format == "auto":
        input_format = "mcap" if Path(args.path).suffix.lower() == ".mcap" else "jsonl"
    if args.topics and input_format != "mcap":
        parser.error("--topic can only be used with MCAP input")
    events = (
        iter_mcap_events(args.path, topics=args.topics)
        if input_format == "mcap"
        else load_jsonl(args.path)
    )
    report = analyze_events(
        events,
        heartbeat_gap_seconds=args.heartbeat_gap,
        events_are_ordered=input_format == "mcap",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
