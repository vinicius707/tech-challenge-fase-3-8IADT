from __future__ import annotations

import json
from pathlib import Path

import pytest

from fase3_orquestracao.rag_chain import (
    RagDataError,
    build_vectorstore,
    load_rag_documents,
    retrieve_context,
)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def _rag_records() -> list[dict]:
    return [
        {
            "doc_id": "doc_prevencao_1",
            "title": "Prevencao",
            "domain": "prevencao",
            "version": "2026.05",
            "source": "fixture",
            "sensitivity": "low",
            "content": "Pergunta: preventivo atrasado. Resposta: orientar agendamento e revisar historico.",
            "citation": "Fixture prevencao",
        },
        {
            "doc_id": "doc_obstetrico_1",
            "title": "Obstetrico",
            "domain": "obstetrico",
            "version": "2026.05",
            "source": "fixture",
            "sensitivity": "medium",
            "content": "Pergunta: gestante com sangramento. Resposta: orientar atendimento obstetrico imediato.",
            "citation": "Fixture obstetrico",
        },
    ]


def test_load_rag_documents_preserva_metadados(tmp_path: Path):
    source = tmp_path / "rag_documents.jsonl"
    _write_jsonl(source, _rag_records())

    docs = load_rag_documents(source)

    assert len(docs) == 2
    assert docs[0].metadata["doc_id"] == "doc_prevencao_1"
    assert docs[0].metadata["domain"] == "prevencao"
    assert docs[0].metadata["source"] == "fixture"
    assert docs[0].metadata["version"] == "2026.05"
    assert docs[0].metadata["sensitivity"] == "low"
    assert docs[0].metadata["citation"] == "Fixture prevencao"


def test_load_rag_documents_falha_com_mensagem_clara_quando_arquivo_ausente(tmp_path: Path):
    with pytest.raises(RagDataError, match="Rode a Fase B"):
        load_rag_documents(tmp_path / "missing.jsonl")


def test_build_vectorstore_e_retrieve_context_filtram_por_dominio(tmp_path: Path):
    source = tmp_path / "rag_documents.jsonl"
    vectorstore_dir = tmp_path / "vectorstore"
    _write_jsonl(source, _rag_records())

    summary = build_vectorstore(documents_path=source, vectorstore_dir=vectorstore_dir)
    index_path = vectorstore_dir / "rag_index.json"

    assert summary["documents_count"] == 2
    assert summary["chunks_count"] == 2
    assert index_path.exists()

    results = retrieve_context(
        "gestante com sangramento vaginal",
        "obstetrico",
        k=1,
        index_path=index_path,
    )

    assert len(results) == 1
    assert results[0]["domain"] == "obstetrico"
    assert results[0]["source"] == "fixture"
    assert results[0]["version"] == "2026.05"
    assert results[0]["citation"] == "Fixture obstetrico"
    assert results[0]["fonte"] == "Fixture obstetrico"
    assert isinstance(results[0]["score"], float)
    assert "gestante" in results[0]["trecho"]


def test_retrieve_context_exige_vectorstore_existente(tmp_path: Path):
    with pytest.raises(RagDataError, match="--build"):
        retrieve_context("preventivo atrasado", "prevencao", index_path=tmp_path / "missing.json")
