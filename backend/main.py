import os
from datetime import date
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from backend import service
from backend.schemas import *
from backend.reporting import deterministic, PLAN

app = FastAPI(title="CornerScout", version="0.7.0", description="StatsBomb Open Data. Analisis historico de LaLiga 2015/16.")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORNERSCOUT_ORIGINS", "http://localhost:4200").split(","), allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
PREFIX = "/api/v1"
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Recurso no encontrado"}}
CONFLICT = {409: {"model": ErrorResponse, "description": "Conflicto con la version o ventana canonica"}}
INVALID = {422: {"model": ErrorResponse, "description": "Solicitud no procesable"}}
UNAVAILABLE = {503: {"model": ErrorResponse, "description": "Artefactos canonicos no disponibles"}}


@app.get(PREFIX + "/health", operation_id="health")
def health() -> dict[str, str]:
    return {"status": "ok", "product": "CornerScout"}


@app.get(PREFIX + "/teams", operation_id="getTeams", responses=UNAVAILABLE)
def teams() -> list[Team]:
    return service.teams()


@app.get(PREFIX + "/matches", operation_id="getMatches", responses={**NOT_FOUND, **INVALID, **UNAVAILABLE})
def matches(rival: str | None = None, before: date | None = None, limit: int = Query(380, ge=1, le=380)) -> list[Match]:
    return service.matches_for(rival, str(before) if before else None, limit)


@app.post(
    PREFIX + "/scouting-runs",
    status_code=201,
    operation_id="createRun",
    responses={**NOT_FOUND, **CONFLICT, **INVALID, **UNAVAILABLE},
)
def create_run(request: RunRequest) -> Run:
    return service.create_run(request)


@app.get(PREFIX + "/scouting-runs/{run_id}", operation_id="getRun", responses={**NOT_FOUND, **CONFLICT, **UNAVAILABLE})
def get_run(run_id: str) -> Run:
    return service.get_run(run_id)


@app.get(PREFIX + "/scouting-runs/{run_id}/summary", operation_id="getSummary", responses={**NOT_FOUND, **CONFLICT, **UNAVAILABLE})
def summary(run_id: str) -> Summary:
    return service.summary(service.get_run(run_id))


@app.get(PREFIX + "/scouting-runs/{run_id}/corners", operation_id="getCorners", responses={**NOT_FOUND, **CONFLICT, **INVALID, **UNAVAILABLE})
def corners(run_id: str, player: str | None = None, side: str | None = None, delivery: str | None = None, cluster: int | None = None, offset: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=1000)) -> list[Corner]:
    rows = service.corners_for(service.get_run(run_id))
    rows = [c for c in rows if all(value is None or getattr(c, field) == value for field, value in {"player": player, "side": side, "delivery": delivery, "cluster": cluster}.items())]
    return rows[offset:offset+limit]


@app.get(PREFIX + "/scouting-runs/{run_id}/patterns", operation_id="getPatterns", responses={**NOT_FOUND, **CONFLICT, **UNAVAILABLE})
def patterns(run_id: str) -> list[Pattern]:
    return service.patterns(service.get_run(run_id))


@app.get(PREFIX + "/scouting-runs/{run_id}/quality", operation_id="getQuality", responses={**NOT_FOUND, **CONFLICT, **UNAVAILABLE})
def quality(run_id: str) -> Quality:
    return service.quality(service.get_run(run_id))


@app.get(PREFIX + "/scouting-runs/{run_id}/model", operation_id="getModel", responses={**NOT_FOUND, **CONFLICT, **UNAVAILABLE})
def model(run_id: str) -> ModelResult:
    return service.model_result(service.get_run(run_id))


@app.get(PREFIX + "/scouting-runs/{run_id}/report-plan", operation_id="getReportPlan", responses={**NOT_FOUND, **CONFLICT, **UNAVAILABLE})
def report_plan(run_id: str) -> list[str]:
    service.get_run(run_id)
    return PLAN


@app.post(PREFIX + "/scouting-runs/{run_id}/report", operation_id="createReport", responses={**NOT_FOUND, **CONFLICT, **UNAVAILABLE})
def report(run_id: str) -> Report:
    from backend.openai import generate
    return generate(service.report_input(service.get_run(run_id)))


@app.post(PREFIX + "/scouting-runs/{run_id}/agent", operation_id="askAgent", responses={**NOT_FOUND, **CONFLICT, **INVALID, **UNAVAILABLE})
def ask_agent(run_id: str, request: AgentRequest) -> AgentResponse:
    from backend.agent import answer
    return answer(service.get_run(run_id), request.question)
