import json
import pytest
from backend.gemini import generate
from backend.reporting import deterministic
from backend.schemas import RunRequest, ReportInput
from backend.service import create_run, report_input


@pytest.fixture(scope="module")
def payload():
    return report_input(create_run(RunRequest(rival="Barcelona", cutoff_date="2016-03-01")))


def test_no_key(payload, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    assert generate(payload).fallback_reason == 'missing_api_key'


def test_typed_valid_mock(payload):
    def mock(value: ReportInput) -> str:
        return json.dumps({'observations':[{'text':f'Corners totales: {value.summary.corners}.','evidence_ids':['corners']}], 'recommendations':[]})
    assert generate(payload, mock).mode == 'gemini'


@pytest.mark.parametrize('text', ['not json', '{"observations":[]}', '{"observations":[{"text":"99999 corners","evidence_ids":["corners"]}],"recommendations":[]}', '{"observations":[{"text":"Hola","evidence_ids":["invented"]}],"recommendations":[]}'])
def test_invalid_output(payload, text):
    assert generate(payload, lambda _: text).fallback_reason == 'invalid_output'


@pytest.mark.parametrize('error', [TimeoutError(), RuntimeError('quota exhausted')])
def test_provider_failures(payload, error):
    def mock(value: ReportInput) -> str:
        raise error
    assert generate(payload, mock).fallback_reason == 'provider_unavailable'
