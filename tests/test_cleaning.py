import math

from analytics.cleaning import normalize


def test_normalize_nested_preserves_ids_and_provenance():
    raw = {
        "id": "event-1", "index": 7, "period": 1, "minute": 2, "second": 3,
        "timestamp": "00:02:03.500", "type": {"id": 30, "name": "Pass"},
        "team": {"id": 1, "name": "A"},
        "possession_team": {"id": 1, "name": "A"},
        "player": {"id": 10, "name": "P"}, "possession": 4,
        "location": [120, 0],
        "pass": {"type": {"name": "Corner"}, "recipient": {"name": "R"},
                 "end_location": [110, 40], "height": {"name": "High Pass"}},
        "related_events": ["other"],
    }
    event = normalize(raw, "events/1.jsonl.gz", 9)
    assert (event["event_id"], event["type_id"], event["team_id"], event["player_id"]) == ("event-1", 30, 1, 10)
    assert event["pass_type"] == "Corner" and event["end_x"] == 110
    assert event["seconds"] == 123.5
    assert event["source_file"] == "events/1.jsonl.gz" and event["raw_line"] == 9


def test_normalize_flat_preserves_explicit_ids_and_missing_values():
    raw = {
        "id": "event-2", "index": 8, "period": 1, "timestamp": "bad",
        "type": "Shot", "type_id": 16, "team": "A", "team_id": 1,
        "possession_team": "A", "possession_team_id": 1,
        "player": "P", "player_id": 10, "shot_statsbomb_xg": 0.25,
        "pass_end_location": [100, 20],
    }
    event = normalize(raw, "events/1.jsonl.gz", 10)
    assert (event["type_id"], event["team_id"], event["possession_team_id"], event["player_id"]) == (16, 1, 1, 10)
    assert event["xg"] == 0.25 and math.isnan(event["seconds"])
