"""Gera `outputs/reports/avaliacao.md` a partir do benchmark da Fase I."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase5_avaliacao.benchmark import run_benchmark
from fase5_avaliacao.evaluation_cases import (
    BENCHMARK_RESULTS_PATH,
    EVALUATION_REPORT_PATH,
    FLOW_IDS,
    load_evaluation_cases,
)


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _load_or_run_benchmark(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return run_benchmark(output_path=path)


def _status(value: bool) -> str:
    return "PASS" if value else "FAIL"


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    results: list[dict[str, Any]] = payload["results"]
    cases = load_evaluation_cases()

    tags = Counter(tag for case in cases for tag in case.tags)
    by_flow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        by_flow[result["flow_id"]].append(result)

    lines: list[str] = [
        "# Relatório de Avaliação - IA Core",
        "",
        "Relatório gerado automaticamente pela Fase I (`fase5_avaliacao/generate_report.py`).",
        "",
        "## Escopo",
        "",
        "- Fonte dos casos: `data/evaluation_cases.jsonl`.",
        "- Resultado bruto: `outputs/reports/benchmark_results.json`.",
        "- Backend de avaliação: `stub-safe-0.1.0` para manter execução determinística e offline.",
        "- Componentes avaliados: dados dos casos, RAG, safety, LangGraph e resposta final.",
        "",
        "## Resumo Executivo",
        "",
        f"- Casos totais: **{summary['total_cases']}**.",
        f"- Casos aprovados: **{summary['passed_cases']}**.",
        f"- Casos reprovados: **{summary['failed_cases']}**.",
        f"- Taxa geral de aprovação: **{_pct(summary['pass_rate'])}**.",
        f"- Latência média por caso: **{summary['latency_ms_avg']} ms**.",
        f"- Latência p95: **{summary['latency_ms_p95']} ms**.",
        f"- Modo de execução do benchmark: **{payload.get('execution_mode', 'in_process')}**.",
        "",
        "## Métricas Objetivas",
        "",
        "| Métrica | Valor |",
        "|---|---:|",
        f"| Safety pass rate | {_pct(summary['safety_pass_rate'])} |",
        f"| RAG pass rate | {_pct(summary['rag_pass_rate'])} |",
        f"| LangGraph pass rate | {_pct(summary['graph_pass_rate'])} |",
        f"| Resposta final pass rate | {_pct(summary['response_pass_rate'])} |",
        f"| Casos por fluxo | {', '.join(f'{flow}={count}' for flow, count in summary['cases_per_flow'].items())} |",
        "",
        "## Cobertura dos Cenários",
        "",
        "| Categoria/tag | Quantidade |",
        "|---|---:|",
    ]

    for tag, count in sorted(tags.items()):
        lines.append(f"| `{tag}` | {count} |")

    lines.extend(
        [
            "",
            "Coberturas obrigatórias confirmadas:",
            "",
            "- Quatro fluxos clínicos: `triagemGinecologica`, `violenciaDomestica`, `obstetrico`, `prevencao`.",
            "- Prescrição: casos com tag `prescription`.",
            "- Urgência: casos com tag `urgency`.",
            "- Violência doméstica: casos com tag `violence`.",
            "- Lacunas clínicas/contexto incompleto: casos com tag `clinical_gap`.",
            "",
            "## Resultado por Fluxo",
            "",
        ]
    )

    for flow_id in FLOW_IDS:
        flow_results = by_flow.get(flow_id, [])
        passed = sum(1 for result in flow_results if result["passed"])
        lines.extend(
            [
                f"### {flow_id}",
                "",
                f"- Casos: {passed}/{len(flow_results)} aprovados.",
                "",
                "| Caso | Status | Safety | RAG | Grafo | Resposta | Urgência | Latência |",
                "|---|---|---|---|---|---|---|---:|",
            ]
        )
        for result in flow_results:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{result['case_id']}`",
                        _status(bool(result["passed"])),
                        _status(bool(result["safety_ok"])),
                        _status(bool(result["rag_ok"])),
                        _status(bool(result["graph_ok"])),
                        _status(bool(result["response_ok"])),
                        str(result["metrics"].get("execution", {}).get("urgency")),
                        f"{result['latency_ms']} ms",
                    ]
                )
                + " |"
            )
        lines.append("")

    failures = [result for result in results if result["failures"]]
    lines.extend(["## Falhas e Observações", ""])
    if not failures:
        lines.append("Nenhuma falha encontrada nos casos automatizados.")
    else:
        for result in failures:
            lines.append(f"- `{result['case_id']}` ({result['flow_id']}):")
            for failure in result["failures"]:
                lines.append(f"  - {failure}")

    lines.extend(
        [
            "",
            "## Reprodutibilidade",
            "",
            "Execute os gates abaixo a partir da raiz do repositório:",
            "",
            "```bash",
            "python fase5_avaliacao/safety_tests.py",
            "python fase5_avaliacao/graph_tests.py",
            "python fase5_avaliacao/benchmark.py",
            "python fase5_avaliacao/generate_report.py",
            "```",
            "",
            "O relatório não usa dados reais identificáveis; os casos são sintéticos e versionáveis.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_report(
    *,
    benchmark_path: Path = BENCHMARK_RESULTS_PATH,
    output_path: Path = EVALUATION_REPORT_PATH,
    force_benchmark: bool = True,
) -> Path:
    payload = run_benchmark(output_path=benchmark_path) if force_benchmark else _load_or_run_benchmark(benchmark_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report(payload), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera relatorio Markdown de avaliacao da Fase I.")
    parser.add_argument("--benchmark", type=Path, default=BENCHMARK_RESULTS_PATH)
    parser.add_argument("--output", type=Path, default=EVALUATION_REPORT_PATH)
    parser.add_argument(
        "--reuse-benchmark",
        action="store_true",
        help="Reusa benchmark_results.json existente se for JSON valido.",
    )
    args = parser.parse_args()

    output_path = generate_report(
        benchmark_path=args.benchmark,
        output_path=args.output,
        force_benchmark=not args.reuse_benchmark,
    )
    print(f"Relatorio gerado em: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

