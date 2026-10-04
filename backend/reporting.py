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
    observations = [Claim(text=(f"{payload.summary.shots} de {payload.summary.evaluable_corners} córners evaluables terminaron en tiro "
                               f"({payload.summary.scr15 * 100:.1f} %)."), evidence_ids=["scr15"])] if payload.summary.scr15 is not None else []
    zones = [item for item in payload.evidence if item.id.startswith("zone-")]
    if zones:
        item = zones[0]
        observations.append(Claim(text=f"{item.description}: {item.value}.", evidence_ids=[item.id]))
    if payload.patterns:
        pattern = payload.patterns[0]
        observations.append(Claim(text=f"{pattern.display_name} reúne {pattern.count} envíos con destinos similares. Cobrador más frecuente: {pattern.main_taker}.",
                                  evidence_ids=[f"cluster-{pattern.cluster}"]))
    for item in zones[1:]:
        observations.append(Claim(text=f"{item.description}: {item.value}.", evidence_ids=[item.id]))
    for pattern in payload.patterns[1:]:
        observations.append(Claim(text=f"{pattern.display_name} reúne {pattern.count} envíos con destinos similares. Cobrador más frecuente: {pattern.main_taker}.", evidence_ids=[f"cluster-{pattern.cluster}"]))
    observations = observations[:6]
    recommendations = [Claim(text=f"Revisar en vídeo los {p.count} envíos del grupo «{p.display_name}»: identificar dónde termina el pase y cómo continúa la acción.", evidence_ids=[f"cluster-{p.cluster}"]) for p in payload.patterns[:3]]
    return Report(mode="deterministic", fallback_reason=reason, plan=PLAN, input=payload, narrative=Narrative(observations=observations, recommendations=recommendations), sources=["StatsBomb Open Data - LaLiga 2015/16", "https://github.com/statsbomb/open-data"])
