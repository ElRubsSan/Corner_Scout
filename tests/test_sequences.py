"""Boundary fixtures only: artificial events test rules, never product metrics."""
from analytics.pipeline import Event, sequences


def corner():
    return Event(event_id="corner", index=1, period=1, seconds=100, type="Pass", pass_type="Corner", team="A", possession_team="A", possession=1, location=[120, 0], end_location=[110, 40])


def event(index=2, seconds=110, **kwargs):
    values = dict(event_id=str(index), index=index, seconds=seconds, period=1, type="Shot", team="A", possession_team="A", possession=1, xg=0.1)
    values.update(kwargs)
    return Event(**values)


def test_boundary_is_inclusive():
    assert sequences([corner(), event(seconds=115)], 1)[0]["shot_within_15s"]
    assert not sequences([corner(), event(seconds=115.001)], 1)[0]["shot_within_15s"]


def test_opponent_possession_never_reopens():
    result = sequences([corner(), event(type="Pass", possession_team="B"), event(index=3, seconds=111)], 1)[0]
    assert not result["shot_within_15s"]
    assert result["end_reason"] == "possession_team_change"


def test_same_team_possession_change_is_audit_only():
    result = sequences([corner(), event(possession=2)], 1)[0]
    assert result["shot_within_15s"]
    assert result["possession_change_ids"] == '["2"]'


def test_restart_is_audit_only():
    result = sequences([corner(), event(type="Pass", pass_type="Throw-in"), event(index=3, seconds=111)], 1)[0]
    assert result["shot_within_15s"]
    assert result["restart_ids"] == '["2"]'


def test_period_boundary():
    assert not sequences([corner(), event(period=2, seconds=1)], 1)[0]["shot_within_15s"]


def test_corrupt_timestamp_is_unknown_not_negative():
    result = sequences([corner(), event(seconds=1)], 1)[0]
    assert result["shot_within_15s"] is None
    assert not result["valid_sequence"]
