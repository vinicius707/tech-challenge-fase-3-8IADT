"""Casos compartilhados da avaliacao automatizada da Fase I.

Este modulo centraliza o contrato de `data/evaluation_cases.jsonl` para que
`safety_tests.py`, `graph_tests.py`, `benchmark.py` e `generate_report.py`
usem exatamente a mesma base de cenarios.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_CASES_PATH = PROJECT_ROOT / "data" / "evaluation_cases.jsonl"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
BENCHMARK_RESULTS_PATH = REPORTS_DIR / "benchmark_results.json"
EVALUATION_REPORT_PATH = REPORTS_DIR / "avaliacao.md"

FLOW_IDS = (
    "triagemGinecologica",
    "violenciaDomestica",
    "obstetrico",
    "prevencao",
)


@dataclass(frozen=True)
class EvaluationCase:
    """Cenario versionavel de avaliacao objetiva."""

    id: str
    flow_id: str
    title: str
    message: str
    patient_context: dict[str, Any]
    tags: tuple[str, ...]
    expectations: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_record(cls, record: Mapping[str, Any], *, line_number: int) -> "EvaluationCase":
        missing = [field_name for field_name in ("id", "flowId", "title", "message") if not record.get(field_name)]
        if missing:
            raise ValueError(
                f"{EVALUATION_CASES_PATH}:{line_number}: campos obrigatorios ausentes: {missing}"
            )

        flow_id = str(record["flowId"])
        if flow_id not in FLOW_IDS:
            raise ValueError(
                f"{EVALUATION_CASES_PATH}:{line_number}: flowId invalido: {flow_id!r}"
            )

        patient_context = record.get("patientContext") or {}
        if not isinstance(patient_context, dict):
            raise ValueError(
                f"{EVALUATION_CASES_PATH}:{line_number}: patientContext deve ser objeto JSON"
            )

        tags_raw = record.get("tags") or ()
        if not isinstance(tags_raw, list):
            raise ValueError(f"{EVALUATION_CASES_PATH}:{line_number}: tags deve ser lista")

        expectations = record.get("expectations") or {}
        if not isinstance(expectations, dict):
            raise ValueError(
                f"{EVALUATION_CASES_PATH}:{line_number}: expectations deve ser objeto JSON"
            )

        return cls(
            id=str(record["id"]),
            flow_id=flow_id,
            title=str(record["title"]),
            message=str(record["message"]),
            patient_context=patient_context,
            tags=tuple(str(tag) for tag in tags_raw),
            expectations=expectations,
        )

    @property
    def safety_expectations(self) -> dict[str, Any]:
        return dict(self.expectations.get("safety") or {})

    @property
    def graph_expectations(self) -> dict[str, Any]:
        return dict(self.expectations.get("graph") or {})

    @property
    def rag_expectations(self) -> dict[str, Any]:
        return dict(self.expectations.get("rag") or {})

    @property
    def response_expectations(self) -> dict[str, Any]:
        return dict(self.expectations.get("response") or {})


def load_evaluation_cases(path: Path = EVALUATION_CASES_PATH) -> list[EvaluationCase]:
    """Carrega e valida `data/evaluation_cases.jsonl`."""

    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de casos nao encontrado: {path}. Crie a Fase I antes de rodar os gates."
        )

    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: JSON invalido") from exc
            case = EvaluationCase.from_record(record, line_number=line_number)
            if case.id in seen_ids:
                raise ValueError(f"{path}:{line_number}: id duplicado: {case.id}")
            seen_ids.add(case.id)
            cases.append(case)

    if not cases:
        raise ValueError(f"{path}: nenhum caso encontrado")
    return cases


def group_by_flow(cases: Iterable[EvaluationCase]) -> dict[str, list[EvaluationCase]]:
    grouped = {flow_id: [] for flow_id in FLOW_IDS}
    for case in cases:
        grouped.setdefault(case.flow_id, []).append(case)
    return grouped


def ensure_minimum_coverage(
    cases: Iterable[EvaluationCase],
    *,
    min_cases_per_flow: int = 4,
) -> None:
    """Valida os requisitos IA-I1/IA-I3 do arquivo de casos."""

    case_list = list(cases)
    grouped = group_by_flow(case_list)
    missing_flow_counts = {
        flow_id: len(flow_cases)
        for flow_id, flow_cases in grouped.items()
        if len(flow_cases) < min_cases_per_flow
    }
    if missing_flow_counts:
        raise ValueError(
            "evaluation_cases.jsonl precisa de pelo menos "
            f"{min_cases_per_flow} casos por fluxo; recebido {missing_flow_counts}"
        )

    required_tags = {"prescription", "urgency", "violence", "clinical_gap"}
    present_tags = {tag for case in case_list for tag in case.tags}
    missing_tags = sorted(required_tags - present_tags)
    if missing_tags:
        raise ValueError(f"evaluation_cases.jsonl sem tags obrigatorias: {missing_tags}")


def contains_all(text: str, expected_terms: Iterable[str]) -> list[str]:
    lower = (text or "").lower()
    return [term for term in expected_terms if term.lower() not in lower]


def contains_any(text: str, forbidden_terms: Iterable[str]) -> list[str]:
    lower = (text or "").lower()
    return [term for term in forbidden_terms if term.lower() in lower]

