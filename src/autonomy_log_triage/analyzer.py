"""Small, dependency-free building blocks for robot log triage."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


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
    def from_mapping(cls, value: dict[str, Any]) -> "Event":
        timestamp = str(value.get("timestamp", "")).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        robot_id = str(value.get("robot_id", "")).strip()
        event = str(value.get("event", "")).strip().lower()
        if not robot_id or not event:
            raise ValueError("Each event needs robot_id and event")
        details = value.get("details") or {}
        if not isinstance(details, dict):
            raise ValueError("details must be an object")
        return cls(parsed, robot_id, event, details)


def load_jsonl(path: str | Path) -> list[Event]:
    events: list[Event] = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            events.append(Event.from_mapping(json.loads(line)))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid event on line {number}: {exc}") from exc
    return events


def analyze_events(events: Iterable[Event], heartbeat_gap_seconds: float = 30.0) -> dict[str, Any]:
    ordered = sorted(events, key=lambda item: (item.robot_id, item.timestamp))
    by_robot: dict[str, list[Event]] = defaultdict(list)
    event_counts: Counter[str] = Counter()
    incidents: list[dict[str, Any]] = []

    for item in ordered:
        by_robot[item.robot_id].append(item)
        event_counts[item.event] += 1
        if item.event in INCIDENT_EVENTS:
            incidents.append({
                "robot_id": item.robot_id,
                "timestamp": item.timestamp.isoformat(),
                "type": item.event,
                "severity": INCIDENT_EVENTS[item.event],
                "details": item.details,
            })

    gaps: list[dict[str, Any]] = []
    for robot_id, robot_events in by_robot.items():
        for previous, current in zip(robot_events, robot_events[1:]):
            gap = (current.timestamp - previous.timestamp).total_seconds()
            if gap > heartbeat_gap_seconds:
                gaps.append({
                    "robot_id": robot_id,
                    "after": previous.timestamp.isoformat(),
                    "gap_seconds": round(gap, 3),
                })

    incidents.sort(key=lambda item: (item["severity"] != "critical", item["timestamp"]))
    return {
        "summary": {
            "events": len(ordered),
            "robots": len(by_robot),
            "incidents": len(incidents),
            "heartbeat_gaps": len(gaps),
        },
        "event_counts": dict(event_counts.most_common()),
        "incidents": incidents,
        "heartbeat_gaps": gaps,
    }

