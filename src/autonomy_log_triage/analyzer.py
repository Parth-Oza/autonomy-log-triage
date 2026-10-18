"""Small, dependency-free building blocks for robot log triage."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INCIDENT_EVENTS = {
    "communication_drop": "high",
    "localization_stale": "high",
    "planning_stall": "medium",
    "recovery_failed": "critical",
    "battery_low": "medium",
}


@dataclass(frozen=True, slots=True)
class Event:
    timestamp: datetime
    robot_id: str
    event: str
    details: dict[str, Any]

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> Event:
        timestamp = str(value.get("timestamp", "")).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        robot_id = str(value.get("robot_id") or "").strip()
        event = str(value.get("event") or "").strip().lower()
        if not robot_id or not event:
            raise ValueError("Each event needs robot_id and event")
        details = value.get("details") or {}
        if not isinstance(details, dict):
            raise TypeError("details must be an object")
        return cls(parsed, robot_id, event, details)


def load_jsonl(path: str | Path) -> list[Event]:
    events: list[Event] = []
    for number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            events.append(Event.from_mapping(json.loads(line)))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid event on line {number}: {exc}") from exc
    return events


def analyze_events(
    events: Iterable[Event],
    heartbeat_gap_seconds: float = 30.0,
    *,
    events_are_ordered: bool = False,
) -> dict[str, Any]:
    ordered = (
        events
        if events_are_ordered
        else sorted(events, key=lambda item: (item.robot_id, item.timestamp))
    )
    robots: set[str] = set()
    previous_by_robot: dict[str, Event] = {}
    event_counts: Counter[str] = Counter()
    incidents: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    event_total = 0

    for item in ordered:
        event_total += 1
        robots.add(item.robot_id)
        event_counts[item.event] += 1
        if item.event in INCIDENT_EVENTS:
            incidents.append(
                {
                    "robot_id": item.robot_id,
                    "timestamp": item.timestamp.isoformat(),
                    "type": item.event,
                    "severity": INCIDENT_EVENTS[item.event],
                    "details": item.details,
                }
            )
        previous = previous_by_robot.get(item.robot_id)
        if previous is not None:
            gap = (item.timestamp - previous.timestamp).total_seconds()
            if events_are_ordered and gap < 0:
                raise ValueError(
                    f"Events for {item.robot_id!r} are not in nondecreasing timestamp order"
                )
            if gap > heartbeat_gap_seconds:
                gaps.append(
                    {
                        "robot_id": item.robot_id,
                        "after": previous.timestamp.isoformat(),
                        "gap_seconds": round(gap, 3),
                    }
                )
        previous_by_robot[item.robot_id] = item

    incidents.sort(key=lambda item: (item["severity"] != "critical", item["timestamp"]))
    return {
        "summary": {
            "events": event_total,
            "robots": len(robots),
            "incidents": len(incidents),
            "heartbeat_gaps": len(gaps),
        },
        "event_counts": dict(event_counts.most_common()),
        "incidents": incidents,
        "heartbeat_gaps": gaps,
    }
