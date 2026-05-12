"""Helpers compartilhados dos grafos LangGraph da Fase F.

Atende IA-F1:

- Define o formato de estado usado pelos quatro grafos clinicos.
- Centraliza trace resumido e seguro, sem conteudo sensivel completo.
- Encapsula SafetyGuard, ResponseValidator, RAG opcional e ExplainBlock.

Os grafos retornam dicionarios para manter compatibilidade com LangGraph e
com os schemas Pydantic ja definidos em `fase3_orquestracao.schemas`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, NotRequired, TypedDict

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase3_orquestracao.rag_chain import RagDataError, retrieve_context
from fase3_orquestracao.schemas import ExplainBlock, TraceNode, TraceSummary
from fase4_seguranca.audit import redact_text
from fase4_seguranca.explainability import build_explain_block
from fase4_seguranca.response_validator import ResponseValidator, ValidationResult
from fase4_seguranca.safety_guard import SafetyGuard, SafetyVerdict


ClinicalFlowId = str


class ClinicalGraphState(TypedDict, total=False):
    """Estado mutavel usado pelo LangGraph em todos os fluxos."""

    flow_id: ClinicalFlowId
    user_input: str
    patient_context: dict[str, Any]
    model_version: str | None
    trace: list[dict[str, Any]]
    safety_flags: list[str]
    input_verdict: SafetyVerdict
    validation_result: ValidationResult
    rag_results: list[dict[str, Any]]
    explain: dict[str, Any]
    urgency: str
    final_risk: str
    route: str
    output_parts: list[str]
    final_response: str
    audit_summary: dict[str, Any]
    gaps: list[str]
    symptoms: list[str]
    risk_factors: list[str]
    due_exams: list[str]
    next_steps: list[str]
    appointment_priority: str
    specialized_team_notified: bool
    secure_documentation: bool
    guard: NotRequired[SafetyGuard]
    validator: NotRequired[ResponseValidator]


_ALARM_PATTERNS: dict[str, tuple[str, ...]] = {
    "bleeding": (r"sangramento", r"hemorrag", r"co[aá]gulo"),
    "pain": (r"dor (forte|intensa|no peito|abdominal)", r"pelvica intensa"),
    "pregnancy": (r"gravidez", r"gestante", r"beb[eê]", r"bolsa rota"),
    "violence": (r"viol[eê]ncia", r"agress", r"amea[cç]a", r"me bate"),
    "self_harm": (r"suicid", r"me matar", r"me machucar", r"n[aã]o quero.*viver"),
}


def make_initial_state(
    *,
    flow_id: str,
    user_input: str,
    patient_context: Mapping[str, Any] | None = None,
    model_version: str | None = None,
    guard: SafetyGuard | None = None,
) -> ClinicalGraphState:
    """Cria o estado inicial dos grafos.

    O guard/validator pode ser injetado em testes, mas por padrao carrega o
    YAML real da Fase E.
    """

    active_guard = guard or SafetyGuard.from_yaml()
    return {
        "flow_id": flow_id,
        "user_input": user_input,
        "patient_context": dict(patient_context or {}),
        "model_version": model_version,
        "trace": [],
        "safety_flags": [],
        "rag_results": [],
        "urgency": "nenhuma",
        "final_risk": "nenhuma",
        "route": "nonEmergency",
        "output_parts": [],
        "gaps": [],
        "symptoms": [],
        "risk_factors": [],
        "due_exams": [],
        "next_steps": [],
        "appointment_priority": "rotina",
        "specialized_team_notified": False,
        "secure_documentation": False,
        "guard": active_guard,
        "validator": ResponseValidator(guard=active_guard),
    }


def merge_flags(*sources: Iterable[str] | None) -> list[str]:
    """Une flags preservando ordem e removendo duplicatas."""

    merged: list[str] = []
    for source in sources:
        for flag in source or ():
            if flag and flag not in merged:
                merged.append(flag)
    return merged


def sanitize_trace_summary(
    summary: str,
    *,
    flow_id: str | None = None,
    safety_flags: Iterable[str] | None = None,
) -> str:
    """Reduz o texto do trace e redige fluxos/categorias sensiveis."""

    flags = list(safety_flags or ())
    categories: list[str] = []
    if "violence_protocol" in flags:
        categories.append("violence")
    if "self_harm_escalation" in flags:
        categories.append("self_harm")
    redacted = redact_text(summary, flow_id=flow_id, categories=categories)
    if redacted == "[REDACTED:sensitive_content]":
        return "Conteudo sensivel redigido; encaminhamento seguro registrado."
    normalized = re.sub(r"\s+", " ", redacted or "").strip()
    if len(normalized) > 140:
        return normalized[:137].rstrip() + "..."
    return normalized


def add_trace(
    state: ClinicalGraphState,
    name: str,
    status: str = "ok",
    summary: str = "",
    safety_flags: Iterable[str] | None = None,
) -> ClinicalGraphState:
    """Adiciona um no ao trace, sem expor conteudo sensivel completo."""

    flags = merge_flags(state.get("safety_flags", []), safety_flags or [])
    node = TraceNode(
        name=name,
        status=status,  # type: ignore[arg-type]
        summary=sanitize_trace_summary(
            summary,
            flow_id=state.get("flow_id"),
            safety_flags=flags,
        ),
        safetyFlags=flags,
    )
    return {
        **state,
        "trace": [*state.get("trace", []), node.model_dump()],
        "safety_flags": flags,
    }


def evaluate_input_safety(state: ClinicalGraphState) -> ClinicalGraphState:
    """Executa SafetyGuard de input e propaga flags para o estado."""

    guard = state["guard"]
    verdict = guard.evaluate(
        state.get("user_input", ""),
        scope="input",
        flow_id=state.get("flow_id"),
    )
    return {
        **state,
        "input_verdict": verdict,
        "safety_flags": merge_flags(state.get("safety_flags", []), verdict.safety_flags),
    }


def retrieve_rag_context_safe(
    state: ClinicalGraphState,
    *,
    query: str | None = None,
    k: int = 3,
) -> ClinicalGraphState:
    """Recupera RAG se o indice existir; caso contrario registra lacuna."""

    try:
        results = retrieve_context(
            query or state.get("user_input", ""),
            state.get("flow_id", ""),
            k=k,
        )
        return {**state, "rag_results": results}
    except (RagDataError, ValueError) as exc:
        gaps = [*state.get("gaps", []), f"RAG indisponivel: {exc}"]
        return {**state, "rag_results": [], "gaps": gaps}


def append_output(state: ClinicalGraphState, text: str) -> ClinicalGraphState:
    """Acrescenta trecho deterministicamente ao rascunho de resposta."""

    return {**state, "output_parts": [*state.get("output_parts", []), text.strip()]}


def validate_final_response(state: ClinicalGraphState) -> ClinicalGraphState:
    """Valida a resposta final com IA-E3 e gera ExplainBlock."""

    validator = state["validator"]
    draft = "\n\n".join(part for part in state.get("output_parts", []) if part)
    result = validator.validate(
        draft,
        flow_id=state.get("flow_id"),
        input_verdict=state.get("input_verdict"),
    )
    flags = merge_flags(state.get("safety_flags", []), result.safety_flags)
    explain = build_explain_block(
        flow_id=state.get("flow_id"),
        rag_results=state.get("rag_results", []),
        patient_context=state.get("patient_context", {}),
        safety_flags=flags,
        urgency=state.get("urgency"),
        extra_gaps=state.get("gaps", []),
    )
    updated: ClinicalGraphState = {
        **state,
        "validation_result": result,
        "final_response": result.text,
        "safety_flags": flags,
        "explain": explain.model_dump(),
    }
    return add_trace(
        updated,
        "validate",
        "blocked" if result.blocked else "ok",
        "Resposta validada por guardrails de saida.",
        flags,
    )


def trace_summary(state: ClinicalGraphState) -> TraceSummary:
    """Converte o trace interno em schema Pydantic da Fase A."""

    nodes = [TraceNode(**node) for node in state.get("trace", [])]
    return TraceSummary(
        flowId=state["flow_id"],  # type: ignore[arg-type]
        nodes=nodes,
        finalRisk=state.get("final_risk") or state.get("urgency"),  # type: ignore[arg-type]
    )


def explain_block(state: ClinicalGraphState) -> ExplainBlock:
    """Retorna ExplainBlock tipado a partir do estado final."""

    payload = state.get("explain") or build_explain_block(
        flow_id=state.get("flow_id"),
        rag_results=state.get("rag_results", []),
        patient_context=state.get("patient_context", {}),
        safety_flags=state.get("safety_flags", []),
        urgency=state.get("urgency"),
        extra_gaps=state.get("gaps", []),
    ).model_dump()
    return ExplainBlock(**payload)


def contains_any(text: str, patterns: Iterable[str]) -> bool:
    """Helper simples de regex case-insensitive para heuristicas clinicas."""

    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def alarm_hits(text: str, *groups: str) -> list[str]:
    """Retorna grupos de sinais de alarme presentes no texto."""

    hits: list[str] = []
    for group in groups:
        patterns = _ALARM_PATTERNS.get(group, ())
        if contains_any(text, patterns):
            hits.append(group)
    return hits


__all__ = [
    "ClinicalGraphState",
    "add_trace",
    "alarm_hits",
    "append_output",
    "contains_any",
    "evaluate_input_safety",
    "explain_block",
    "make_initial_state",
    "merge_flags",
    "retrieve_rag_context_safe",
    "sanitize_trace_summary",
    "trace_summary",
    "validate_final_response",
]
