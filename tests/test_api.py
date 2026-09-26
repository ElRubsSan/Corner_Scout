import hashlib
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from analytics.contracts import Artifact as ContractArtifact
from analytics.contracts import StageContract
from backend.main import app
from backend.repository import ArtifactError, CanonicalRepository


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_tree(root):
    directories = {
        "02": root / "interim" / "02_clean",
        "03": root / "interim" / "03_scr15",
        "04": root / "processed" / "04_features",
        "05": root / "processed" / "05_modeling",
    }
    for directory in directories.values():
        directory.mkdir(parents=True)
    tables = {
        ("02", "matches_clean.parquet"): pd.DataFrame([{"match_id": 1, "match_date": "2016-01-01", "kick_off": "12:00:00", "home_team": "A", "away_team": "B"}]),
        ("03", "corners_scr15.parquet"): pd.DataFrame([{"event_id": "e1"}]),
        ("04", "corners_engineered.parquet"): pd.DataFrame([{"event_id": "e1", "match_id": 1}]),
        ("04", "cluster_assignments.parquet"): pd.DataFrame([{"event_id": "e1", "cluster_id": 0}]),
        ("04", "cluster_centers.parquet"): pd.DataFrame([{"cluster_id": 0, "end_x": 110.0, "end_y_relative": 40.0}]),
        ("05", "objective_winners.parquet"): pd.DataFrame([{"objective": "scr15", "winner": "league_reference"}]),
        ("05", "temporal_metrics.parquet"): pd.DataFrame([{"objective": "scr15", "model": "league_reference", "brier": 0.2}]),
    }
    records: dict[str, list[ContractArtifact]] = {stage: [] for stage in directories}
    for (stage, name), frame in tables.items():
        path = directories[stage] / name
        frame.to_parquet(path, index=False)
        records[stage].append(ContractArtifact(file=name, sha256=_digest(path), rows=len(frame)))
    audit_path = directories["04"] / "feature_audit.json"
    audit_path.write_text('{"status":"ok"}', encoding="utf-8")
    feature_audit = ContractArtifact(file=audit_path.name, sha256=_digest(audit_path))
    manifest_path = directories["05"] / "model_manifest.json"
    manifest_path.write_text('{"status":"ok"}', encoding="utf-8")
    model_manifest = ContractArtifact(file=manifest_path.name, sha256=_digest(manifest_path))
    contracts = {
        "02": StageContract(stage="02_clean", contract_version="02-clean-v2", run_id="run02", exports=records["02"]),
        "03": StageContract(stage="03_scr15", contract_version="03-scr15-v2", run_id="run03",
                            source_contract_version="02-clean-v2", source_run_id="run02",
                            rule_version="scr15", exports=records["03"]),
        "04": StageContract(stage="04_features", contract_version="04-features-v2", run_id="run04",
                            source_contract_version="03-scr15-v2", source_run_id="run03",
                            source_corners_sha256=records["03"][0].sha256,
                            exports=records["04"], artifacts=[feature_audit]),
        "05": StageContract(stage="05_modeling", contract_version="05-modeling-v3-objectives", run_id="run05",
                            source_contract_version="04-features-v2", source_run_id="run04",
                            exports=[model_manifest], artifacts=records["05"]),
    }
    for stage, contract in contracts.items():
        (directories[stage] / "contract.json").write_text(contract.model_dump_json(), encoding="utf-8")
    return directories


def _contract_payload(directory):
    path = directory / "contract.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def test_repository_verifies_canonical_lineage_and_tables(tmp_path):
    _canonical_tree(tmp_path)
    repository = CanonicalRepository(tmp_path)
    assert repository.identity["05-modeling-v3-objectives"] == "run05"
    assert repository.rows("matches_clean")[0]["match_id"] == 1
    assert repository.rows("objective_winners")[0]["objective"] == "scr15"
    assert ("04", "feature_audit.json") in repository._artifacts
    assert ("05", "model_manifest.json") in repository._artifacts


def test_repository_rejects_hash_mismatch_before_read(tmp_path):
    directories = _canonical_tree(tmp_path)
    pd.DataFrame([{"event_id": "tampered"}]).to_parquet(directories["03"] / "corners_scr15.parquet", index=False)
    with pytest.raises(ArtifactError, match="hash_mismatch"):
        CanonicalRepository(tmp_path)


def test_repository_verifies_hash_of_every_declared_artifact(tmp_path):
    directories = _canonical_tree(tmp_path)
    (directories["05"] / "model_manifest.json").write_text("tampered", encoding="utf-8")
    with pytest.raises(ArtifactError, match="hash_mismatch:05:model_manifest.json"):
        CanonicalRepository(tmp_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [("stage", "04_wrong"), ("contract_version", "04-features-v1"), ("run_id", "")],
)
def test_repository_rejects_invalid_stage_version_or_run(tmp_path, field, value):
    directories = _canonical_tree(tmp_path)
    path, payload = _contract_payload(directories["04"])
    payload[field] = value
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ArtifactError, match="canonical_contract_invalid:04"):
        CanonicalRepository(tmp_path)


@pytest.mark.parametrize(
    ("stage", "field", "value", "error"),
    [
        ("03", "source_contract_version", "wrong", "canonical_lineage_invalid:03"),
        ("03", "source_run_id", "wrong", "canonical_run_lineage_invalid:03"),
        ("04", "source_run_id", "wrong", "canonical_run_lineage_invalid:04"),
        ("05", "source_run_id", "wrong", "canonical_run_lineage_invalid:05"),
        ("04", "source_corners_sha256", "0" * 64, "canonical_hash_lineage_invalid:04"),
    ],
)
def test_repository_rejects_invalid_lineage(tmp_path, stage, field, value, error):
    directories = _canonical_tree(tmp_path)
    path, payload = _contract_payload(directories[stage])
    payload[field] = value
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ArtifactError, match=error):
        CanonicalRepository(tmp_path)


@pytest.mark.parametrize("file", ["../escape.parquet", "C:/escape.parquet"])
def test_repository_rejects_artifact_path_traversal(tmp_path, file):
    directories = _canonical_tree(tmp_path)
    path, payload = _contract_payload(directories["05"])
    payload["artifacts"][0]["file"] = file
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ArtifactError, match="canonical_contract_invalid|canonical_artifact_path_invalid"):
        CanonicalRepository(tmp_path)


def test_repository_rejects_duplicate_across_exports_and_artifacts(tmp_path):
    directories = _canonical_tree(tmp_path)
    path, payload = _contract_payload(directories["05"])
    duplicate = {**payload["exports"][0], "file": "./model_manifest.json"}
    payload["artifacts"].append(duplicate)
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ArtifactError, match="canonical_artifact_duplicate:05"):
        CanonicalRepository(tmp_path)


def test_existing_routes_and_agent_route_are_registered():
    paths = {route.path for route in app.routes}
    expected = {"/api/v1/teams", "/api/v1/matches", "/api/v1/scouting-runs",
                "/api/v1/scouting-runs/{run_id}/summary", "/api/v1/scouting-runs/{run_id}/corners",
                "/api/v1/scouting-runs/{run_id}/patterns", "/api/v1/scouting-runs/{run_id}/quality",
                "/api/v1/scouting-runs/{run_id}/model", "/api/v1/scouting-runs/{run_id}/report",
                "/api/v1/scouting-runs/{run_id}/agent"}
    assert expected <= paths
    assert TestClient(app).get("/api/v1/health").json()["status"] == "ok"


def test_openapi_documents_real_error_responses():
    schema = app.openapi()
    create_responses = schema["paths"]["/api/v1/scouting-runs"]["post"]["responses"]
    assert {"404", "409", "422", "503"} <= set(create_responses)
    assert create_responses["409"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")
    agent_responses = schema["paths"]["/api/v1/scouting-runs/{run_id}/agent"]["post"]["responses"]
    assert {"404", "409", "422", "503"} <= set(agent_responses)
