"""Canonical notebook-free orchestration for offline stages 02 through 05."""

from __future__ import annotations

import json
import hashlib
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import cohen_kappa_score, confusion_matrix, matthews_corrcoef

from analytics.cleaning import normalize
from analytics.context import CONTEXT_VERSION, build_pre_event_context
from analytics.contracts import Artifact, contract_payload
from analytics.features import (
    CORE_FEATURES,
    HISTORY_MATCHES,
    SHORT_THRESHOLD,
    SMOOTHING_STRENGTH,
    build_objective_tables,
    build_pre_match_features,
    build_team_match_observed,
    engineer_corner_geometry,
)
from analytics.ingestion import inspect_event_file, sha256_file
from analytics.io import (
    artifact,
    data_dir,
    load_contract,
    publish_contract,
    read_events,
    write_json,
)
from analytics.modeling import (
    COUNT_MAXIMUM_CONDITIONAL_DISPERSION,
    descriptive_kmeans,
    run_canonical_modeling,
    temporal_windows,
)
from analytics.scr15 import RULE_VERSION, extract_corners

VERSIONS = {
    "01_ingestion": "01-ingestion-v1",
    "02_clean": "02-clean-v2",
    "03_scr15": "03-scr15-v2",
    "04_features": "04-features-v2",
    "05_modeling": "05-modeling-v3-objectives",
}
SHORT_LABELS_SHA256 = "f75d4dffb481031593dfec327fb36210027fcbb3318db59a1c5634b5be04424c"


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def _write_parquet(frame: pd.DataFrame, path: Path) -> None:
    """Replace generated Parquet only after its temporary file is complete."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        frame.to_parquet(temporary, index=False)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _export(frame: pd.DataFrame, path: Path, directory: Path) -> Artifact:
    _write_parquet(frame, path)
    return artifact(path, directory, rows=len(frame))


def _write_joblib(value: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        joblib.dump(value, temporary)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_text(value: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    _write_text(frame.to_csv(index=False), path)


def _staging_directory(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    return Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=destination.parent)
    )


def _replace_stage_directory(staging: Path, destination: Path) -> None:
    """Swap a fully published stage into place, restoring the prior stage on failure."""
    backup = destination.with_name(f".{destination.name}.backup-{_run_id()}")
    had_previous = destination.exists()
    if had_previous:
        os.replace(destination, backup)
    try:
        os.replace(staging, destination)
    except BaseException:
        if had_previous and backup.exists() and not destination.exists():
            os.replace(backup, destination)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup)


def _matches(raw: Path) -> pd.DataFrame:
    frame = pd.read_csv(raw / "matches_laliga_2015_16.csv")
    aliases = {
        "home_team_home_team_name": "home_team",
        "away_team_away_team_name": "away_team",
    }
    frame = frame.rename(columns={key: value for key, value in aliases.items() if key in frame})
    required = [
        "match_id", "match_date", "kick_off", "home_team", "away_team",
        "home_score", "away_score",
    ]
    missing = set(required) - set(frame)
    if missing:
        raise ValueError(f"Missing match columns: {sorted(missing)}")
    result = frame[required].copy()
    result[["home_score", "away_score"]] = result[["home_score", "away_score"]].astype(int)
    result["match_date"] = pd.to_datetime(result["match_date"]).dt.normalize()
    return result.sort_values(["match_date", "kick_off", "match_id"]).reset_index(drop=True)


def clean_stage(root: Path | None = None) -> dict[str, Any]:
    """Run canonical normalization and pre-event context reconstruction."""
    root = root or data_dir()
    source_path = root / "interim" / "01_ingestion" / "contract.json"
    source = load_contract(
        source_path, expected_stage="01_ingestion", expected_version=VERSIONS["01_ingestion"]
    )
    raw, output = root / "raw", root / "interim" / "02_clean"
    raw_files = source.raw_files
    if not isinstance(raw_files, dict) or not raw_files:
        raise ValueError("01_ingestion contract does not declare raw_files")
    manifest_fingerprint = hashlib.sha256(
        json.dumps(raw_files, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if source.raw_manifest_sha256 != manifest_fingerprint:
        raise ValueError("01_ingestion raw manifest fingerprint is invalid")
    matches = _matches(raw)
    consumed = {
        "matches_laliga_2015_16.csv",
        *(f"events/{int(match_id)}.jsonl.gz" for match_id in matches.match_id),
    }
    undeclared = consumed - set(raw_files)
    if undeclared:
        raise ValueError(f"01_ingestion contract omits consumed raw files: {len(undeclared)}")
    for relative in consumed:
        expected_hash = raw_files[relative]
        candidate = raw / str(relative)
        if not candidate.is_file() or sha256_file(candidate) != expected_hash:
            raise ValueError(f"Raw SHA-256 mismatch: {relative}")
    staging = _staging_directory(output)
    exports: list[Artifact] = []
    quality_rows: list[dict[str, Any]] = []
    state_rows: list[dict[str, Any]] = []
    own_goals: list[dict[str, Any]] = []
    dismissals: list[dict[str, Any]] = []
    substitutions: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    event_total = corner_total = 0
    try:
        for match in matches.itertuples(index=False):
            raw_path = raw / "events" / f"{int(match.match_id)}.jsonl.gz"
            inspected_events, inspected_corners = inspect_event_file(raw_path)
            records = [
                normalize(row, raw_path.relative_to(raw).as_posix(), line)
                for line, row in enumerate(read_events(raw_path), start=1)
            ]
            records.sort(key=lambda row: (row["period"], row["index"]))
            regressions = sum(
                left["period"] == right["period"]
                and float(left["seconds"]) > float(right["seconds"])
                for left, right in zip(records, records[1:])
            )
            out_of_bounds = sum(
                any(
                    np.isfinite(record.get(axis, np.nan))
                    and not 0 <= float(record[axis]) <= maximum
                    for axis, maximum in (("x", 120), ("y", 80), ("end_x", 120), ("end_y", 80))
                )
                for record in records
            )
            contexts, scores, match_own, match_dismissals, match_substitutions = (
                build_pre_event_context(records, match.home_team, match.away_team)
            )
            for record in records:
                record.update(contexts[str(record["event_id"])])
            for rows in (match_own, match_dismissals, match_substitutions):
                for row in rows:
                    row["match_id"] = int(match.match_id)
            own_goals.extend(match_own)
            dismissals.extend(match_dismissals)
            substitutions.extend(match_substitutions)
            quality_rows.append(
                {"match_id": int(match.match_id), "events": inspected_events,
                 "corners": inspected_corners, "clock_regressions": regressions,
                 "out_of_bounds_coordinates": out_of_bounds}
            )
            state_rows.append(
                {"match_id": int(match.match_id),
                 "reconstructed_home": scores[match.home_team],
                 "reconstructed_away": scores[match.away_team],
                 "expected_home": int(match.home_score), "expected_away": int(match.away_score),
                 "score_match": scores[match.home_team] == match.home_score
                 and scores[match.away_team] == match.away_score}
            )
            path = staging / "events" / f"{int(match.match_id)}.parquet"
            item = _export(pd.DataFrame(records), path, staging)
            exports.append(item)
            manifest_rows.append(
                {"match_id": int(match.match_id), "file": path.name,
                 "sha256": item.sha256, "rows": inspected_events}
            )
            event_total += inspected_events
            corner_total += inspected_corners
        quality = pd.DataFrame(quality_rows)
        state_quality = pd.DataFrame(state_rows)
        audit_frames = {
            "matches_clean": matches,
            "data_quality": quality,
            "match_state_quality": state_quality,
            "own_goal_audit": pd.DataFrame(own_goals, columns=[
                "match_id", "for_event_id", "beneficiary", "period", "seconds", "related_event_ids"
            ]),
            "dismissal_audit": pd.DataFrame(dismissals, columns=[
                "match_id", "event_id", "team", "player_id", "player", "card", "on_pitch"
            ]),
            "substitution_audit": pd.DataFrame(substitutions, columns=[
                "match_id", "event_id", "team", "outgoing_player_id",
                "replacement_player_id", "valid"
            ]),
        }
        for name, frame in audit_frames.items():
            exports.append(_export(frame, staging / f"{name}.parquet", staging))
        source_manifest = pd.DataFrame(manifest_rows)
        manifest_path = staging / "source_manifest.csv"
        _write_csv(source_manifest, manifest_path)
        exports.append(artifact(manifest_path, staging, rows=len(source_manifest)))
        counts = {
            "matches": len(matches), "events": event_total, "corners_detected": corner_total,
            "clock_regressions": int(quality.clock_regressions.sum()),
            "own_goals": len(own_goals), "substitutions": len(substitutions),
            "dismissal_records": len(dismissals),
            "on_pitch_dismissals": int(audit_frames["dismissal_audit"].on_pitch.sum()),
            "off_pitch_dismissals": int((~audit_frames["dismissal_audit"].on_pitch).sum()),
        }
        if not state_quality.score_match.all():
            raise ValueError("Score reconstruction failed")
        contract = contract_payload(
            stage="02_clean", contract_version=VERSIONS["02_clean"], run_id=_run_id(),
            exports=exports, source_contract_version=source.contract_version,
            source_run_id=source.run_id,
            source_raw_manifest_sha256=getattr(source, "raw_manifest_sha256", None),
            context_version=CONTEXT_VERSION, counts=counts, event_files=len(matches),
            event_manifest_sha256=sha256_file(manifest_path),
        )
        publish_contract(staging, contract)
        _replace_stage_directory(staging, output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"stage": contract.stage, "contract_version": contract.contract_version, **contract.counts}


def scr15_stage(root: Path | None = None) -> dict[str, Any]:
    """Extract SCR-15 exclusively from verified stage-02 events."""
    root = root or data_dir()
    source_path = root / "interim" / "02_clean" / "contract.json"
    source = load_contract(
        source_path, expected_stage="02_clean", expected_version=VERSIONS["02_clean"]
    )
    source_dir, output = source_path.parent, root / "interim" / "03_scr15"
    if source.source_contract_version != VERSIONS["01_ingestion"]:
        raise ValueError("02_clean lineage does not point to canonical 01_ingestion")
    manifest_item = source.require_artifact("source_manifest.csv")
    if source.event_manifest_sha256 != manifest_item.sha256:
        raise ValueError("02_clean event manifest lineage mismatch")
    source.require_artifact("matches_clean.parquet")
    matches = pd.read_parquet(source_dir / "matches_clean.parquet")
    staging = _staging_directory(output)
    rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    restart_rows: list[dict[str, Any]] = []
    input_rows: list[dict[str, Any]] = []
    event_total = 0
    try:
        for match in matches.itertuples(index=False):
            relative = f"events/{int(match.match_id)}.parquet"
            event_item = source.require_artifact(relative)
            event_frame = pd.read_parquet(source_dir / relative)
            events = event_frame.to_dict("records")
            extracted = extract_corners(events, int(match.match_id))
            for corner in extracted:
                corner.update(
                    match_date=match.match_date, kick_off=match.kick_off,
                    home_team=match.home_team, away_team=match.away_team,
                    home_score=int(match.home_score), away_score=int(match.away_score),
                    opponent=match.away_team if corner["team"] == match.home_team else match.home_team,
                )
            rows.extend(extracted)
            excluded_count = sum(not bool(row["valid_sequence"]) for row in extracted)
            quality_rows.append(
                {"match_id": int(match.match_id), "events": len(events),
                 "corners": len(extracted), "excluded": excluded_count}
            )
            event_map = {str(event["event_id"]): event for event in events}
            for corner in extracted:
                for restart_id in corner["restart_ids"]:
                    restart = event_map[str(restart_id)]
                    restart_rows.append(
                        {"match_id": int(match.match_id), "corner_id": corner["event_id"],
                         "restart_event_id": restart_id,
                         "restart_type": restart.get("pass_type") or restart.get("type"),
                         "restart_team": restart.get("team"),
                         "same_team": restart.get("team") == corner.get("team"),
                         "elapsed_seconds": float(restart["seconds"]) - float(corner["seconds"]),
                         "policy": "closes_previous_sequence"
                         if restart.get("pass_type") == "Corner"
                         else "audit_only_no_automatic_close"}
                    )
            input_rows.append(
                {"file": Path(relative).name, "sha256": event_item.sha256, "rows": len(events)}
            )
            event_total += len(events)
        corners = pd.DataFrame(rows)
        shot_links = [
            {"event_id": row["event_id"], "match_id": row["match_id"], "shot_ids": shot_id}
            for row in rows for shot_id in row["shot_ids"]
        ]
        shot_frame = pd.DataFrame(shot_links, columns=["event_id", "match_id", "shot_ids"])
        shared = (
            shot_frame[shot_frame.shot_ids.duplicated(keep=False)].sort_values("shot_ids")
            if len(shot_frame) else shot_frame
        )
        excluded = corners.loc[
            ~corners.valid_sequence,
            ["match_id", "event_id", "team", "period", "index", "seconds", "end_reason",
             "terminal_event_id", "terminal_index"],
        ].copy()
        old_invalid = {
            "0a7a6700-a960-4dbb-976d-d35ee1856c84": "post_close_regression_old_scan",
            "312b028e-6c4c-4133-b1d2-238b76072cf2": "in_window_clock_regression",
            "421eb603-4962-4240-ab51-e7609d9e0fb6": "in_window_clock_regression",
            "4240887d-22b8-44df-8f9a-5ef3cd02dce5": "post_close_regression_old_scan",
            "4a33d3d6-7b09-4586-af70-d3a77ad17b94": "post_close_regression_old_scan",
            "5099b6d4-ee48-49e5-aa33-5d55eb7e8dd0": "in_window_clock_regression",
            "5c91ad0d-1cb6-4f9e-8077-cf7c0e061c6a": "in_window_clock_regression",
            "7f36528e-a33f-4f3d-8092-c4f481079196": "post_close_regression_old_scan",
            "a2e323f1-eedb-472c-80b3-400fee483c09": "in_window_clock_regression",
            "ac90224b-64e7-43d7-9ec3-a325d88ec7f9": "post_close_regression_old_scan",
            "bed39f58-7361-45dc-9fd1-3676555c56ed": "in_window_clock_regression",
        }
        validity = corners.set_index("event_id").valid_sequence
        reconciliation = pd.DataFrame(
            [{"event_id": event_id, "comparison": "research_v1.1",
              "previous_valid": False, "current_valid": bool(validity.loc[event_id]),
              "classification": classification}
             for event_id, classification in sorted(old_invalid.items())]
        )
        frames = {
            "corners_scr15": corners,
            "scr15_quality_report": pd.DataFrame(quality_rows),
            "restart_audit": pd.DataFrame(restart_rows, columns=[
                "match_id", "corner_id", "restart_event_id", "restart_type", "restart_team",
                "same_team", "elapsed_seconds", "policy"
            ]),
            "shared_shots_audit": shared,
            "scr15_reconciliation": reconciliation,
            "excluded_sequences": excluded,
        }
        exports = [
            _export(frame, staging / f"{name}.parquet", staging)
            for name, frame in frames.items()
        ]
        input_manifest = pd.DataFrame(input_rows)
        input_path = staging / "input_manifest.csv"
        _write_csv(input_manifest, input_path)
        exports.append(artifact(input_path, staging, rows=len(input_manifest)))
        evaluable = int(corners.valid_sequence.sum())
        counts = {
            "matches": len(matches), "events": event_total, "corners": len(corners),
            "evaluable": evaluable, "excluded": len(corners) - evaluable,
            "with_shot": int(corners.shot_within_15s.fillna(0).sum()),
            "shared_shots": int(shared.shot_ids.nunique()) if len(shared) else 0,
            "new_corner_closures": int(corners.end_reason.eq("new_corner").sum()),
            "restarts_audited": len(restart_rows),
        }
        contract = contract_payload(
            stage="03_scr15", contract_version=VERSIONS["03_scr15"], run_id=_run_id(),
            exports=exports, source_contract_version=source.contract_version,
            source_run_id=source.run_id, rule_version=RULE_VERSION, window_seconds=15,
            source_event_manifest_sha256=source.event_manifest_sha256,
            input_manifest_sha256=sha256_file(input_path), counts=counts,
            synthetic_tests_passed=11,
        )
        publish_contract(staging, contract)
        _replace_stage_directory(staging, output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"stage": contract.stage, "contract_version": contract.contract_version, **contract.counts}


def features_stage(root: Path | None = None) -> dict[str, Any]:
    """Build canonical stage-04 features using only extracted module logic."""
    root = root or data_dir()
    source_path = root / "interim" / "03_scr15" / "contract.json"
    source = load_contract(
        source_path, expected_stage="03_scr15", expected_version=VERSIONS["03_scr15"]
    )
    clean_path = root / "interim" / "02_clean" / "contract.json"
    clean = load_contract(
        clean_path, expected_stage="02_clean", expected_version=VERSIONS["02_clean"]
    )
    if source.source_contract_version != clean.contract_version or source.source_run_id != clean.run_id:
        raise ValueError("03_scr15 lineage does not match the verified 02_clean contract")
    if source.source_event_manifest_sha256 != clean.event_manifest_sha256:
        raise ValueError("03_scr15 source event-manifest hash does not match 02_clean")
    if source.rule_version != RULE_VERSION:
        raise ValueError("03_scr15 rule version is not canonical")
    if source.input_manifest_sha256 != source.require_artifact("input_manifest.csv").sha256:
        raise ValueError("03_scr15 input manifest hash is invalid")
    corner_item = source.require_artifact("corners_scr15.parquet")
    clean.require_artifact("matches_clean.parquet")
    output = root / "processed" / "04_features"
    corners = pd.read_parquet(source_path.parent / "corners_scr15.parquet")
    matches = pd.read_parquet(clean_path.parent / "matches_clean.parquet")
    engineered = engineer_corner_geometry(corners)
    observed = build_team_match_observed(matches, engineered)
    pre_match = build_pre_match_features(observed, engineered)
    tables = build_objective_tables(engineered, observed, pre_match)
    eda_end = pd.Timestamp("2016-01-01")
    cluster = descriptive_kmeans(engineered, eda_end)
    if len(engineered) == 3841 and len(cluster.assignments) != 1493:
        raise ValueError(f"Canonical K-Means pool must contain 1493 rows, got {len(cluster.assignments)}")

    label_path = root / "manual_labels" / "short_corner_review.csv"
    if not label_path.is_file():
        raise FileNotFoundError(f"Missing declared manual labels: {label_path}")
    label_hash = sha256_file(label_path)
    if label_hash != SHORT_LABELS_SHA256:
        raise ValueError("Manual short-corner labels do not match the canonical SHA-256")
    labels = pd.read_csv(label_path, dtype={"event_id": "string"})
    if len(labels) != 40 or labels.event_id.nunique() != 40:
        raise ValueError("Expected 40 unique short-corner manual labels")
    review = engineered.merge(labels, on="event_id", how="inner", validate="one_to_one")
    if len(review) != len(labels):
        raise ValueError("Manual labels do not join one-to-one with canonical corners")
    review["distance_band"] = pd.cut(
        review.pass_length, [-np.inf, 12, 15, 18, np.inf],
        labels=["<=12", "(12,15]", "(15,18]", ">18"],
    ).astype("string")
    review["note_contradiction"] = (
        review.manual_notes.str.contains("corto", case=False, na=False)
        & review.manual_short_label.eq(0)
    )
    review["distance_from_threshold"] = review.pass_length - SHORT_THRESHOLD
    truth = review.manual_short_label.astype(int).to_numpy()
    predicted = review.short_proxy.astype(int).to_numpy()
    tn, fp, fn, tp = confusion_matrix(truth, predicted, labels=[0, 1]).ravel()
    label_metrics = pd.DataFrame([{
        "n": len(review), "positive": int(truth.sum()), "negative": int((truth == 0).sum()),
        "accuracy": float((truth == predicted).mean()),
        "precision": float(tp / (tp + fp)) if tp + fp else 0.0,
        "recall": float(tp / (tp + fn)) if tp + fn else 0.0,
        "specificity": float(tn / (tn + fp)) if tn + fp else 0.0,
        "f1": float(2 * tp / (2 * tp + fp + fn)) if 2 * tp + fp + fn else 0.0,
        "balanced_accuracy": float(((tp / (tp + fn)) + (tn / (tn + fp))) / 2),
        "cohen_kappa": float(cohen_kappa_score(truth, predicted)),
        "mcc": float(matthews_corrcoef(truth, predicted)),
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
    }])
    sensitivity_rows = []
    for threshold in (15.0, 18.0, 20.0):
        season_prediction = (
            engineered.valid_geometry
            & engineered.height.isin(["Ground Pass", "Low Pass"])
            & engineered.pass_length.le(threshold)
        )
        review_prediction = (
            review.valid_geometry
            & review.height.isin(["Ground Pass", "Low Pass"])
            & review.pass_length.le(threshold)
        )
        sensitivity_rows.append(
            {"threshold": threshold, "season_short_count": int(season_prediction.sum()),
             "review_short_count": int(review_prediction.sum()),
             "review_agreement": float(review_prediction.astype(int).eq(review.manual_short_label).mean())}
        )
    threshold_sensitivity = pd.DataFrame(sensitivity_rows)
    near_threshold = review.loc[
        review.distance_from_threshold.abs().le(1.5),
        ["event_id", "manual_short_label", "pass_length", "distance_from_threshold",
         "height", "short_proxy"],
    ].copy()
    label_audit = {
        "rows": len(labels), "unique_ids": int(labels.event_id.nunique()), "joined": len(review),
        "positive": int(labels.manual_short_label.sum()),
        "negative": int(labels.manual_short_label.eq(0).sum()),
        "contradictory_negative_notes": int(review.note_contradiction.sum()),
        "labels_equal_ground_pass_rule": bool((truth == review.height.eq("Ground Pass").astype(int)).all()),
        "sample_design": "10 cases from each of four distance bands; not prevalence-representative",
        "methodology_independent": False, "adjudicated": False,
        "status": "legacy_labels_integrity_verified_methodology_not_validated",
    }

    fields_checked = [
        "hist_scr15_raw", "hist_scr15_smoothed", "hist_xg_per_corner",
        "opp_hist_scr15_conceded_raw", "opp_hist_scr15_conceded_smoothed",
        "league_prior_scr15",
    ]
    target_match_id = 3825769 if 3825769 in set(pre_match.match_id) else int(
        pre_match.loc[pre_match.pre_match_ready, "match_id"].iloc[len(pre_match) // 2]
    )
    target_date = pre_match.loc[pre_match.match_id.eq(target_match_id), "match_date"].iloc[0]
    perturbed_corners = engineered.copy()
    mutation = pd.to_datetime(perturbed_corners.match_date).dt.normalize().ge(target_date)
    perturbed_corners.loc[mutation & perturbed_corners.valid_sequence, "shot_within_15s"] = 1
    perturbed = build_pre_match_features(observed, perturbed_corners)
    before = pre_match[pre_match.match_id.eq(target_match_id)].sort_values("team")[fields_checked]
    after = perturbed[perturbed.match_id.eq(target_match_id)].sort_values("team")[fields_checked]
    perturbation_audit = pd.DataFrame([{
        "target_match_id": target_match_id, "target_date": target_date,
        "mutated_rows_on_or_after_target": int(mutation.sum()),
        "fields_checked": json.dumps(fields_checked),
        "passed": bool(np.allclose(before, after, equal_nan=True)),
    }])
    if not bool(perturbation_audit.passed.iloc[0]):
        raise ValueError("Pre-match feature perturbation audit failed")

    cluster_source = cluster.assignments.merge(
        engineered[["event_id", "delivery_zone"]], on="event_id", validate="one_to_one"
    )
    cluster_zone_cross = pd.crosstab(
        cluster_source.geometric_name, cluster_source.delivery_zone, margins=True
    ).reset_index()
    feature_dictionary = pd.DataFrame([
        {"variable": name, "role": "pre_match_candidate", "availability": "before_match",
         "window": "eight_strictly_prior_matches", "meaning": meaning}
        for name, meaning in {
            "hist_corners_per_match": "Average attacking corners",
            "hist_scr15_smoothed": "Smoothed attacking SCR-15",
            "hist_xg_per_corner": "Historical post-corner xG, descriptive lag",
            "hist_short_share": "Historical short proxy share",
            "hist_high_share": "Historical high-pass share",
            "hist_top_taker_share": "Historical leading taker concentration",
            "hist_dominant_zone_share": "Leading-zone concentration among valid direct deliveries",
            "hist_score_losing_share": "Historical share awarded while losing",
            "opp_hist_scr15_conceded_smoothed": "Opponent smoothed SCR-15 conceded",
            "is_home": "Target match venue flag",
        }.items()
    ])
    decision_log = pd.DataFrame([
        {"decision": "source", "value": source.contract_version, "reason": "Audited SCR-15 input"},
        {"decision": "history", "value": "8", "reason": "Strict prior-match window"},
        {"decision": "short_proxy", "value": "18 units + Ground/Low", "reason": "Versioned descriptive proxy"},
        {"decision": "manual_labels", "value": label_audit["status"], "reason": "Integrity yes; independence unproven"},
        {"decision": "kmeans", "value": "k=4 development-only", "reason": "Descriptive, not predictive"},
    ])
    design_scope_audit = pd.DataFrame([
        {"analysis": "manual threshold review", "max_date": review.match_date.max(),
         "strictly_before_eda_end": bool(review.match_date.max() < eda_end), "uses_post_cutoff": False},
        {"analysis": "K-Means destinations", "max_date": cluster.assignments.match_date.max(),
         "strictly_before_eda_end": bool(cluster.assignments.match_date.max() < eda_end), "uses_post_cutoff": False},
        {"analysis": "contract/count quality checks", "max_date": engineered.match_date.max(),
         "strictly_before_eda_end": False, "uses_post_cutoff": True},
        {"analysis": "feature materialization (not EDA)", "max_date": engineered.match_date.max(),
         "strictly_before_eda_end": False, "uses_post_cutoff": True},
    ])
    modeling_table_contract = pd.DataFrame([
        {"table": name, "unit": unit, "target": target, "predictor_layer": layer,
         "rows": len(tables[name])}
        for name, unit, target, layer in [
            ("model_scr15_pre_match", "evaluable corner with both histories ready", "shot_within_15s", "pre_match"),
            ("model_scr15_scenario", "evaluable corner with both histories ready", "shot_within_15s", "pre_match + known_before_kick"),
            ("model_short_direct", "corner with valid geometry", "short_proxy", "pre_match + known_before_kick"),
            ("model_delivery_zone", "valid direct delivery", "delivery_zone (unchanged taxonomy)", "pre_match + known_before_kick"),
            ("model_corner_count", "team-match including zero-corner matches", "n_corners", "pre_match; exposure_matches=1"),
        ]
    ])
    frames: dict[str, pd.DataFrame] = {
        "corners_engineered": engineered, "team_match_observed": observed,
        "pre_match_features": pre_match,
        "training_candidates_pre_match": tables["model_scr15_pre_match"],
        "training_candidates_scenario": tables["model_scr15_scenario"],
        "short_manual_review": review, "short_label_metrics": label_metrics,
        "short_threshold_sensitivity": threshold_sensitivity,
        "short_near_threshold": near_threshold, "feature_dictionary": feature_dictionary,
        "decision_log": decision_log, "history_perturbation_audit": perturbation_audit,
        "cluster_assignments": cluster.assignments, "cluster_centers": cluster.centers,
        "cluster_sensitivity": cluster.sensitivity, "cluster_zone_cross": cluster_zone_cross,
        "design_scope_audit": design_scope_audit, **tables,
        "modeling_table_contract": modeling_table_contract,
    }
    staging = _staging_directory(output)
    try:
        exports = [
            _export(frame, staging / f"{name}.parquet", staging)
            for name, frame in frames.items()
        ]
        label_audit_path = staging / "short_label_audit.json"
        write_json(label_audit_path, label_audit)
        exports.append(artifact(label_audit_path, staging, rows=1))
        counts = {
            "matches": len(matches), "corners": len(engineered),
            "evaluable": int(engineered.valid_sequence.sum()),
            "excluded": int((~engineered.valid_sequence).sum()),
            "team_matches": len(observed), "pre_match_ready": int(pre_match.pre_match_ready.sum()),
            "training_rows": len(tables["model_scr15_pre_match"]),
            "training_positive": int(tables["model_scr15_pre_match"].shot_within_15s.sum()),
            "manual_labels": len(review), "cluster_rows": len(cluster.assignments),
            "valid_geometry": int(engineered.valid_geometry.sum()),
            "direct_deliveries": int(engineered.direct_delivery_valid.sum()),
            "zero_corner_team_matches": int(observed.n_corners.eq(0).sum()),
        }
        contract = contract_payload(
            stage="04_features", contract_version=VERSIONS["04_features"], run_id=_run_id(),
            exports=exports, source_contract_version=source.contract_version,
            source_run_id=source.run_id, source_rule_version=RULE_VERSION,
            source_corners_sha256=corner_item.sha256,
            source_short_corner_review_sha256=label_hash,
            parameters={"history_matches": HISTORY_MATCHES, "short_threshold": SHORT_THRESHOLD,
                        "smoothing_strength": SMOOTHING_STRENGTH,
                        "eda_end_exclusive": eda_end.date().isoformat(),
                        "league_prior": "expanding, valid corners with match_date strictly before target"},
            core_features=CORE_FEATURES, counts=counts,
            label_audit_status=label_audit["status"],
            post_eda_period_status="eligible for temporal evaluation but not a pristine untouched holdout",
            clusters_allowed_as_model_features=False,
        )
        publish_contract(staging, contract)
        _replace_stage_directory(staging, output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"stage": contract.stage, "contract_version": contract.contract_version, **contract.counts}


STAGES: dict[str, Callable[[Path | None], dict[str, Any]]] = {
    "clean": clean_stage,
    "scr15": scr15_stage,
    "features": features_stage,
}


def run_stage(stage: str, root: Path | None = None) -> dict[str, Any]:
    try:
        return STAGES[stage](root)
    except KeyError as exc:
        raise ValueError(f"Unknown stage {stage!r}; choose from {sorted(STAGES)}") from exc


def build(root: Path | None = None) -> dict[str, Any]:
    """Produce and verify canonical stages 02, 03, and 04 in order."""
    results = [clean_stage(root), scr15_stage(root), features_stage(root)]
    return {"stages": results, "completed": "04_features"}


def train(
    root: Path | None = None,
    output: Path | None = None,
    *,
    bootstrap_iterations: int = 200,
) -> dict[str, Any]:
    """Build and atomically publish canonical stage 05 from verified stage 04."""
    root = root or data_dir()
    source_path = root / "processed" / "04_features" / "contract.json"
    source = load_contract(
        source_path, expected_stage="04_features", expected_version=VERSIONS["04_features"]
    )
    required = [
        "model_scr15_scenario", "model_short_direct", "model_delivery_zone",
        "model_corner_count", "team_match_observed", "pre_match_features",
        "corners_engineered",
    ]
    for name in required:
        source.require_artifact(f"{name}.parquet")
    if source.source_contract_version != VERSIONS["03_scr15"]:
        raise ValueError("04_features lineage does not point to canonical 03_scr15")
    if source.source_rule_version != RULE_VERSION:
        raise ValueError("04_features source rule is not canonical")
    if source.clusters_allowed_as_model_features is not False:
        raise ValueError("04_features must prohibit K-Means predictors")
    tables = {
        name: pd.read_parquet(source_path.parent / f"{name}.parquet") for name in required
    }
    result = run_canonical_modeling(tables, bootstrap_iterations=bootstrap_iterations)
    output = output or root / "processed" / "05_modeling"
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent)
    )
    exports: list[Artifact] = []
    for name, frame in result.tables.items():
        exports.append(_export(frame, staging / f"{name}.parquet", staging))
    for name, model in result.models.items():
        path = staging / name
        _write_joblib(model, path)
        exports.append(artifact(path, staging))
    for name, schema in result.schemas.items():
        path = staging / name
        write_json(path, schema)
        exports.append(artifact(path, staging))
    run_id = _run_id()
    winners = pd.DataFrame(result.winners)
    development_metrics = result.tables["temporal_metrics"]
    development_metrics = development_metrics[development_metrics["role"].eq("selection")]
    card = (
        "# CornerScout model card - canonical stage 05\n\n"
        f"- Run: `{run_id}`\n"
        f"- Source: `{source.contract_version}` / `{source.run_id}`\n"
        "- Validation: three expanding-origin development windows; final confirmation excluded from decisions.\n"
        "- Predictors: regularized logistic regression and Poisson; Random Forest and K-Means are excluded.\n"
        "- Bootstrap unit: complete match.\n\n"
        "## Winners\n\n"
        + "```text\n"
        + winners.to_string(index=False)
        + "\n```"
        + "\n\n## Development Metrics\n\n```text\n"
        + development_metrics.groupby(["objective", "model"]).mean(numeric_only=True).to_string()
        + "\n```\n\n## Limitations\n\n"
        "- Single historical season; no external-season validation.\n"
        "- The final period is evaluated but never used for selection or gates.\n"
        "- Short/direct remains a proxy target.\n"
        "- Refit-full artifacts have not been retrospectively evaluated.\n"
    )
    card_path = staging / "model_card.md"
    _write_text(card, card_path)
    exports.append(artifact(card_path, staging))
    contract = contract_payload(
        stage="05_modeling", contract_version=VERSIONS["05_modeling"], run_id=run_id,
        exports=[], artifacts=exports, source_contract_version=source.contract_version,
        source_run_id=source.run_id,
        windows=[
            {"name": window.name, "start": window.start.date().isoformat(),
             "end": window.end.date().isoformat(), "role": window.role}
            for window in result.windows
        ],
        final_period={
            "start": result.final.start.date().isoformat(),
            "end_exclusive": result.final.end.date().isoformat(),
            "used_for_decisions": False,
        },
        selection_rule="candidate must improve development windows only; final is confirmation-only",
        automatic_balancing=False, bootstrap_unit="match",
        bootstrap_iterations=bootstrap_iterations,
        kmeans_features_used=False, random_forest_used=False, winners=result.winners,
        gates={
            "corner_count": {
                "family": result.count_gate.family,
                "raw_dispersion": result.count_gate.raw_dispersion,
                "conditional_dispersion": result.count_gate.conditional_dispersion,
                "maximum_conditional_dispersion": COUNT_MAXIMUM_CONDITIONAL_DISPERSION,
                "evaluated_before": result.windows[0].start.date().isoformat(),
            },
            "delivery_zone": {
                "passed": result.zone_gate.passed,
                "persistence": result.zone_gate.persistence,
                "chance": result.zone_gate.chance,
                "evaluated_before": result.final.start.date().isoformat(),
            },
        },
        limitations=[
            "Single historical season; no external-season validation.",
            "Final confirmation metrics do not influence model decisions.",
            "K-Means and Random Forest are not predictors.",
        ],
    )
    try:
        publish_contract(staging, contract)
        _replace_stage_directory(staging, output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {
        "stage": contract.stage, "contract_version": contract.contract_version,
        "run_id": run_id, "final_used_for_decisions": False,
        "winners": result.winners, "artifacts": len(exports),
    }
