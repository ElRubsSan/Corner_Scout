import json

import numpy as np
import pandas as pd

from analytics.features import (
    build_pre_match_features,
    build_team_match_observed,
    engineer_corner_geometry,
    select_team_and_opponent_history,
)


def _season() -> tuple[pd.DataFrame, pd.DataFrame]:
    matches = pd.DataFrame(
        {
            "match_id": range(1, 11),
            "match_date": pd.date_range("2015-01-01", periods=10),
            "kick_off": ["12:00:00"] * 10,
            "home_team": ["A"] * 10,
            "away_team": ["B"] * 10,
        }
    )
    rows = []
    for match in matches.itertuples(index=False):
        for index, team in enumerate(("A", "B")):
            rows.append(
                {
                    "event_id": f"{match.match_id}-{team}",
                    "match_id": match.match_id,
                    "match_date": match.match_date,
                    "team": team,
                    "opponent": "B" if team == "A" else "A",
                    "x": 120.0,
                    "y": 0.0 if index == 0 else 80.0,
                    "end_x": 110.0,
                    "end_y": 10.0 if index == 0 else 70.0,
                    "height": "Ground Pass" if match.match_id % 2 else "High Pass",
                    "valid_sequence": True,
                    "shot_within_15s": match.match_id % 2,
                    "xg_sequence": 0.1,
                    "player": f"P-{team}",
                    "game_state": "drawing",
                }
            )
    return matches, engineer_corner_geometry(pd.DataFrame(rows))


def test_geometry_proxy_and_relative_zones() -> None:
    corners = pd.DataFrame(
        [
            {"x": 120, "y": 0, "end_x": 110, "end_y": 5, "height": "Ground Pass"},
            {"x": 120, "y": 80, "end_x": 108, "end_y": 40, "height": "High Pass"},
            {"x": 117, "y": 0, "end_x": 110, "end_y": 40, "height": "High Pass"},
        ]
    )
    result = engineer_corner_geometry(corners)

    assert result.loc[0, "short_proxy"]
    assert pd.isna(result.loc[0, "delivery_zone"])
    assert result.loc[1, "end_y_relative"] == 40
    assert result.loc[1, "delivery_zone"] == "franja_central"
    assert not result.loc[2, "valid_geometry"]
    assert result.loc[2, "execution_type"] == "unknown"


def test_team_match_unit_and_strict_eight_match_histories() -> None:
    matches, corners = _season()
    observed = build_team_match_observed(matches, corners)
    team, rival = select_team_and_opponent_history(observed, "A", "B", "2015-01-09")

    assert len(observed) == 20
    assert observed.groupby("match_id").size().eq(2).all()
    assert team.match_id.tolist() == list(range(1, 9))
    assert rival.match_id.tolist() == list(range(1, 9))
    assert team.match_date.max() < pd.Timestamp("2015-01-09")


def test_historical_features_are_traceable_and_ignore_target() -> None:
    matches, corners = _season()
    observed = build_team_match_observed(matches, corners)
    result = build_pre_match_features(observed, corners)
    target = result[(result.match_id == 9) & (result.team == "A")].iloc[0]

    assert target.pre_match_ready
    assert json.loads(target.history_match_ids) == list(range(1, 9))
    assert target.history_max_date < target.match_date
    assert np.isclose(target.hist_corners_per_match, 1.0)

    changed = corners.copy()
    changed.loc[changed.match_date >= target.match_date, "shot_within_15s"] = 1
    rebuilt = build_pre_match_features(observed, changed)
    changed_target = rebuilt[(rebuilt.match_id == 9) & (rebuilt.team == "A")].iloc[0]
    for column in [
        "hist_scr15_raw",
        "hist_scr15_smoothed",
        "hist_xg_per_corner",
        "opp_hist_scr15_conceded_smoothed",
        "league_prior_scr15",
    ]:
        assert np.isclose(target[column], changed_target[column])


def test_team_match_unit_keeps_zero_corner_rows() -> None:
    matches, corners = _season()
    corners = corners[~((corners.match_id == 10) & corners.team.eq("A"))]
    observed = build_team_match_observed(matches, corners)
    row = observed[(observed.match_id == 10) & observed.team.eq("A")].iloc[0]

    assert row.n_corners == 0
    assert row.n_evaluable == 0
