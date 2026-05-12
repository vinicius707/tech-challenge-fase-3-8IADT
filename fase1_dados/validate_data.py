"""Valida os artefatos de dados gerados na Fase B.

Gate IA-B8:
    python fase1_dados/validate_data.py

O script verifica schema minimo, duplicatas, dominios aceitos, metadados de
RAG, formato chat para fine-tuning e cobertura minima dos quatro fluxos.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase1_dados.common import (
    ALLOWED_DOMAINS,
    NORMALIZED_PATH,
    RAG_DOCUMENTS_PATH,
    SYNTHETIC_PATH,
    TRAIN_PATH,
    VAL_PATH,
    VALIDATION_REPORT_PATH,
    ensure_dirs,
    iter_jsonl,
)
from fase5_avaliacao.evaluation_cases import (
    EVALUATION_CASES_PATH,
    ensure_minimum_coverage,
    load_evaluation_cases,
)

REQUIRED_FLOW_DOMAINS = {
    "triagemGinecologica",
    "violenciaDomestica",
    "obstetrico",
    "prevencao",
}

SENSITIVITY_VALUES = {"low", "medium", "high"}


class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.metrics: dict[str, Any] = {}

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors


def _require_fields(record: dict[str, Any], fields: set[str], *, label: str, result: ValidationResult) -> None:
    missing = sorted(field for field in fields if field not in record or record[field] in (None, ""))
    if missing:
        result.error(f"{label}: campos obrigatorios ausentes: {', '.join(missing)}")


def _validate_domain_and_sensitivity(record: dict[str, Any], *, label: str, result: ValidationResult) -> None:
    domain = record.get("domain")
    if domain not in ALLOWED_DOMAINS:
        result.error(f"{label}: dominio invalido: {domain!r}")
    sensitivity = record.get("sensitivity")
    if sensitivity not in SENSITIVITY_VALUES:
        result.error(f"{label}: sensitivity invalida: {sensitivity!r}")


def validate_normalized(path: Path, result: ValidationResult) -> list[dict[str, Any]]:
    if not path.exists():
        result.error(f"Arquivo normalizado nao encontrado: {path}")
        return []
    records = list(iter_jsonl(path))
    seen: set[str] = set()
    domains = Counter()
    for idx, record in enumerate(records, start=1):
        label = f"{path}:{idx}"
        _require_fields(
            record,
            {
                "id",
                "question",
                "answer",
                "domain",
                "source",
                "dataset_slug",
                "citation",
                "sensitivity",
                "include_for_training",
                "include_for_rag",
            },
            label=label,
            result=result,
        )
        _validate_domain_and_sensitivity(record, label=label, result=result)
        record_id = str(record.get("id", ""))
        if record_id in seen:
            result.error(f"{label}: id duplicado: {record_id}")
        seen.add(record_id)
        domains[str(record.get("domain"))] += 1
        if len(str(record.get("answer", ""))) < 20:
            result.warn(f"{label}: resposta curta demais para uso clinico/RAG")
    result.metrics["normalized_count"] = len(records)
    result.metrics["normalized_domains"] = dict(sorted(domains.items()))
    return records


def validate_synthetic(path: Path, result: ValidationResult) -> list[dict[str, Any]]:
    if not path.exists():
        result.error(f"Arquivo sintetico/curado nao encontrado: {path}")
        return []
    records = list(iter_jsonl(path))
    domains = Counter(str(record.get("domain")) for record in records)
    for idx, record in enumerate(records, start=1):
        label = f"{path}:{idx}"
        _require_fields(
            record,
            {
                "id",
                "question",
                "answer",
                "domain",
                "source",
                "citation",
                "sensitivity",
                "include_for_training",
                "include_for_rag",
            },
            label=label,
            result=result,
        )
        _validate_domain_and_sensitivity(record, label=label, result=result)
    missing_domains = sorted(REQUIRED_FLOW_DOMAINS - set(domains))
    if missing_domains:
        result.error(f"Sinteticos/curados nao cobrem dominios: {', '.join(missing_domains)}")
    result.metrics["synthetic_count"] = len(records)
    result.metrics["synthetic_domains"] = dict(sorted(domains.items()))
    return records


def validate_rag_documents(path: Path, result: ValidationResult) -> list[dict[str, Any]]:
    if not path.exists():
        result.error(f"Arquivo RAG nao encontrado: {path}")
        return []
    docs = list(iter_jsonl(path))
    seen: set[str] = set()
    domains = Counter()
    for idx, doc in enumerate(docs, start=1):
        label = f"{path}:{idx}"
        _require_fields(
            doc,
            {"doc_id", "title", "domain", "version", "source", "sensitivity", "content", "citation"},
            label=label,
            result=result,
        )
        doc_id = str(doc.get("doc_id", ""))
        if doc_id in seen:
            result.error(f"{label}: doc_id duplicado: {doc_id}")
        seen.add(doc_id)
        if doc.get("domain") == "excluir":
            result.error(f"{label}: documento RAG nao pode usar dominio excluir")
        _validate_domain_and_sensitivity(doc, label=label, result=result)
        if len(str(doc.get("content", ""))) < 80:
            result.warn(f"{label}: content curto para retrieval")
        domains[str(doc.get("domain"))] += 1
    missing_domains = sorted(REQUIRED_FLOW_DOMAINS - set(domains))
    if missing_domains:
        result.error(f"RAG nao cobre dominios obrigatorios: {', '.join(missing_domains)}")
    result.metrics["rag_documents_count"] = len(docs)
    result.metrics["rag_domains"] = dict(sorted(domains.items()))
    return docs


def validate_training_file(path: Path, result: ValidationResult, *, label_name: str) -> list[dict[str, Any]]:
    if not path.exists():
        result.error(f"Arquivo {label_name} nao encontrado: {path}")
        return []
    examples = list(iter_jsonl(path))
    for idx, example in enumerate(examples, start=1):
        label = f"{path}:{idx}"
        _require_fields(example, {"id", "domain", "sensitivity", "source", "messages"}, label=label, result=result)
        _validate_domain_and_sensitivity(example, label=label, result=result)
        messages = example.get("messages")
        if not isinstance(messages, list) or len(messages) < 3:
            result.error(f"{label}: messages deve conter system, user e assistant")
            continue
        roles = [message.get("role") for message in messages if isinstance(message, dict)]
        if roles[:3] != ["system", "user", "assistant"]:
            result.error(f"{label}: roles esperados system/user/assistant, recebido {roles!r}")
        for message in messages:
            if not isinstance(message, dict) or not str(message.get("content", "")).strip():
                result.error(f"{label}: mensagem sem content")
    result.metrics[f"{label_name}_count"] = len(examples)
    return examples


def validate_evaluation_cases(path: Path, result: ValidationResult) -> None:
    """Valida `data/evaluation_cases.jsonl` (IA-I1).

    A Fase I depende dos artefatos da Fase B, mas o gate indicado em
    `tasks.md` para IA-I1 continua sendo `validate_data`. Por isso o validador
    de dados também checa schema mínimo, unicidade e cobertura dos casos de
    avaliação quando o arquivo já faz parte da entrega.
    """

    if not path.exists():
        result.error(f"Arquivo de avaliacao nao encontrado: {path}")
        return

    try:
        cases = load_evaluation_cases(path)
        ensure_minimum_coverage(cases, min_cases_per_flow=4)
    except (OSError, ValueError) as exc:
        result.error(f"{path}: casos de avaliacao invalidos: {exc}")
        return

    tag_counter = Counter(tag for case in cases for tag in case.tags)
    flow_counter = Counter(case.flow_id for case in cases)
    required_tags = {"prescription", "urgency", "violence", "clinical_gap"}
    missing_tags = sorted(required_tags - set(tag_counter))
    if missing_tags:
        result.error(f"{path}: tags obrigatorias ausentes: {', '.join(missing_tags)}")

    for case in cases:
        label = f"{path}:{case.id}"
        if not case.safety_expectations:
            result.warn(f"{label}: sem expectations.safety")
        if not case.graph_expectations:
            result.warn(f"{label}: sem expectations.graph")
        if not case.rag_expectations:
            result.warn(f"{label}: sem expectations.rag")
        if not case.response_expectations:
            result.warn(f"{label}: sem expectations.response")

    result.metrics["evaluation_cases_count"] = len(cases)
    result.metrics["evaluation_cases_by_flow"] = dict(sorted(flow_counter.items()))
    result.metrics["evaluation_cases_tags"] = dict(sorted(tag_counter.items()))


def write_validation_report(result: ValidationResult) -> None:
    status = "PASS" if result.ok else "FAIL"
    lines = [
        "# Relatorio de Validacao de Dados",
        "",
        f"- Status: **{status}**",
        f"- Erros criticos: **{len(result.errors)}**",
        f"- Avisos: **{len(result.warnings)}**",
        "",
        "## Metricas",
        "",
    ]
    for key, value in sorted(result.metrics.items()):
        lines.append(f"- `{key}`: `{value}`")

    lines.extend(["", "## Erros", ""])
    lines.extend([f"- {error}" for error in result.errors] or ["- Nenhum."])
    lines.extend(["", "## Avisos", ""])
    lines.extend([f"- {warning}" for warning in result.warnings] or ["- Nenhum."])

    VALIDATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_REPORT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def validate_all() -> ValidationResult:
    ensure_dirs()
    result = ValidationResult()
    validate_normalized(NORMALIZED_PATH, result)
    validate_synthetic(SYNTHETIC_PATH, result)
    validate_rag_documents(RAG_DOCUMENTS_PATH, result)
    validate_training_file(TRAIN_PATH, result, label_name="train")
    validate_training_file(VAL_PATH, result, label_name="val")
    validate_evaluation_cases(EVALUATION_CASES_PATH, result)
    write_validation_report(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida dados gerados para IA Core.")
    parser.parse_args()
    result = validate_all()
    print(f"Status: {'PASS' if result.ok else 'FAIL'}")
    print(f"Relatorio: {VALIDATION_REPORT_PATH}")
    if result.errors:
        for error in result.errors:
            print(f"ERRO: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
