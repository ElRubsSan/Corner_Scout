import json

import pytest

from backend.openai import generate
from backend.schemas import Evidence, Match, ReportInput, Summary


@pytest.fixture()
def payload():
    summary = Summary(rival="A", cutoff_date="2016-03-01", matches=8, corners=10,
                      evaluable_corners=10, excluded_corners=0, shots=3, scr15=0.3,
                      xg_per_corner=0.02, probability=0.3, probability_method="reference",
                      players=[], sides=[], deliveries=[], zones=[])
    matches = [Match(match_id=index, match_date=f"2016-02-{index:02d}", kick_off="12:00:00", home_team="A", away_team="B") for index in range(1, 9)]
    return ReportInput(rival="A", cutoff_date="2016-03-01", matches=matches, summary=summary,
                       patterns=[], evidence=[Evidence(id="corners", description="Corners totales", value="10")], limitations=[])


def test_no_key_uses_deterministic_fallback(payload, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    report = generate(payload)
    assert report.mode == "deterministic"
    assert report.fallback_reason == "missing_api_key"


def test_valid_typed_mock(payload):
    output = json.dumps({"observations": [{"text": "Corners totales: 10.", "evidence_ids": ["corners"]}], "recommendations": []})
    assert generate(payload, lambda _: output).mode == "openai"


@pytest.mark.parametrize("output", ["not json", '{"observations":[]}', '{"observations":[{"text":"999 corners","evidence_ids":["corners"]}],"recommendations":[]}'])
def test_invalid_outputs_fall_back(payload, output):
    assert generate(payload, lambda _: output).fallback_reason == "invalid_output"


def test_provider_failure_is_sanitized(payload):
    def failing(_):
        raise RuntimeError("secret provider detail")
    assert generate(payload, failing).fallback_reason == "provider_unavailable"
