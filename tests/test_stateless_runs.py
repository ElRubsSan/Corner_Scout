import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.run_context import sign, verify
from backend import service
from backend.schemas import Run


def test_signed_context_rejects_tampering(monkeypatch):
    monkeypatch.setenv("CORNERSCOUT_SESSION_SECRET", "test-secret-" * 4)
    token = sign({"run_id": "a" * 64})
    assert verify(token)["run_id"] == "a" * 64
    with pytest.raises(Exception) as caught:
        verify(token[:-1] + ("0" if token[-1] != "0" else "1"))
    assert caught.value.status_code == 404


def test_stateless_run_survives_without_disk_and_locks_dataset(monkeypatch, tmp_path):
    monkeypatch.setenv("CORNERSCOUT_STATELESS_RUNS", "1")
    monkeypatch.setenv("CORNERSCOUT_SESSION_SECRET", "test-secret-" * 4)
    from types import SimpleNamespace
    canonical = SimpleNamespace(fingerprint="version-one", identity={"04": "run04"})
    monkeypatch.setattr(service, "repo", lambda: canonical)
    run = Run(run_id="a" * 64, rival="Barcelona", analyst=None, cutoff_date="2016-03-01", matches=[], dataset_version="version-one", canonical_runs=canonical.identity)
    monkeypatch.setattr(service, "create_run", lambda request: run)
    client = TestClient(app)
    response = client.post("/api/v1/scouting-runs", json={"rival": "Barcelona", "cutoff_date": "2016-03-01"})
    token = response.headers["X-CornerScout-Run"]
    assert client.get("/api/v1/scouting-runs/" + run.run_id).status_code == 404
    assert client.get("/api/v1/scouting-runs/" + run.run_id, headers={"X-CornerScout-Run": token}).status_code == 200
    canonical.fingerprint = "version-two"
    assert client.get("/api/v1/scouting-runs/" + run.run_id, headers={"X-CornerScout-Run": token}).status_code == 409


@pytest.mark.parametrize("selection", ["date", "match"])
def test_real_canonical_run_reconstructed_in_a_fresh_client(monkeypatch, selection):
    from analytics.io import data_dir
    if not (data_dir() / "processed/05_modeling/contract.json").exists():
        pytest.skip("canonical local data required")
    monkeypatch.setenv("CORNERSCOUT_STATELESS_RUNS", "1")
    monkeypatch.setenv("CORNERSCOUT_SESSION_SECRET", "test-secret-" * 4)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    def no_disk(*args):
        raise AssertionError("stateless run must not write a file")
    monkeypatch.setattr(service, "write_json", no_disk)
    body = {"rival": "Barcelona", "cutoff_date": "2016-03-01"}
    if selection == "match":
        match = service.matches_for("Barcelona", None, 1)[0]
        body = {"rival": "Barcelona", "target_match_id": match.match_id}
    first = TestClient(app).post("/api/v1/scouting-runs", json=body)
    assert first.status_code == 201
    run_id = first.json()["run_id"]
    token = first.headers["X-CornerScout-Run"]
    second = TestClient(app)
    for suffix in ("", "/summary", "/destination-heatmap", "/quality"):
        response = second.get("/api/v1/scouting-runs/" + run_id + suffix, headers={"X-CornerScout-Run": token})
        assert response.status_code == 200
    response = second.post("/api/v1/scouting-runs/" + run_id + "/agent", headers={"X-CornerScout-Run": token}, json={"question": "¿Qué partidos se analizaron?"})
    assert response.status_code == 200 and response.json()["mode"] == "deterministic"
