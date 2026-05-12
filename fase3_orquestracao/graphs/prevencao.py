"""Grafo LangGraph de prevencao (IA-F5)."""

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
    append_output,
    evaluate_input_safety,
    retrieve_rag_context_safe,
    validate_final_response,
)


def load_patient_history(state: ClinicalGraphState) -> ClinicalGraphState:
    state = evaluate_input_safety(state)
    context = state.get("patient_context", {})
    preventivos = dict(context.get("preventivos", {}) or {})
    text = state.get("user_input", "")
    age_match = re.search(r"(\d{2})\s*anos", text, flags=re.IGNORECASE)
    if age_match:
        preventivos["idade"] = int(age_match.group(1))
    updated_context = {**context, "preventivos": preventivos}
    updated = {**state, "patient_context": updated_context}
    return add_trace(updated, "loadPatientHistory", "ok", "Historico preventivo carregado sem expor dados livres.")


def identify_due_exams(state: ClinicalGraphState) -> ClinicalGraphState:
    text = state.get("user_input", "").lower()
    preventivos = state.get("patient_context", {}).get("preventivos", {}) or {}
    age = preventivos.get("idade")
    due: list[str] = []
    high_risk = any(term in text for term in ("alto risco", "historia familiar", "imunossuprim"))
    symptomatic = any(term in text for term in ("sangramento", "dor", "caroco", "nódulo", "nodulo"))

    if "preventivo" in text or "papanicolau" in text or age:
        due.append("avaliar citopatologico conforme faixa etaria e historico")
    if age and int(age) >= 40:
        due.append("discutir rastreamento mamografico conforme protocolo local")
    if high_risk:
        due.append("avaliacao individual por alto risco")
    if symptomatic:
        due.append("investigacao clinica por sintoma, nao apenas rastreamento")

    if not due:
        due.append("revisar carteira de vacinas e calendario preventivo")

    urgency = "moderada" if symptomatic or high_risk else "nenhuma"
    updated = {
        **state,
        "due_exams": due,
        "urgency": urgency,
        "final_risk": urgency,
        "risk_factors": ["sintomatico" if symptomatic else "", "alto_risco" if high_risk else ""],
    }
    return add_trace(updated, "identifyDueExams", "ok", f"{len(due)} demanda(s) preventiva(s) identificada(s).")


def preventive_guidance(state: ClinicalGraphState) -> ClinicalGraphState:
    state = retrieve_rag_context_safe(state, k=3)
    exams = "; ".join(state.get("due_exams", []))
    updated = append_output(
        state,
        f"Prevencao: diferenciar rastreamento de rotina, investigacao por sintomas e alto risco. Pendencias: {exams}.",
    )
    return add_trace(updated, "preventiveGuidance", "ok", "Orientacao preventiva gerada com separacao de cenarios.")


def auto_schedule_prevention(state: ClinicalGraphState) -> ClinicalGraphState:
    priority = "prioritaria" if state.get("urgency") == "moderada" else "rotina"
    updated = {**state, "appointment_priority": priority}
    updated = append_output(updated, f"Agendamento sugerido: consulta preventiva {priority}.")
    return add_trace(updated, "autoSchedulePrevention", "ok", f"Agendamento preventivo {priority} sugerido.")


def personalized_reminders(state: ClinicalGraphState) -> ClinicalGraphState:
    reminders = [
        "levar exames anteriores",
        "informar data da ultima menstruacao quando aplicavel",
        "retornar antes se surgirem sintomas de alarme",
    ]
    updated = {**state, "next_steps": reminders}
    updated = append_output(updated, "Lembretes personalizados: " + "; ".join(reminders) + ".")
    return add_trace(updated, "personalizedReminders", "ok", f"{len(reminders)} lembrete(s) seguro(s) adicionados.")


def build_graph():
    graph = StateGraph(ClinicalGraphState)
    graph.add_node("loadPatientHistory", load_patient_history)
    graph.add_node("identifyDueExams", identify_due_exams)
    graph.add_node("preventiveGuidance", preventive_guidance)
    graph.add_node("autoSchedulePrevention", auto_schedule_prevention)
    graph.add_node("personalizedReminders", personalized_reminders)
    graph.add_node("validate", validate_final_response)
    graph.set_entry_point("loadPatientHistory")
    graph.add_edge("loadPatientHistory", "identifyDueExams")
    graph.add_edge("identifyDueExams", "preventiveGuidance")
    graph.add_edge("preventiveGuidance", "autoSchedulePrevention")
    graph.add_edge("autoSchedulePrevention", "personalizedReminders")
    graph.add_edge("personalizedReminders", "validate")
    graph.add_edge("validate", END)
    return graph.compile()


__all__ = ["build_graph"]
