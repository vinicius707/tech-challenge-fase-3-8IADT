"""Grafo LangGraph de triagem ginecologica (IA-F2)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from langgraph.graph import END, StateGraph

from fase3_orquestracao.graph_helpers import (
    ClinicalGraphState,
    add_trace,
    alarm_hits,
    append_output,
    evaluate_input_safety,
    retrieve_rag_context_safe,
    validate_final_response,
)


def collect_symptoms(state: ClinicalGraphState) -> ClinicalGraphState:
    state = evaluate_input_safety(state)
    text = state.get("user_input", "")
    symptoms: list[str] = []
    for label, pattern in (
        ("dor pelvica", r"dor (pelv|abdominal|baixo ventre|colica)"),
        ("sangramento", r"sangramento|escape|hemorrag"),
        ("corrimento", r"corrimento|secre[cç][aã]o"),
        ("febre", r"febre|calafrio"),
        ("ciclo irregular", r"atraso menstrual|ciclo irregular|menstrua"),
    ):
        if re.search(pattern, text, flags=re.IGNORECASE):
            symptoms.append(label)
    if not symptoms:
        symptoms.append("sintoma nao especificado")
    updated = {**state, "symptoms": symptoms}
    return add_trace(updated, "collectSymptoms", "ok", f"{len(symptoms)} grupo(s) de sintomas normalizados.")


def analyze_risk(state: ClinicalGraphState) -> ClinicalGraphState:
    text = state.get("user_input", "")
    alarms = alarm_hits(text, "bleeding", "pain", "self_harm")
    risk_factors = list(state.get("risk_factors", []))
    if alarms:
        risk_factors.extend(f"alarme:{item}" for item in alarms)
    if state.get("input_verdict") and state["input_verdict"].blocked:
        risk_factors.append("safety:blocking_input")
    risk = "alta" if risk_factors else "moderada"
    updated = {**state, "risk_factors": risk_factors, "final_risk": risk}
    return add_trace(updated, "analyzeRisk", "ok", f"Risco classificado como {risk}.")


def classify_urgency(state: ClinicalGraphState) -> ClinicalGraphState:
    text = state.get("user_input", "")
    alarms = alarm_hits(text, "bleeding", "pain", "self_harm")
    flags = state.get("safety_flags", [])
    if state.get("input_verdict") and state["input_verdict"].blocked:
        urgency = "emergencia" if {"self_harm_escalation", "urgent_referral"} & set(flags) else "alta"
        route = "emergency"
    elif alarms:
        urgency = "emergencia"
        route = "emergency"
    else:
        urgency = "moderada"
        route = "nonEmergency"
    updated = {**state, "urgency": urgency, "final_risk": urgency, "route": route}
    return add_trace(updated, "classifyUrgency", "ok", f"Rota definida: {route}; urgencia {urgency}.")


def suggest_exams(state: ClinicalGraphState) -> ClinicalGraphState:
    state = retrieve_rag_context_safe(state, k=3)
    exams = ["avaliacao clinica presencial"]
    text = state.get("user_input", "").lower()
    if "preventivo" in text or "papanicolau" in text:
        exams.append("citopatologico conforme protocolo local")
    if "corrimento" in text:
        exams.append("avaliacao de corrimento e testes conforme consulta")
    updated = {**state, "due_exams": exams}
    updated = append_output(
        updated,
        "A avaliacao inicial sugere organizar consulta para revisar sintomas, historico e exames pendentes.",
    )
    return add_trace(updated, "suggestExams", "ok", f"{len(exams)} item(ns) de avaliacao sugeridos.")


def initial_guidance(state: ClinicalGraphState) -> ClinicalGraphState:
    exams = ", ".join(state.get("due_exams", []))
    updated = append_output(
        state,
        f"Orientacao inicial: evite automedicacao, registre duracao/intensidade dos sintomas e leve historico menstrual. Itens para discutir: {exams}.",
    )
    return add_trace(updated, "initialGuidance", "ok", "Orientacao conservadora gerada sem prescricao.")


def schedule_appointment(state: ClinicalGraphState) -> ClinicalGraphState:
    priority = "prioritaria" if state.get("urgency") == "alta" else "rotina"
    updated = {**state, "appointment_priority": priority}
    updated = append_output(updated, f"Agendamento recomendado: consulta {priority} na unidade de referencia.")
    return add_trace(updated, "scheduleAppointment", "ok", f"Consulta {priority} recomendada.")


def emergency_guidance(state: ClinicalGraphState) -> ClinicalGraphState:
    updated = append_output(
        state,
        "Ha sinais de alarme. Procure pronto atendimento agora; em emergencia ligue 192 (SAMU).",
    )
    return add_trace(
        updated,
        "emergencyGuidance",
        "ok",
        "Rota de emergencia acionada por sinais de alarme.",
        ["urgent_referral", "human_review_required"],
    )


def _route_after_urgency(state: ClinicalGraphState) -> str:
    return "emergencyGuidance" if state.get("route") == "emergency" else "suggestExams"


def build_graph():
    graph = StateGraph(ClinicalGraphState)
    graph.add_node("collectSymptoms", collect_symptoms)
    graph.add_node("analyzeRisk", analyze_risk)
    graph.add_node("classifyUrgency", classify_urgency)
    graph.add_node("suggestExams", suggest_exams)
    graph.add_node("initialGuidance", initial_guidance)
    graph.add_node("scheduleAppointment", schedule_appointment)
    graph.add_node("emergencyGuidance", emergency_guidance)
    graph.add_node("validate", validate_final_response)
    graph.set_entry_point("collectSymptoms")
    graph.add_edge("collectSymptoms", "analyzeRisk")
    graph.add_edge("analyzeRisk", "classifyUrgency")
    graph.add_conditional_edges(
        "classifyUrgency",
        _route_after_urgency,
        {"emergencyGuidance": "emergencyGuidance", "suggestExams": "suggestExams"},
    )
    graph.add_edge("suggestExams", "initialGuidance")
    graph.add_edge("initialGuidance", "scheduleAppointment")
    graph.add_edge("scheduleAppointment", "validate")
    graph.add_edge("emergencyGuidance", "validate")
    graph.add_edge("validate", END)
    return graph.compile()


__all__ = ["build_graph"]
