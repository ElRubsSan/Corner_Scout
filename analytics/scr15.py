"""Canonical SCR-15 sequence extraction from notebook 03."""

from __future__ import annotations

import math
from typing import Any

EventRecord = dict[str, Any]
RULE_VERSION = "scr15-research-v1.2-first-limit"
RESTARTS = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off", "Penalty"}


def _finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def scan_window(
    records: list[EventRecord], start: int, seconds_limit: float = 15
) -> EventRecord:
    """Scan only until the first SCR-15 boundary after one corner."""
    corner = records[start]
    result: EventRecord = {
        "valid_sequence": True,
        "end_reason": None,
        "end_seconds": corner.get("seconds"),
        "terminal_event_id": None,
        "terminal_index": None,
        "shot_ids": [],
        "shot_times": [],
        "shot_xgs": [],
        "restart_ids": [],
        "possession_change_ids": [],
        "followup_cross_ids": [],
        "first_recipient": corner.get("recipient"),
    }
    if (
        not _finite(corner.get("seconds"))
        or not corner.get("team")
        or corner.get("possession_team") != corner.get("team")
    ):
        result.update(valid_sequence=False, end_reason="invalid_start")
        return result

    corner_time = float(corner["seconds"])
    previous_time = corner_time
    previous_possession = corner.get("possession")
    for event in records[start + 1:]:
        terminal = {
            "terminal_event_id": event.get("event_id"),
            "terminal_index": event.get("index"),
        }
        if event.get("period") != corner.get("period"):
            result.update(end_reason="period_end", **terminal)
            break
        if not _finite(event.get("seconds")):
            result.update(
                valid_sequence=False, end_reason="ambiguous_clock", **terminal
            )
            break
        current_time = float(event["seconds"])
        elapsed = current_time - corner_time
        # The time boundary is checked before monotonicity so events observed
        # after closure cannot retrospectively invalidate the sequence.
        if elapsed > seconds_limit:
            result.update(
                end_reason="time_limit",
                end_seconds=corner_time + seconds_limit,
                **terminal,
            )
            break
        if current_time < previous_time or elapsed < 0:
            result.update(
                valid_sequence=False, end_reason="ambiguous_clock", **terminal
            )
            break
        previous_time = current_time
        result["end_seconds"] = current_time
        if event.get("type") == "Half End":
            result.update(end_reason="period_end", **terminal)
            break
        if not event.get("possession_team"):
            result.update(
                valid_sequence=False, end_reason="unknown_possession", **terminal
            )
            break
        if event.get("possession_team") != corner.get("team"):
            result.update(end_reason="possession_team_change", **terminal)
            break
        if event.get("type") == "Pass" and event.get("pass_type") == "Corner":
            result["restart_ids"].append(event["event_id"])
            result.update(end_reason="new_corner", **terminal)
            break

        if event.get("possession") != previous_possession:
            result["possession_change_ids"].append(event["event_id"])
        previous_possession = event.get("possession")
        if event.get("pass_type") in RESTARTS:
            result["restart_ids"].append(event["event_id"])
        if (
            event.get("team") == corner.get("team")
            and event.get("type") == "Pass"
            and event.get("cross") is True
        ):
            result["followup_cross_ids"].append(event["event_id"])
        if event.get("team") == corner.get("team") and event.get("type") == "Shot":
            result["shot_ids"].append(event["event_id"])
            result["shot_times"].append(elapsed)
            result["shot_xgs"].append(event.get("xg"))
    else:
        result.update(valid_sequence=False, end_reason="unobserved_end")
    return result


def label_sequence(result: EventRecord) -> EventRecord:
    """Build the target independently from optional xG completeness."""
    valid = bool(result["valid_sequence"])
    xgs = result["shot_xgs"]
    complete_xg = valid and all(
        _finite(value) and 0 <= float(value) <= 1 for value in xgs
    )
    return {
        "shot_within_15s": int(bool(result["shot_ids"])) if valid else math.nan,
        "n_shots": len(result["shot_ids"]) if valid else math.nan,
        "seconds_to_first_shot": (
            min(result["shot_times"])
            if valid and result["shot_times"]
            else math.nan
        ),
        "xg_complete": complete_xg,
        "xg_sequence": float(sum(xgs)) if complete_xg else math.nan,
    }


def extract_corners(
    records: list[EventRecord], match_id: int, seconds_limit: float = 15
) -> list[EventRecord]:
    """Extract all corner sequences and reject overlapping shot attribution."""
    rows: list[EventRecord] = []
    attributed_shots: set[str] = set()
    for index, corner in enumerate(records):
        if corner.get("type") != "Pass" or corner.get("pass_type") != "Corner":
            continue
        result = scan_window(records, index, seconds_limit)
        duplicate_shots = attributed_shots.intersection(result["shot_ids"])
        if duplicate_shots:
            raise ValueError(f"Overlapping SCR-15 shots: {sorted(duplicate_shots)}")
        attributed_shots.update(result["shot_ids"])
        rows.append({
            **corner,
            **result,
            **label_sequence(result),
            "match_id": int(match_id),
            "rule_version": RULE_VERSION,
            "window_seconds": seconds_limit,
        })
    return rows
