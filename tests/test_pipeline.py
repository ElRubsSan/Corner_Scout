import pandas as pd
import pytest
from types import SimpleNamespace

import analytics.pipeline as pipeline
from analytics.contracts import contract_payload
from analytics.io import artifact, publish_contract
from analytics.io import load_contract
from analytics.modeling import TemporalWindow


def test_build_runs_canonical_stages_in_order(monkeypatch, tmp_path):
    calls = []

    def stage(name):
        def run(root):
            calls.append((name, root))
            return {"stage": name}
        return run

    monkeypatch.setattr(pipeline, "clean_stage", stage("02_clean"))
    monkeypatch.setattr(pipeline, "scr15_stage", stage("03_scr15"))
    monkeypatch.setattr(pipeline, "features_stage", stage("04_features"))

    result = pipeline.build(tmp_path)

    assert [name for name, _ in calls] == ["02_clean", "03_scr15", "04_features"]
    assert all(root == tmp_path for _, root in calls)
    assert result["completed"] == "04_features"


def test_train_verifies_04_and_publishes_complete_05(monkeypatch, tmp_path):
    stage = tmp_path / "processed" / "04_features"
    stage.mkdir(parents=True)
    required = [
        "model_scr15_scenario", "model_short_direct", "model_delivery_zone",
        "model_corner_count", "team_match_observed", "pre_match_features",
        "corners_engineered",
    ]
    exports = []
    for name in required:
        table = stage / f"{name}.parquet"
        pd.DataFrame({"value": [1]}).to_parquet(table, index=False)
        exports.append(artifact(table, stage, rows=1))
    contract = contract_payload(
        stage="04_features",
        contract_version="04-features-v2",
        run_id="features-run",
        exports=exports,
        source_contract_version="03-scr15-v2",
        source_rule_version="scr15-research-v1.2-first-limit",
        clusters_allowed_as_model_features=False,
    )
    publish_contract(stage, contract)
    final = TemporalWindow("final", pd.Timestamp("2016-04-01"), pd.Timestamp("2016-05-01"), "confirmation_only")
    result = SimpleNamespace(
        tables={
            "temporal_metrics": pd.DataFrame(
                [{"objective": "scr15", "model": "league_reference", "role": "selection", "brier": 0.2}]
            ),
            "objective_winners": pd.DataFrame(
                [{"objective": "scr15", "winner": "league_reference", "modeled": True, "justification": "test"}]
            ),
        },
        models={}, schemas={"scr15_input_schema.json": {"objective": "scr15"}},
        winners=[{"objective": "scr15", "winner": "league_reference", "modeled": True, "justification": "test"}],
        windows=[TemporalWindow("development_1", pd.Timestamp("2016-03-01"), pd.Timestamp("2016-04-01"), "selection")],
        final=final,
        count_gate=SimpleNamespace(family="poisson", raw_dispersion=1.0, conditional_dispersion=1.0),
        zone_gate=SimpleNamespace(passed=False, persistence=0.4, chance=0.5),
    )
    monkeypatch.setattr(
        pipeline, "run_canonical_modeling",
        lambda tables, bootstrap_iterations: result,
    )

    response = pipeline.train(tmp_path)

    published = load_contract(
        tmp_path / "processed" / "05_modeling" / "contract.json",
        expected_stage="05_modeling", expected_version="05-modeling-v3-objectives",
    )
    assert response["final_used_for_decisions"] is False
    assert len(published.all_artifacts) == response["artifacts"]


def test_train_rejects_tampered_04_before_modeling(tmp_path):
    stage = tmp_path / "processed" / "04_features"
    stage.mkdir(parents=True)
    table = stage / "model_corner_count.parquet"
    pd.DataFrame({"match_date": ["2015-01-01"]}).to_parquet(table, index=False)
    contract = contract_payload(
        stage="04_features",
        contract_version="04-features-v2",
        run_id="features-run",
        exports=[artifact(table, stage)],
    )
    publish_contract(stage, contract)
    table.write_bytes(b"not parquet")

    with pytest.raises(ValueError, match="Artifact size mismatch|SHA-256 mismatch"):
        pipeline.train(tmp_path)


def test_unknown_stage_is_explicit():
    with pytest.raises(ValueError, match="Unknown stage"):
        pipeline.run_stage("notebook")
