"""Streaming MCAP adapter for JSON and ROS 2 CDR event channels."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from mcap.exceptions import McapError
from mcap.reader import make_reader
from mcap.records import Channel, Message, Schema
from mcap_ros2.decoder import DecoderFactory

from .analyzer import Event


class McapInputError(ValueError):
    """Raised when an MCAP recording cannot be converted to triage events."""


def _payload_mapping(payload: object) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return payload
    if isinstance(payload, SimpleNamespace):
        values = vars(payload)
        if values:
            return values
    values = {
        field: getattr(payload, field)
        for field in ("robot_id", "event", "details", "details_json")
        if hasattr(payload, field)
    }
    if values:
        return values
    raise McapInputError("decoded message must be an object with named fields")


def _decode_payload(
    schema: Schema | None,
    channel: Channel,
    message: Message,
    ros2_decoder: DecoderFactory,
) -> Mapping[str, Any]:
    if channel.message_encoding == "json":
        try:
            return _payload_mapping(json.loads(message.data))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise McapInputError(f"invalid JSON payload: {exc}") from exc

    decoder = ros2_decoder.decoder_for(channel.message_encoding, schema)
    if decoder is None:
        schema_name = schema.name if schema else "none"
        raise McapInputError(
            f"unsupported encoding {channel.message_encoding!r} for schema {schema_name!r}"
        )
    return _payload_mapping(decoder(message.data))


def _event_details(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_details = payload.get("details")
    if raw_details is None and "details_json" in payload:
        try:
            raw_details = json.loads(str(payload["details_json"]))
        except json.JSONDecodeError as exc:
            raise McapInputError(f"details_json is invalid: {exc}") from exc
    if raw_details is None:
        return {}
    if not isinstance(raw_details, Mapping):
        raise McapInputError("details or details_json must contain an object")
    return dict(raw_details)


def _convert_message(
    schema: Schema | None,
    channel: Channel,
    message: Message,
    ros2_decoder: DecoderFactory,
) -> Event:
    payload = _decode_payload(schema, channel, message, ros2_decoder)
    details = _event_details(payload)
    if "mcap" in details:
        raise McapInputError("details must not contain the reserved key 'mcap'")
    details["mcap"] = {
        "topic": channel.topic,
        "log_time_ns": message.log_time,
        "publish_time_ns": message.publish_time,
        "schema": schema.name if schema else None,
    }
    timestamp = datetime.fromtimestamp(
        message.log_time / 1_000_000_000, tz=timezone.utc
    )
    try:
        return Event.from_mapping(
            {
                "timestamp": timestamp.isoformat(),
                "robot_id": payload.get("robot_id"),
                "event": payload.get("event"),
                "details": details,
            }
        )
    except (TypeError, ValueError) as exc:
        raise McapInputError(str(exc)) from exc


def iter_mcap_events(
    path: str | Path,
    topics: Iterable[str] | str | None = None,
) -> Iterator[Event]:
    """Yield triage events from an MCAP without loading the recording at once.

    Messages are read in file order so the MCAP reader does not sort and retain
    an entire non-indexed recording in memory. JSON channels and ROS 2 CDR
    channels with ``ros2msg`` schemas are supported.
    """

    source = Path(path)
    decoder = DecoderFactory()
    try:
        with source.open("rb") as stream:
            reader = make_reader(stream, validate_crcs=True)
            messages = reader.iter_messages(topics=topics, log_time_order=False)
            for record_number, (schema, channel, message) in enumerate(messages, 1):
                try:
                    yield _convert_message(schema, channel, message, decoder)
                except McapInputError as exc:
                    raise McapInputError(
                        f"Invalid MCAP message {record_number} on topic {channel.topic!r}: {exc}"
                    ) from exc
    except McapInputError:
        raise
    except (McapError, OSError, EOFError) as exc:
        raise McapInputError(f"Invalid MCAP recording {source}: {exc}") from exc
