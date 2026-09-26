import hashlib
import json
import os
from pathlib import Path
import shutil

import pandas as pd
import pytest

from analytics.contracts import contract_payload
from analytics.ingestion import sha256_file
from analytics.io import load_contract, publish_contract
from analytics.pipeline import build, train


PROJECT_DATA = Path(__file__).resolve().parents[1] / "data"


def _link_or_copy(source: str, destination: str) -> str:
    try:
        os.link(source, destination)
        return destination
    except OSError:
        return shutil.copy2(source, destination)


def _prepare_root(root: Path) -> dict[str, str]:
    shutil.copytree(PROJECT_DATA / "raw", root / "raw", copy_function=_link_or_copy)
    (root / "manual_labels").mkdir(parents=True)
    shutil.copy2(
        PROJECT_DATA / "manual_labels" / "short_corner_review.csv",
        root / "manual_labels" / "short_corner_review.csv",
    )
    raw_files = {
        path.relative_to(root / "raw").as_posix(): sha256_file(path)
        for path in sorted((root / "raw").rglob("*")) if path.is_file()
    }
    fingerprint = hashlib.sha256(
        json.dumps(raw_files, sort_keys=True).encode("utf-8")
    ).hexdigest()
    contract = contract_payload(
        stage="01_ingestion", contract_version="01-ingestion-v1", run_id="full-regression",
        exports=[], raw_files=raw_files, raw_manifest_sha256=fingerprint,
        counts={"matches": 380, "event_files": 380},
    )
    publish_contract(root / "interim" / "01_ingestion", contract)
    return raw_files


@pytest.mark.skipif(
    os.environ.get("CORNERSCOUT_RUN_FULL_PIPELINE") != "1",
    reason="set CORNERSCOUT_RUN_FULL_PIPELINE=1 for raw-to-05 local regression",
)
def test_canonical_full_pipeline_from_raw(tmp_path: Path) -> None:
    if not (PROJECT_DATA / "raw" / "matches_laliga_2015_16.csv").is_file():
        pytest.skip("canonical raw data is unavailable")
    root = tmp_path / "data"
    raw_before = _prepare_root(root)

    build_result = build(root)
    train_result = train(root)

    contract02 = load_contract(
        root / "interim/02_clean/contract.json",
        expected_stage="02_clean", expected_version="02-clean-v2",
    )
    contract03 = load_contract(
        root / "interim/03_scr15/contract.json",
        expected_stage="03_scr15", expected_version="03-scr15-v2",
    )
    contract04 = load_contract(
        root / "processed/04_features/contract.json",
        expected_stage="04_features", expected_version="04-features-v2",
    )
    contract05 = load_contract(
        root / "processed/05_modeling/contract.json",
        expected_stage="05_modeling", expected_version="05-modeling-v3-objectives",
    )

    assert build_result["completed"] == "04_features"
    assert train_result["final_used_for_decisions"] is False
    assert contract02.counts == {
        "matches": 380, "events": 1_295_354, "corners_detected": 3_841,
        "clock_regressions": 126, "own_goals": 29, "substitutions": 2_190,
        "dismissal_records": 109, "on_pitch_dismissals": 106,
        "off_pitch_dismissals": 3,
    }
    assert contract03.counts == {
        "matches": 380, "events": 1_295_354, "corners": 3_841,
        "evaluable": 3_835, "excluded": 6, "with_shot": 1_245,
        "shared_shots": 0, "new_corner_closures": 29, "restarts_audited": 105,
    }
    assert contract04.counts == {
        "matches": 380, "corners": 3_841, "evaluable": 3_835, "excluded": 6,
        "team_matches": 760, "pre_match_ready": 600, "training_rows": 3_039,
        "training_positive": 976, "manual_labels": 40, "cluster_rows": 1_493,
        "valid_geometry": 3_838, "direct_deliveries": 3_374,
        "zero_corner_team_matches": 17,
    }
    assert len([item for item in contract02.all_artifacts if item.file.startswith("events/")]) == 380
    assert {
        "matches_clean.parquet", "data_quality.parquet", "match_state_quality.parquet",
        "own_goal_audit.parquet", "dismissal_audit.parquet",
        "substitution_audit.parquet", "source_manifest.csv",
    }.issubset({item.file for item in contract02.all_artifacts})
    assert {
        "corners_scr15.parquet", "scr15_quality_report.parquet", "restart_audit.parquet",
        "shared_shots_audit.parquet", "scr15_reconciliation.parquet",
        "excluded_sequences.parquet", "input_manifest.csv",
    } == {item.file for item in contract03.all_artifacts}
    expected04 = {
        "corners_engineered.parquet", "team_match_observed.parquet",
        "pre_match_features.parquet", "training_candidates_pre_match.parquet",
        "training_candidates_scenario.parquet", "short_manual_review.parquet",
        "short_label_metrics.parquet", "short_threshold_sensitivity.parquet",
        "short_near_threshold.parquet", "feature_dictionary.parquet",
        "decision_log.parquet", "history_perturbation_audit.parquet",
        "cluster_assignments.parquet", "cluster_centers.parquet",
        "cluster_sensitivity.parquet", "cluster_zone_cross.parquet",
        "design_scope_audit.parquet", "model_scr15_pre_match.parquet",
        "model_scr15_scenario.parquet", "model_short_direct.parquet",
        "model_delivery_zone.parquet", "model_corner_count.parquet",
        "modeling_table_contract.parquet", "short_label_audit.json",
    }
    assert expected04 == {item.file for item in contract04.all_artifacts}
    assert contract03.source_run_id == contract02.run_id
    assert contract04.source_run_id == contract03.run_id
    assert contract04.source_corners_sha256 == contract03.require_artifact(
        "corners_scr15.parquet"
    ).sha256

    clusters = pd.read_parquet(root / "processed/04_features/cluster_assignments.parquet")
    assert len(clusters) == 1_493
    assert pd.to_datetime(clusters.match_date).max() < pd.Timestamp("2016-01-01")
    tuning = pd.read_parquet(root / "processed/05_modeling/tuning_development.parquet")
    smoothing = tuning[tuning.parameter.eq("smoothing_alpha")]
    assert set(smoothing.objective) == {"scr15", "short_direct", "corner_count"}
    assert set(smoothing.value) == {2.0, 5.0, 10.0, 20.0}
    assert contract05.gates["corner_count"]["maximum_conditional_dispersion"] == 1.5
    assert contract05.gates["corner_count"]["evaluated_before"] == contract05.windows[0]["start"]
    assert contract05.final_period["used_for_decisions"] is False

    raw_after = {
        path.relative_to(root / "raw").as_posix(): sha256_file(path)
        for path in sorted((root / "raw").rglob("*")) if path.is_file()
    }
    assert raw_after == raw_before
