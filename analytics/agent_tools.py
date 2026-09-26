"""Three bounded, read-only tools over an immutable evidence session."""

from __future__ import annotations

import json
import re
import time
from datetime import date
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from analytics.tactical_report import (
    EvidenceContract,
    EvidenceLimitation,
    Indicator,
    ModelEvidence,
    TacticalReport,
    evidence_index,
    numeric_tokens,
)


MAX_TOOL_CALLS = 4
MAX_WALL_SECONDS = 45.0
MAX_SESSION_TOKENS = 12000
MAX_REAL_TURNS = 4


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class SessionArgs(StrictModel):
    rival: str = Field(min_length=1)
    fecha_corte: date

    @field_validator("fecha_corte", mode="before")
    @classmethod
    def parse_date(cls, value: object) -> object:
        return date.fromisoformat(value) if isinstance(value, str) else value


class EvidenceArgs(StrictModel):
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=12)

    @field_validator("evidence_ids", mode="before")
    @classmethod
    def freeze_ids(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


class AgentSession(StrictModel):
    evidence: EvidenceContract
    report: TacticalReport | None = None


class Budget(StrictModel):
    max_calls: int = Field(default=MAX_TOOL_CALLS, gt=0)
    max_seconds: float = Field(default=MAX_WALL_SECONDS, gt=0)
    max_session_tokens: int = Field(default=MAX_SESSION_TOKENS, gt=0)
    max_real_turns: int = Field(default=MAX_REAL_TURNS, gt=0)


class ToolTrace(StrictModel):
    kind: Literal["tool"] = "tool"
    tool: str
    arguments: dict[str, Any]
    arguments_validated: bool
    status: Literal["ok", "error"]
    result_summary: dict[str, Any] | None = None
    error_type: str | None = None
    error_code: str | None = None
    latency_ms: float = Field(ge=0)


class AgentState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, arbitrary_types_allowed=True)
    started_at: float = Field(default_factory=time.perf_counter)
    calls_used: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    traces: list[ToolTrace] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    failure_injection: frozenset[str] = frozenset()


class AgentAnswer(StrictModel):
    status: Literal["answered", "out_of_scope", "error"]
    answer: str = Field(min_length=1, max_length=4000)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=12)
    tool_calls: int = Field(ge=0)

    @field_validator("evidence_ids", mode="before")
    @classmethod
    def freeze_ids(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


class AgentDraft(StrictModel):
    status: Literal["answered", "out_of_scope", "error"]
    qualitative_answer: str = Field(min_length=1, max_length=4000)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=12)
    tool_calls: int = Field(ge=0)

    @field_validator("evidence_ids", mode="before")
    @classmethod
    def freeze_ids(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


class ToolError(RuntimeError):
    pass


class ScopeError(ToolError):
    pass


class BudgetError(ToolError):
    pass


EvidenceItem = Indicator | EvidenceLimitation | ModelEvidence
ToolHandler = Callable[[BaseModel, AgentSession], dict[str, Any]]


class ToolSpec(StrictModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, arbitrary_types_allowed=True)
    name: str
    description: str
    args_model: type[BaseModel]
    handler: ToolHandler
    read_only: Literal[True] = True


def create_session(evidence: EvidenceContract, report: TacticalReport | None = None) -> AgentSession:
    return AgentSession(evidence=evidence, report=report)


def _require_session(args: SessionArgs, session: AgentSession) -> None:
    if args.rival != session.evidence.rival:
        raise ScopeError("rival_locked_to_session")
    if args.fecha_corte != session.evidence.fecha_corte:
        raise ScopeError("cutoff_locked_to_session")


def obtener_historial(args: SessionArgs, session: AgentSession) -> dict[str, Any]:
    _require_session(args, session)
    ids = session.evidence.history_match_ids
    return {
        "rival": session.evidence.rival,
        "fecha_corte": session.evidence.fecha_corte.isoformat(),
        "history_match_ids": list(ids),
        "n_partidos": len(ids),
        "evidence_ids": ["L_SAMPLE"],
    }


def obtener_perfil_corners(args: SessionArgs, session: AgentSession) -> dict[str, Any]:
    _require_session(args, session)
    evidence = session.evidence
    return {
        "rival": evidence.rival,
        "fecha_corte": evidence.fecha_corte.isoformat(),
        "indicadores": [item.model_dump(mode="json") for item in evidence.indicadores],
        "limitaciones": [item.model_dump(mode="json") for item in evidence.limitaciones],
        "modelos_promovidos": [item.model_dump(mode="json") for item in evidence.resultados_modelo_promovidos],
        "evidence_ids": sorted(evidence_index(evidence)),
    }


def consultar_evidencia(args: EvidenceArgs, session: AgentSession) -> dict[str, Any]:
    known = evidence_index(session.evidence)
    missing = sorted(set(args.evidence_ids) - set(known))
    if missing:
        raise ToolError("unknown_evidence_ids:" + ",".join(missing))
    return {
        "evidencia": [known[item].model_dump(mode="json") for item in args.evidence_ids],
        "evidence_ids": list(args.evidence_ids),
    }


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "obtener_historial": ToolSpec(
        name="obtener_historial",
        description="Devuelve los ocho partidos previos de la sesion bloqueada.",
        args_model=SessionArgs,
        handler=obtener_historial,
    ),
    "obtener_perfil_corners": ToolSpec(
        name="obtener_perfil_corners",
        description="Devuelve los indicadores calculados para la sesion bloqueada.",
        args_model=SessionArgs,
        handler=obtener_perfil_corners,
    ),
    "consultar_evidencia": ToolSpec(
        name="consultar_evidencia",
        description="Devuelve el detalle de evidence_ids existentes en la sesion.",
        args_model=EvidenceArgs,
        handler=consultar_evidencia,
    ),
}


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "keys": sorted(result),
        "row_counts": {key: len(value) for key, value in result.items() if isinstance(value, (list, tuple))},
    }


def invoke_tool(
    name: str,
    arguments: dict[str, Any],
    session: AgentSession,
    state: AgentState,
    budget: Budget,
) -> dict[str, Any]:
    """Validate, budget, execute and trace the only permitted tool path."""
    started = time.perf_counter()
    validated = False
    result_summary = None
    error: Exception | None = None
    try:
        spec = TOOL_REGISTRY.get(name)
        if spec is None:
            raise ScopeError("tool_not_registered")
        if spec.read_only is not True:
            raise ScopeError("tool_not_read_only")
        if state.calls_used >= budget.max_calls:
            raise BudgetError("tool_call_budget_exceeded")
        if time.perf_counter() - state.started_at >= budget.max_seconds:
            raise BudgetError("wall_time_budget_exceeded")
        if state.total_tokens >= budget.max_session_tokens:
            raise BudgetError("session_token_budget_exceeded")
        args = spec.args_model.model_validate(arguments)
        validated = True
        state.calls_used += 1
        if name in state.failure_injection:
            raise ToolError("simulated_tool_failure")
        result = spec.handler(args, session)
        result_summary = _summary(result)
        return result
    except Exception as caught:
        error = caught
        state.errors.append(f"{type(caught).__name__}:{caught}")
        raise
    finally:
        state.traces.append(
            ToolTrace(
                tool=name,
                arguments=dict(arguments),
                arguments_validated=validated,
                status="error" if error else "ok",
                result_summary=result_summary,
                error_type=type(error).__name__ if error else None,
                error_code=str(error) if error else None,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        )


def result_evidence_ids(tool_results: list[dict[str, Any]]) -> set[str]:
    available: set[str] = set()
    for result in tool_results:
        available.update(result.get("evidence_ids", []))
        for key in ("evidencia", "indicadores", "limitaciones", "modelos_promovidos"):
            available.update(
                item["evidence_id"]
                for item in result.get(key, [])
                if isinstance(item, dict) and item.get("evidence_id")
            )
    return available


def validate_agent_draft(
    draft: AgentDraft | dict[str, Any],
    state: AgentState,
    tool_results: list[dict[str, Any]],
    *,
    require_tool: bool = False,
) -> AgentDraft:
    parsed = draft if isinstance(draft, AgentDraft) else AgentDraft.model_validate(draft)
    if parsed.tool_calls != state.calls_used:
        raise ValueError("tool_calls_mismatch")
    if len(parsed.evidence_ids) != len(set(parsed.evidence_ids)):
        raise ValueError("duplicate_evidence_ids")
    if not set(parsed.evidence_ids) <= result_evidence_ids(tool_results):
        raise ValueError("evidence_not_returned_by_tool")
    if numeric_tokens(parsed.qualitative_answer):
        raise ValueError("draft_contains_numbers")
    if require_tool and state.calls_used == 0:
        raise ValueError("required_tool_not_called")
    if parsed.status == "answered" and (state.calls_used == 0 or not parsed.evidence_ids):
        raise ValueError("answered_requires_tool_and_evidence")
    return parsed


def _literal(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _render_evidence_item(item: dict[str, Any]) -> str:
    evidence_id = item["evidence_id"]
    if "nombre" in item:
        fields = ("numerador", "denominador", "valor", "referencia_liga_previa", "cobertura")
        values = "; ".join(f"{field}={_literal(item.get(field))}" for field in fields)
        return f"{item['nombre']} [{evidence_id}]: {values}."
    if "texto" in item:
        suffix_fields = ("objetivo", "modelo_seleccionado", "supero_referencia")
        suffix = "; ".join(f"{field}={_literal(item[field])}" for field in suffix_fields if field in item)
        return f"{item['texto']} [{evidence_id}]" + (f": {suffix}." if suffix else "")
    fields = "; ".join(
        f"{key}={_literal(value)}" for key, value in item.items() if key != "evidence_id"
    )
    return f"[{evidence_id}]: {fields}."


def render_grounded_answer(draft: AgentDraft, tool_results: list[dict[str, Any]], question: str) -> str:
    """Combine qualitative model output with values copied verbatim from tool results."""
    if not isinstance(question, str):
        raise TypeError("question_must_be_string")
    if numeric_tokens(draft.qualitative_answer):
        raise ValueError("draft_contains_numbers")
    if not set(draft.evidence_ids) <= result_evidence_ids(tool_results):
        raise ValueError("evidence_not_returned_by_tool")
    sections = [draft.qualitative_answer.strip()]
    selected = set(draft.evidence_ids)
    rendered_items: set[str] = set()
    history_rendered = False
    for result in tool_results:
        if "history_match_ids" in result and "L_SAMPLE" in selected and not history_rendered:
            sections.append(
                "Historial [L_SAMPLE]: "
                f"rival={_literal(result.get('rival'))}; "
                f"fecha_corte={_literal(result.get('fecha_corte'))}; "
                f"history_match_ids={_literal(result['history_match_ids'])}; "
                f"n_partidos={_literal(result.get('n_partidos'))}."
            )
            history_rendered = True
        for key in ("evidencia", "indicadores", "limitaciones", "modelos_promovidos"):
            for item in result.get(key, []):
                evidence_id = item.get("evidence_id") if isinstance(item, dict) else None
                if evidence_id in selected and evidence_id not in rendered_items:
                    sections.append(_render_evidence_item(item))
                    rendered_items.add(evidence_id)

    rendered = " ".join(section for section in sections if section)
    source = json.dumps(tool_results, ensure_ascii=False)
    source_tokens = set(re.findall(r"(?<![A-Za-z0-9_])[-+]?\d+(?:[.,]\d+)?", source))
    rendered_tokens = set(re.findall(r"(?<![A-Za-z0-9_])[-+]?\d+(?:[.,]\d+)?", rendered))
    if not rendered_tokens <= source_tokens:
        raise ValueError("grounded_renderer_introduced_number")
    return rendered


def validate_agent_answer(
    answer: AgentAnswer | dict[str, Any],
    session: AgentSession,
    state: AgentState,
    tool_results: list[dict[str, Any]],
    *,
    require_tool: bool = False,
) -> AgentAnswer:
    parsed = answer if isinstance(answer, AgentAnswer) else AgentAnswer.model_validate(answer)
    if parsed.tool_calls != state.calls_used:
        raise ValueError("tool_calls_mismatch")
    if len(parsed.evidence_ids) != len(set(parsed.evidence_ids)):
        raise ValueError("duplicate_evidence_ids")
    if not set(parsed.evidence_ids) <= set(evidence_index(session.evidence)):
        raise ValueError("unknown_answer_evidence_id")
    if require_tool and state.calls_used == 0:
        raise ValueError("required_tool_not_called")
    if parsed.status == "answered":
        if state.calls_used == 0 or not parsed.evidence_ids:
            raise ValueError("answered_requires_tool_and_evidence")
        if not set(parsed.evidence_ids) <= result_evidence_ids(tool_results):
            raise ValueError("evidence_not_returned_by_tool")
        allowed = {number for result in tool_results for number in _all_numbers(result)}
        unsupported = set(numeric_tokens(parsed.answer)) - allowed
        if unsupported:
            raise ValueError("unsupported_numbers:" + ",".join(format(value, "g") for value in sorted(unsupported)))
    return parsed


def _all_numbers(value: Any) -> set[float]:
    if isinstance(value, bool) or value is None:
        return set()
    if isinstance(value, (int, float)):
        return {float(value)}
    if isinstance(value, dict):
        return set().union(*(_all_numbers(item) for item in value.values()), set())
    if isinstance(value, (list, tuple)):
        return set().union(*(_all_numbers(item) for item in value), set())
    return set()


OUT_OF_SCOPE = (
    "sql",
    "insert",
    "update",
    "delete",
    "escribe",
    "archivo",
    "apuesta",
    "marcador",
    "navega",
    "internet",
    "web",
)


def contains_scope_term(question: str, terms: tuple[str, ...] = OUT_OF_SCOPE) -> bool:
    lowered = question.lower()
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered) for term in terms)


def _format_evidence(item: EvidenceItem) -> str:
    if isinstance(item, Indicator):
        return (
            f"{item.nombre}: {item.numerador}/{item.denominador}, valor={item.valor}, "
            f"referencia={item.referencia_liga_previa}, cobertura={item.cobertura} [{item.evidence_id}]"
        )
    return f"{item.texto} [{item.evidence_id}]"


def deterministic_fallback(
    question: str,
    session: AgentSession,
    *,
    budget: Budget | None = None,
    state: AgentState | None = None,
) -> tuple[AgentAnswer, AgentState]:
    """Bounded local answer used for tests and provider-independent fallback."""
    budget = budget or Budget()
    state = state or AgentState()
    lowered = question.lower()
    if contains_scope_term(question):
        return AgentAnswer(
            status="out_of_scope",
            answer="Solicitud fuera del alcance de la sesion de solo lectura.",
            evidence_ids=(),
            tool_calls=state.calls_used,
        ), state
    results: list[dict[str, Any]] = []
    try:
        requested = tuple(sorted(set(re.findall(r"(?:E|L|M)_[A-Z0-9_]+", question.upper()))))
        if requested:
            result = invoke_tool("consultar_evidencia", {"evidence_ids": requested}, session, state, budget)
            results.append(result)
            items = [evidence_index(session.evidence)[item] for item in requested]
            answer = AgentAnswer(
                status="answered",
                answer=" ".join(_format_evidence(item) for item in items),
                evidence_ids=requested,
                tool_calls=state.calls_used,
            )
        elif any(term in lowered for term in ("partidos", "historial", "match_ids")):
            result = invoke_tool(
                "obtener_historial",
                {"rival": session.evidence.rival, "fecha_corte": session.evidence.fecha_corte.isoformat()},
                session,
                state,
                budget,
            )
            results.append(result)
            answer = AgentAnswer(
                status="answered",
                answer="history_match_ids=" + json.dumps(result["history_match_ids"]),
                evidence_ids=("L_SAMPLE",),
                tool_calls=state.calls_used,
            )
        else:
            result = invoke_tool(
                "obtener_perfil_corners",
                {"rival": session.evidence.rival, "fecha_corte": session.evidence.fecha_corte.isoformat()},
                session,
                state,
                budget,
            )
            results.append(result)
            known = evidence_index(session.evidence)
            if any(term in lowered for term in ("alto", "alta", "altura", "aereo", "aéreo")):
                candidates = ("E_HIGH", "E_SHORT")
            elif any(term in lowered for term in ("corto", "corta", "short")):
                candidates = ("E_SHORT", "E_HIGH")
            elif any(term in lowered for term in ("patron", "patrón", "envio", "envío", "entrega", "delivery")):
                candidates = ("E_SHORT", "E_HIGH")
            elif "scr" in lowered:
                candidates = ("E_SCR15",)
            else:
                candidates = ("E_CORNERS",)
            target = next((candidate for candidate in candidates if candidate in known), None)
            if target is None:
                raise ToolError("pertinent_evidence_unavailable")
            item = known[target]
            answer = AgentAnswer(
                status="answered",
                answer=_format_evidence(item),
                evidence_ids=(target,),
                tool_calls=state.calls_used,
            )
        return validate_agent_answer(answer, session, state, results, require_tool=True), state
    except Exception as caught:
        state.errors.append(f"fallback:{type(caught).__name__}:{caught}")
        return AgentAnswer(
            status="error",
            answer="No fue posible responder con la evidencia disponible.",
            evidence_ids=(),
            tool_calls=state.calls_used,
        ), state
