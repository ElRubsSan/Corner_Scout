import json
import os
from datetime import date
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from analytics.io import data_dir
from backend import service
from backend.schemas import *
from backend.reporting import deterministic, PLAN

app = FastAPI(title="CornerScout", version="0.4.0", description="StatsBomb Open Data. Analisis historico de LaLiga 2015/16.")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORNERSCOUT_ORIGINS", "http://localhost:4200").split(","), allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
PREFIX = "/api/v1"


@app.get(PREFIX + "/health", operation_id="health")
def health() -> dict[str, str]:
    return {"status": "ok", "product": "CornerScout"}


@app.get(PREFIX + "/teams", operation_id="getTeams")
def teams() -> list[Team]:
    return service.teams()


@app.get(PREFIX + "/matches", operation_id="getMatches")
def matches(rival: str | None = None, before: date | None = None, limit: int = Query(380, ge=1, le=380)) -> list[Match]:
    return service.matches_for(rival, str(before) if before else None, limit)


@app.post(PREFIX + "/scouting-runs", status_code=201, operation_id="createRun")
def create_run(request: RunRequest) -> Run:
    return service.create_run(request)


@app.get(PREFIX + "/scouting-runs/{run_id}", operation_id="getRun")
def get_run(run_id: str) -> Run:
    return service.get_run(run_id)


@app.get(PREFIX + "/scouting-runs/{run_id}/summary", operation_id="getSummary")
def summary(run_id: str) -> Summary:
    return service.summary(service.get_run(run_id))


@app.get(PREFIX + "/scouting-runs/{run_id}/corners", operation_id="getCorners")
def corners(run_id: str, player: str | None = None, side: str | None = None, delivery: str | None = None, cluster: int | None = None, offset: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=1000)) -> list[Corner]:
    rows = service.corners_for(service.get_run(run_id))
    rows = [c for c in rows if all(value is None or getattr(c, field) == value for field, value in {"player": player, "side": side, "delivery": delivery, "cluster": cluster}.items())]
    return rows[offset:offset+limit]


@app.get(PREFIX + "/scouting-runs/{run_id}/patterns", operation_id="getPatterns")
def patterns(run_id: str) -> list[Pattern]:
    return service.patterns(service.get_run(run_id))


@app.get(PREFIX + "/scouting-runs/{run_id}/quality", operation_id="getQuality")
def quality(run_id: str) -> Quality:
    return service.quality(service.get_run(run_id))


@app.get(PREFIX + "/scouting-runs/{run_id}/model", operation_id="getModel")
def model(run_id: str) -> ModelResult:
    result = service.summary(service.get_run(run_id))
    evaluation = json.loads((data_dir() / "processed/model-evaluation.json").read_text(encoding="utf-8"))
    return ModelResult(served=result.probability_method, probability=result.probability, evaluation_scope="Retrospectiva de temporada; no se usa para inferir en cortes anteriores", evaluations=evaluation)


@app.get(PREFIX + "/scouting-runs/{run_id}/report-plan", operation_id="getReportPlan")
def report_plan(run_id: str) -> list[str]:
    service.get_run(run_id)
    return PLAN


@app.post(PREFIX + "/scouting-runs/{run_id}/report", operation_id="createReport")
def report(run_id: str) -> Report:
    return deterministic(service.report_input(service.get_run(run_id)))
