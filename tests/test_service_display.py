import pytest
from fastapi import HTTPException
from types import SimpleNamespace

from backend import service
from backend.reporting import deterministic
from backend.schemas import Corner, Match, MatchProfile, Pattern


def _corner(event_id: str, delivery: str, zone: str, valid: bool = True) -> Corner:
    return Corner(
        match_id=1, event_id=event_id, player="Cobrador", x=120, y=0,
        end_x=110, end_y=40, side="y_bajo", delivery=delivery, zone=zone,
        height="High Pass", shot_within_15s=False if valid else None,
        xg=0.0 if valid else None, valid_sequence=valid, spatial_valid=valid,
        end_reason="time_limit", shot_ids=[], restart_ids=[], possession_change_ids=[],
    )


def test_summary_distinguishes_direct_destinations_from_short_and_invalid_corners(monkeypatch):
    corners = [_corner("direct", "envio", "franja_central"),
               _corner("short", "corto", "no_disponible"),
               _corner("invalid", "desconocido", "no_disponible", False)]
    monkeypatch.setattr(service, "corners_for", lambda run: corners)
    monkeypatch.setattr(service, "query", lambda *args, **kwargs: [])
    result = service.summary(SimpleNamespace(rival="A", cutoff_date="2016-03-01", matches=[1] * 8))

    assert result.corners == 3
    assert result.evaluable_corners == 2
    assert [(group.label, group.count) for group in result.zones] == [("franja_central", 1)]
    assert sum(group.count for group in result.deliveries) == 3


def test_report_uses_destination_names_but_preserves_evidence_ids(monkeypatch):
    corner = _corner("direct", "envio", "fuera_area")
    monkeypatch.setattr(service, "corners_for", lambda run: [corner])
    monkeypatch.setattr(service, "query", lambda *args, **kwargs: [])
    monkeypatch.setattr(service, "patterns", lambda run: [Pattern(
        cluster=3, count=1, evaluable=1, scr15=0.0, xg_per_corner=0.0,
        dominant_zone="fuera_area", main_taker="Cobrador",
        example_event_ids=["direct"], snapshot="2016-01-01",
    )])
    matches = [Match(match_id=index, match_date=f"2016-02-{index:02d}",
                     kick_off="12:00:00", home_team="A", away_team="B") for index in range(1, 9)]
    payload = service.report_input(SimpleNamespace(rival="A", cutoff_date="2016-03-01", matches=matches))
    report = deterministic(payload)

    assert payload.evidence[-1].id == "cluster-3"
    assert payload.evidence[-1].value == "1"
    assert payload.evidence[0].value == "0 de 1 córners evaluables (0.0 %)"
    assert "fuera del área" in payload.evidence[-1].description
    assert "Patron 3" not in payload.evidence[-1].description
    assert report.narrative.recommendations[0].evidence_ids == ["cluster-3"]
    assert "hacia fuera del área" in report.narrative.recommendations[0].text
    assert "la fuera" not in report.narrative.recommendations[0].text


def test_match_profiles_include_zero_corners_scores_and_tied_takers(monkeypatch):
    matches = [Match(match_id=index, match_date=f"2016-02-{index:02d}",
                     kick_off="12:00:00", home_team="A", away_team="B") for index in range(1, 9)]
    corners = [_corner("one", "envio", "franja_central"),
               _corner("two", "envio", "franja_central")]
    corners[1].player = "Segundo"
    monkeypatch.setattr(service, "corners_for", lambda run: corners)
    monkeypatch.setattr(service, "team_ids", lambda: {"A": 101, "B": 102})
    monkeypatch.setattr(service, "query", lambda *args, **kwargs: [
        {"match_id": match.match_id, "home_score": 2, "away_score": 1} for match in matches
    ])
    profiles = service.match_profiles(SimpleNamespace(matches=matches))
    assert len(profiles) == 8
    assert profiles[0].main_takers == ["Cobrador", "Segundo"]
    assert (profiles[0].home_score, profiles[0].away_score, profiles[0].rival_corners) == (2, 1, 2)
    assert (profiles[0].home_team_id, profiles[0].away_team_id) == (101, 102)
    assert profiles[1].rival_corners == 0
    assert profiles[1].main_takers == []


def test_team_identity_rejects_conflicting_source_ids(monkeypatch):
    monkeypatch.setattr(service, "query", lambda *args, **kwargs: [
        {"team": "Barcelona", "team_id": 217}, {"team": "Barcelona", "team_id": 999}
    ])
    with pytest.raises(HTTPException, match="Identidad de club inconsistente"):
        service.team_ids()


def test_heatmap_counts_only_valid_direct_destinations_after_filters(monkeypatch):
    direct = _corner("direct", "envio", "franja_central")
    direct.end_x, direct.end_y = 120, 80
    second = _corner("second", "envio", "franja_central")
    invalid = _corner("invalid", "envio", "no_disponible", False)
    short = _corner("short", "corto", "no_disponible")
    monkeypatch.setattr(service, "corners_for", lambda run: [direct, second, invalid, short])
    result = service.destination_heatmap(SimpleNamespace())
    assert (result.filtered_corners, result.included, result.excluded_spatial, result.excluded_non_direct) == (4, 2, 1, 1)
    assert sum(cell.count for cell in result.cells) == result.included
    assert sum(group.count for group in result.zones) == result.included
    assert (110, 70, 1) in [(cell.x, cell.y, cell.count) for cell in result.cells]
    filtered = service.destination_heatmap(SimpleNamespace(), delivery="corto")
    assert (filtered.filtered_corners, filtered.included, filtered.excluded_non_direct) == (1, 0, 1)
    assert filtered.max_count == 0 and filtered.cells == []


def test_habit_profile_counts_side_taker_and_match_recurrence(monkeypatch):
    first = _corner("a", "envio", "franja_central")
    first.player_id = 4320
    second = _corner("b", "envio", "franja_central")
    second.match_id = 2
    second.side = "y_alto"
    second.player_id = 4320
    short = _corner("c", "corto", "no_disponible")
    short.match_id = 2
    invalid = _corner("d", "envio", "no_disponible", False)
    monkeypatch.setattr(service, "corners_for", lambda run: [first, second, short, invalid])
    profile = service.habits(SimpleNamespace())
    assert (profile.corners, profile.direct) == (4, 2)
    assert profile.max_match_corners == 2
    assert profile.zones[0].count == 2 and profile.zones[0].matches == 2
    assert profile.takers[0].player_id == 4320
    assert (profile.takers[0].matches, profile.takers[0].short) == (2, 1)
    assert [(side.label, side.corners, side.direct) for side in profile.sides] == [
        ("y_bajo", 3, 1), ("y_alto", 1, 1)
    ]


def test_match_history_carries_club_ids_and_scores_without_reordering(monkeypatch):
    """Display fields are added, but the canonical newest-first window is untouched."""
    dates = ["2016-02-08", "2016-02-01", "2016-01-24", "2016-01-17",
             "2016-01-10", "2016-01-03", "2015-12-27", "2015-12-20"]
    rows = [{"match_id": index, "match_date": date, "kick_off": "20:00:00",
             "home_team": "Barcelona", "away_team": "Sevilla",
             "home_score": 2, "away_score": 1} for index, date in enumerate(dates, start=1)]
    monkeypatch.setattr(service, "query", lambda *args, **kwargs: rows)
    monkeypatch.setattr(service, "team_ids", lambda: {"Barcelona": 217, "Sevilla": 229})

    history = service.matches_for("Barcelona", "2016-03-01", 8)

    assert [match.match_id for match in history] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert (history[0].home_team_id, history[0].away_team_id) == (217, 229)
    assert (history[0].home_score, history[0].away_score) == (2, 1)
    assert MatchProfile(
        **history[0].model_dump(), rival_corners=0, main_takers=[]
    ).home_score == 2
