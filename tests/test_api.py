from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_real_scouting_flow():
    assert len(client.get('/api/v1/teams').json()) == 20
    window = client.get('/api/v1/matches', params={'rival': 'Barcelona', 'before': '2016-03-01', 'limit': 8}).json()
    request = {'rival': 'Barcelona', 'cutoff_date': '2016-03-01', 'expected_match_ids': [m['match_id'] for m in window]}
    response = client.post('/api/v1/scouting-runs', json=request)
    assert response.status_code == 201, response.text
    run_id = response.json()['run_id']
    assert client.post('/api/v1/scouting-runs', json=request).json()['run_id'] == run_id
    for endpoint in ['summary', 'corners', 'patterns', 'quality', 'model', 'report-plan']:
        response = client.get(f'/api/v1/scouting-runs/{run_id}/{endpoint}')
        assert response.status_code == 200, response.text
    summary = client.get(f'/api/v1/scouting-runs/{run_id}/summary').json()
    assert summary['scr15'] == summary['shots'] / summary['evaluable_corners']
    report = client.post(f'/api/v1/scouting-runs/{run_id}/report')
    assert report.status_code == 200, report.text
    assert len(report.json()['input']['matches']) == 8


def test_errors():
    assert client.post('/api/v1/scouting-runs', json={'rival':'Barcelona', 'cutoff_date':'2015-08-01'}).status_code == 422
    assert client.post('/api/v1/scouting-runs', json={'rival':'missing', 'cutoff_date':'2016-03-01'}).status_code == 404
    assert client.post('/api/v1/scouting-runs', json={'rival':'Barcelona'}).status_code == 422
    assert client.get('/api/v1/scouting-runs/unknown').status_code == 404
    assert client.post('/api/v1/scouting-runs', json={'rival':'Barcelona', 'cutoff_date':'2016-03-01','expected_match_ids':list(range(8))}).status_code == 409
