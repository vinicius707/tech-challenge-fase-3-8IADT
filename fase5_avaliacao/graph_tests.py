"""Gate dos grafos LangGraph da Fase F.

Uso:

```bash
python fase5_avaliacao/graph_tests.py --flow triagemGinecologica
python fase5_avaliacao/graph_tests.py --flow violenciaDomestica
python fase5_avaliacao/graph_tests.py --flow obstetrico
python fase5_avaliacao/graph_tests.py --flow prevencao
```
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase3_orquestracao.clinical_router import ClinicalGraphResult, available_flows, route_clinical_flow


@dataclass(frozen=True)
class GraphCase:
    flow_id: str
    message: str
    patient_context: dict
    required_nodes: tuple[str, ...]
    min_nodes: int
    expected_urgency: tuple[str, ...] = ("nenhuma", "moderada", "alta", "emergencia")
    expected_flags: tuple[str, ...] = ()
    response_must_include: tuple[str, ...] = ()
    response_must_not_include: tuple[str, ...] = ()
    trace_must_not_include: tuple[str, ...] = ()


@dataclass
class GraphCaseResult:
    flow_id: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    trace_nodes: list[str] = field(default_factory=list)
    urgency: str | None = None
    safety_flags: list[str] = field(default_factory=list)


CASES: dict[str, GraphCase] = {
    "triagemGinecologica": GraphCase(
        flow_id="triagemGinecologica",
        message="Estou com dor no peito e dor pelvica intensa.",
        patient_context={"resumo": "Paciente ficticia", "cicloMenstrual": {"ultimoCiclo": "10/04"}},
        required_nodes=("collectSymptoms", "analyzeRisk", "classifyUrgency", "emergencyGuidance", "validate"),
        min_nodes=5,
        expected_urgency=("emergencia",),
        expected_flags=("urgent_referral", "human_review_required"),
        response_must_include=("pronto atendimento", "192"),
    ),
    "violenciaDomestica": GraphCase(
        flow_id="violenciaDomestica",
        message="Meu marido me bate em casa e tenho medo de voltar.",
        patient_context={"resumo": "Paciente ficticia em situacao sensivel"},
        required_nodes=(
            "captureAlertSignals",
            "assessViolenceRisk",
            "applySafetyProtocol",
            "notifySpecializedTeam",
            "secureDocumentation",
            "followUpPlan",
            "validate",
        ),
        min_nodes=7,
        expected_urgency=("alta",),
        expected_flags=("violence_protocol", "human_review_required", "sensitive"),
        response_must_include=("190", "180", "equipe qualificada"),
        trace_must_not_include=("marido", "bate", "medo de voltar"),
    ),
    "obstetrico": GraphCase(
        flow_id="obstetrico",
        message="Estou gravida de 34 semanas e nao sinto o bebe desde ontem.",
        patient_context={"resumo": "Gestante ficticia", "obstetrica": {"gestacoes": 1}},
        required_nodes=(
            "ingestPregnancyData",
            "assessObstetricRisk",
            "specificGuidance",
            "scheduleObstetricExams",
            "urgencyAlerts",
            "continuousSupport",
            "validate",
        ),
        min_nodes=7,
        expected_urgency=("alta", "emergencia"),
        expected_flags=("urgent_referral", "human_review_required"),
        response_must_include=("maternidade", "imediatamente"),
    ),
    "prevencao": GraphCase(
        flow_id="prevencao",
        message="Tenho 42 anos e quero saber se meu preventivo e mamografia estao em dia.",
        patient_context={
            "resumo": "Paciente ficticia",
            "preventivos": {"ultimoPreventivo": "2021"},
            "historicoReprodutivo": {"partos": 1},
        },
        required_nodes=(
            "loadPatientHistory",
            "identifyDueExams",
            "preventiveGuidance",
            "autoSchedulePrevention",
            "personalizedReminders",
            "validate",
        ),
        min_nodes=6,
        expected_urgency=("nenhuma", "moderada"),
        response_must_include=("rastreamento", "Agendamento"),
    ),
}


def _contains_all(haystack: str, needles: Iterable[str]) -> list[str]:
    lower = haystack.lower()
    return [needle for needle in needles if needle.lower() not in lower]


def _assert_case(case: GraphCase, result: ClinicalGraphResult) -> GraphCaseResult:
    trace_nodes = [node.name for node in result.trace.nodes]
    flags = list(result.safety_flags)
    failures: list[str] = []

    if len(trace_nodes) < case.min_nodes:
        failures.append(f"trace curto: {len(trace_nodes)} < {case.min_nodes}")
    missing_nodes = [node for node in case.required_nodes if node not in trace_nodes]
    if missing_nodes:
        failures.append(f"nos ausentes: {missing_nodes}")
    if result.urgency not in case.expected_urgency:
        failures.append(f"urgencia inesperada: {result.urgency}; esperado {case.expected_urgency}")
    missing_flags = [flag for flag in case.expected_flags if flag not in flags]
    if missing_flags:
        failures.append(f"flags ausentes: {missing_flags}; obtidas {flags}")
    missing_response = _contains_all(result.response, case.response_must_include)
    if missing_response:
        failures.append(f"resposta nao contem: {missing_response}")
    forbidden_response = [
        value for value in case.response_must_not_include if value.lower() in result.response.lower()
    ]
    if forbidden_response:
        failures.append(f"resposta contem termo proibido: {forbidden_response}")
    trace_text = json.dumps(result.trace.model_dump(), ensure_ascii=False).lower()
    forbidden_trace = [value for value in case.trace_must_not_include if value.lower() in trace_text]
    if forbidden_trace:
        failures.append(f"trace contem conteudo sensivel: {forbidden_trace}")
    if not result.explain.fonte:
        failures.append("ExplainBlock sem fonte")
    if not (0.0 <= result.explain.confianca <= 1.0):
        failures.append(f"confianca fora de [0,1]: {result.explain.confianca}")
    if not result.explain.lacunas:
        failures.append("ExplainBlock sem lacunas")

    return GraphCaseResult(
        flow_id=case.flow_id,
        passed=not failures,
        failures=failures,
        trace_nodes=trace_nodes,
        urgency=result.urgency,
        safety_flags=flags,
    )


def run_graph_case(flow_id: str) -> GraphCaseResult:
    if flow_id not in CASES:
        raise ValueError(f"flow invalido: {flow_id}. Disponiveis: {', '.join(available_flows())}")
    case = CASES[flow_id]
    result = route_clinical_flow(
        flow_id=case.flow_id,
        message=case.message,
        patient_context=case.patient_context,
        model_version="stub-safe-0.1.0",
    )
    return _assert_case(case, result)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate dos grafos LangGraph da Fase F.")
    parser.add_argument("--flow", choices=available_flows(), required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_graph_case(args.flow)
    if args.json:
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.flow_id}")
        print(f"  urgency: {result.urgency}")
        print(f"  safety_flags: {result.safety_flags}")
        print(f"  trace_nodes: {result.trace_nodes}")
        for failure in result.failures:
            print(f"  - {failure}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
