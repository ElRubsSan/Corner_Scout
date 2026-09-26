"""Provider-independent evidence and tactical report validation.

The language model, when present, is only a renderer.  This module owns the
numbers, provenance checks and deterministic report used when rendering fails.
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Annotated, Iterable, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


EvidenceId = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]+$")]
Number = int | float


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Indicator(StrictModel):
    evidence_id: EvidenceId
    nombre: str = Field(min_length=1)
    numerador: Number | None
    denominador: Number | None
    valor: Number | None
    referencia_liga_previa: Number | None
    cobertura: float = Field(ge=0, le=1)


class EvidenceLimitation(StrictModel):
    evidence_id: EvidenceId
    texto: str = Field(min_length=1)


class ModelEvidence(StrictModel):
    evidence_id: EvidenceId
    objetivo: str = Field(min_length=1)
    modelo_seleccionado: str = Field(min_length=1)
    supero_referencia: bool
    texto: str = Field(min_length=1)


class EvidenceContract(StrictModel):
    rival: str = Field(min_length=1)
    fecha_corte: date
    history_match_ids: tuple[int, ...] = Field(min_length=1, max_length=8)
    indicadores: tuple[Indicator, ...] = Field(min_length=1)
    limitaciones: tuple[EvidenceLimitation, ...] = Field(min_length=1)
    resultados_modelo_promovidos: tuple[ModelEvidence, ...] = ()

    @field_validator("fecha_corte", mode="before")
    @classmethod
    def parse_date(cls, value: object) -> object:
        return date.fromisoformat(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def unique_ids(self) -> "EvidenceContract":
        ids = [item.evidence_id for item in self.all_evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate_evidence_ids")
        if len(self.history_match_ids) != len(set(self.history_match_ids)):
            raise ValueError("duplicate_history_match_ids")
        return self

    @property
    def all_evidence(self) -> tuple[Indicator | EvidenceLimitation | ModelEvidence, ...]:
        return self.indicadores + self.limitaciones + self.resultados_modelo_promovidos


class Finding(StrictModel):
    texto: str = Field(min_length=1)
    tipo: Literal["observación", "interpretación", "revisar"]
    evidence_ids: tuple[EvidenceId, ...] = Field(min_length=1)


class TacticalReport(StrictModel):
    resumen: str = Field(min_length=1)
    hallazgos: tuple[Finding, ...]
    limitaciones: tuple[str, ...]


_HISTORICAL = "Datos historicos de LaLiga 2015/16; no describen el estado actual."
_TRACKING = "Sin video, tracking ni datos 360; no permite inferir acciones defensivas fuera del evento."
_MODEL_LIMIT = "SCR-15 usa tasa historica con denominador porque el modelo candidato no supero la referencia."
_FORBIDDEN = (
    "apuesta",
    "marcador",
    "garantiza",
    "jugada ensayada confirmada",
    "marcaje",
    "movimiento sin balón",
    "movimiento sin balon",
    "sistema táctico",
    "sistema tactico",
)
_NUMERIC = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d+(?:[.,]\d+)?")


def _require_columns(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{name}_missing_columns:{','.join(missing)}")


def _ratio(numerator: Number, denominator: Number) -> float | None:
    return float(numerator / denominator) if denominator else None


def _number(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non_finite_evidence_number")
    return result


def _indicator(
    evidence_id: str,
    name: str,
    numerator: Number | None,
    denominator: Number | None,
    reference: Number | None,
    coverage: float,
) -> Indicator:
    numerator = _number(numerator)
    denominator = _number(denominator)
    return Indicator(
        evidence_id=evidence_id,
        nombre=name,
        numerador=numerator,
        denominador=denominator,
        valor=_ratio(numerator, denominator) if numerator is not None and denominator is not None else None,
        referencia_liga_previa=_number(reference),
        cobertura=float(coverage),
    )


def _team_matches(matches: pd.DataFrame, team: str, cutoff: date) -> pd.DataFrame:
    dates = pd.to_datetime(matches["match_date"], errors="raise").dt.date
    mask = ((matches["home_team"] == team) | (matches["away_team"] == team)) & (dates < cutoff)
    ordered = matches.loc[mask].assign(_date=dates[mask])
    sort = [column for column in ("_date", "kick_off", "match_id") if column in ordered]
    return ordered.sort_values(sort, ascending=False, kind="stable").head(8)


def build_evidence(
    matches: pd.DataFrame,
    corners: pd.DataFrame,
    *,
    rival: str,
    fecha_corte: date | str,
    promoted_models: Iterable[ModelEvidence | dict[str, object]] = (),
) -> EvidenceContract:
    """Build auditable evidence from canonical match and corner frames.

    The cutoff is exclusive and the selected match IDs are provider IDs.  The
    league references use only rows strictly before the same cutoff.
    """
    if isinstance(fecha_corte, str):
        cutoff = datetime.fromisoformat(
            fecha_corte.replace("Z", "+00:00")
        ).date()
    else:
        cutoff = fecha_corte
    if not isinstance(cutoff, date):
        raise TypeError("fecha_corte_must_be_date")
    _require_columns(matches, {"match_id", "match_date", "home_team", "away_team"}, "matches")
    _require_columns(
        corners,
        {"match_id", "team", "valid_sequence", "shot_within_15s", "delivery", "height"},
        "corners",
    )
    if matches["match_id"].duplicated().any():
        raise ValueError("duplicate_match_ids")

    history_matches = _team_matches(matches, rival, cutoff)
    if len(history_matches) != 8:
        raise ValueError(f"history_requires_8_matches:found_{len(history_matches)}")
    history_ids = tuple(int(value) for value in history_matches["match_id"].tolist())
    history = corners[(corners["team"] == rival) & corners["match_id"].isin(history_ids)].copy()
    if history.empty:
        raise ValueError("history_has_no_corners")

    prior_ids = set(matches.loc[pd.to_datetime(matches["match_date"]).dt.date < cutoff, "match_id"])
    league = corners[corners["match_id"].isin(prior_ids)].copy()
    prior_matches = matches[matches["match_id"].isin(prior_ids)]
    team_match_denominator = 2 * len(prior_matches)

    valid = history[history["valid_sequence"].eq(True)]
    league_valid = league[league["valid_sequence"].eq(True)]
    total = len(history)
    league_corners_per_match = _ratio(len(league), team_match_denominator)
    indicators = [
        _indicator("E_CORNERS", "corners_por_partido", total, 8, league_corners_per_match, 1.0),
        _indicator(
            "E_SCR15",
            "tasa_historica_scr15",
            int(valid["shot_within_15s"].eq(True).sum()),
            len(valid),
            _ratio(int(league_valid["shot_within_15s"].eq(True).sum()), len(league_valid)),
            len(valid) / total,
        ),
        _indicator(
            "E_SHORT",
            "proporcion_proxy_corto",
            int(history["delivery"].eq("corto").sum()),
            total,
            _ratio(int(league["delivery"].eq("corto").sum()), len(league)),
            1.0,
        ),
        _indicator(
            "E_HIGH",
            "proporcion_pase_alto",
            int(history["height"].eq("High Pass").sum()),
            total,
            _ratio(int(league["height"].eq("High Pass").sum()), len(league)),
            1.0,
        ),
    ]

    limitations = [
        EvidenceLimitation(evidence_id="L_HISTORICAL", texto=_HISTORICAL),
        EvidenceLimitation(evidence_id="L_TRACKING", texto=_TRACKING),
        EvidenceLimitation(evidence_id="L_SAMPLE", texto="Ventana disponible: 8 de 8 partidos previos."),
        EvidenceLimitation(evidence_id="L_MODEL", texto=_MODEL_LIMIT),
    ]
    if "xg" in history:
        complete = valid[valid["xg"].notna()]
        league_complete = league_valid[league_valid["xg"].notna()]
        indicators.append(
            _indicator(
                "E_XG",
                "xg_descriptivo_por_corner_evaluable_completo",
                complete["xg"].sum(),
                len(complete),
                _ratio(float(league_complete["xg"].sum()), len(league_complete)),
                len(complete) / total,
            )
        )
    else:
        limitations.append(EvidenceLimitation(evidence_id="L_INCOMPLETE", texto="xG no disponible; no debe inferirse."))

    if "zone" in history:
        direct = history[history["delivery"].ne("corto") & history["zone"].notna()]
        league_direct = league[league["delivery"].ne("corto") & league["zone"].notna()]
        if not direct.empty:
            zone = str(direct["zone"].value_counts().index[0])
            indicators.append(
                _indicator(
                    "E_ZONE",
                    f"proporcion_zona_directa_dominante:{zone}",
                    int(direct["zone"].eq(zone).sum()),
                    len(direct),
                    _ratio(int(league_direct["zone"].eq(zone).sum()), len(league_direct)),
                    len(direct) / total,
                )
            )

    models = tuple(
        item if isinstance(item, ModelEvidence) else ModelEvidence.model_validate(item)
        for item in promoted_models
    )
    return EvidenceContract(
        rival=rival,
        fecha_corte=cutoff,
        history_match_ids=history_ids,
        indicadores=tuple(indicators),
        limitaciones=tuple(limitations),
        resultados_modelo_promovidos=models,
    )


def evidence_index(evidence: EvidenceContract) -> dict[str, Indicator | EvidenceLimitation | ModelEvidence]:
    return {item.evidence_id: item for item in evidence.all_evidence}


def numeric_tokens(text: str) -> tuple[float, ...]:
    return tuple(float(token.replace(",", ".")) for token in _NUMERIC.findall(text))


def _display_number(value: Number | None, precision: str = "g") -> str:
    return "no disponible" if value is None else format(value, precision)


def verify_report(
    report: TacticalReport | dict[str, object],
    evidence: EvidenceContract,
    *,
    number_tolerance: float = 0.0005,
) -> TacticalReport:
    """Reject unknown/duplicate citations, unsupported numbers and claims."""
    parsed = report if isinstance(report, TacticalReport) else TacticalReport.model_validate(report)
    known = evidence_index(evidence)
    complete_text = " ".join(
        (parsed.resumen, *(finding.texto for finding in parsed.hallazgos), *parsed.limitaciones)
    ).lower()
    if any(term in complete_text for term in _FORBIDDEN):
        raise ValueError("forbidden_claim")
    for finding in parsed.hallazgos:
        if len(finding.evidence_ids) != len(set(finding.evidence_ids)):
            raise ValueError("duplicate_evidence_ids")
        unknown = sorted(set(finding.evidence_ids) - set(known))
        if unknown:
            raise ValueError("unknown_evidence_ids:" + ",".join(unknown))
        allowed = []
        for evidence_id in finding.evidence_ids:
            item = known[evidence_id]
            if isinstance(item, Indicator):
                allowed.extend(
                    float(value)
                    for value in (item.numerador, item.denominador, item.valor, item.referencia_liga_previa, item.cobertura)
                    if value is not None
                )
        unsupported = [
            value
            for value in numeric_tokens(finding.texto)
            if not any(math.isclose(value, candidate, abs_tol=number_tolerance, rel_tol=0) for candidate in allowed)
        ]
        if unsupported:
            raise ValueError("unsupported_numbers:" + ",".join(format(value, "g") for value in unsupported))
    return parsed


def deterministic_report(evidence: EvidenceContract, *, fallback: bool = True) -> TacticalReport:
    by_id = {item.evidence_id: item for item in evidence.indicadores}
    findings = []
    for evidence_id in ("E_CORNERS", "E_SCR15", "E_SHORT"):
        item = by_id.get(evidence_id)
        if item is None:
            continue
        findings.append(
            Finding(
                texto=(
                    f"{item.nombre}: {_display_number(item.numerador)}/{_display_number(item.denominador)}, "
                    f"valor {_display_number(item.valor, '.4g')}."
                ),
                tipo="observación",
                evidence_ids=(evidence_id,),
            )
        )
    limitations = tuple(item.texto for item in evidence.limitaciones)
    if fallback:
        limitations = ("FALLBACK DETERMINISTA: salida del proveedor no utilizable.",) + limitations
    report = TacticalReport(
        resumen="Reporte historico determinista basado en evidencia validada.",
        hallazgos=tuple(findings),
        limitaciones=limitations,
    )
    return verify_report(report, evidence)
