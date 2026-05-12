"""Router clinico dos quatro grafos LangGraph (IA-F6)."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase3_orquestracao.graph_helpers import (
    ClinicalGraphState,
    explain_block,
    make_initial_state,
    trace_summary,
)
from fase3_orquestracao.graphs.obstetrico import build_graph as build_obstetric_graph
from fase3_orquestracao.graphs.prevencao import build_graph as build_prevention_graph
from fase3_orquestracao.graphs.triagem_ginecologica import build_graph as build_triage_graph
from fase3_orquestracao.graphs.violencia_domestica import build_graph as build_violence_graph
from fase3_orquestracao.schemas import ExplainBlock, TraceSummary


GraphFactory = Callable[[], Any]

GRAPH_FACTORIES: dict[str, GraphFactory] = {
    "triagemGinecologica": build_triage_graph,
    "violenciaDomestica": build_violence_graph,
    "obstetrico": build_obstetric_graph,
    "prevencao": build_prevention_graph,
}


class ClinicalRouterError(ValueError):
    """Erro de roteamento clinico recuperavel."""


@dataclass(frozen=True)
class ClinicalGraphResult:
    """Resultado padronizado de uma execucao de fluxo clinico."""

    flow_id: str
    response: str
    urgency: str
    safety_flags: tuple[str, ...]
    trace: TraceSummary
    explain: ExplainBlock
    raw_state: ClinicalGraphState

    def to_dict(self) -> dict[str, Any]:
        return {
            "flowId": self.flow_id,
            "response": self.response,
            "urgency": self.urgency,
            "safetyFlags": list(self.safety_flags),
            "trace": self.trace.model_dump(),
            "explain": self.explain.model_dump(),
        }


def available_flows() -> list[str]:
    """Lista os `flowId` suportados pelo router."""

    return sorted(GRAPH_FACTORIES)


def route_clinical_flow(
    *,
    flow_id: str,
    message: str,
    patient_context: Mapping[str, Any] | None = None,
    model_version: str | None = None,
) -> ClinicalGraphResult:
    """Executa o grafo LangGraph correspondente ao `flow_id` explicito do BFF."""

    if flow_id not in GRAPH_FACTORIES:
        raise ClinicalRouterError(
            f"flowId invalido: {flow_id!r}. Disponiveis: {', '.join(available_flows())}"
        )
    if not message or not message.strip():
        raise ClinicalRouterError("message nao pode ser vazio")

    initial_state = make_initial_state(
        flow_id=flow_id,
        user_input=message,
        patient_context=patient_context,
        model_version=model_version,
    )
    graph = GRAPH_FACTORIES[flow_id]()
    final_state: ClinicalGraphState = graph.invoke(initial_state)

    return ClinicalGraphResult(
        flow_id=flow_id,
        response=final_state.get("final_response", ""),
        urgency=final_state.get("urgency", "nenhuma"),
        safety_flags=tuple(final_state.get("safety_flags", [])),
        trace=trace_summary(final_state),
        explain=explain_block(final_state),
        raw_state=final_state,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa um fluxo clinico LangGraph.")
    parser.add_argument("--flow", required=True, choices=available_flows())
    parser.add_argument("--message", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = route_clinical_flow(flow_id=args.flow, message=args.message)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.response)
        print(json.dumps(result.trace.model_dump(), ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = [
    "ClinicalGraphResult",
    "ClinicalRouterError",
    "GRAPH_FACTORIES",
    "available_flows",
    "route_clinical_flow",
]
