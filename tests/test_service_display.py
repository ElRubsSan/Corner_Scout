from types import SimpleNamespace

from backend import service
from backend.reporting import deterministic
from backend.schemas import Corner, Match, Pattern


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
    assert "fuera del área" in payload.evidence[-1].description
    assert "Patron 3" not in payload.evidence[-1].description
    assert report.narrative.recommendations[0].evidence_ids == ["cluster-3"]
    assert "destino fuera del área" in report.narrative.recommendations[0].text
    assert "la fuera" not in report.narrative.recommendations[0].text
