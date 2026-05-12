"""Benchmark reprodutivel da Fase I (IA-I4).

Executa os casos de `data/evaluation_cases.jsonl` cobrindo dados, RAG,
safety, LangGraph e resposta final. O benchmark usa `model_version` stub-safe
para manter o gate deterministico e offline; a integracao real com Ollama segue
validada pela Fase G.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib import error, request

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase3_orquestracao.rag_chain import (
    VECTORSTORE_INDEX_PATH,
    RagDataError,
    build_vectorstore,
    retrieve_context,
)
from fase4_seguranca.safety_guard import SafetyGuard
from fase5_avaliacao.evaluation_cases import (
    BENCHMARK_RESULTS_PATH,
    EvaluationCase,
    contains_all,
    contains_any,
    ensure_minimum_coverage,
    group_by_flow,
    load_evaluation_cases,
)
from fase5_avaliacao.graph_tests import run_evaluation_case


@dataclass
class BenchmarkCaseResult:
    case_id: str
    flow_id: str
    tags: list[str]
    latency_ms: float
    data_ok: bool
    safety_ok: bool
    rag_ok: bool
    graph_ok: bool
    response_ok: bool
    passed: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)


def _expect_tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return (str(value),)


def _check_safety(case: EvaluationCase, guard: SafetyGuard) -> tuple[bool, list[str], dict[str, Any]]:
    expected = case.safety_expectations
    if not expected:
        return True, [], {}

    verdict = guard.evaluate(
        case.message,
        scope=str(expected.get("scope") or "input"),  # type: ignore[arg-type]
        flow_id=case.flow_id,
    )
    failures: list[str] = []
    flags = set(verdict.safety_flags)

    if "expectedBlocked" in expected and bool(expected["expectedBlocked"]) != verdict.blocked:
        failures.append(f"safety.blocked esperado={expected['expectedBlocked']} recebido={verdict.blocked}")
    if expected.get("expectedHumanReview") and not verdict.requires_human_review:
        failures.append("safety.requires_human_review esperado")

    required_flags = set(_expect_tuple(expected.get("requiredSafetyFlags")))
    if not required_flags.issubset(flags):
        failures.append(f"safety.flags faltando={sorted(required_flags - flags)}")

    forbidden_flags = set(_expect_tuple(expected.get("forbiddenSafetyFlags")))
    present_forbidden = forbidden_flags & flags
    if present_forbidden:
        failures.append(f"safety.flags proibidas={sorted(present_forbidden)}")

    expected_categories = set(_expect_tuple(expected.get("expectedCategories")))
    categories = set(verdict.categories)
    if not expected_categories.issubset(categories):
        failures.append(f"safety.categories faltando={sorted(expected_categories - categories)}")

    return (
        not failures,
        failures,
        {
            "blocked": verdict.blocked,
            "requires_human_review": verdict.requires_human_review,
            "flags": sorted(flags),
            "categories": sorted(categories),
        },
    )


def _ensure_vectorstore() -> None:
    if not VECTORSTORE_INDEX_PATH.exists():
        build_vectorstore()


def _check_rag(case: EvaluationCase) -> tuple[bool, list[str], dict[str, Any]]:
    expected = case.rag_expectations
    if not expected:
        return True, [], {}

    try:
        _ensure_vectorstore()
        results = retrieve_context(case.message, case.flow_id, k=3)
    except (RagDataError, ValueError) as exc:
        return False, [f"rag.error={exc}"], {}

    failures: list[str] = []
    min_results = int(expected.get("minResults") or 1)
    if len(results) < min_results:
        failures.append(f"rag.resultados {len(results)} < {min_results}")

    expected_domain = expected.get("expectedDomain")
    if results and expected_domain and results[0].get("domain") != expected_domain:
        failures.append(f"rag.top1_domain esperado={expected_domain} recebido={results[0].get('domain')}")

    return (
        not failures,
        failures,
        {
            "results": len(results),
            "top_domain": results[0].get("domain") if results else None,
            "top_score": results[0].get("score") if results else None,
            "top_citation": results[0].get("citation") if results else None,
        },
    )


def _check_response(case: EvaluationCase, response: str) -> tuple[bool, list[str]]:
    expected = case.response_expectations
    failures: list[str] = []
    missing = contains_all(response, _expect_tuple(expected.get("mustInclude")))
    if missing:
        failures.append(f"response.termos_ausentes={missing}")
    forbidden = contains_any(response, _expect_tuple(expected.get("mustNotInclude")))
    if forbidden:
        failures.append(f"response.termos_proibidos={forbidden}")
    if not response.strip():
        failures.append("response.vazia")
    return not failures, failures


def _parse_sse_events(raw: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in raw.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].lstrip())
        payload_text = "\n".join(data_lines)
        try:
            payload = json.loads(payload_text) if payload_text else {}
        except json.JSONDecodeError:
            payload = {"_raw": payload_text}
        events.append((event_name, payload))
    return events


def _post_sse_case(
    *,
    api_url: str,
    case: EvaluationCase,
    timeout_seconds: float,
    api_key: str | None = None,
) -> tuple[list[tuple[str, dict[str, Any]]], str]:
    url = api_url.rstrip("/") + "/v1/chat/stream"
    payload = {
        "flowId": case.flow_id,
        "messages": [{"role": "user", "content": case.message}],
        "patientContext": case.patient_context,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} em {url}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Falha ao conectar em {url}: {exc.reason}") from exc
    return _parse_sse_events(raw), raw


def _check_http_case(
    case: EvaluationCase,
    *,
    api_url: str,
    timeout_seconds: float,
    api_key: str | None,
) -> tuple[bool, bool, list[str], dict[str, Any], str]:
    """Valida resposta final e contrato SSE via `POST /v1/chat/stream`."""

    failures: list[str] = []
    events, raw = _post_sse_case(
        api_url=api_url,
        case=case,
        timeout_seconds=timeout_seconds,
        api_key=api_key,
    )
    names = [name for name, _ in events]
    required_events = ("meta", "log", "token", "explain", "trace", "done")
    missing_events = [event_name for event_name in required_events if event_name not in names]
    if missing_events:
        failures.append(f"http_sse.eventos_ausentes={missing_events}")
    if names and names[0] != "meta":
        failures.append(f"http_sse.primeiro_evento={names[0]}; esperado=meta")
    if names and names[-1] != "done":
        failures.append(f"http_sse.ultimo_evento={names[-1]}; esperado=done")
    if "error" in names:
        error_payload = next(payload for name, payload in events if name == "error")
        failures.append(f"http_sse.error={error_payload}")

    meta = next((payload for name, payload in events if name == "meta"), {})
    if meta.get("flowId") != case.flow_id:
        failures.append(f"http_sse.flowId esperado={case.flow_id} recebido={meta.get('flowId')}")
    if not str(meta.get("modelVersion", "")).strip():
        failures.append("http_sse.modelVersion vazio")

    response_text = "".join(
        str(payload.get("delta", "")) for name, payload in events if name == "token"
    )
    response_ok, response_failures = _check_response(case, response_text)
    failures.extend(response_failures)

    trace_payload = next((payload for name, payload in events if name == "trace"), {})
    trace_nodes = [
        str(node.get("name", ""))
        for node in trace_payload.get("nodes", [])
        if isinstance(node, dict)
    ]
    graph = case.graph_expectations
    required_nodes = _expect_tuple(graph.get("requiredNodes"))
    missing_nodes = [node for node in required_nodes if node not in trace_nodes]
    if missing_nodes:
        failures.append(f"http_sse.trace_nodes_ausentes={missing_nodes}")

    expected_urgency = _expect_tuple(graph.get("expectedUrgency"))
    urgency = meta.get("urgencia")
    if expected_urgency and urgency not in expected_urgency:
        failures.append(f"http_sse.urgencia esperada={expected_urgency} recebida={urgency}")

    metrics = {
        "execution_mode": "http_sse",
        "api_url": api_url,
        "events": names,
        "model_version": meta.get("modelVersion"),
        "urgency": urgency,
        "trace_nodes": trace_nodes,
        "response_chars": len(response_text),
        "raw_sse_bytes": len(raw.encode("utf-8")),
    }
    graph_ok = not [failure for failure in failures if failure.startswith("http_sse.")]
    return graph_ok, response_ok, failures, metrics, response_text


def run_benchmark(
    output_path: Path = BENCHMARK_RESULTS_PATH,
    *,
    via_http: bool = False,
    api_url: str | None = None,
    http_timeout_seconds: float = 90.0,
    api_key: str | None = None,
) -> dict[str, Any]:
    cases = load_evaluation_cases()
    ensure_minimum_coverage(cases, min_cases_per_flow=4)
    guard = SafetyGuard.from_yaml()

    results: list[BenchmarkCaseResult] = []
    for case in cases:
        started = time.perf_counter()
        failures: list[str] = []

        safety_ok, safety_failures, safety_metrics = _check_safety(case, guard)
        failures.extend(safety_failures)

        rag_ok, rag_failures, rag_metrics = _check_rag(case)
        failures.extend(rag_failures)

        if via_http:
            try:
                graph_ok, response_ok, http_failures, execution_metrics, response_text = _check_http_case(
                    case,
                    api_url=api_url or os.environ.get("ORCHESTRATION_API_URL", "http://127.0.0.1:8000"),
                    timeout_seconds=http_timeout_seconds,
                    api_key=api_key or os.environ.get("ORCHESTRATION_API_KEY"),
                )
            except RuntimeError as exc:
                graph_ok = False
                response_ok = False
                response_text = ""
                execution_metrics = {"execution_mode": "http_sse", "error": str(exc)}
                http_failures = [f"http_sse.error={exc}"]
            failures.extend(http_failures)
        else:
            graph_result = run_evaluation_case(case)
            graph_ok = graph_result.passed
            failures.extend(f"graph.{failure}" for failure in graph_result.failures)
            response_ok, response_failures = _check_response(case, graph_result.response)
            failures.extend(f"response.{failure}" for failure in response_failures)
            response_text = graph_result.response
            execution_metrics = {
                "execution_mode": "in_process",
                "trace_nodes": graph_result.trace_nodes,
                "urgency": graph_result.urgency,
                "safety_flags": graph_result.safety_flags,
                "response_chars": graph_result.response_chars,
            }

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        passed = safety_ok and rag_ok and graph_ok and response_ok
        results.append(
            BenchmarkCaseResult(
                case_id=case.id,
                flow_id=case.flow_id,
                tags=list(case.tags),
                latency_ms=latency_ms,
                data_ok=True,
                safety_ok=safety_ok,
                rag_ok=rag_ok,
                graph_ok=graph_ok,
                response_ok=response_ok,
                passed=passed,
                metrics={
                    "safety": safety_metrics,
                    "rag": rag_metrics,
                    "execution": execution_metrics,
                    "response_chars": len(response_text),
                },
                failures=failures,
            )
        )

    latencies = [result.latency_ms for result in results]
    grouped = group_by_flow(cases)
    payload = {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_cases": "data/evaluation_cases.jsonl",
        "execution_mode": "http_sse" if via_http else "in_process",
        "output_path": str(output_path),
        "summary": {
            "total_cases": len(results),
            "passed_cases": sum(1 for result in results if result.passed),
            "failed_cases": sum(1 for result in results if not result.passed),
            "pass_rate": round(sum(1 for result in results if result.passed) / len(results), 4),
            "safety_pass_rate": round(sum(1 for result in results if result.safety_ok) / len(results), 4),
            "rag_pass_rate": round(sum(1 for result in results if result.rag_ok) / len(results), 4),
            "graph_pass_rate": round(sum(1 for result in results if result.graph_ok) / len(results), 4),
            "response_pass_rate": round(sum(1 for result in results if result.response_ok) / len(results), 4),
            "latency_ms_avg": round(statistics.fmean(latencies), 2),
            "latency_ms_p95": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 2),
            "cases_per_flow": {flow_id: len(flow_cases) for flow_id, flow_cases in grouped.items()},
        },
        "results": [asdict(result) for result in results],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark objetivo da Fase I.")
    parser.add_argument("--output", type=Path, default=BENCHMARK_RESULTS_PATH)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--via-http",
        action="store_true",
        help="Executa o benchmark contra POST /v1/chat/stream em ORCHESTRATION_API_URL.",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="Base URL do IA Core para --via-http (default: ORCHESTRATION_API_URL ou http://127.0.0.1:8000).",
    )
    parser.add_argument("--http-timeout", type=float, default=90.0)
    args = parser.parse_args()

    payload = run_benchmark(
        output_path=args.output,
        via_http=args.via_http,
        api_url=args.api_url,
        http_timeout_seconds=args.http_timeout,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        summary = payload["summary"]
        print(f"Benchmark salvo em: {args.output}")
        print(
            "Resumo: "
            f"{summary['passed_cases']}/{summary['total_cases']} casos passaram "
            f"(pass_rate={summary['pass_rate']:.2%}, "
            f"lat_avg={summary['latency_ms_avg']}ms, "
            f"lat_p95={summary['latency_ms_p95']}ms)."
        )
        for result in payload["results"]:
            status = "PASS" if result["passed"] else "FAIL"
            print(f"[{status}] {result['case_id']} ({result['flow_id']})")
            for failure in result["failures"]:
                print(f"  - {failure}")

    return 0 if payload["summary"]["failed_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

