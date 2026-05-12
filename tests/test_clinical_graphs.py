"""Testes unitarios dos grafos LangGraph da Fase F."""

from __future__ import annotations

import pytest

from fase3_orquestracao.clinical_router import (
    ClinicalRouterError,
    available_flows,
    route_clinical_flow,
)
from fase3_orquestracao.graph_helpers import add_trace, make_initial_state, sanitize_trace_summary


def _node_names(result):
    return [node.name for node in result.trace.nodes]


def test_available_flows_contains_four_required_graphs():
    assert available_flows() == [
        "obstetrico",
        "prevencao",
        "triagemGinecologica",
        "violenciaDomestica",
    ]


def test_router_rejects_unknown_flow():
    with pytest.raises(ClinicalRouterError, match="flowId invalido"):
        route_clinical_flow(flow_id="desconhecido", message="oi")


def test_router_rejects_empty_message():
    with pytest.raises(ClinicalRouterError, match="message nao pode ser vazio"):
        route_clinical_flow(flow_id="prevencao", message="   ")


def test_add_trace_redacts_sensitive_summary():
    state = make_initial_state(
        flow_id="violenciaDomestica",
        user_input="Meu marido me bate.",
    )
    updated = add_trace(
        state,
        "secureDocumentation",
        "ok",
        "Meu marido me bate em casa.",
        ["violence_protocol", "sensitive"],
    )
    summary = updated["trace"][0]["summary"]
    assert "marido" not in summary.lower()
    assert "bate" not in summary.lower()
    assert "redigido" in summary.lower()


def test_sanitize_trace_summary_masks_pii_in_regular_flow():
    summary = sanitize_trace_summary(
        "Paciente CPF 123.456.789-00, telefone 11 91234-5678.",
        flow_id="triagemGinecologica",
    )
    assert "123.456.789-00" not in summary
    assert "91234-5678" not in summary
    assert "[REDACTED:cpf]" in summary


def test_triage_graph_routes_alarm_to_emergency_guidance():
    result = route_clinical_flow(
        flow_id="triagemGinecologica",
        message="Estou com dor no peito e dor pelvica intensa.",
        patient_context={"resumo": "Paciente ficticia", "cicloMenstrual": {"ultimoCiclo": "10/04"}},
    )
    nodes = _node_names(result)
    assert "collectSymptoms" in nodes
    assert "classifyUrgency" in nodes
    assert "emergencyGuidance" in nodes
    assert result.urgency == "emergencia"
    assert "urgent_referral" in result.safety_flags


def test_violence_graph_always_notifies_specialized_team_and_redacts_trace():
    result = route_clinical_flow(
        flow_id="violenciaDomestica",
        message="Meu marido me bate em casa.",
        patient_context={"resumo": "Paciente ficticia em situacao sensivel"},
    )
    nodes = _node_names(result)
    assert "notifySpecializedTeam" in nodes
    assert "secureDocumentation" in nodes
    assert result.raw_state["specialized_team_notified"] is True
    assert result.raw_state["secure_documentation"] is True
    assert "equipe qualificada" in result.response
    trace_text = result.trace.model_dump_json().lower()
    assert "marido" not in trace_text
    assert "bate" not in trace_text
    assert "sensitive" in result.safety_flags


def test_obstetric_graph_escalates_red_flags():
    result = route_clinical_flow(
        flow_id="obstetrico",
        message="Estou gravida de 34 semanas e nao sinto o bebe desde ontem.",
        patient_context={"resumo": "Gestante ficticia", "obstetrica": {"gestacoes": 1}},
    )
    nodes = _node_names(result)
    assert nodes[:2] == ["ingestPregnancyData", "assessObstetricRisk"]
    assert "urgencyAlerts" in nodes
    assert result.urgency == "emergencia"
    assert "urgent_referral" in result.safety_flags
    assert "maternidade" in result.response.lower()


def test_prevention_graph_identifies_due_exams_and_reminders():
    result = route_clinical_flow(
        flow_id="prevencao",
        message="Tenho 42 anos e quero saber se meu preventivo e mamografia estao em dia.",
        patient_context={
            "resumo": "Paciente ficticia",
            "preventivos": {"ultimoPreventivo": "2021"},
            "historicoReprodutivo": {"partos": 1},
        },
    )
    nodes = _node_names(result)
    assert "identifyDueExams" in nodes
    assert "personalizedReminders" in nodes
    assert any("mamografico" in item for item in result.raw_state["due_exams"])
    assert "rastreamento" in result.response.lower()
    assert result.trace.finalRisk in {"nenhuma", "moderada"}


def test_result_contains_explain_block_and_trace_summary():
    result = route_clinical_flow(
        flow_id="prevencao",
        message="Quero revisar exames preventivos.",
        patient_context={},
    )
    assert result.explain.fonte
    assert 0.0 <= result.explain.confianca <= 1.0
    assert result.explain.lacunas
    assert result.trace.flowId == "prevencao"
    assert len(result.trace.nodes) >= 3
