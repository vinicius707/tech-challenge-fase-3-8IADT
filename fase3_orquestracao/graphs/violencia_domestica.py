"""Grafo LangGraph de violencia domestica (IA-F3)."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from langgraph.graph import END, StateGraph

from fase3_orquestracao.graph_helpers import (
    ClinicalGraphState,
    add_trace,
    append_output,
    evaluate_input_safety,
    validate_final_response,
)


def capture_alert_signals(state: ClinicalGraphState) -> ClinicalGraphState:
    state = evaluate_input_safety(state)
    verdict = state.get("input_verdict")
    if verdict and verdict.replacement_text and "equipe qualificada" not in verdict.replacement_text:
        state = {
            **state,
            "input_verdict": replace(
                verdict,
                replacement_text=(
                    verdict.replacement_text
                    + " Encaminhamento obrigatorio: acionar equipe qualificada da rede de protecao/saude."
                ),
            ),
        }
    flags = state.get("safety_flags", [])
    updated = {
        **state,
        "urgency": "alta" if "violence_protocol" in flags else "moderada",
        "final_risk": "alta",
        "secure_documentation": True,
    }
    return add_trace(
        updated,
        "captureAlertSignals",
        "ok",
        "Sinais de violencia avaliados; conteudo sensivel redigido no trace.",
        ["sensitive"],
    )


def assess_violence_risk(state: ClinicalGraphState) -> ClinicalGraphState:
    flags = state.get("safety_flags", [])
    risk = "alta" if "violence_protocol" in flags else "moderada"
    updated = {**state, "final_risk": risk, "urgency": "alta"}
    return add_trace(
        updated,
        "assessViolenceRisk",
        "ok",
        f"Risco de violencia classificado como {risk}; encaminhamento humano obrigatorio.",
        ["human_review_required", "sensitive"],
    )


def apply_safety_protocol(state: ClinicalGraphState) -> ClinicalGraphState:
    input_verdict = state.get("input_verdict")
    protocol = (
        input_verdict.replacement_text
        if input_verdict and input_verdict.replacement_text
        else (
            "Se houver risco imediato, ligue 190. Para orientacao e encaminhamento, "
            "acione o Disque 180 e procure a rede local de protecao."
        )
    )
    updated = append_output(state, protocol)
    return add_trace(
        updated,
        "applySafetyProtocol",
        "ok",
        "Protocolo de seguranca aplicado com contatos de rede de protecao.",
        ["violence_protocol", "human_review_required", "sensitive"],
    )


def notify_specialized_team(state: ClinicalGraphState) -> ClinicalGraphState:
    updated = {
        **state,
        "specialized_team_notified": True,
        "next_steps": [*state.get("next_steps", []), "encaminhar equipe qualificada"],
    }
    updated = append_output(
        updated,
        "Encaminhamento: acionar equipe qualificada da rede de protecao/saude para atendimento seguro.",
    )
    return add_trace(
        updated,
        "notifySpecializedTeam",
        "ok",
        "Equipe qualificada marcada para encaminhamento.",
        ["human_review_required", "sensitive"],
    )


def secure_documentation(state: ClinicalGraphState) -> ClinicalGraphState:
    updated = {
        **state,
        "secure_documentation": True,
        "audit_summary": {
            "sensitive_redacted": True,
            "summary": "[REDACTED:sensitive_content]",
        },
    }
    return add_trace(
        updated,
        "secureDocumentation",
        "ok",
        "Documentacao segura configurada; texto livre sensivel nao sera persistido.",
        ["sensitive"],
    )


def follow_up_plan(state: ClinicalGraphState) -> ClinicalGraphState:
    updated = append_output(
        state,
        "Plano de seguimento: combinar contato seguro, evitar mensagens que aumentem risco e priorizar atendimento presencial protegido.",
    )
    return add_trace(
        updated,
        "followUpPlan",
        "ok",
        "Plano de acompanhamento seguro registrado em alto nivel.",
        ["human_review_required", "sensitive"],
    )


def build_graph():
    graph = StateGraph(ClinicalGraphState)
    graph.add_node("captureAlertSignals", capture_alert_signals)
    graph.add_node("assessViolenceRisk", assess_violence_risk)
    graph.add_node("applySafetyProtocol", apply_safety_protocol)
    graph.add_node("notifySpecializedTeam", notify_specialized_team)
    graph.add_node("secureDocumentation", secure_documentation)
    graph.add_node("followUpPlan", follow_up_plan)
    graph.add_node("validate", validate_final_response)
    graph.set_entry_point("captureAlertSignals")
    graph.add_edge("captureAlertSignals", "assessViolenceRisk")
    graph.add_edge("assessViolenceRisk", "applySafetyProtocol")
    graph.add_edge("applySafetyProtocol", "notifySpecializedTeam")
    graph.add_edge("notifySpecializedTeam", "secureDocumentation")
    graph.add_edge("secureDocumentation", "followUpPlan")
    graph.add_edge("followUpPlan", "validate")
    graph.add_edge("validate", END)
    return graph.compile()


__all__ = ["build_graph"]
