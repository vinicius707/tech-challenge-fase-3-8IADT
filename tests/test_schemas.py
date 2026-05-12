"""Testes dos schemas Pydantic (gate IA-A5).

O criterio de aceite e: o payload enviado pelo BFF (docs/api.md) deve validar
sem erro contra `ChatStreamRequest`.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fase3_orquestracao.schemas import (
    ChatStreamRequest,
    ExplainBlock,
    TraceNode,
    TraceSummary,
)


# Payload identico ao documentado em docs/api.md (POST /api/chat/stream) e
# em spec.md secao 7. Esta e a forma canonica que o BFF envia.
BFF_PAYLOAD_TRIAGEM = {
    "flowId": "triagemGinecologica",
    "threadId": "opcional-id-de-thread",
    "messages": [{"role": "user", "content": "estou com dor pelvica"}],
    "patientContext": {
        "resumo": "Paciente ficticia, sem PII real",
        "preventivos": {},
        "obstetrica": {},
        "cicloMenstrual": {},
        "historicoReprodutivo": {},
    },
}


def test_payload_do_bff_valida_triagem():
    req = ChatStreamRequest.model_validate(BFF_PAYLOAD_TRIAGEM)
    assert req.flowId == "triagemGinecologica"
    assert req.threadId == "opcional-id-de-thread"
    assert req.messages[0].role == "user"
    assert req.messages[0].content == "estou com dor pelvica"
    assert req.patientContext is not None
    assert req.patientContext.resumo == "Paciente ficticia, sem PII real"


@pytest.mark.parametrize(
    "flow_id",
    ["triagemGinecologica", "violenciaDomestica", "obstetrico", "prevencao"],
)
def test_aceita_os_quatro_fluxos_obrigatorios(flow_id):
    payload = {**BFF_PAYLOAD_TRIAGEM, "flowId": flow_id}
    req = ChatStreamRequest.model_validate(payload)
    assert req.flowId == flow_id


def test_payload_minimo_sem_patient_context():
    req = ChatStreamRequest.model_validate(
        {
            "flowId": "prevencao",
            "messages": [{"role": "user", "content": "qual exame preciso?"}],
        }
    )
    assert req.threadId is None
    assert req.patientContext is None


def test_rejeita_flow_id_desconhecido():
    with pytest.raises(ValidationError):
        ChatStreamRequest.model_validate(
            {
                "flowId": "fluxoInexistente",
                "messages": [{"role": "user", "content": "teste"}],
            }
        )


def test_rejeita_messages_vazio():
    with pytest.raises(ValidationError):
        ChatStreamRequest.model_validate(
            {"flowId": "prevencao", "messages": []}
        )


def test_rejeita_role_invalida():
    with pytest.raises(ValidationError):
        ChatStreamRequest.model_validate(
            {
                "flowId": "prevencao",
                "messages": [{"role": "robot", "content": "x"}],
            }
        )


def test_ignora_campos_extras_no_request():
    """Garante forward-compat: BFF pode enviar campos novos sem quebrar."""
    req = ChatStreamRequest.model_validate(
        {**BFF_PAYLOAD_TRIAGEM, "novoCampoFuturo": "ok"}
    )
    assert req.flowId == "triagemGinecologica"


def test_explain_block_valida_o_exemplo_de_spec_md():
    block = ExplainBlock.model_validate(
        {
            "fonte": "INCA 2025 / protocolo sintetico v1",
            "confianca": 0.72,
            "lacunas": ["sem exame fisico", "sem sinais vitais"],
            "raciocinioClinico": "Resumo alto nivel, sem chain-of-thought sensivel.",
        }
    )
    assert block.confianca == 0.72
    assert len(block.lacunas) == 2


def test_explain_block_recusa_confianca_fora_de_intervalo():
    with pytest.raises(ValidationError):
        ExplainBlock.model_validate({"fonte": "x", "confianca": 1.5})


def test_trace_summary_valida_exemplo_canonico():
    trace = TraceSummary.model_validate(
        {
            "flowId": "triagemGinecologica",
            "nodes": [
                {
                    "name": "collectSymptoms",
                    "status": "ok",
                    "summary": "Sintomas normalizados",
                    "safetyFlags": [],
                }
            ],
            "finalRisk": "moderada",
        }
    )
    assert trace.flowId == "triagemGinecologica"
    assert trace.nodes[0].name == "collectSymptoms"
    assert trace.finalRisk == "moderada"


def test_trace_node_default_status_ok():
    node = TraceNode.model_validate({"name": "analyzeRisk"})
    assert node.status == "ok"
    assert node.safetyFlags == []
