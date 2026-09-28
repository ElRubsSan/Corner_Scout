from backend.schemas import Claim, Narrative, Report, ReportInput

PLAN = ["Verificar rival y fecha de corte", "Seleccionar ocho partidos anteriores", "Consultar KPIs, patrones y evidencia", "Validar cobertura y limitaciones", "Redactar y validar reporte tactico"]


def destination_label(zone: str) -> str:
    """Describe a pass destination without interpreting it as a shot location."""
    return {
        "franja_cercana": "la zona cercana al punto de cobro",
        "franja_central": "la zona central del área",
        "franja_lejana": "la zona alejada del punto de cobro",
        "fuera_area": "fuera del área",
    }.get(zone, "un destino sin clasificación espacial")


def deterministic(payload: ReportInput, reason: str | None = None) -> Report:
    observations = [Claim(text=f"{e.description}: {e.value}.", evidence_ids=[e.id]) for e in payload.evidence[:8]]
    recommendations = [Claim(text=f"Revisar defensivamente los envíos con destino {destination_label(p.dominant_zone)} y sus ejemplos asociados; no implican una jugada ensayada confirmada.", evidence_ids=[f"cluster-{p.cluster}"]) for p in payload.patterns[:3]]
    return Report(mode="deterministic", fallback_reason=reason, plan=PLAN, input=payload, narrative=Narrative(observations=observations, recommendations=recommendations), sources=["StatsBomb Open Data - LaLiga 2015/16", "https://github.com/statsbomb/open-data"])
