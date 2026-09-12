from backend.schemas import Claim, Narrative, Report, ReportInput

PLAN = ["Verificar rival y fecha de corte", "Seleccionar ocho partidos anteriores", "Consultar KPIs, patrones y evidencia", "Validar cobertura y limitaciones", "Redactar y validar reporte tactico"]


def deterministic(payload: ReportInput, reason: str | None = None) -> Report:
    observations = [Claim(text=f"{e.description}: {e.value}.", evidence_ids=[e.id]) for e in payload.evidence[:8]]
    recommendations = [Claim(text=f"Revisar defensivamente la zona {p.dominant_zone} y los ejemplos asociados al patron; no implica una jugada ensayada confirmada.", evidence_ids=[f"cluster-{p.cluster}"]) for p in payload.patterns[:3]]
    return Report(mode="deterministic", fallback_reason=reason, plan=PLAN, input=payload, narrative=Narrative(observations=observations, recommendations=recommendations), sources=["StatsBomb Open Data — LaLiga 2015/16", "https://github.com/statsbomb/open-data"])
