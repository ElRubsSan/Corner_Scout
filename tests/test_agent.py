import json
import time
from types import SimpleNamespace

import pytest

from analytics.agent_tools import (
    AgentAnswer,
    AgentDraft,
    AgentState,
    Budget,
    BudgetError,
    ScopeError,
    TOOL_REGISTRY,
    create_session,
    invoke_tool,
)
from analytics.tactical_report import EvidenceContract, EvidenceLimitation, Indicator
from backend.agent import answer, openai_provider
from backend.schemas import Match, Run


def _run():
    return Run(run_id="a" * 64, rival="Barcelona", analyst=None, cutoff_date="2016-03-01",
               matches=[], dataset_version="canonical", canonical_runs={})


def _evidence():
    return EvidenceContract(rival="Barcelona", fecha_corte="2016-03-01", history_match_ids=tuple(range(1, 9)),
                            indicadores=(Indicator(evidence_id="E_CORNERS", nombre="corners_por_partido",
                                                   numerador=40, denominador=8, valor=5.0,
                                                   referencia_liga_previa=4.5, cobertura=1.0),),
                            limitaciones=(EvidenceLimitation(evidence_id="L_SAMPLE", texto="Ventana de 8 partidos."),))


def _tool_response(response_id="resp-tool", *, tool="obtener_perfil_corners", input_tokens=10, output_tokens=5):
    call = SimpleNamespace(
        type="function_call",
        name=tool,
        arguments=json.dumps({"rival": "Barcelona", "fecha_corte": "2016-03-01"}),
        call_id="call-profile",
    )
    return SimpleNamespace(
        id=response_id,
        output=[call],
        output_parsed=None,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def _answer_response(response_id, answer):
    return SimpleNamespace(
        id=response_id,
        output=[],
        output_parsed=answer,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


def _fake_openai(monkeypatch, responses):
    requests = []
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeResponses:
        def parse(self, **kwargs):
            requests.append(kwargs)
            response = responses.pop(0)
            if isinstance(response, BaseException):
                raise response
            return response

    client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setattr("openai.OpenAI", lambda **_: client)
    return requests


def test_exactly_three_imported_read_only_tools():
    assert set(TOOL_REGISTRY) == {"obtener_historial", "obtener_perfil_corners", "consultar_evidencia"}
    assert all(tool.read_only is True for tool in TOOL_REGISTRY.values())


def test_out_of_scope_is_blocked_before_provider(monkeypatch):
    monkeypatch.setattr("backend.service.agent_evidence", lambda _: _evidence())
    called = False

    def provider(*_):
        nonlocal called
        called = True
        raise AssertionError
    result = answer(_run(), "Ejecuta SQL y escribe un archivo", provider=provider)
    assert result.status == "out_of_scope"
    assert result.tool_calls == 0
    assert (result.input_tokens, result.output_tokens, result.total_tokens) == (0, 0, 0)
    assert result.traces == []
    assert called is False


def test_mock_provider_uses_pydantic_tool_arguments(monkeypatch):
    monkeypatch.setattr("backend.service.agent_evidence", lambda _: _evidence())

    def provider(_, session, state, budget):
        result = invoke_tool("obtener_historial", {"rival": "Barcelona", "fecha_corte": "2016-03-01"}, session, state, budget)
        assert result["n_partidos"] == 8
        return AgentAnswer(status="answered", answer="Ventana consultada.", evidence_ids=("L_SAMPLE",), tool_calls=1)
    result = answer(_run(), "Muestra el historial", provider=provider, budget=Budget(max_calls=1))
    assert result.mode == "openai"
    assert result.tool_calls == 1
    assert result.traces[0].arguments_validated is True


def test_history_question_names_matches_without_exposing_match_ids(monkeypatch):
    monkeypatch.setattr("backend.service.agent_evidence", lambda _: _evidence())
    run = _run().model_copy(update={"matches": [Match(
        match_id=123456, match_date="2016-02-28T00:00:00", kick_off="20:00",
        home_team="Barcelona", away_team="Sevilla"
    )]})
    result = answer(run, "¿Qué partidos se analizaron?", provider=lambda *_: AgentAnswer(
        status="answered", answer="Historial consultado.", evidence_ids=("L_SAMPLE",), tool_calls=1
    ))
    assert "Barcelona vs. Sevilla" in result.answer
    assert "28/Feb/2016" in result.answer
    assert "- 🗓️" in result.answer
    assert "123456" not in result.answer


def test_history_is_chronological_and_scr15_is_observed_not_forecast(monkeypatch):
    run = _run().model_copy(update={"matches": [Match(
        match_id=index, match_date=f"2016-02-{day:02d}", kick_off="20:00",
        home_team="Barcelona", away_team="Sevilla"
    ) for index, day in ((2, 28), (1, 21))]})
    indicator = Indicator(evidence_id="E_SCR15", nombre="tasa_historica_scr15",
                          numerador=19, denominador=52, valor=19 / 52,
                          referencia_liga_previa=None, cobertura=1.0)
    evidence = _evidence().model_copy(update={"indicadores": (*_evidence().indicadores, indicator)})
    monkeypatch.setattr("backend.service.agent_evidence", lambda _: evidence)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    history = answer(run, "¿Qué partidos se analizaron?")
    assert history.answer.index("21/Feb/2016") < history.answer.index("28/Feb/2016")
    assert history.answer.count("- 🗓️") == 2
    observed = answer(run, "¿Cuántos córners evaluables acabaron con tiro en SCR-15?")
    assert "**52 córners evaluables**" in observed.answer
    assert "**19 terminaron en tiro** (36,5 %)" in observed.answer
    assert "tasa histórica de la liga" in observed.answer
    assert "no es una predicción" in observed.answer
    assisted = answer(run, "¿Cuántos córners evaluables acabaron con tiro en SCR-15?",
                      provider=lambda *_: AgentAnswer(status="answered", answer="Lectura cualitativa.",
                                                     evidence_ids=("E_SCR15",), tool_calls=1))
    assert assisted.mode == "openai"
    assert assisted.answer == observed.answer


def test_openai_zone_answer_is_readable_and_grounded(monkeypatch):
    zone = Indicator(evidence_id="E_ZONE",
                     nombre="proporcion_zona_directa_dominante:franja_central",
                     numerador=22, denominador=46, valor=22 / 46,
                     referencia_liga_previa=0.37467411545623835, cobertura=46 / 52)
    evidence = _evidence().model_copy(update={"indicadores": (*_evidence().indicadores, zone)})
    monkeypatch.setattr("backend.service.agent_evidence", lambda _: evidence)
    _fake_openai(monkeypatch, [
        _tool_response(),
        _answer_response("resp-zone", AgentDraft(
            status="answered", qualitative_answer="La zona central del área aparece con mayor frecuencia.",
            evidence_ids=("E_ZONE",), tool_calls=1,
        )),
    ])

    result = answer(_run(), "¿Qué zona de envío aparece con mayor frecuencia?")

    assert result.mode == "openai"
    assert result.status == "answered"
    assert result.evidence_ids == ["E_ZONE"]
    assert "22 de 46 envíos directos (47,8 %)" in result.answer
    assert "referencia_liga_previa=" not in result.answer


def test_missing_key_uses_deterministic_fallback(monkeypatch):
    monkeypatch.setattr("backend.service.agent_evidence", lambda _: _evidence())
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = answer(_run(), "Muestra el historial")
    assert result.mode == "deterministic"
    assert result.fallback_reason == "missing_api_key"


def test_provider_failure_preserves_consumed_state_for_fallback(monkeypatch):
    monkeypatch.setattr("backend.service.agent_evidence", lambda _: _evidence())

    def provider(_, session, state, budget):
        invoke_tool("obtener_historial", {"rival": "Barcelona", "fecha_corte": "2016-03-01"}, session, state, budget)
        state.input_tokens = 11
        state.output_tokens = 7
        state.total_tokens = 18
        raise RuntimeError("provider failed")

    result = answer(_run(), "Muestra el historial", provider=provider, budget=Budget(max_calls=2))
    assert result.mode == "deterministic"
    assert result.fallback_reason == "provider_unavailable"
    assert result.status == "answered"
    assert result.tool_calls == 2
    assert (result.input_tokens, result.output_tokens, result.total_tokens) == (11, 7, 18)
    assert [trace.status for trace in result.traces] == ["ok", "ok"]


def test_provider_failure_does_not_restart_exhausted_budget(monkeypatch):
    monkeypatch.setattr("backend.service.agent_evidence", lambda _: _evidence())

    def provider(_, session, state, budget):
        invoke_tool("obtener_historial", {"rival": "Barcelona", "fecha_corte": "2016-03-01"}, session, state, budget)
        raise RuntimeError("provider failed")

    result = answer(_run(), "Muestra el historial", provider=provider, budget=Budget(max_calls=1))
    assert result.status == "error"
    assert result.tool_calls == 1
    assert [trace.status for trace in result.traces] == ["ok", "error"]
    assert result.traces[-1].error_code == "tool_call_budget_exceeded"


def test_openai_provider_uses_required_then_auto_and_previous_response(monkeypatch):
    responses = [
        _tool_response(),
        _answer_response(
            "resp-valid",
            AgentDraft(
                status="answered",
                qualitative_answer="El perfil sugiere una produccion relevante de corners.",
                evidence_ids=("E_CORNERS",),
                tool_calls=1,
            ),
        ),
    ]
    requests = _fake_openai(monkeypatch, responses)
    state = AgentState()

    result = openai_provider("Analiza los corners", create_session(_evidence()), state, Budget())

    assert result.status == "answered"
    assert "40 córners en 8 partidos (5,0 por partido)" in result.answer
    assert len(requests) == 2
    assert requests[0]["tool_choice"] == "required"
    assert requests[0]["previous_response_id"] is None
    assert requests[0]["reasoning"] == {"effort": "low"}
    assert requests[1]["tool_choice"] == "auto"
    assert requests[1]["previous_response_id"] == "resp-tool"
    assert requests[1]["input"][0]["type"] == "function_call_output"


def test_draft_numbers_get_exactly_one_repair_without_more_tools(monkeypatch):
    monkeypatch.setattr("backend.service.agent_evidence", lambda _: _evidence())
    responses = [
        _tool_response(),
        _answer_response(
            "resp-invalid",
            AgentDraft(
                status="answered",
                qualitative_answer="El valor representa 99 por ciento.",
                evidence_ids=("E_CORNERS",),
                tool_calls=1,
            ),
        ),
        _answer_response(
            "resp-repaired",
            AgentDraft(
                status="answered",
                qualitative_answer="El perfil sugiere una produccion relevante de corners.",
                evidence_ids=("E_CORNERS",),
                tool_calls=1,
            ),
        ),
    ]
    requests = _fake_openai(monkeypatch, responses)

    result = answer(_run(), "Analiza los corners")

    assert result.mode == "openai"
    assert result.status == "answered"
    assert result.tool_calls == 1
    assert len(result.traces) == 1
    assert len(requests) == 3
    repair_request = requests[2]
    assert repair_request["tool_choice"] == "auto"
    assert repair_request["previous_response_id"] == "resp-invalid"
    correction = repair_request["input"][0]["content"]
    assert "draft_contains_numbers" in correction
    assert "tool_calls debe ser exactamente 1" in correction
    assert 'evidence_ids permitidos: ["E_CORNERS", "L_SAMPLE"]' in correction
    assert "no puede contener ningun digito" in correction
    assert "40 córners en 8 partidos (5,0 por partido)" in result.answer


def test_second_invalid_answer_uses_deterministic_fallback(monkeypatch, caplog):
    monkeypatch.setattr("backend.service.agent_evidence", lambda _: _evidence())
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    invalid = AgentDraft(
        status="answered",
        qualitative_answer="El valor representa 99 por ciento.",
        evidence_ids=("E_CORNERS",),
        tool_calls=1,
    )
    responses = [
        _tool_response(),
        _answer_response("resp-invalid", invalid),
        _answer_response("resp-invalid-again", invalid),
    ]
    requests = _fake_openai(monkeypatch, responses)

    result = answer(_run(), "Analiza los corners")

    assert len(requests) == 3
    assert result.mode == "deterministic"
    assert result.fallback_reason == "validation_failed"
    assert result.status == "answered"
    assert "draft_contains_numbers" in caplog.text
    assert "99" not in caplog.text
    assert "test-key" not in caplog.text


def test_repair_turn_never_executes_a_requested_tool(monkeypatch):
    repeated_call = _tool_response("resp-repeat")
    responses = [
        _tool_response(),
        _answer_response(
            "resp-invalid",
            AgentDraft(
                status="answered",
                qualitative_answer="El valor representa 99 por ciento.",
                evidence_ids=("E_CORNERS",),
                tool_calls=1,
            ),
        ),
        repeated_call,
    ]
    requests = _fake_openai(monkeypatch, responses)
    state = AgentState()

    with pytest.raises(ValueError, match="repair_requested_tool_call"):
        openai_provider("Analiza los corners", create_session(_evidence()), state, Budget())

    assert len(requests) == 3
    assert state.calls_used == 1
    assert len(state.traces) == 1


def test_real_turn_time_and_token_budgets_remain_active(monkeypatch):
    assert Budget().max_real_turns == 4
    assert Budget().max_session_tokens == 12000
    assert Budget().max_seconds == 45.0
    assert Budget().max_calls == 4

    turn_responses = [_tool_response()]
    turn_requests = _fake_openai(monkeypatch, turn_responses)
    turn_state = AgentState()
    with pytest.raises(BudgetError, match="real_turn_budget_exceeded"):
        openai_provider(
            "Analiza los corners",
            create_session(_evidence()),
            turn_state,
            Budget(max_real_turns=1),
        )
    assert len(turn_requests) == 1
    assert turn_state.calls_used == 1

    token_responses = [_tool_response(input_tokens=6001, output_tokens=0)]
    token_requests = _fake_openai(monkeypatch, token_responses)
    token_state = AgentState()
    with pytest.raises(BudgetError, match="session_token_budget_exceeded"):
        openai_provider(
            "Analiza los corners",
            create_session(_evidence()),
            token_state,
            Budget(max_session_tokens=6000),
        )
    assert len(token_requests) == 1
    assert token_state.calls_used == 0

    time_requests = _fake_openai(monkeypatch, [])
    with pytest.raises(BudgetError, match="wall_time_budget_exceeded"):
        openai_provider(
            "Analiza los corners",
            create_session(_evidence()),
            AgentState(started_at=time.perf_counter() - 2),
            Budget(max_seconds=1),
        )
    assert time_requests == []


def test_multi_tool_query_renders_history_and_profile(monkeypatch):
    responses = [
        _tool_response("resp-history", tool="obtener_historial"),
        _tool_response("resp-profile"),
        _answer_response(
            "resp-final",
            AgentDraft(
                status="answered",
                qualitative_answer="El historial y el perfil permiten contextualizar la produccion de corners.",
                evidence_ids=("L_SAMPLE", "E_CORNERS"),
                tool_calls=2,
            ),
        ),
    ]
    requests = _fake_openai(monkeypatch, responses)

    result = openai_provider(
        "Relaciona el historial de partidos con el perfil de corners",
        create_session(_evidence()),
        AgentState(),
        Budget(),
    )

    assert len(requests) == 3
    assert [request["tool_choice"] for request in requests] == ["required", "auto", "auto"]
    assert requests[1]["previous_response_id"] == "resp-history"
    assert requests[2]["previous_response_id"] == "resp-profile"
    assert "8 partidos anteriores al corte 2016-03-01" in result.answer
    assert "40 córners en 8 partidos (5,0 por partido)" in result.answer
    assert result.evidence_ids == ("L_SAMPLE", "E_CORNERS")
    assert result.tool_calls == 2


def test_failure_categories_are_distinct(monkeypatch):
    monkeypatch.setattr("backend.service.agent_evidence", lambda _: _evidence())

    def budget_failure(*_):
        raise BudgetError("real_turn_budget_exceeded")

    budget_result = answer(_run(), "Analiza los corners", provider=budget_failure)
    assert budget_result.fallback_reason == "budget_exceeded"

    def scope_failure(*_):
        raise ScopeError("rival_locked_to_session")

    scope_result = answer(_run(), "Analiza los corners", provider=scope_failure)
    assert scope_result.fallback_reason == "tool_scope_violation"

    requests = _fake_openai(monkeypatch, [ConnectionError("sdk unavailable")])
    provider_result = answer(_run(), "Analiza los corners")
    assert provider_result.fallback_reason == "provider_unavailable"
    assert len(requests) == 1
