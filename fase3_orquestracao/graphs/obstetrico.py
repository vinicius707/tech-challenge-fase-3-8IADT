"""Grafo LangGraph obstetrico (IA-F4)."""

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


def ingest_pregnancy_data(state: ClinicalGraphState) -> ClinicalGraphState:
    state = evaluate_input_safety(state)
    text = state.get("user_input", "")
    weeks_match = re.search(r"(\d{1,2})\s*(semanas|sem)", text, flags=re.IGNORECASE)
    pregnancy_data = dict(state.get("patient_context", {}).get("obstetrica", {}) or {})
    if weeks_match:
        pregnancy_data["idade_gestacional_semanas"] = int(weeks_match.group(1))
    updated_context = {**state.get("patient_context", {}), "obstetrica": pregnancy_data}
    updated = {**state, "patient_context": updated_context}
    return add_trace(updated, "ingestPregnancyData", "ok", "Dados gestacionais normalizados em estrutura segura.")


def assess_obstetric_risk(state: ClinicalGraphState) -> ClinicalGraphState:
    text = state.get("user_input", "")
    alarms = alarm_hits(text, "bleeding", "pregnancy", "pain")
    emergency_phrases = (
        r"sangramento (intenso|abundante|com co[aá]gulo)",
        r"n[aã]o sinto (mais )?(o )?beb[eê]",
        r"bolsa rota",
        r"convuls[aã]o",
        r"press[aã]o (muito )?alta",
    )
    emergency = any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in emergency_phrases)
    urgency = "emergencia" if emergency else ("alta" if alarms else "moderada")
    risk_factors = [f"alarme:{item}" for item in alarms]
    updated = {
        **state,
        "risk_factors": risk_factors,
        "urgency": urgency,
        "final_risk": urgency,
        "route": "emergency" if urgency in {"alta", "emergencia"} else "nonEmergency",
    }
    return add_trace(updated, "assessObstetricRisk", "ok", f"Risco obstetrico classificado como {urgency}.")


def specific_guidance(state: ClinicalGraphState) -> ClinicalGraphState:
    state = retrieve_rag_context_safe(state, k=3)
    if state.get("urgency") in {"alta", "emergencia"}:
        text = "Sinais de alarme gestacional exigem avaliacao imediata em maternidade ou pronto-socorro."
    else:
        text = "Orientacao obstetrica inicial: manter acompanhamento pre-natal e observar evolucao dos sintomas."
    updated = append_output(state, text)
    return add_trace(updated, "specificGuidance", "ok", "Orientacao obstetrica especifica gerada.")


def schedule_obstetric_exams(state: ClinicalGraphState) -> ClinicalGraphState:
    exams = ["consulta pre-natal"]
    if state.get("urgency") in {"alta", "emergencia"}:
        exams.append("avaliacao obstetrica imediata")
    else:
        exams.extend(["exames de rotina conforme idade gestacional", "revisao de sinais vitais"])
    updated = {**state, "due_exams": exams}
    updated = append_output(updated, "Exames/avaliacoes: " + "; ".join(exams) + ".")
    return add_trace(updated, "scheduleObstetricExams", "ok", f"{len(exams)} avaliacao(oes) obstetricas sugeridas.")


def urgency_alerts(state: ClinicalGraphState) -> ClinicalGraphState:
    if state.get("urgency") in {"alta", "emergencia"}:
        updated = append_output(
            state,
            "Alerta: se houver sangramento intenso, perda de liquido, dor forte, pressao alta ou reducao de movimentos fetais, procure atendimento imediatamente.",
        )
        return add_trace(
            updated,
            "urgencyAlerts",
            "ok",
            "Alerta de urgencia obstetrica acionado.",
            ["urgent_referral", "human_review_required"],
        )
    updated = append_output(state, "Sem red flags maiores no relato, mas manter vigilancia e retorno se houver piora.")
    return add_trace(updated, "urgencyAlerts", "ok", "Sem emergencia obstetrica pelo relato atual.")


def continuous_support(state: ClinicalGraphState) -> ClinicalGraphState:
    priority = "imediato" if state.get("urgency") in {"alta", "emergencia"} else "rotina"
    updated = {**state, "appointment_priority": priority}
    updated = append_output(updated, f"Seguimento: atendimento {priority}, com revisao por equipe obstetrica.")
    return add_trace(updated, "continuousSupport", "ok", f"Seguimento {priority} definido.")


def build_graph():
    graph = StateGraph(ClinicalGraphState)
    graph.add_node("ingestPregnancyData", ingest_pregnancy_data)
    graph.add_node("assessObstetricRisk", assess_obstetric_risk)
    graph.add_node("specificGuidance", specific_guidance)
    graph.add_node("scheduleObstetricExams", schedule_obstetric_exams)
    graph.add_node("urgencyAlerts", urgency_alerts)
    graph.add_node("continuousSupport", continuous_support)
    graph.add_node("validate", validate_final_response)
    graph.set_entry_point("ingestPregnancyData")
    graph.add_edge("ingestPregnancyData", "assessObstetricRisk")
    graph.add_edge("assessObstetricRisk", "specificGuidance")
    graph.add_edge("specificGuidance", "scheduleObstetricExams")
    graph.add_edge("scheduleObstetricExams", "urgencyAlerts")
    graph.add_edge("urgencyAlerts", "continuousSupport")
    graph.add_edge("continuousSupport", "validate")
    graph.add_edge("validate", END)
    return graph.compile()


__all__ = ["build_graph"]
