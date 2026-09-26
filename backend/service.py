"""Read-only canonical analytics, immutable run identities and report evidence."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any

from fastapi import HTTPException

from analytics.io import data_dir, write_json
from analytics.tactical_report import ModelEvidence, build_evidence
from backend.repository import ArtifactError, repository
from backend.schemas import *

LIMITATIONS = [
    "Caso historico LaLiga 2015/16; no informacion actual ni en vivo.",
    "Zonas de destino del pase, no ubicaciones de remate. Sin video ni tracking.",
    "Muestra de ocho partidos; patrones poco frecuentes no prueban jugadas ensayadas.",
    "SCR-15 usa corners evaluables; secuencias excluidas no se consideran negativas.",
    "Los resultados de modelos proceden de la evaluacion temporal canonica; la API no entrena.",
]


def repo():
    try:
        return repository()
    except ArtifactError as exc:
        raise HTTPException(503, f"Artefactos canonicos no disponibles: {exc}") from exc


def query(table: str, where: str = "", params: list[Any] | None = None) -> list[dict[str, Any]]:
    try:
        return repo().rows(table, where, params)
    except ArtifactError as exc:
        raise HTTPException(503, f"Artefacto canonico no disponible: {exc}") from exc


def _text(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _json_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parsed = json.loads(value)
        return [str(item) for item in parsed]
    return [str(item) for item in value]


def teams() -> list[Team]:
    matches = query("matches_clean")
    return [Team(name=name) for name in sorted({row[key] for row in matches for key in ("home_team", "away_team")})]


def matches_for(rival: str | None = None, before: str | None = None, limit: int = 380) -> list[Match]:
    clauses, params = [], []
    if rival:
        if rival not in {team.name for team in teams()}:
            raise HTTPException(404, "Rival desconocido")
        clauses.append("(home_team = ? OR away_team = ?)")
        params.extend((rival, rival))
    if before:
        clauses.append("match_date < ?")
        params.append(before)
    sql = ("WHERE " + " AND ".join(clauses) if clauses else "")
    sql += " ORDER BY match_date DESC, kick_off DESC, match_id DESC LIMIT ?"
    records = query("matches_clean", sql, [*params, limit])
    return [Match(match_id=row["match_id"], match_date=_text(row["match_date"]), kick_off=_text(row["kick_off"]),
                  home_team=row["home_team"], away_team=row["away_team"]) for row in records]


def create_run(request: RunRequest) -> Run:
    canonical = repo()
    cutoff = str(request.cutoff_date) if request.cutoff_date else None
    if request.target_match_id:
        target = query("matches_clean", "WHERE match_id = ?", [request.target_match_id])
        if not target:
            raise HTTPException(404, "Partido objetivo desconocido")
        if request.rival not in (target[0]["home_team"], target[0]["away_team"]):
            raise HTTPException(422, "El rival no participa en el partido objetivo")
        cutoff = _text(target[0]["match_date"])
    if request.analyst and request.analyst not in {team.name for team in teams()}:
        raise HTTPException(404, "Equipo analista desconocido")
    matches = matches_for(request.rival, cutoff, 8)
    if len(matches) != 8:
        raise HTTPException(422, f"Historial insuficiente: {len(matches)} de 8 partidos anteriores")
    if request.expected_match_ids is not None and request.expected_match_ids != [match.match_id for match in matches]:
        raise HTTPException(409, "La ventana confirmada no coincide")
    identity = {
        "rival": request.rival,
        "cutoff": cutoff,
        "analyst": request.analyst,
        "matches": [match.match_id for match in matches],
        "canonical_runs": canonical.identity,
    }
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    run = Run(run_id=run_id, rival=request.rival, analyst=request.analyst, cutoff_date=cutoff,
              matches=matches, dataset_version=canonical.fingerprint, canonical_runs=canonical.identity)
    write_json(data_dir() / "processed" / "runs" / f"{run_id}.json", run.model_dump())
    return run


def get_run(run_id: str) -> Run:
    if len(run_id) != 64 or any(char not in "0123456789abcdef" for char in run_id):
        raise HTTPException(404, "Analisis desconocido")
    path = data_dir() / "processed" / "runs" / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(404, "Analisis desconocido")
    run = Run.model_validate_json(path.read_text(encoding="utf-8"))
    canonical = repo()
    if run.dataset_version != canonical.fingerprint or run.canonical_runs != canonical.identity:
        raise HTTPException(409, "Version canonica distinta; cree otro analisis")
    return run


def _snapshot() -> str:
    contract = repo().contracts["04"]
    parameters = (contract.model_extra or {}).get("parameters", {})
    return str(parameters.get("eda_end_exclusive", contract.run_id))


def corners_for(run: Run) -> list[Corner]:
    ids = [match.match_id for match in run.matches]
    placeholders = ",".join("?" for _ in ids)
    records = query("corners_engineered", f"WHERE team = ? AND match_id IN ({placeholders}) ORDER BY match_date, match_id, index", [run.rival, *ids])
    assignments = query("cluster_assignments")
    labels = {str(row["event_id"]): int(row.get("cluster_id", row.get("cluster"))) for row in assignments}
    centers = query("cluster_centers")
    results = []
    for row in records:
        event_id = str(row["event_id"])
        cluster = labels.get(event_id)
        if cluster is None and bool(row.get("direct_delivery_valid")) and centers:
            end_x = float(row["end_x"])
            end_y_relative = float(row["end_y_relative"])
            cluster = int(
                min(
                    centers,
                    key=lambda center: math.hypot(
                        end_x - float(center["end_x"]),
                        end_y_relative - float(center["end_y_relative"]),
                    ),
                )["cluster_id"]
            )
        side = str(row.get("side") or row.get("corner_side") or "desconocido")
        side = {"left": "y_bajo", "right": "y_alto"}.get(side, side)
        delivery = str(row.get("execution_type") or row.get("delivery") or "desconocido")
        delivery = {"short": "corto", "direct": "envio", "unknown": "desconocido"}.get(
            delivery, delivery
        )
        values = {
            "match_id": int(row["match_id"]), "event_id": event_id,
            "player": str(row.get("player") or "Desconocido"),
            "x": float(row["x"]), "y": float(row["y"]), "end_x": float(row["end_x"]), "end_y": float(row["end_y"]),
            "side": side,
            "delivery": delivery,
            "zone": str(row.get("delivery_zone") or row.get("zone") or "no_disponible"),
            "height": str(row.get("height") or "No disponible"),
            "shot_within_15s": row.get("shot_within_15s"),
            "xg": row.get("xg_sequence", row.get("xg")),
            "valid_sequence": bool(row["valid_sequence"]),
            "spatial_valid": bool(row.get("spatial_valid", row.get("valid_geometry", False))),
            "end_reason": str(row["end_reason"]), "shot_ids": _json_list(row.get("shot_ids")),
            "restart_ids": _json_list(row.get("restart_ids")),
            "possession_change_ids": _json_list(row.get("possession_change_ids")), "cluster": cluster,
        }
        results.append(Corner(**values))
    return results


def groups(corners: list[Corner], field: str) -> list[Group]:
    return [Group(label=key, count=count) for key, count in Counter(getattr(item, field) for item in corners).most_common()]


def summary(run: Run) -> Summary:
    corners = corners_for(run)
    valid = [corner for corner in corners if corner.valid_sequence]
    history = query("corners_engineered", "WHERE match_date < ? AND valid_sequence = true", [run.cutoff_date])
    probability = sum(bool(row["shot_within_15s"]) for row in history) / len(history) if history else None
    xg_values = [corner.xg for corner in valid if corner.xg is not None]
    return Summary(rival=run.rival, cutoff_date=run.cutoff_date, matches=len(run.matches), corners=len(corners),
                   evaluable_corners=len(valid), excluded_corners=len(corners) - len(valid),
                   shots=sum(bool(corner.shot_within_15s) for corner in valid),
                   scr15=sum(bool(corner.shot_within_15s) for corner in valid) / len(valid) if valid else None,
                   xg_per_corner=sum(xg_values) / len(valid) if valid and len(xg_values) == len(valid) else None,
                   probability=probability, probability_method="ganador_canonico_05_con_referencia_historica",
                   players=groups(corners, "player"), sides=groups(corners, "side"),
                   deliveries=groups(corners, "delivery"), zones=groups(corners, "zone"))


def patterns(run: Run) -> list[Pattern]:
    corners = corners_for(run)
    result = []
    for label in sorted({corner.cluster for corner in corners if corner.cluster is not None}):
        members = [corner for corner in corners if corner.cluster == label]
        valid = [corner for corner in members if corner.valid_sequence]
        xg_values = [corner.xg for corner in valid if corner.xg is not None]
        result.append(Pattern(cluster=label, count=len(members), evaluable=len(valid),
                              scr15=sum(bool(corner.shot_within_15s) for corner in valid) / len(valid) if valid else None,
                              xg_per_corner=sum(xg_values) / len(valid) if valid and len(xg_values) == len(valid) else None,
                              dominant_zone=groups(members, "zone")[0].label, main_taker=groups(members, "player")[0].label,
                              example_event_ids=[corner.event_id for corner in members[:3]], snapshot=_snapshot()))
    return sorted(result, key=lambda item: -item.count)


def quality(run: Run) -> Quality:
    canonical = repo()
    contract03 = canonical.contracts["03"]
    metadata = contract03.model_extra or {}
    corners = corners_for(run)
    return Quality(processed_at=contract03.run_id, source_manifest_sha256=canonical.fingerprint,
                   rule_version=str(metadata["rule_version"]), coverage_matches=int(metadata["counts"]["matches"]),
                   coverage_events=int(metadata["counts"]["events"]),
                   excluded_sequences=sum(not corner.valid_sequence for corner in corners),
                   excluded_spatial=sum(not corner.spatial_valid for corner in corners), limitations=LIMITATIONS)


def model_result(run: Run) -> ModelResult:
    result = summary(run)
    winners = query("objective_winners")
    metrics = query("temporal_metrics")
    return ModelResult(
        served=result.probability_method,
        probability=result.probability,
        evaluation_scope="Evaluacion temporal canonica 05; sin entrenamiento por solicitud",
        evaluations=ModelEvaluation(
            objective_winners=[ObjectiveWinner.model_validate(row) for row in winners],
            temporal_metrics=[TemporalMetric.model_validate(row) for row in metrics],
        ),
    )


def report_input(run: Run) -> ReportInput:
    result, pattern_rows = summary(run), patterns(run)
    evidence = [Evidence(id="scr15", description="SCR-15 observado", value=f"{result.scr15:.3f}" if result.scr15 is not None else "No evaluable"),
                Evidence(id="corners", description="Corners totales", value=str(result.corners)),
                Evidence(id="xg", description="xG por corner evaluable", value=f"{result.xg_per_corner:.4f}" if result.xg_per_corner is not None else "No evaluable")]
    evidence.extend(Evidence(id=f"cluster-{item.cluster}", description=f"Patron {item.cluster}, zona {item.dominant_zone}", value=str(item.count), event_ids=item.example_event_ids) for item in pattern_rows)
    return ReportInput(rival=run.rival, cutoff_date=run.cutoff_date, matches=run.matches, summary=result,
                       patterns=pattern_rows, evidence=evidence, limitations=LIMITATIONS)


def agent_evidence(run: Run):
    matches = repo().frame("matches_clean")
    corners = repo().frame("corners_engineered").copy()
    if "delivery" not in corners:
        corners["delivery"] = corners["execution_type"].map(
            {"short": "corto", "direct": "envio", "unknown": "desconocido"}
        )
    if "xg" not in corners and "xg_sequence" in corners:
        corners["xg"] = corners["xg_sequence"]
    if "zone" not in corners and "delivery_zone" in corners:
        corners["zone"] = corners["delivery_zone"]
    promoted = []
    for row in query("objective_winners"):
        objective = str(row["objective"])
        winner = str(row["winner"])
        promoted.append(ModelEvidence(evidence_id="M_" + objective.upper(), objetivo=objective,
                                      modelo_seleccionado=winner, supero_referencia=winner == "candidate",
                                      texto=str(row.get("justification") or f"Ganador canonico: {winner}.")))
    return build_evidence(matches, corners, rival=run.rival, fecha_corte=run.cutoff_date, promoted_models=promoted)
