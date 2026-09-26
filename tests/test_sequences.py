import math

import pytest

from analytics.scr15 import extract_corners


def toy_event(index, seconds, kind="Pass", team="A", possession=1, period=1, **changes):
    event = {
        "event_id": f"toy-{index}", "index": index, "period": period,
        "seconds": float(seconds), "type": kind, "team": team,
        "possession_team": team, "possession": possession, "recipient": None,
        "pass_type": None, "cross": False, "xg": 0.1,
    }
    event.update(changes)
    return event


CORNER = toy_event(1, 100, pass_type="Corner")
CASES = [
    ("shot exactly at 15", [CORNER, toy_event(2, 115, "Shot"), toy_event(3, 116)], 1, True, "time_limit"),
    ("shot after limit", [CORNER, toy_event(2, 115.001, "Shot")], 0, True, "time_limit"),
    ("lost possession never reopens", [CORNER, toy_event(2, 103, team="B"), toy_event(3, 110, "Shot")], 0, True, "possession_team_change"),
    ("new possession id same team", [CORNER, toy_event(2, 104, possession=2), toy_event(3, 110, "Shot", possession=2), toy_event(4, 116)], 1, True, "time_limit"),
    ("other period", [CORNER, toy_event(2, 102, "Shot", period=2)], 0, True, "period_end"),
    ("regression inside window", [CORNER, toy_event(2, 108), toy_event(3, 106)], None, False, "ambiguous_clock"),
    ("regression after time limit", [CORNER, toy_event(2, 116), toy_event(3, 112, "Shot")], 0, True, "time_limit"),
    ("regression after possession", [CORNER, toy_event(2, 104, team="B"), toy_event(3, 102)], 0, True, "possession_team_change"),
    ("regression after new corner", [CORNER, toy_event(2, 108, pass_type="Corner"), toy_event(3, 106)], 0, True, "new_corner"),
    ("new corner closes", [CORNER, toy_event(2, 108, pass_type="Corner"), toy_event(3, 110, "Shot")], 0, True, "new_corner"),
    ("shot without xg", [CORNER, toy_event(2, 110, "Shot", xg=math.nan), toy_event(3, 116)], 1, True, "time_limit"),
]


@pytest.mark.parametrize("description,events,expected,valid,reason", CASES, ids=[case[0] for case in CASES])
def test_notebook_synthetic_cases(description, events, expected, valid, reason):
    found = extract_corners(events, -1)[0]
    if expected is None:
        assert math.isnan(found["shot_within_15s"]), description
    else:
        assert found["shot_within_15s"] == expected, description
    assert found["valid_sequence"] is valid
    assert found["end_reason"] == reason
    if description == "shot without xg":
        assert not found["xg_complete"] and math.isnan(found["xg_sequence"])


def test_unknown_possession_is_not_evaluable():
    events = [CORNER, toy_event(2, 105, possession_team=None), toy_event(3, 116)]
    found = extract_corners(events, -1)[0]
    assert not found["valid_sequence"]
    assert found["end_reason"] == "unknown_possession"
    assert math.isnan(found["shot_within_15s"])


def test_ordinary_restart_is_audit_only():
    events = [CORNER, toy_event(2, 105, pass_type="Throw-in"), toy_event(3, 110, "Shot"), toy_event(4, 116)]
    found = extract_corners(events, -1)[0]
    assert found["restart_ids"] == ["toy-2"]
    assert found["shot_within_15s"] == 1


def test_new_corner_prevents_overlapping_shot_attribution():
    events = [CORNER, toy_event(2, 105, pass_type="Corner"), toy_event(3, 110, "Shot"), toy_event(4, 121)]
    first, second = extract_corners(events, -1)
    assert first["shot_ids"] == []
    assert second["shot_ids"] == ["toy-3"]
