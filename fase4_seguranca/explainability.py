"""Explainability da Fase E (IA-E4).

Constroi o `ExplainBlock` enviado no evento SSE `explain` conforme
`docs/api.md` e `docs/sdd/ia-core/spec.md` §7 e o requisito IA-EXP-01:

- `fonte`           -> citacao/versao da principal fonte recuperada via RAG.
- `confianca`       -> agregacao das similaridades top-k (0.0 a 1.0).
- `lacunas`         -> lista de campos clinicos ausentes ou nao informados.
- `raciocinioClinico` -> resumo de alto nivel (sem chain-of-thought).

Decisoes de design:

- O modulo so depende dos schemas Pydantic existentes para reaproveitar o
  contrato de saida. Nao acoplamos a LangGraph ou ao LLM aqui.
- O texto de `raciocinioClinico` nunca cita conteudo sensivel: apenas o
  fluxo, urgencia, dominios de fonte e flags de safety em alto nivel.
- Quando nao ha fontes RAG, `fonte` cai em string padrao explicita e a
  confianca e baixa (proxima de zero).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase3_orquestracao.schemas import ExplainBlock


_NO_SOURCE_FONTE = "Sem fonte RAG disponivel"
_DEFAULT_CONFIDENCE_WITHOUT_SOURCES = 0.1
_PATIENT_FIELD_LABELS: dict[str, str] = {
    "resumo": "sem resumo clinico estruturado",
    "preventivos": "sem historico de exames preventivos",
    "obstetrica": "sem dados obstetricos",
    "cicloMenstrual": "sem informacoes do ciclo menstrual",
    "historicoReprodutivo": "sem historico reprodutivo registrado",
}
_FLOW_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "triagemGinecologica": ("resumo", "cicloMenstrual"),
    "violenciaDomestica": ("resumo",),
    "obstetrico": ("resumo", "obstetrica"),
    "prevencao": ("resumo", "preventivos", "historicoReprodutivo"),
}
_FLOW_HUMAN_LABEL: dict[str, str] = {
    "triagemGinecologica": "triagem ginecologica",
    "violenciaDomestica": "violencia domestica",
    "obstetrico": "obstetrico",
    "prevencao": "prevencao",
}
_URGENCY_LABEL: dict[str, str] = {
    "nenhuma": "sem urgencia identificada",
    "moderada": "urgencia moderada",
    "alta": "urgencia alta",
    "emergencia": "emergencia clinica",
}


def _safe_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _primary_source(rag_results: Sequence[Mapping[str, Any]]) -> str:
    if not rag_results:
        return _NO_SOURCE_FONTE
    top = rag_results[0]
    citation = str(top.get("citation") or "").strip()
    version = str(top.get("version") or "").strip()
    source = str(top.get("source") or "").strip()
    parts: list[str] = []
    if citation:
        parts.append(citation)
    elif source:
        parts.append(source)
    else:
        parts.append("Fonte sem citacao registrada")
    if version and version not in parts[0]:
        parts.append(version)
    return " / ".join(parts)


def _aggregate_confidence(rag_results: Sequence[Mapping[str, Any]]) -> float:
    if not rag_results:
        return _DEFAULT_CONFIDENCE_WITHOUT_SOURCES
    scores = [_safe_score(item.get("score")) for item in rag_results]
    if not scores:
        return _DEFAULT_CONFIDENCE_WITHOUT_SOURCES
    # Ponderacao: top-1 conta mais. Mantemos 0..1 e arredondamos a 2 casas.
    top_score = scores[0]
    avg = sum(scores) / len(scores)
    aggregate = (top_score * 0.7) + (avg * 0.3)
    return round(max(0.0, min(1.0, aggregate)), 2)


def _detect_patient_gaps(
    flow_id: str | None,
    patient_context: Mapping[str, Any] | None,
) -> list[str]:
    required = _FLOW_REQUIRED_FIELDS.get(flow_id or "", ())
    gaps: list[str] = []
    if patient_context is None:
        gaps.append("sem contexto clinico estruturado")
        return gaps
    for field_name in required:
        value = patient_context.get(field_name)
        empty = value is None or (
            isinstance(value, (list, dict, str)) and len(value) == 0
        )
        if empty:
            label = _PATIENT_FIELD_LABELS.get(field_name, f"sem `{field_name}`")
            if label not in gaps:
                gaps.append(label)
    return gaps


def _detect_clinical_gaps(rag_results: Sequence[Mapping[str, Any]]) -> list[str]:
    gaps: list[str] = []
    if not rag_results:
        gaps.append("nenhuma fonte RAG recuperada")
    gaps.append("sem exame fisico")
    gaps.append("sem sinais vitais")
    return gaps


def _summarize_sources(rag_results: Sequence[Mapping[str, Any]]) -> str:
    if not rag_results:
        return "sem fontes RAG"
    domains: list[str] = []
    for item in rag_results:
        domain = str(item.get("domain") or "").strip()
        if domain and domain not in domains:
            domains.append(domain)
    if not domains:
        return f"{len(rag_results)} fontes anonimas"
    return f"{len(rag_results)} fontes ({', '.join(domains)})"


def _safety_summary(safety_flags: Iterable[str] | None) -> str:
    flags = list(safety_flags or ())
    if not flags:
        return "sem flags de safety"
    visible = [f for f in flags if f != "sensitive"]
    if not visible:
        return "marcado como sensivel"
    return "flags: " + ", ".join(visible)


def _build_reasoning(
    *,
    flow_id: str | None,
    urgency: str | None,
    rag_results: Sequence[Mapping[str, Any]],
    safety_flags: Iterable[str] | None,
) -> str:
    flow_label = _FLOW_HUMAN_LABEL.get(flow_id or "", flow_id or "fluxo nao identificado")
    urgency_label = _URGENCY_LABEL.get(urgency or "", "urgencia nao classificada")
    sources_summary = _summarize_sources(rag_results)
    safety_part = _safety_summary(safety_flags)
    return (
        f"Fluxo {flow_label}; {urgency_label}. "
        f"Resposta combinou {sources_summary} com guardrails clinicos ({safety_part}). "
        "Resumo de alto nivel para auditoria; conteudo detalhado de raciocinio "
        "nao e exposto."
    )


def build_explain_block(
    *,
    flow_id: str | None,
    rag_results: Sequence[Mapping[str, Any]] | None = None,
    patient_context: Mapping[str, Any] | None = None,
    safety_flags: Iterable[str] | None = None,
    urgency: str | None = None,
    extra_gaps: Iterable[str] | None = None,
) -> ExplainBlock:
    """Monta o `ExplainBlock` final para o evento SSE `explain`."""
    sources = list(rag_results or [])
    fonte = _primary_source(sources)
    confianca = _aggregate_confidence(sources)

    gaps = _detect_patient_gaps(flow_id, patient_context)
    for gap in _detect_clinical_gaps(sources):
        if gap not in gaps:
            gaps.append(gap)
    for gap in extra_gaps or ():
        if gap and gap not in gaps:
            gaps.append(gap)

    raciocinio = _build_reasoning(
        flow_id=flow_id,
        urgency=urgency,
        rag_results=sources,
        safety_flags=safety_flags,
    )

    return ExplainBlock(
        fonte=fonte,
        confianca=confianca,
        lacunas=gaps,
        raciocinioClinico=raciocinio,
    )


__all__ = ["build_explain_block"]
