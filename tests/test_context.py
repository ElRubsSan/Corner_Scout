from analytics.context import build_pre_event_context


def event(event_id, kind, team, **changes):
    row = {
        "event_id": event_id, "type": kind, "team": team, "period": 1,
        "minute": 0.0, "second": 0.0, "seconds": 0.0,
        "starting_xi_ids": [], "related_event_ids": [], "pass_type": None,
        "shot_outcome": None, "player_id": None, "player": None, "card": None,
        "substitution_replacement_id": None,
    }
    row.update(changes)
    return row


def lineups():
    return [
        event("xa", "Starting XI", "A", starting_xi_ids=list(range(1, 12))),
        event("xb", "Starting XI", "B", starting_xi_ids=list(range(21, 32))),
    ]


def test_score_and_players_are_strictly_pre_event():
    records = lineups() + [
        event("goal", "Shot", "A", seconds=10, shot_outcome="Goal", player_id=1),
        event("sub", "Substitution", "A", seconds=20, player_id=1, substitution_replacement_id=12),
        event("red", "Foul Committed", "B", seconds=30, player_id=21, card="Red Card"),
        event("next", "Pass", "A", seconds=31),
    ]
    contexts, scores, _, dismissals, substitutions = build_pre_event_context(records, "A", "B")
    assert contexts["goal"]["home_score_before"] == 0
    assert contexts["sub"]["home_score_before"] == 1 and contexts["sub"]["attacking_players"] == 11
    assert contexts["red"]["defending_players"] == 11
    assert contexts["next"]["defending_players"] == 10
    assert scores == {"A": 1, "B": 0}
    assert substitutions[0]["valid"] and dismissals[0]["on_pitch"]


def test_previous_corner_context_excludes_current_corner():
    records = lineups() + [
        event("c1", "Pass", "A", seconds=100, pass_type="Corner"),
        event("c2", "Pass", "A", seconds=150, pass_type="Corner"),
    ]
    contexts, *_ = build_pre_event_context(records, "A", "B")
    assert not contexts["c1"]["repeat_corner_60s"]
    assert contexts["c2"]["seconds_since_previous_same_team_corner"] == 50
    assert contexts["c2"]["repeat_corner_60s"]
