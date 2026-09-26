"""Canonical nested/flat event normalization extracted from notebook 02."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

EventRecord = dict[str, Any]


def present(value: object) -> bool:
    """Return whether a scalar can supply a normalized field."""
    return value is not None and not (
        isinstance(value, float) and math.isnan(value)
    )


def get_name(value: object) -> object:
    """Read a name from nested StatsBomb data or return a flat value."""
    return value.get("name") if isinstance(value, dict) else value


def get_id(value: object) -> object:
    """Read an ID from a nested StatsBomb value."""
    return value.get("id") if isinstance(value, dict) else None


def field(raw: EventRecord, flat: str, section: str, key: str) -> object:
    """Prefer a present flat value, falling back to its nested equivalent."""
    value = raw.get(flat)
    nested = raw.get(section)
    return value if present(value) else (
        nested.get(key) if isinstance(nested, dict) else None
    )


def numeric(value: object) -> float:
    """Coerce finite numeric input, returning NaN for missing/invalid values."""
    try:
        result = float(value)  # type: ignore[arg-type]
        return result if math.isfinite(result) else math.nan
    except (TypeError, ValueError):
        return math.nan


def xy(value: object) -> list[float]:
    """Normalize the first two coordinates without inventing missing values."""
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return [numeric(value[0]), numeric(value[1])]
    return [math.nan, math.nan]


def normalized_id(flat_value: object, nested_value: object = None) -> int | None:
    """Normalize an ID from flat notebook output or nested provider data."""
    value = flat_value if present(flat_value) else get_id(nested_value)
    result = numeric(value)
    return int(result) if math.isfinite(result) else None


def lineup_ids(raw: EventRecord) -> list[int]:
    """Extract starting-player IDs from nested or flat tactics data."""
    lineup = raw.get("tactics_lineup")
    if not isinstance(lineup, list):
        tactics = raw.get("tactics")
        lineup = tactics.get("lineup", []) if isinstance(tactics, dict) else []
    result: list[int] = []
    for item in lineup:
        player = item.get("player") if isinstance(item, dict) else None
        player_id = normalized_id(
            item.get("player_id") if isinstance(item, dict) else None, player
        )
        if player_id is not None:
            result.append(player_id)
    return result


def related_ids(raw: EventRecord) -> list[str]:
    """Preserve provider related-event IDs as strings."""
    value = raw.get("related_events") or raw.get("related_event_ids") or []
    return [str(item) for item in value] if isinstance(value, list) else []


def normalize(raw: EventRecord, source_file: str, raw_line: int) -> EventRecord:
    """Normalize one event while preserving IDs and source provenance."""
    location = xy(raw.get("location"))
    destination = xy(field(raw, "pass_end_location", "pass", "end_location"))
    timestamp = pd.to_timedelta(raw.get("timestamp"), errors="coerce")
    player = raw.get("player")
    replacement = field(
        raw, "substitution_replacement", "substitution", "replacement"
    )
    card = field(raw, "foul_committed_card", "foul_committed", "card")
    if not present(card):
        card = field(raw, "bad_behaviour_card", "bad_behaviour", "card")
    team = raw.get("team")
    possession_team = raw.get("possession_team")
    event_type = raw.get("type")
    seconds = timestamp.total_seconds() if pd.notna(timestamp) else math.nan

    return {
        "event_id": raw.get("id") or raw.get("event_id"),
        "index": numeric(raw.get("index")),
        "period": numeric(raw.get("period")),
        "minute": numeric(raw.get("minute")),
        "second": numeric(raw.get("second")),
        "seconds": seconds,
        "type": get_name(event_type),
        "type_id": normalized_id(raw.get("type_id"), event_type),
        "team": get_name(team),
        "team_id": normalized_id(raw.get("team_id"), team),
        "possession_team": get_name(possession_team),
        "possession_team_id": normalized_id(
            raw.get("possession_team_id"), possession_team
        ),
        "possession": raw.get("possession"),
        "player": get_name(player),
        "player_id": normalized_id(raw.get("player_id"), player),
        "recipient": get_name(field(raw, "pass_recipient", "pass", "recipient")),
        "pass_type": get_name(field(raw, "pass_type", "pass", "type")),
        "height": get_name(field(raw, "pass_height", "pass", "height")),
        "pass_technique": get_name(
            field(raw, "pass_technique", "pass", "technique")
        ),
        "pass_outcome": get_name(field(raw, "pass_outcome", "pass", "outcome")),
        "shot_outcome": get_name(field(raw, "shot_outcome", "shot", "outcome")),
        "card": get_name(card),
        "cross": field(raw, "pass_cross", "pass", "cross"),
        "substitution_replacement": get_name(replacement),
        "substitution_replacement_id": normalized_id(
            raw.get("substitution_replacement_id"), replacement
        ),
        "starting_xi_ids": lineup_ids(raw),
        "related_event_ids": related_ids(raw),
        "x": location[0],
        "y": location[1],
        "end_x": destination[0],
        "end_y": destination[1],
        "xg": numeric(field(raw, "shot_statsbomb_xg", "shot", "statsbomb_xg")),
        "source_file": source_file,
        "raw_line": raw_line,
    }
