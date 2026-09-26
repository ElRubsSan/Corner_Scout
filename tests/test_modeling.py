import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analytics.modeling import (
    binary_metrics,
    count_dispersion_gate,
    count_metrics,
    delivery_zone_gate,
    descriptive_kmeans,
    choose_binary_winner,
    HistoricalCountModel,
    HistoricalProbabilityModel,
    multiclass_metrics,
    run_canonical_modeling,
    tune_binary_smoothing,
    tune_count_smoothing,
)


def test_descriptive_kmeans_uses_only_predevelopment_deliveries() -> None:
    points = [(104, 25), (105, 26), (116, 52), (117, 53)] * 3
    rows = [
        {
            "event_id": f"e{i}",
            "match_id": i,
            "match_date": "2015-12-01",
            "team": "A",
            "direct_delivery_valid": True,
            "end_x": x,
            "end_y_relative": y,
        }
        for i, (x, y) in enumerate(points)
    ]
    rows.append(
        {
            "event_id": "future",
            "match_id": 99,
            "match_date": "2016-01-01",
            "team": "A",
            "direct_delivery_valid": True,
            "end_x": 0,
            "end_y_relative": 0,
        }
    )
    result = descriptive_kmeans(
        pd.DataFrame(rows), "2016-01-01", n_clusters=2, k_values=range(2, 4)
    )

    assert "future" not in set(result.assignments.event_id)
    assert result.assignments.match_date.max() < "2016-01-01"
    assert len(result.centers) == 2
    assert result.centers.geometric_name.is_unique


def _zone_gate_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    corners = []
    features = []
    for i, zone in enumerate(["a", "b", "a", "b"], start=1):
        history_id = 100 + i
        target_id = 200 + i
        corners.extend(
            [
                {
                    "event_id": f"h{i}", "match_id": history_id,
                    "match_date": "2015-12-01", "team": f"T{i}",
                    "delivery_zone": zone, "direct_delivery_valid": True,
                    "pre_match_ready": True,
                },
                {
                    "event_id": f"t{i}", "match_id": target_id,
                    "match_date": f"2015-12-{10+i:02d}", "team": f"T{i}",
                    "delivery_zone": zone, "direct_delivery_valid": True,
                    "pre_match_ready": True,
                },
            ]
        )
        features.append(
            {
                "match_id": target_id,
                "match_date": f"2015-12-{10+i:02d}",
                "team": f"T{i}",
                "pre_match_ready": True,
                "history_match_ids": json.dumps([history_id]),
            }
        )
    corners.append(
        {
            "event_id": "future", "match_id": 999, "match_date": "2016-01-01",
            "team": "Future", "delivery_zone": "future_only",
            "direct_delivery_valid": True, "pre_match_ready": True,
        }
    )
    corners.append(
        {
            "event_id": "not-ready", "match_id": 998, "match_date": "2015-12-20",
            "team": "NotReady", "delivery_zone": "not_ready_only",
            "direct_delivery_valid": True, "pre_match_ready": False,
        }
    )
    features.append(
        {
            "match_id": 999, "match_date": "2016-01-01", "team": "Future",
            "pre_match_ready": True, "history_match_ids": "[]",
        }
    )
    corner_frame = pd.DataFrame(corners)
    return corner_frame.copy(), pd.DataFrame(features), corner_frame


def test_delivery_zone_gate_is_entirely_prefinal() -> None:
    zone_data, features, corners = _zone_gate_inputs()
    baseline = delivery_zone_gate(
        zone_data, features, corners, "2016-01-01", minimum_total=1, minimum_teams=1
    )
    leaked = pd.concat(
        [
            zone_data,
            pd.DataFrame(
                {
                    "event_id": [f"leak-{i}" for i in range(50)],
                    "match_id": range(1000, 1050),
                    "match_date": ["2016-02-01"] * 50,
                    "team": [f"L{i}" for i in range(50)],
                    "delivery_zone": ["leaked_class"] * 50,
                    "direct_delivery_valid": [True] * 50,
                    "pre_match_ready": [True] * 50,
                }
            ),
        ],
        ignore_index=True,
    )
    after = delivery_zone_gate(
        leaked, features, leaked, "2016-01-01", minimum_total=1, minimum_teams=1
    )

    assert baseline.classes == ("a", "b") == after.classes
    pd.testing.assert_frame_equal(baseline.support, after.support)
    pd.testing.assert_frame_equal(baseline.persistence_rows, after.persistence_rows)
    assert baseline.persistence == after.persistence == 1.0
    assert baseline.chance == after.chance == 0.5
    assert baseline.passed is after.passed is True
    assert (after.persistence_rows.match_date < after.final_start).all()


def test_historical_smoothing_is_tuned_on_inner_time_only() -> None:
    frame = pd.DataFrame(
        {
            "match_date": pd.date_range("2015-01-01", periods=20),
            "target": [0, 1] * 10,
            "raw": [0.25, 0.75] * 10,
            "history_exposure": [8] * 20,
            "n_corners": [2, 6] * 10,
            "hist_corners_per_match": [3.0, 5.0] * 10,
        }
    )
    binary_alpha, binary_grid = tune_binary_smoothing(
        frame, target="target", raw_feature="raw"
    )
    count_alpha, count_grid = tune_count_smoothing(frame)

    assert set(binary_grid.value) == {2.0, 5.0, 10.0, 20.0}
    assert set(count_grid.value) == {2.0, 5.0, 10.0, 20.0}
    assert binary_alpha in set(binary_grid.value)
    assert count_alpha in set(count_grid.value)
    assert binary_grid.parameter.eq("smoothing_alpha").all()
    assert count_grid.parameter.eq("smoothing_alpha").all()


def test_objective_metrics_return_canonical_scores() -> None:
    binary = binary_metrics(np.array([0, 1]), np.array([0.1, 0.9]))
    multiclass = multiclass_metrics(
        np.array(["a", "b"]), np.array([[0.8, 0.2], [0.1, 0.9]]), ("a", "b")
    )
    count = count_metrics(np.array([1, 3]), np.array([1.0, 2.5]))

    assert binary["brier"] < 0.02
    assert multiclass["multiclass_brier"] < 0.1
    assert count["mae"] == 0.25


def test_count_dispersion_gate_fits_only_before_development() -> None:
    frame = pd.DataFrame(
        {
            "match_date": pd.date_range("2015-01-01", periods=21),
            "n_corners": [2, 3, 4] * 7,
            "hist_corners_per_match": [3.0] * 21,
        }
    )
    baseline = count_dispersion_gate(frame, "2015-01-20", ["hist_corners_per_match"])
    frame.loc[frame.match_date >= "2015-01-20", "n_corners"] = 1000
    changed = count_dispersion_gate(frame, "2015-01-20", ["hist_corners_per_match"])

    assert baseline == changed


def test_historical_references_remain_functional_estimators() -> None:
    frame = pd.DataFrame(
        {"hist_scr15_raw": [0.2, 0.8], "history_exposure": [8, 8],
         "hist_corners_per_match": [3.0, 7.0]}
    )
    binary = HistoricalProbabilityModel("hist_scr15_raw", alpha=2).fit(
        frame, pd.Series([0, 1])
    )
    count = HistoricalCountModel(alpha=2).fit(frame, pd.Series([4, 6]))

    assert np.allclose(binary.predict_proba(frame)[:, 1], [0.26, 0.74])
    assert np.allclose(count.predict(frame), [3.4, 6.6])


def test_final_metrics_never_change_binary_selection() -> None:
    rows = []
    for index in range(1, 4):
        for model, brier, loss, ap in [
            ("league_reference", 0.20, 0.60, 0.40),
            ("historical_baseline", 0.21, 0.61, 0.41),
            ("candidate", 0.30, 0.80, 0.30),
        ]:
            rows.append(
                {"objective": "scr15", "window": f"development_{index}",
                 "role": "selection", "model": model, "brier": brier,
                 "log_loss": loss, "average_precision": ap, "calibration_gap": 0.01}
            )
    for model, brier, loss, ap in [
        ("league_reference", 0.40, 1.0, 0.2),
        ("historical_baseline", 0.39, 0.9, 0.2),
        ("candidate", 0.01, 0.1, 0.9),
    ]:
        rows.append(
            {"objective": "scr15", "window": "final", "role": "confirmation_only",
             "model": model, "brier": brier, "log_loss": loss,
             "average_precision": ap, "calibration_gap": 0.0}
        )

    winner, checks = choose_binary_winner(pd.DataFrame(rows), "scr15")

    assert winner == "league_reference"
    assert len(checks) == 3


@pytest.mark.skipif(
    os.environ.get("CORNERSCOUT_RUN_LOCAL_MODELING") != "1",
    reason="set CORNERSCOUT_RUN_LOCAL_MODELING=1 for local stage-04 integration",
)
def test_local_stage04_modeling_integration() -> None:
    root = Path(os.environ.get("CORNERSCOUT_DATA_DIR", "data"))
    source = root / "processed" / "04_features"
    required = [
        "model_scr15_scenario", "model_short_direct", "model_delivery_zone",
        "model_corner_count", "team_match_observed", "pre_match_features",
        "corners_engineered",
    ]
    if not all((source / f"{name}.parquet").is_file() for name in required):
        pytest.skip("local canonical stage 04 is unavailable")
    result = run_canonical_modeling(
        {name: pd.read_parquet(source / f"{name}.parquet") for name in required},
        bootstrap_iterations=2,
    )
    assert len(result.tables["temporal_metrics"]) == 36
    assert len(result.tables["tuning_development"]) == 96
    assert result.final.role == "confirmation_only"
    assert not result.zone_gate.passed
