import time

import pytest

from analytics.agent_tools import (
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
    invoke_tool,
    render_grounded_answer,
    validate_agent_answer,
    validate_agent_draft,
)
from analytics.tactical_report import EvidenceContract, EvidenceLimitation, Indicator


@pytest.fixture()
def session():
    indicators = tuple(
        Indicator(
            evidence_id=evidence_id,
            nombre=name,
            numerador=numerator,
            denominador=denominator,
            valor=numerator / denominator,
            referencia_liga_previa=reference,
            cobertura=1.0,
        )
        for evidence_id, name, numerator, denominator, reference in (
            ("E_CORNERS", "corners_por_partido", 39, 8, 5.0),
            ("E_SCR15", "tasa_historica_scr15", 12, 39, 0.32),
            ("E_SHORT", "proporcion_proxy_corto", 14, 39, 0.12),
            ("E_HIGH", "proporcion_pase_alto", 20, 39, 0.76),
        )
    )
    evidence = EvidenceContract(
        rival="Barcelona",
        fecha_corte="2016-03-01",
        history_match_ids=(265839, 267273, 266815, 266254, 266160, 267576, 265894, 266149),
        indicadores=indicators,
        limitaciones=(
            EvidenceLimitation(evidence_id="L_SAMPLE", texto="Ventana disponible: 8 de 8 partidos previos."),
            EvidenceLimitation(evidence_id="L_MODEL", texto="Modelo no promovido."),
        ),
    )
    return create_session(evidence)


@pytest.mark.parametrize(
    ("question", "evidence_id"),
    [
        ("Muestra el historial de partidos usado.", "L_SAMPLE"),
        ("Consulta E_SHORT", "E_SHORT"),
        ("Consulta E_HIGH y su referencia", "E_HIGH"),
        ("Consulta L_MODEL", "L_MODEL"),
    ],
)
def test_mock_questions(session, question, evidence_id):
    answer, state = deterministic_fallback(question, session)
    assert answer.status == "answered"
    assert answer.evidence_ids == (evidence_id,)
    assert answer.tool_calls == state.calls_used == 1


@pytest.mark.parametrize(
    ("question", "evidence_id"),
    [
        ("Que patron de envio corto utiliza?", "E_SHORT"),
        ("Como son sus envios altos?", "E_HIGH"),
        ("Describe el patron de envio.", "E_SHORT"),
    ],
)
def test_pattern_and_delivery_questions_use_pertinent_evidence(session, question, evidence_id):
    answer, _ = deterministic_fallback(question, session)
    assert answer.status == "answered"
    assert answer.evidence_ids == (evidence_id,)
    assert "E_CORNERS" not in answer.evidence_ids


def test_pattern_question_uses_available_delivery_evidence_without_key_error(session):
    evidence = session.evidence.model_copy(
        update={"indicadores": tuple(item for item in session.evidence.indicadores if item.evidence_id != "E_SHORT")}
    )
    answer, state = deterministic_fallback("Describe el patron de envio", create_session(evidence))
    assert answer.status == "answered"
    assert answer.evidence_ids == ("E_HIGH",)
    assert not any("KeyError" in error for error in state.errors)


def test_pattern_question_without_delivery_evidence_fails_cleanly(session):
    evidence = session.evidence.model_copy(
        update={"indicadores": tuple(
            item for item in session.evidence.indicadores if item.evidence_id not in {"E_SHORT", "E_HIGH"}
        )}
    )
    answer, state = deterministic_fallback("Describe el patron de envio", create_session(evidence))
    assert answer.status == "error"
    assert answer.evidence_ids == ()
    assert not any("KeyError" in error for error in state.errors)


def test_exactly_three_read_only_tools():
    assert set(TOOL_REGISTRY) == {"obtener_historial", "obtener_perfil_corners", "consultar_evidencia"}
    assert all(spec.read_only is True for spec in TOOL_REGISTRY.values())


def invoke(session, name, arguments, **state_args):
    return invoke_tool(name, arguments, session, AgentState(**state_args), Budget())


def test_different_rival(session):
    with pytest.raises(ScopeError, match="rival_locked"):
        invoke(session, "obtener_historial", {"rival": "Real Madrid", "fecha_corte": "2016-03-01"})


def test_different_date(session):
    with pytest.raises(ScopeError, match="cutoff_locked"):
        invoke(session, "obtener_perfil_corners", {"rival": "Barcelona", "fecha_corte": "2016-04-01"})


def test_unknown_evidence(session):
    with pytest.raises(ToolError, match="unknown_evidence_ids"):
        invoke(session, "consultar_evidencia", {"evidence_ids": ["E_DOES_NOT_EXIST"]})


@pytest.mark.parametrize(
    "question",
    ["Ejecuta SQL SELECT * FROM corners", "Escribe un archivo con el reporte", "Dame una apuesta y marcador"],
)
def test_out_of_scope_without_tool_call(session, question):
    answer, state = deterministic_fallback(question, session)
    assert answer.status == "out_of_scope"
    assert answer.tool_calls == state.calls_used == 0


def test_excess_tool_calls(session):
    state = AgentState()
    budget = Budget(max_calls=1)
    args = {"rival": "Barcelona", "fecha_corte": "2016-03-01"}
    invoke_tool("obtener_historial", args, session, state, budget)
    with pytest.raises(BudgetError, match="tool_call_budget_exceeded"):
        invoke_tool("obtener_perfil_corners", args, session, state, budget)


def test_simulated_timeout(session):
    state = AgentState(started_at=time.perf_counter() - 46)
    with pytest.raises(BudgetError, match="wall_time_budget_exceeded"):
        invoke_tool(
            "obtener_historial",
            {"rival": "Barcelona", "fecha_corte": "2016-03-01"},
            session,
            state,
            Budget(),
        )


def test_tool_failure_is_traced(session):
    state = AgentState(failure_injection=frozenset({"obtener_perfil_corners"}))
    with pytest.raises(ToolError, match="simulated_tool_failure"):
        invoke_tool(
            "obtener_perfil_corners",
            {"rival": "Barcelona", "fecha_corte": "2016-03-01"},
            session,
            state,
            Budget(),
        )
    assert state.traces[-1].status == "error"
    assert state.traces[-1].arguments_validated is True


def test_invalid_final_answer(session):
    state = AgentState(calls_used=1)
    result = {"evidence_ids": ["E_SHORT"], "evidencia": [{"evidence_id": "E_SHORT", "valor": 0.35}]}
    answer = AgentAnswer(status="answered", answer="Valor inventado 999.", evidence_ids=("E_SHORT",), tool_calls=1)
    with pytest.raises(ValueError, match="unsupported_numbers"):
        validate_agent_answer(answer, session, state, [result], require_tool=True)


def test_qualitative_draft_accepts_no_numbers_and_rejects_generated_numbers():
    state = AgentState(calls_used=1)
    results = [{"evidence_ids": ["E_SHORT"]}]
    valid = AgentDraft(
        status="answered",
        qualitative_answer="El recurso corto aparece como una tendencia relevante.",
        evidence_ids=("E_SHORT",),
        tool_calls=1,
    )
    assert validate_agent_draft(valid, state, results, require_tool=True) == valid

    invalid = valid.model_copy(update={"qualitative_answer": "El recurso aparece en 33.3%."})
    with pytest.raises(ValueError, match="draft_contains_numbers"):
        validate_agent_draft(invalid, state, results, require_tool=True)


def test_grounded_renderer_copies_exact_indicator_without_percentage():
    draft = AgentDraft(
        status="answered",
        qualitative_answer="La evidencia sugiere una tendencia que debe interpretarse con cautela.",
        evidence_ids=("E_SCR15",),
        tool_calls=1,
    )
    results = [{
        "indicadores": [{
            "evidence_id": "E_SCR15",
            "nombre": "tasa_historica_scr15",
            "numerador": 1,
            "denominador": 3,
            "valor": 0.333,
            "referencia_liga_previa": 0.32,
            "cobertura": 1.0,
        }],
        "evidence_ids": ["E_SCR15"],
    }]

    rendered = render_grounded_answer(draft, results, "Describe SCR")

    assert "numerador=1" in rendered
    assert "denominador=3" in rendered
    assert "valor=0.333" in rendered
    assert "referencia_liga_previa=0.32" in rendered
    assert "33.3%" not in rendered


def test_grounded_renderer_history_ids_come_from_tool_result():
    match_ids = [265839, 267273, 266815, 266254, 266160, 267576, 265894, 266149]
    draft = AgentDraft(
        status="answered",
        qualitative_answer="El historial aporta el contexto previo disponible.",
        evidence_ids=("L_SAMPLE",),
        tool_calls=1,
    )
    results = [{
        "rival": "Barcelona",
        "fecha_corte": "2016-03-01",
        "history_match_ids": match_ids,
        "n_partidos": 8,
        "evidence_ids": ["L_SAMPLE"],
    }]

    rendered = render_grounded_answer(draft, results, "Muestra el historial")

    assert f"history_match_ids={match_ids}" in rendered
    assert "fecha_corte=2016-03-01" in rendered


def test_unregistered_tool_is_blocked_and_traced(session):
    state = AgentState()
    with pytest.raises(ScopeError, match="tool_not_registered"):
        invoke_tool("leer_archivo", {}, session, state, Budget())
    assert state.calls_used == 0
    assert state.traces[-1].status == "error"
