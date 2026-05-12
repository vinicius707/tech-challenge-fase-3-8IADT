"""Testes do `build_explain_block` (Fase E, IA-E4)."""

from __future__ import annotations

from fase3_orquestracao.schemas import ExplainBlock
from fase4_seguranca.explainability import build_explain_block


def _rag_results():
    return [
        {
            "doc_id": "doc-tri-001",
            "domain": "triagemGinecologica",
            "citation": "Protocolo sintetico v1",
            "version": "v1",
            "score": 0.88,
            "content": "Trecho exemplo",
        },
        {
            "doc_id": "doc-gen-001",
            "domain": "geral",
            "citation": "INCA 2025",
            "version": "2025",
            "score": 0.6,
            "content": "Outro trecho",
        },
    ]


def test_explain_block_includes_top_source_and_version():
    block = build_explain_block(
        flow_id="triagemGinecologica",
        rag_results=_rag_results(),
        patient_context={"resumo": "Paciente ficticia", "cicloMenstrual": {"ultimoCiclo": "10/04"}},
        urgency="moderada",
        safety_flags=["human_review_required"],
    )
    assert isinstance(block, ExplainBlock)
    assert "Protocolo sintetico v1" in block.fonte
    assert "v1" in block.fonte
    assert 0.0 < block.confianca <= 1.0


def test_explain_block_aggregates_confidence_within_bounds():
    block = build_explain_block(
        flow_id="prevencao",
        rag_results=[{"citation": "A", "version": "v1", "score": 1.5}],  # score acima de 1
        patient_context={"resumo": "Ficticia", "preventivos": {"papanicolau": "2024"}, "historicoReprodutivo": {}},
    )
    assert 0.0 <= block.confianca <= 1.0


def test_explain_block_marks_gaps_when_context_empty():
    block = build_explain_block(
        flow_id="prevencao",
        rag_results=[],
        patient_context=None,
        safety_flags=[],
    )
    assert block.fonte.startswith("Sem fonte")
    assert block.confianca <= 0.2
    assert any("contexto" in lacuna for lacuna in block.lacunas)
    assert "sem exame fisico" in block.lacunas
    assert "sem sinais vitais" in block.lacunas


def test_explain_block_flow_specific_gaps():
    block = build_explain_block(
        flow_id="obstetrico",
        rag_results=[{"citation": "X", "version": "v1", "score": 0.5}],
        patient_context={"resumo": "Paciente", "obstetrica": {}},
    )
    assert any("obstetric" in lacuna.lower() for lacuna in block.lacunas)


def test_reasoning_is_high_level_without_chain_of_thought():
    block = build_explain_block(
        flow_id="triagemGinecologica",
        rag_results=_rag_results(),
        patient_context={"resumo": "Paciente"},
        urgency="alta",
        safety_flags=["prescription_blocked", "human_review_required"],
    )
    assert block.raciocinioClinico is not None
    text_lower = block.raciocinioClinico.lower()
    forbidden_markers = ("passo a passo", "chain of thought", "raciocinio detalhado", "etapa 1")
    assert not any(marker in text_lower for marker in forbidden_markers)
    assert "triagem ginecologica" in text_lower
    assert "urgencia alta" in text_lower


def test_extra_gaps_are_merged_without_duplicates():
    block = build_explain_block(
        flow_id="triagemGinecologica",
        rag_results=_rag_results(),
        patient_context={"resumo": "Paciente"},
        extra_gaps=["sem exame fisico", "sem ultrassom recente"],
    )
    assert block.lacunas.count("sem exame fisico") == 1
    assert "sem ultrassom recente" in block.lacunas
