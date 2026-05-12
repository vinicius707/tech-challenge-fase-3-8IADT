"""Schemas Pydantic do servico IA Core.

Atende IA-A5 (Fase A). Modela o payload enviado pelo BFF Next.js conforme
`docs/api.md` (POST /api/chat/stream) e o contrato Python documentado em
`docs/sdd/ia-core/design.md` secao 5.

Os schemas tambem cobrem os blocos de saida usados a partir da Fase F
(`ExplainBlock`, `TraceNode`, `TraceSummary`) para que callers internos
possam reaproveita-los desde ja.

Pydantic v2 (configurado em requirements.txt). Estes schemas:

- Aceitam o payload do BFF tal como esta documentado.
- Recusam `flowId` desconhecido (mapeia para o 400 do BFF).
- Garantem que `messages` tenha pelo menos uma entrada (caso contrario o
  servico nao tem o que processar).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums / literais compartilhados
# ---------------------------------------------------------------------------

ClinicalFlowId = Literal[
    "triagemGinecologica",
    "violenciaDomestica",
    "obstetrico",
    "prevencao",
]

UrgencyLevel = Literal["nenhuma", "moderada", "alta", "emergencia"]

ChatRole = Literal["user", "assistant", "system"]


# ---------------------------------------------------------------------------
# Request (BFF -> Python)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """Mensagem unica em uma conversa de chat."""

    model_config = ConfigDict(extra="forbid")

    role: ChatRole
    content: str = Field(min_length=1)


class PatientContext(BaseModel):
    """Contexto da paciente fornecido pelo BFF (formato livre por dominio).

    Todos os blocos sao dict-livres para permitir evolucao do front sem
    quebrar o servico. Apenas `resumo` e tipado.
    """

    model_config = ConfigDict(extra="allow")

    resumo: str | None = None
    preventivos: dict[str, Any] = Field(default_factory=dict)
    obstetrica: dict[str, Any] = Field(default_factory=dict)
    cicloMenstrual: dict[str, Any] = Field(default_factory=dict)
    historicoReprodutivo: dict[str, Any] = Field(default_factory=dict)


class ChatStreamRequest(BaseModel):
    """Payload do BFF para `POST /v1/chat/stream`."""

    model_config = ConfigDict(extra="ignore")

    flowId: ClinicalFlowId
    threadId: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)
    patientContext: PatientContext | None = None


# ---------------------------------------------------------------------------
# Response building blocks (usados nas Fases E/F/G)
# ---------------------------------------------------------------------------


class ExplainBlock(BaseModel):
    """Bloco de explicabilidade enviado no evento SSE `explain`.

    Espelha `docs/api.md` (#ExplainBlock) e `docs/sdd/ia-core/spec.md` §7.
    """

    model_config = ConfigDict(extra="forbid")

    fonte: str
    confianca: float = Field(ge=0.0, le=1.0)
    lacunas: list[str] = Field(default_factory=list)
    raciocinioClinico: str | None = None


class TraceNode(BaseModel):
    """Um no executado pelo LangGraph com resumo seguro."""

    model_config = ConfigDict(extra="forbid")

    name: str
    status: Literal["ok", "skipped", "blocked", "error"] = "ok"
    summary: str = ""
    safetyFlags: list[str] = Field(default_factory=list)


class TraceSummary(BaseModel):
    """Trace resumido por requisicao - persistido como `langgraphTraceJson`."""

    model_config = ConfigDict(extra="forbid")

    flowId: ClinicalFlowId
    nodes: list[TraceNode] = Field(default_factory=list)
    finalRisk: UrgencyLevel | None = None


class MetaEvent(BaseModel):
    """Payload do evento SSE `meta` (primeiro evento da stream)."""

    model_config = ConfigDict(extra="forbid")

    requestId: str
    flowId: ClinicalFlowId
    modelVersion: str | None = None
    urgencia: UrgencyLevel | None = None


class ErrorEvent(BaseModel):
    """Payload do evento SSE `error`."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


__all__ = [
    "ChatMessage",
    "ChatRole",
    "ChatStreamRequest",
    "ClinicalFlowId",
    "ErrorEvent",
    "ExplainBlock",
    "MetaEvent",
    "PatientContext",
    "TraceNode",
    "TraceSummary",
    "UrgencyLevel",
]
