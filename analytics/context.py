"""Pre-event match context reconstruction extracted from notebook 02."""

from __future__ import annotations

import math
from typing import Any

EventRecord = dict[str, Any]
CONTEXT_VERSION = "match-context-v1-on-pitch"
DISMISSAL_CARDS = {"red card", "second yellow", "second yellow card"}


def phase_from_minute(minute: float) -> str:
    """Map elapsed match minutes to the research phase buckets."""
    if minute <= 30:
        return "00-30"
    if minute <= 60:
        return "31-60"
    if minute <= 75:
        return "61-75"
    return "76+"


def build_pre_event_context(
    records: list[EventRecord], home_team: str, away_team: str
) -> tuple[
    dict[str, EventRecord],
    dict[str, int],
    list[EventRecord],
    list[EventRecord],
    list[EventRecord],
]:
    """Reconstruct score and on-pitch state immediately before every event."""
    teams = [home_team, away_team]
    scores = {team: 0 for team in teams}
    active: dict[str, set[int]] = {team: set() for team in teams}
    for event in records:
        if event.get("type") == "Starting XI" and event.get("team") in active:
            active[event["team"]].update(int(value) for value in event["starting_xi_ids"])
    if any(len(players) != 11 for players in active.values()):
        sizes = [(team, len(players)) for team, players in active.items()]
        raise ValueError(f"Incomplete Starting XI: {sizes}")

    contexts: dict[str, EventRecord] = {}
    own_goals: list[EventRecord] = []
    dismissals: list[EventRecord] = []
    substitutions: list[EventRecord] = []
    last_corner: dict[str, tuple[float, float, str]] = {}

    for event in records:
        event_id = str(event["event_id"])
        team = event.get("team")
        opponent = next((value for value in teams if value != team), None)
        second = float(event.get("second", math.nan))
        minute = float(event.get("minute", math.nan))
        match_minute = minute + (second / 60 if math.isfinite(second) else 0)
        team_score = scores.get(team, math.nan)
        opponent_score = scores.get(opponent, math.nan)
        score_diff = team_score - opponent_score
        previous = last_corner.get(team)
        event_seconds = float(event.get("seconds", math.nan))
        delta_corner = (
            event_seconds - previous[1]
            if previous
            and previous[0] == event.get("period")
            and math.isfinite(event_seconds)
            else math.nan
        )
        attacking = len(active[team]) if team in active else math.nan
        defending = len(active[opponent]) if opponent in active else math.nan
        players_known = math.isfinite(attacking) and math.isfinite(defending)
        contexts[event_id] = {
            "home_score_before": scores[home_team],
            "away_score_before": scores[away_team],
            "goals_for_before": team_score,
            "goals_against_before": opponent_score,
            "score_diff": score_diff,
            "game_state": (
                "unknown" if not math.isfinite(score_diff) else
                "winning" if score_diff > 0 else
                "losing" if score_diff < 0 else "drawing"
            ),
            "match_minute": match_minute,
            "match_phase": phase_from_minute(match_minute),
            "is_stoppage_time": bool(
                (event.get("period") == 1 and match_minute >= 45)
                or (event.get("period") == 2 and match_minute >= 90)
            ),
            "attacking_players": attacking,
            "defending_players": defending,
            "player_difference": attacking - defending if players_known else math.nan,
            "numerical_state": (
                "unknown" if not players_known else
                "advantage" if attacking > defending else
                "disadvantage" if attacking < defending else "equal"
            ),
            "seconds_since_previous_same_team_corner": delta_corner,
            "repeat_corner_60s": bool(
                math.isfinite(delta_corner) and 0 <= delta_corner <= 60
            ),
            "context_version": CONTEXT_VERSION,
        }

        if event.get("type") == "Pass" and event.get("pass_type") == "Corner":
            last_corner[team] = (event["period"], event_seconds, event_id)
        if event.get("type") == "Shot" and event.get("shot_outcome") == "Goal":
            if team in scores:
                scores[team] += 1
        elif event.get("type") == "Own Goal For" and team in scores:
            scores[team] += 1
            own_goals.append({
                "for_event_id": event_id,
                "beneficiary": team,
                "period": event.get("period"),
                "seconds": event.get("seconds"),
                "related_event_ids": event.get("related_event_ids", []),
            })

        if event.get("type") == "Substitution":
            outgoing = event.get("player_id")
            replacement = event.get("substitution_replacement_id")
            valid = bool(
                team in active
                and outgoing in active[team]
                and replacement not in active[team]
            )
            substitutions.append({
                "event_id": event_id,
                "team": team,
                "outgoing_player_id": outgoing,
                "replacement_player_id": replacement,
                "valid": valid,
            })
            if valid:
                active[team].remove(outgoing)
                active[team].add(replacement)

        card = str(event.get("card") or "").strip().lower()
        if card in DISMISSAL_CARDS:
            player_id = event.get("player_id")
            on_pitch = bool(team in active and player_id in active[team])
            dismissals.append({
                "event_id": event_id,
                "team": team,
                "player_id": player_id,
                "player": event.get("player"),
                "card": event.get("card"),
                "on_pitch": on_pitch,
            })
            if on_pitch:
                active[team].remove(player_id)

    return contexts, scores, own_goals, dismissals, substitutions
