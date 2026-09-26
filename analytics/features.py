"""Canonical, reusable feature extraction from notebooks 04 and 05."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

HISTORY_MATCHES = 8
SHORT_THRESHOLD = 18.0
SMOOTHING_STRENGTH = 10.0

CORE_FEATURES = [
    "hist_corners_per_match",
    "hist_scr15_smoothed",
    "hist_xg_per_corner",
    "hist_short_share",
    "hist_high_share",
    "hist_top_taker_share",
    "hist_dominant_zone_share",
    "hist_score_losing_share",
    "opp_hist_scr15_conceded_smoothed",
    "is_home",
]

SCENARIO_FEATURES = [
    "match_minute",
    "score_diff",
    "player_difference",
    "match_phase",
    "game_state",
    "numerical_state",
    "corner_side",
    "repeat_corner_60s",
    "seconds_since_previous_same_team_corner",
    "attacking_players",
    "defending_players",
]


def _dates(frame: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(frame["match_date"]).dt.normalize()


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def engineer_corner_geometry(
    corners: pd.DataFrame, *, short_threshold: float = SHORT_THRESHOLD
) -> pd.DataFrame:
    """Add notebook-04 geometry, short-proxy and delivery-zone columns.

    The input is not mutated. A valid origin must be at a StatsBomb corner and
    every coordinate must be on the 120 x 80 pitch.
    """
    required = {"x", "y", "end_x", "end_y", "height"}
    missing = required - set(corners.columns)
    if missing:
        raise ValueError(f"Missing geometry columns: {sorted(missing)}")

    result = corners.copy()
    result["valid_geometry"] = (
        result[["x", "y", "end_x", "end_y"]].notna().all(axis=1)
        & result["x"].between(0, 120)
        & result["y"].between(0, 80)
        & result["end_x"].between(0, 120)
        & result["end_y"].between(0, 80)
        & result["x"].ge(118)
        & (result["y"].le(2) | result["y"].ge(78))
    )
    result["pass_length"] = np.hypot(
        result["end_x"] - result["x"], result["end_y"] - result["y"]
    )
    result["end_y_relative"] = np.where(
        result["y"] < 40, result["end_y"], 80 - result["end_y"]
    )
    result["short_proxy"] = (
        result["valid_geometry"]
        & result["height"].isin(["Ground Pass", "Low Pass"])
        & result["pass_length"].le(short_threshold)
    )
    result["execution_type"] = np.select(
        [result["short_proxy"], result["valid_geometry"]],
        ["short", "direct"],
        default="unknown",
    )
    result["direct_delivery_valid"] = result["valid_geometry"] & ~result["short_proxy"]

    result["delivery_zone"] = pd.Series(pd.NA, index=result.index, dtype="string")
    outside = (
        result["end_x"].lt(102)
        | result["end_y_relative"].lt(18)
        | result["end_y_relative"].gt(62)
    )
    direct = result["direct_delivery_valid"]
    result.loc[direct & outside, "delivery_zone"] = "fuera_area"
    result.loc[direct & ~outside & result["end_y_relative"].lt(36), "delivery_zone"] = (
        "franja_cercana"
    )
    result.loc[
        direct & ~outside & result["end_y_relative"].between(36, 44), "delivery_zone"
    ] = "franja_central"
    result.loc[direct & ~outside & result["end_y_relative"].gt(44), "delivery_zone"] = (
        "franja_lejana"
    )
    result["corner_side"] = np.where(result["y"] < 40, "left", "right")
    result["is_high"] = result["height"].eq("High Pass")
    return result


def build_team_match_observed(matches: pd.DataFrame, corners: pd.DataFrame) -> pd.DataFrame:
    """Build one row per team and match, retaining teams with zero corners."""
    required_matches = {"match_id", "match_date", "kick_off", "home_team", "away_team"}
    missing = required_matches - set(matches.columns)
    if missing:
        raise ValueError(f"Missing match columns: {sorted(missing)}")

    corner_dates = corners.copy()
    if "match_date" in corner_dates:
        corner_dates["match_date"] = _dates(corner_dates)
    ordered = matches.copy()
    ordered["match_date"] = _dates(ordered)
    ordered = ordered.sort_values(["match_date", "kick_off", "match_id"])
    rows: list[dict[str, Any]] = []
    for match in ordered.itertuples(index=False):
        for team in (match.home_team, match.away_team):
            opponent = match.away_team if team == match.home_team else match.home_team
            group = corner_dates[
                corner_dates["match_id"].eq(match.match_id) & corner_dates["team"].eq(team)
            ]
            evaluable = group[group["valid_sequence"].fillna(False)]
            rows.append(
                {
                    "match_id": int(match.match_id),
                    "match_date": match.match_date,
                    "kick_off": match.kick_off,
                    "team": team,
                    "opponent": opponent,
                    "is_home": int(team == match.home_team),
                    "n_corners": len(group),
                    "n_evaluable": len(evaluable),
                    "n_with_shot": int(evaluable["shot_within_15s"].sum()),
                    "xg_sum": float(evaluable["xg_sequence"].fillna(0).sum()),
                    "n_short": int(group["short_proxy"].sum()),
                    "n_high": int(group["is_high"].sum()),
                    "n_losing": int(group["game_state"].eq("losing").sum()),
                }
            )
    return pd.DataFrame(rows)


def select_prior_matches(
    team_matches: pd.DataFrame,
    team: str,
    cutoff: str | pd.Timestamp,
    *,
    n_matches: int = HISTORY_MATCHES,
) -> pd.DataFrame:
    """Select the latest N team-matches strictly before a target date."""
    dated = team_matches.copy()
    dated["match_date"] = _dates(dated)
    cutoff_date = pd.Timestamp(cutoff).normalize()
    return (
        dated[dated["team"].eq(team) & dated["match_date"].lt(cutoff_date)]
        .sort_values(["match_date", "kick_off", "match_id"])
        .tail(n_matches)
        .copy()
    )


def select_team_and_opponent_history(
    team_matches: pd.DataFrame,
    team: str,
    opponent: str,
    cutoff: str | pd.Timestamp,
    *,
    n_matches: int = HISTORY_MATCHES,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return independent strict windows for the target team and its rival."""
    return (
        select_prior_matches(team_matches, team, cutoff, n_matches=n_matches),
        select_prior_matches(team_matches, opponent, cutoff, n_matches=n_matches),
    )


def historical_features_for_match(
    row: Mapping[str, Any] | pd.Series,
    team_matches: pd.DataFrame,
    corners: pd.DataFrame,
    *,
    n_matches: int = HISTORY_MATCHES,
    smoothing_strength: float = SMOOTHING_STRENGTH,
) -> dict[str, Any]:
    """Calculate traceable pre-match features for one team-match."""
    values = row.to_dict() if isinstance(row, pd.Series) else dict(row)
    cutoff = pd.Timestamp(values["match_date"]).normalize()
    history, opponent_history = select_team_and_opponent_history(
        team_matches,
        str(values["team"]),
        str(values["opponent"]),
        cutoff,
        n_matches=n_matches,
    )
    result: dict[str, Any] = {
        "match_id": int(values["match_id"]),
        "match_date": cutoff,
        "team": values["team"],
        "opponent": values["opponent"],
        "is_home": int(values["is_home"]),
        "history_n_matches": len(history),
        "opp_history_n_matches": len(opponent_history),
        "history_match_ids": json.dumps(history["match_id"].astype(int).tolist()),
        "opp_history_match_ids": json.dumps(opponent_history["match_id"].astype(int).tolist()),
        "history_max_date": history["match_date"].max() if len(history) else pd.NaT,
        "opp_history_max_date": (
            opponent_history["match_date"].max() if len(opponent_history) else pd.NaT
        ),
        "history_ready": len(history) == n_matches,
        "pre_match_ready": len(history) == n_matches and len(opponent_history) == n_matches,
    }
    if not result["pre_match_ready"]:
        return result

    source = corners.copy()
    source["match_date"] = _dates(source)
    history_ids = set(history["match_id"].astype(int))
    team_corners = source[
        source["match_id"].isin(history_ids) & source["team"].eq(values["team"])
    ]
    team_evaluable = team_corners[team_corners["valid_sequence"].fillna(False)]
    league_prior = source[
        source["match_date"].lt(cutoff) & source["valid_sequence"].fillna(False)
    ]
    league_rate = _ratio(league_prior["shot_within_15s"].sum(), len(league_prior))

    opponent_ids = set(opponent_history["match_id"].astype(int))
    conceded = source[
        source["match_id"].isin(opponent_ids) & ~source["team"].eq(values["opponent"])
    ]
    conceded_evaluable = conceded[conceded["valid_sequence"].fillna(False)]
    taker_counts = team_corners["player"].value_counts()
    zoned = team_corners[team_corners["delivery_zone"].notna()]
    zone_counts = zoned["delivery_zone"].value_counts()
    team_shots = float(team_evaluable["shot_within_15s"].sum())
    conceded_shots = float(conceded_evaluable["shot_within_15s"].sum())

    result.update(
        {
            "hist_corners_per_match": len(team_corners) / n_matches,
            "hist_scr15_raw": _ratio(team_shots, len(team_evaluable)),
            "hist_scr15_smoothed": (
                team_shots + smoothing_strength * league_rate
            )
            / (len(team_evaluable) + smoothing_strength),
            "hist_xg_per_corner": _ratio(
                team_evaluable["xg_sequence"].fillna(0).sum(), len(team_evaluable)
            ),
            "hist_short_share": _ratio(team_corners["short_proxy"].sum(), len(team_corners)),
            "hist_high_share": _ratio(team_corners["is_high"].sum(), len(team_corners)),
            "hist_top_taker_share": _ratio(
                taker_counts.max() if len(taker_counts) else 0, len(team_corners)
            ),
            "hist_dominant_zone_share": _ratio(
                zone_counts.max() if len(zone_counts) else 0, len(zoned)
            ),
            "hist_score_losing_share": _ratio(
                team_corners["game_state"].eq("losing").sum(), len(team_corners)
            ),
            "opp_hist_scr15_conceded_raw": _ratio(
                conceded_shots, len(conceded_evaluable)
            ),
            "opp_hist_scr15_conceded_smoothed": (
                conceded_shots + smoothing_strength * league_rate
            )
            / (len(conceded_evaluable) + smoothing_strength),
            "league_prior_scr15": league_rate,
        }
    )
    return result


def build_pre_match_features(
    team_matches: pd.DataFrame,
    corners: pd.DataFrame,
    *,
    n_matches: int = HISTORY_MATCHES,
    smoothing_strength: float = SMOOTHING_STRENGTH,
) -> pd.DataFrame:
    """Materialize historical features for every team-match."""
    return pd.DataFrame(
        historical_features_for_match(
            row,
            team_matches,
            corners,
            n_matches=n_matches,
            smoothing_strength=smoothing_strength,
        )
        for _, row in team_matches.iterrows()
    )


def build_objective_tables(
    corners: pd.DataFrame, team_matches: pd.DataFrame, pre_match: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    """Build the five canonical objective tables without fitting models."""
    merged = corners.merge(
        pre_match,
        on=["match_id", "match_date", "team", "opponent"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_history"),
    )
    trace = ["event_id", "match_id", "match_date", "team", "opponent", "pre_match_ready"]
    model_predictors = CORE_FEATURES + SCENARIO_FEATURES
    pre_columns = [
        "event_id",
        "match_id",
        "match_date",
        "team",
        "opponent",
        "shot_within_15s",
        "history_match_ids",
        "opp_history_match_ids",
        "history_max_date",
        "opp_history_max_date",
        "history_n_matches",
        "opp_history_n_matches",
        "pre_match_ready",
        *CORE_FEATURES,
    ]
    scr = merged[merged["valid_sequence"].fillna(False) & merged["pre_match_ready"].fillna(False)]
    scr_pre = scr[pre_columns].copy()
    scr_pre["shot_within_15s"] = scr_pre["shot_within_15s"].astype(int)
    scr_scenario = scr[pre_columns + SCENARIO_FEATURES].copy()
    scr_scenario["shot_within_15s"] = scr_scenario["shot_within_15s"].astype(int)

    short = merged.loc[merged["valid_geometry"], trace + model_predictors + ["short_proxy"]].copy()
    short["short_proxy"] = short["short_proxy"].astype(int)
    zone = merged.loc[
        merged["direct_delivery_valid"], trace + model_predictors + ["delivery_zone"]
    ].copy()
    count = team_matches.merge(
        pre_match,
        on=["match_id", "match_date", "team", "opponent", "is_home"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_history"),
    )
    count["exposure_matches"] = 1
    count_columns = [
        "match_id",
        "match_date",
        "team",
        "opponent",
        "pre_match_ready",
        "history_match_ids",
        "opp_history_match_ids",
        "n_corners",
        "exposure_matches",
        *CORE_FEATURES,
    ]
    return {
        "model_scr15_pre_match": scr_pre,
        "model_scr15_scenario": scr_scenario,
        "model_short_direct": short,
        "model_delivery_zone": zone,
        "model_corner_count": count[count_columns].copy(),
    }
