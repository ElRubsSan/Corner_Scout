import json

import pytest
from pydantic import ValidationError

from analytics.contracts import Artifact, contract_payload
from analytics.io import artifact, load_contract, publish_contract, write_json


def test_contract_rejects_unsafe_artifact_paths_and_wrong_boundary(tmp_path):
    with pytest.raises(ValidationError, match="safe relative path"):
        Artifact(file="../raw.csv", sha256="0" * 64)
    with pytest.raises(ValidationError, match="raw file must be a safe relative path"):
        contract_payload(
            stage="01_ingestion", contract_version="01-ingestion-v1", run_id="run",
            exports=[], raw_files={"../outside": "0" * 64},
        )

    stage = tmp_path / "stage"
    stage.mkdir()
    payload = stage / "data.json"
    write_json(payload, {"ok": True})
    contract = contract_payload(
        stage="02_clean",
        contract_version="02-clean-v2",
        run_id="run-1",
        exports=[artifact(payload, stage)],
    )
    publish_contract(stage, contract)

    with pytest.raises(ValueError, match="Expected stage"):
        load_contract(
            stage / "contract.json",
            expected_stage="03_scr15",
            expected_version="02-clean-v2",
        )
    with pytest.raises(ValueError, match="Expected contract version"):
        load_contract(
            stage / "contract.json",
            expected_stage="02_clean",
            expected_version="old",
        )


def test_contract_detects_artifact_tampering(tmp_path):
    stage = tmp_path / "stage"
    stage.mkdir()
    payload = stage / "artifact.bin"
    payload.write_bytes(b"canonical")
    contract = contract_payload(
        stage="03_scr15",
        contract_version="03-scr15-v2",
        run_id="run-2",
        exports=[artifact(payload, stage)],
    )
    publish_contract(stage, contract)
    payload.write_bytes(b"tampered!")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_contract(
            stage / "contract.json",
            expected_stage="03_scr15",
            expected_version="03-scr15-v2",
        )


def test_json_publication_is_complete_and_leaves_no_temporary_file(tmp_path):
    target = tmp_path / "nested" / "contract.json"
    write_json(target, {"stage": "test", "values": [1, 2, 3]})

    assert json.loads(target.read_text(encoding="utf-8"))["values"] == [1, 2, 3]
    assert list(target.parent.glob("*.tmp")) == []


def test_contract_is_not_published_when_an_artifact_is_missing(tmp_path):
    stage = tmp_path / "stage"
    contract = contract_payload(
        stage="04_features",
        contract_version="04-features-v2",
        run_id="run-3",
        exports=[Artifact(file="missing.parquet", sha256="0" * 64)],
    )

    with pytest.raises(FileNotFoundError, match="Missing 04_features artifact"):
        publish_contract(stage, contract)
    assert not (stage / "contract.json").exists()
