"""Bounded OpenAI agent over the three canonical read-only analytics tools."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Protocol

from pydantic import ValidationError

from analytics.agent_tools import (
    OUT_OF_SCOPE,
    AgentAnswer,
    AgentDraft,
    AgentState,
    Budget,
    BudgetError,
    ScopeError,
    TOOL_REGISTRY,
    ToolError,
    create_session,
    deterministic_fallback,
    contains_scope_term,
    invoke_tool,
    render_grounded_answer,
    result_evidence_ids,
    validate_agent_draft,
)
from backend import service
from backend.schemas import AgentResponse, Run

logger = logging.getLogger(__name__)


class AgentProvider(Protocol):
    def __call__(self, question: str, session: Any, state: AgentState, budget: Budget) -> AgentAnswer: ...


class AgentValidationError(ValueError):
    pass


def _out_of_scope(question: str) -> bool:
    blocked = (*OUT_OF_SCOPE, "borra", "elimina", "modifica", "entrena", "datos raw", "en vivo", "actuales")
    return contains_scope_term(question, blocked)


def openai_provider(question: str, session: Any, state: AgentState, budget: Budget) -> AgentAnswer:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=min(20.0, budget.max_seconds), max_retries=1)
    tools = [{"type": "function", "name": spec.name, "description": spec.description,
              "parameters": spec.args_model.model_json_schema(), "strict": True}
             for spec in TOOL_REGISTRY.values()]
    if len(tools) != 3:
        raise RuntimeError("agent_requires_exactly_three_tools")
    system_prompt = (
        "Selecciona evidencia mediante las herramientas y redacta solo una interpretacion cualitativa. "
        "qualitative_answer no puede contener digitos, cantidades, porcentajes, fechas, ordinales, "
        "probabilidades, identificadores numericos ni cifras escritas con simbolos. "
        "El backend agregara todos los valores. "
        "Sin apuestas ni conocimiento externo. "
        f"La sesion esta bloqueada al rival '{session.evidence.rival}' "
        f"y a la fecha de corte '{session.evidence.fecha_corte.isoformat()}'. "
        "Usa exactamente esos valores en todos los argumentos de herramientas. "
        "No los modifiques, completes ni sustituyas."
    )

    input_items: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": question,
        },
    ]
    tool_results: list[dict[str, Any]] = []
    turns = 0
    previous_response_id: str | None = None
    repair_attempted = False
    while True:
        turns += 1
        if turns > budget.max_real_turns:
            raise BudgetError("real_turn_budget_exceeded")
        if time.perf_counter() - state.started_at >= budget.max_seconds:
            raise BudgetError("wall_time_budget_exceeded")
        response = client.responses.parse(
            model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
            input=input_items,
            previous_response_id=previous_response_id,
            tools=tools,
            tool_choice="required" if state.calls_used == 0 else "auto",
            text_format=AgentDraft,
            reasoning={"effort": "low"},
            max_output_tokens=1200,
        )
        if time.perf_counter() - state.started_at >= budget.max_seconds:
            raise BudgetError("wall_time_budget_exceeded")
        usage = getattr(response, "usage", None)
        if usage:
            state.input_tokens += int(getattr(usage, "input_tokens", 0))
            state.output_tokens += int(getattr(usage, "output_tokens", 0))
            state.total_tokens = state.input_tokens + state.output_tokens
            if state.total_tokens > budget.max_session_tokens:
                raise BudgetError("session_token_budget_exceeded")
        calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
        if repair_attempted and calls:
            raise AgentValidationError("repair_requested_tool_call")
        if not calls:
            parsed = response.output_parsed
            if parsed is None:
                raise AgentValidationError("missing_structured_output")
            try:
                draft = validate_agent_draft(parsed, state, tool_results, require_tool=True)
                rendered = render_grounded_answer(draft, tool_results, question)
                return AgentAnswer(
                    status=draft.status,
                    answer=rendered,
                    evidence_ids=draft.evidence_ids,
                    tool_calls=draft.tool_calls,
                )
            except ValueError as exc:
                if repair_attempted:
                    failure_type = (
                        "invalid_draft_schema"
                        if isinstance(exc, ValidationError)
                        else str(exc).partition(":")[0]
                    )
                    raise AgentValidationError(failure_type) from None
                repair_attempted = True
                previous_response_id = response.id
                failure_type = (
                    "invalid_draft_schema"
                    if isinstance(exc, ValidationError)
                    else str(exc).partition(":")[0]
                )
                logger.warning("OpenAI agent answer validation failed: %s", failure_type)
                allowed_ids = sorted(result_evidence_ids(tool_results))
                input_items = [
                    {
                        "role": "user",
                        "content": (
                            "Corrige la respuesta estructurada final sin llamar herramientas. "
                            f"Motivo de validacion: {failure_type}. "
                            f"tool_calls debe ser exactamente {state.calls_used}. "
                            "evidence_ids permitidos: " + json.dumps(allowed_ids, ensure_ascii=True) + ". "
                            "qualitative_answer debe ser puramente cualitativo y no puede contener ningun "
                            "digito, cantidad, porcentaje, fecha, ordinal ni identificador numerico. "
                            "No llames herramientas; el backend agregara los valores."
                        ),
                    }
                ]
                continue
        previous_response_id = response.id
        next_input_items: list[dict[str, Any]] = []
        for call in calls:
            try:
                arguments = json.loads(call.arguments)
                if not isinstance(arguments, dict):
                    raise ScopeError("tool_arguments_must_be_object")
                result = invoke_tool(call.name, arguments, session, state, budget)
            except BudgetError:
                raise
            except ScopeError:
                raise
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ScopeError("invalid_tool_arguments") from exc
            tool_results.append(result)
            next_input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )
        input_items = next_input_items


def answer(run: Run, question: str, provider: AgentProvider | None = None, budget: Budget | None = None) -> AgentResponse:
    session = create_session(service.agent_evidence(run))
    budget = budget or Budget()
    if _out_of_scope(question):
        result, state = deterministic_fallback(question, session, budget=budget)
        return AgentResponse(mode="deterministic", status=result.status, answer=result.answer,
                             evidence_ids=list(result.evidence_ids), tool_calls=result.tool_calls,
                             input_tokens=state.input_tokens, output_tokens=state.output_tokens,
                             total_tokens=state.total_tokens,
                             traces=[trace.model_dump(mode="json") for trace in state.traces])
    if provider is None and not os.environ.get("OPENAI_API_KEY"):
        result, state = deterministic_fallback(question, session, budget=budget)
        return AgentResponse(mode="deterministic", fallback_reason="missing_api_key", status=result.status,
                             answer=result.answer, evidence_ids=list(result.evidence_ids), tool_calls=result.tool_calls,
                             input_tokens=state.input_tokens, output_tokens=state.output_tokens,
                             total_tokens=state.total_tokens,
                             traces=[trace.model_dump(mode="json") for trace in state.traces])
    state = AgentState()
    try:
        result = (provider or openai_provider)(question, session, state, budget)
        return AgentResponse(mode="openai", status=result.status, answer=result.answer,
                             evidence_ids=list(result.evidence_ids), tool_calls=result.tool_calls,
                             input_tokens=state.input_tokens, output_tokens=state.output_tokens,
                             total_tokens=state.total_tokens,
                             traces=[trace.model_dump(mode="json") for trace in state.traces])
    except AgentValidationError as exc:
        fallback_reason = "validation_failed"
        failure_type = str(exc).partition(":")[0]
    except ValidationError:
        fallback_reason = "validation_failed"
        failure_type = "structured_output_validation"
    except BudgetError as exc:
        fallback_reason = "budget_exceeded"
        failure_type = str(exc).partition(":")[0]
    except ScopeError as exc:
        fallback_reason = "tool_scope_violation"
        failure_type = str(exc).partition(":")[0]
    except ToolError as exc:
        fallback_reason = "tool_error"
        failure_type = type(exc).__name__
    except Exception as exc:
        fallback_reason = "provider_unavailable"
        failure_type = type(exc).__name__
    logger.error(
        "OpenAI agent failed: category=%s type=%s",
        fallback_reason,
        failure_type,
    )
    result, fallback_state = deterministic_fallback(question, session, budget=budget, state=state)
    return AgentResponse(mode="deterministic", fallback_reason=fallback_reason, status=result.status,
                         answer=result.answer, evidence_ids=list(result.evidence_ids), tool_calls=result.tool_calls,
                         input_tokens=fallback_state.input_tokens,
                         output_tokens=fallback_state.output_tokens,
                         total_tokens=fallback_state.total_tokens,
                         traces=[trace.model_dump(mode="json") for trace in fallback_state.traces])
