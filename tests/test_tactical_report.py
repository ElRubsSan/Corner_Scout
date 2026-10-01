from datetime import date

import pandas as pd
import pytest
from pydantic import ValidationError

from analytics.tactical_report import (
    EvidenceContract,
    Finding,
    TacticalReport,
    build_evidence,
    deterministic_report,
    verify_report,
)


def frames():
    matches = pd.DataFrame(
        {
            "match_id": range(1, 10),
            "match_date": pd.date_range("2016-01-01", periods=9).astype(str),
            "kick_off": ["20:00"] * 9,
            "home_team": ["Barcelona"] * 9,
            "away_team": [f"Team {i}" for i in range(9)],
        }
    )
    corners = pd.DataFrame(
        {
            "match_id": range(1, 10),
            "team": ["Barcelona"] * 9,
            "valid_sequence": [True] * 9,
            "shot_within_15s": [True, False] * 4 + [True],
            "delivery": ["corto", "envio"] * 4 + ["envio"],
            "height": ["High Pass", "Low Pass"] * 4 + ["High Pass"],
            "xg": [0.1] * 9,
            "zone": ["centro"] * 9,
        }
    )
    return matches, corners


@pytest.fixture()
def evidence():
    matches, corners = frames()
    return build_evidence(matches, corners, rival="Barcelona", fecha_corte="2016-01-10")


def test_build_uses_eight_strictly_previous_provider_ids(evidence):
    assert evidence.fecha_corte == date(2016, 1, 10)
    assert evidence.history_match_ids == (9, 8, 7, 6, 5, 4, 3, 2)
    assert {item.evidence_id for item in evidence.indicadores} == {
        "E_CORNERS", "E_SCR15", "E_SHORT", "E_HIGH", "E_XG", "E_ZONE"
    }


def test_contracts_are_strict_and_frozen(evidence):
    with pytest.raises(ValidationError):
        EvidenceContract.model_validate({**evidence.model_dump(), "unexpected": True})
    with pytest.raises(ValidationError):
        evidence.rival = "Other"


def test_deterministic_fallback_is_verified(evidence):
    report = deterministic_report(evidence)
    assert report.hallazgos[0].evidence_ids == ("E_CORNERS",)
    assert report.limitaciones[0].startswith("FALLBACK DETERMINISTA")


def test_verification_rejects_unknown_id_and_number(evidence):
    base = TacticalReport(resumen="Historico.", hallazgos=(), limitaciones=())
    bad_id = base.model_copy(update={"hallazgos": (Finding(texto="Texto.", tipo="observación", evidence_ids=("E_FAKE",)),)})
    with pytest.raises(ValueError, match="unknown_evidence_ids"):
        verify_report(bad_id, evidence)
    bad_number = base.model_copy(update={"hallazgos": (Finding(texto="999 corners.", tipo="observación", evidence_ids=("E_CORNERS",)),)})
    with pytest.raises(ValueError, match="unsupported_numbers"):
        verify_report(bad_number, evidence)


def test_verification_rejects_forbidden_claim(evidence):
    report = TacticalReport(resumen="Garantiza una apuesta.", hallazgos=(), limitaciones=())
    with pytest.raises(ValueError, match="forbidden_claim"):
        verify_report(report, evidence)


def test_missing_history_is_rejected():
    matches, corners = frames()
    with pytest.raises(ValueError, match="history_requires_8_matches"):
        build_evidence(matches, corners, rival="Barcelona", fecha_corte="2016-01-05")


@pytest.mark.parametrize("cutoff", ["2016-01-09", "2016-01-10"])
@pytest.mark.parametrize("incomplete", [False, True])
def test_record_runtime_matches_dataframe_evidence(cutoff, incomplete):
    from analytics.record_evidence import build_record_evidence

    matches, corners = frames()
    if incomplete:
        corners.loc[2, "valid_sequence"] = False
        corners.loc[3, "xg"] = None
        corners.loc[4, "zone"] = None
    expected = build_evidence(matches, corners, rival="Barcelona", fecha_corte=cutoff)
    records = corners.astype(object).where(corners.notna(), None).to_dict("records")
    actual = build_record_evidence(matches.to_dict("records"), records,
                                  rival="Barcelona", fecha_corte=date.fromisoformat(cutoff))
    assert actual.history_match_ids == expected.history_match_ids
    assert actual.limitaciones == expected.limitaciones
    for observed, reference in zip(actual.indicadores, expected.indicadores, strict=True):
        assert observed.model_dump(exclude={"numerador", "valor", "referencia_liga_previa"}) == reference.model_dump(exclude={"numerador", "valor", "referencia_liga_previa"})
        for field in ("numerador", "valor", "referencia_liga_previa"):
            assert getattr(observed, field) == pytest.approx(getattr(reference, field))


@pytest.mark.parametrize("rival", ["Barcelona", "Real Madrid", "Atlético Madrid"])
@pytest.mark.parametrize("cutoff", ["2016-03-01", "2016-05-14"])
def test_record_runtime_matches_canonical_evidence(rival, cutoff):
    from analytics.io import data_dir
    from analytics.record_evidence import build_record_evidence
    from backend.repository import CanonicalRepository

    if not (data_dir() / "processed/05_modeling/contract.json").exists():
        pytest.skip("canonical local data required")
    repo = CanonicalRepository()
    matches = repo.rows("matches_clean")
    corners = repo.rows("corners_engineered")
    for row in corners:
        row["delivery"] = {"short": "corto", "direct": "envio", "unknown": "desconocido"}.get(row["execution_type"])
        row["xg"] = row["xg_sequence"]
        row["zone"] = row["delivery_zone"]
    expected = build_evidence(pd.DataFrame(matches), pd.DataFrame(corners), rival=rival, fecha_corte=cutoff)
    actual = build_record_evidence(matches, corners, rival=rival, fecha_corte=cutoff)
    assert actual.history_match_ids == expected.history_match_ids
    assert actual.limitaciones == expected.limitaciones
    for observed, reference in zip(actual.indicadores, expected.indicadores, strict=True):
        assert observed.evidence_id == reference.evidence_id
        assert observed.nombre == reference.nombre
        for field in ("numerador", "denominador", "valor", "referencia_liga_previa", "cobertura"):
            assert getattr(observed, field) == pytest.approx(getattr(reference, field))
