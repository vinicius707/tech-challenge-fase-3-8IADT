"""Testes de avaliacao RAG da Fase C.

Gate IA-C4:
    python fase5_avaliacao/rag_tests.py

Este script usa apenas fontes presentes em `data/rag_documents.jsonl` e o index
persistido em `outputs/vectorstore/rag_index.json`.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase3_orquestracao.rag_chain import (  # noqa: E402
    RAG_DOCUMENTS_PATH,
    VECTORSTORE_INDEX_PATH,
    RagDataError,
    build_vectorstore,
    load_rag_documents,
    retrieve_context,
)


CASES = [
    {
        "id": "rag_triagem_001",
        "flow_id": "triagemGinecologica",
        "query": "dor pelvica intensa e sangramento fora do periodo menstrual",
        "expected_domain": "triagemGinecologica",
    },
    {
        "id": "rag_violencia_001",
        "flow_id": "violenciaDomestica",
        "query": "paciente tem medo do parceiro e relata lesoes recorrentes",
        "expected_domain": "violenciaDomestica",
    },
    {
        "id": "rag_obstetrico_001",
        "flow_id": "obstetrico",
        "query": "gestante com sangramento vaginal e dor abdominal forte",
        "expected_domain": "obstetrico",
    },
    {
        "id": "rag_prevencao_001",
        "flow_id": "prevencao",
        "query": "preventivo atrasado sem sintomas qual orientacao inicial",
        "expected_domain": "prevencao",
    },
]

REQUIRED_RESULT_FIELDS = {
    "doc_id",
    "domain",
    "source",
    "version",
    "sensitivity",
    "citation",
    "fonte",
    "score",
    "trecho",
}


def _ensure_phase_b_data() -> None:
    if not RAG_DOCUMENTS_PATH.exists():
        raise RagDataError(
            f"Arquivo RAG ausente: {RAG_DOCUMENTS_PATH}. "
            "Execute a Fase B antes: `python fase1_dados/build_dataset.py`."
        )
    docs = load_rag_documents(RAG_DOCUMENTS_PATH)
    domains = {doc.metadata["domain"] for doc in docs}
    missing = {case["expected_domain"] for case in CASES} - domains
    if missing:
        raise RagDataError(
            f"`data/rag_documents.jsonl` nao cobre dominios obrigatorios: {sorted(missing)}. "
            "Reexecute `python fase1_dados/build_dataset.py` e `python fase1_dados/validate_data.py`."
        )


def run() -> None:
    _ensure_phase_b_data()
    if not VECTORSTORE_INDEX_PATH.exists():
        build_vectorstore()

    failures: list[str] = []
    for case in CASES:
        results = retrieve_context(case["query"], case["flow_id"], k=3)
        if not results:
            failures.append(f"{case['id']}: nenhum resultado")
            continue

        first = results[0]
        missing_fields = sorted(REQUIRED_RESULT_FIELDS - set(first))
        if missing_fields:
            failures.append(f"{case['id']}: campos ausentes no resultado: {missing_fields}")

        if first["domain"] != case["expected_domain"]:
            failures.append(
                f"{case['id']}: dominio esperado {case['expected_domain']}, recebido {first['domain']}"
            )

        if first["citation"] != first["fonte"]:
            failures.append(f"{case['id']}: `fonte` deve refletir `citation`")

        if not isinstance(first["score"], float):
            failures.append(f"{case['id']}: score deve ser float")

        if not str(first["trecho"]).strip():
            failures.append(f"{case['id']}: trecho vazio")

        print(
            f"PASS {case['id']} -> {first['domain']} | "
            f"score={first['score']:.4f} | fonte={first['fonte']}"
        )

    if failures:
        print("\nFalhas:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print(f"\nRAG tests PASS ({len(CASES)} casos)")


if __name__ == "__main__":
    run()
