"""Read-only analytical queries, immutable run identities and report evidence."""
import hashlib
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

import duckdb
from fastapi import HTTPException

from analytics.io import data_dir, write_json
from backend.schemas import *

LIMITATIONS = ["Caso historico LaLiga 2015/16; no informacion actual ni en vivo.",
              "Zonas de destino del pase, no ubicaciones de remate. Sin video ni tracking.",
              "Muestra de ocho partidos; patrones poco frecuentes no prueban jugadas ensayadas.",
              "SCR-15 usa corners evaluables; secuencias con reloj invalido se excluyen, no se consideran negativas.",
              "Regresion logistica y Random Forest no superaron consistentemente el baseline; se sirve tasa historica."]


def query(table: str, where: str = "", params: list | None = None) -> list[dict]:
    if table not in {"matches", "corners", "clusters"}:
        raise ValueError("Unknown analytical table")
    path = data_dir() / "processed" / f"{table}.parquet"
    if not path.exists():
        raise HTTPException(503, "Faltan datos procesados. Ejecute ingest, build y train.")
    # In-memory connection is request-local. Only SELECT on immutable Parquet.
    with duckdb.connect(":memory:") as connection:
        result = connection.execute(f"SELECT * FROM read_parquet(?) {where}", [str(path), *(params or [])])
        columns = [c[0] for c in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]


def quality_data() -> dict:
    path = data_dir() / "processed/quality.json"
    if not path.exists():
        raise HTTPException(503, "Falta auditoria de datos")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload["passed"]:
        raise HTTPException(503, "La auditoria no permite publicar resultados")
    return payload


def teams() -> list[Team]:
    matches = query("matches")
    return [Team(name=t) for t in sorted({m[s] for m in matches for s in ("home_team", "away_team")})]


def matches_for(rival: str | None = None, before: str | None = None, limit: int = 380) -> list[Match]:
    where, params = [], []
    if rival:
        if rival not in {t.name for t in teams()}:
            raise HTTPException(404, "Rival desconocido")
        where.append("(home_team = ? OR away_team = ?)")
        params += [rival, rival]
    if before:
        where.append("match_date < ?")
        params.append(before)
    sql = ("WHERE " + " AND ".join(where) if where else "") + " ORDER BY match_date DESC, kick_off DESC, match_id DESC LIMIT ?"
    return [Match(**{k: m[k] for k in Match.model_fields}) for m in query("matches", sql, [*params, limit])]


def create_run(request: RunRequest) -> Run:
    q = quality_data()
    cutoff = str(request.cutoff_date) if request.cutoff_date else None
    if request.target_match_id:
        target = query("matches", "WHERE match_id = ?", [request.target_match_id])
        if not target:
            raise HTTPException(404, "Partido objetivo desconocido")
        if request.rival not in (target[0]["home_team"], target[0]["away_team"]):
            raise HTTPException(422, "El rival no participa en el partido objetivo")
        cutoff = target[0]["match_date"]
    if request.analyst and request.analyst not in {t.name for t in teams()}:
        raise HTTPException(404, "Equipo analista desconocido")
    matches = matches_for(request.rival, cutoff, 8)
    if len(matches) != 8:
        raise HTTPException(422, f"Historial insuficiente: {len(matches)} de 8 partidos anteriores")
    if request.expected_match_ids is not None and request.expected_match_ids != [m.match_id for m in matches]:
        raise HTTPException(409, "La ventana confirmada no coincide")
    identity = {"rival": request.rival, "cutoff": cutoff, "analyst": request.analyst, "matches": [m.match_id for m in matches], "dataset": q["source_manifest_sha256"], "rule": q["rule_version"], "model": "v0.3"}
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    run = Run(run_id=run_id, rival=request.rival, analyst=request.analyst, cutoff_date=cutoff, matches=matches, dataset_version=q["source_manifest_sha256"])
    write_json(data_dir() / "processed/runs" / f"{run_id}.json", run.model_dump())
    return run


def get_run(run_id: str) -> Run:
    if len(run_id) != 64 or any(c not in "0123456789abcdef" for c in run_id):
        raise HTTPException(404, "Analisis desconocido")
    path = data_dir() / "processed/runs" / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(404, "Analisis desconocido")
    run = Run.model_validate_json(path.read_text(encoding="utf-8"))
    if run.dataset_version != quality_data()["source_manifest_sha256"]:
        raise HTTPException(409, "Version de datos distinta; cree otro analisis")
    return run


def snapshot(cutoff: str) -> str | None:
    rows = query("clusters", "WHERE available_from <= ? ORDER BY available_from DESC LIMIT 1", [cutoff])
    return rows[0]["available_from"] if rows else None


def corners_for(run: Run) -> list[Corner]:
    ids = [m.match_id for m in run.matches]
    records = query("corners", f"WHERE team = ? AND match_id IN ({','.join('?' for _ in ids)}) ORDER BY match_date, match_id, index", [run.rival, *ids])
    current = snapshot(run.cutoff_date)
    labels = {r["event_id"]: r["cluster"] for r in query("clusters", "WHERE available_from = ?", [current])} if current else {}
    # All assignments use centers fitted strictly before the snapshot date.
    results = []
    for row in records:
        values = {k: row[k] for k in Corner.model_fields if k in row}
        for field in ["shot_ids", "restart_ids", "possession_change_ids"]:
            values[field] = json.loads(values[field])
        values["cluster"] = labels.get(row["event_id"])
        results.append(Corner(**values))
    return results


def groups(corners: list[Corner], field: str) -> list[Group]:
    return [Group(label=k, count=v) for k, v in Counter(getattr(c, field) for c in corners).most_common()]


def summary(run: Run) -> Summary:
    corners = corners_for(run)
    valid = [c for c in corners if c.valid_sequence]
    # Descriptive historical league baseline strictly prior to this cutoff.
    history = query("corners", "WHERE match_date < ? AND valid_sequence = true", [run.cutoff_date])
    probability = sum(bool(c["shot_within_15s"]) for c in history) / len(history) if history else None
    return Summary(rival=run.rival, cutoff_date=run.cutoff_date, matches=8, corners=len(corners), evaluable_corners=len(valid), excluded_corners=len(corners)-len(valid), shots=sum(bool(c.shot_within_15s) for c in valid), scr15=sum(bool(c.shot_within_15s) for c in valid)/len(valid) if valid else None,
                   xg_per_corner=sum(c.xg for c in valid)/len(valid) if valid else None, probability=probability, probability_method="baseline_liga_anterior_al_corte", players=groups(corners,"player"), sides=groups(corners,"side"), deliveries=groups(corners,"delivery"), zones=groups(corners,"zone"))


def patterns(run: Run) -> list[Pattern]:
    corners = corners_for(run)
    result = []
    for label in sorted({c.cluster for c in corners if c.cluster is not None}):
        members = [c for c in corners if c.cluster == label]
        valid = [c for c in members if c.valid_sequence]
        result.append(Pattern(cluster=label, count=len(members), evaluable=len(valid), scr15=sum(bool(c.shot_within_15s) for c in valid)/len(valid) if valid else None, xg_per_corner=sum(c.xg for c in valid)/len(valid) if valid else None, dominant_zone=groups(members,"zone")[0].label, main_taker=groups(members,"player")[0].label, example_event_ids=[c.event_id for c in members[:3]], snapshot=snapshot(run.cutoff_date)))
    return sorted(result, key=lambda p: -p.count)


def quality(run: Run) -> Quality:
    q = quality_data()
    corners = corners_for(run)
    return Quality(processed_at=q["processed_at"], source_manifest_sha256=q["source_manifest_sha256"], rule_version=q["rule_version"], coverage_matches=q["matches"], coverage_events=q["events"], excluded_sequences=sum(not c.valid_sequence for c in corners), excluded_spatial=sum(not c.spatial_valid for c in corners), limitations=LIMITATIONS)


def report_input(run: Run) -> ReportInput:
    s, p = summary(run), patterns(run)
    evidence = [Evidence(id="scr15", description="SCR-15 observado", value=f"{s.scr15:.3f}" if s.scr15 is not None else "No evaluable"), Evidence(id="corners", description="Corners totales", value=str(s.corners)), Evidence(id="xg", description="xG por corner evaluable", value=f"{s.xg_per_corner:.4f}" if s.xg_per_corner is not None else "No evaluable")]
    evidence += [Evidence(id=f"cluster-{v.cluster}", description=f"Patron {v.cluster}, zona {v.dominant_zone}", value=str(v.count), event_ids=v.example_event_ids) for v in p]
    return ReportInput(rival=run.rival, cutoff_date=run.cutoff_date, matches=run.matches, summary=s, patterns=p, evidence=evidence, limitations=LIMITATIONS)
