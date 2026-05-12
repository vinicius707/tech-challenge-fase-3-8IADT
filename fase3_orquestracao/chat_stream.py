"""Endpoint `POST /v1/chat/stream` em SSE (Fase G).

Cobre IA-G1, IA-G2, IA-G3 e IA-G5. Liga o BFF Next.js (`web/`) ao serviço
Python por meio de Server-Sent Events conforme `docs/api.md` e
`docs/sdd/ia-core/design.md` §4.

Pontos principais:

- Aceita o mesmo payload que o BFF (`ChatStreamRequest`).
- Resolve `modelVersion` via `create_backend()`; jamais devolve
  `stub-0.1.0` (essa string é reservada ao stub interno da UI).
- Executa o grafo LangGraph apropriado por `flowId` via `clinical_router`.
- Emite eventos `meta`, `log`, `token`, `explain`, `trace`, `done` nessa
  ordem. Em erros, fecha o stream com `error`.
- Aceita `Authorization: Bearer <ORCHESTRATION_API_KEY>` quando a env do
  serviço estiver definida (compatibilidade com BFF privado).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Iterable

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from fase3_orquestracao.clinical_router import (
    ClinicalGraphResult,
    ClinicalRouterError,
    route_clinical_flow,
)
from fase3_orquestracao.llm_backend import (
    LlmBackendError,
    create_backend,
    resolve_backend_name,
)
from fase3_orquestracao.schemas import ChatStreamRequest, TraceNode, TraceSummary
from fase3_orquestracao.sse import (
    SSE_HEADERS,
    SSE_MEDIA_TYPE,
    done_event,
    error_event,
    explain_event,
    format_event,
    log_event,
    meta_event,
    token_event,
)


logger = logging.getLogger(__name__)


router = APIRouter()


# Reservado pelo stub do BFF (`web/src/app/api/chat/stream/route.ts`). Se o
# backend Python responder com essa string, a UI assumiria modo stub - o que
# violaria IA-G2. Mantemos como sentinela de bloqueio.
_RESERVED_STUB_VERSION = "stub-0.1.0"
_FALLBACK_MODEL_VERSION = "ia-core:safe-fallback"

_TOKEN_DELAY_SECONDS = max(
    0.0, float(os.environ.get("IA_TOKEN_DELAY_MS", "0") or 0) / 1000.0
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_request_id(header_value: str | None) -> str:
    candidate = (header_value or "").strip()
    return candidate or str(uuid.uuid4())


def _check_optional_auth(authorization: str | None) -> None:
    """Valida `Authorization: Bearer <key>` se ORCHESTRATION_API_KEY estiver
    configurada no processo Python. Em ambiente local sem chave a verificação
    é desativada para não atrapalhar a demo da UI em modo proxy.
    """

    expected = os.environ.get("ORCHESTRATION_API_KEY", "").strip()
    if not expected:
        return
    received = (authorization or "").strip()
    if not received.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_bearer")
    token = received[7:].strip()
    if token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_bearer")


def resolve_model_version() -> str:
    """Resolve `modelVersion` ativo respeitando `IA_LLM_BACKEND` e o YAML.

    Nunca retorna `stub-0.1.0` (reservado ao stub do BFF). Em caso de falha
    de configuração (ex.: chave ausente no Ollama remoto), faz fallback para
    uma string clara que indica modo seguro do serviço Python.
    """

    try:
        backend_name = resolve_backend_name()
    except LlmBackendError:
        backend_name = None

    try:
        backend = create_backend(backend_name)
    except LlmBackendError as exc:
        logger.warning("Falha ao instanciar backend %r: %s", backend_name, exc)
        return _FALLBACK_MODEL_VERSION

    version = (backend.model_version or "").strip()
    if not version or version == _RESERVED_STUB_VERSION:
        return _FALLBACK_MODEL_VERSION
    return version


def _last_user_message(payload: ChatStreamRequest) -> str:
    for msg in reversed(payload.messages):
        if msg.role == "user":
            text = (msg.content or "").strip()
            if text:
                return text
    return ""


_TOKEN_SPLIT_RE = re.compile(r"(\s+)")


def _tokenize_response(text: str) -> list[str]:
    """Quebra a resposta em pedaços preservando espaços para reconstrução fiel."""

    if not text:
        return []
    parts = _TOKEN_SPLIT_RE.split(text)
    return [chunk for chunk in parts if chunk]


def _log_lines_for_trace(nodes: Iterable[TraceNode]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for node in nodes:
        summary = (node.summary or "").strip()
        message = f"{node.name} {node.status}"
        if summary:
            message = f"{message}: {summary}"
        lines.append({"level": _level_for_status(node.status), "message": message})
    return lines


def _level_for_status(status_name: str) -> str:
    if status_name == "error":
        return "error"
    if status_name == "blocked":
        return "warning"
    return "info"


async def _stream_clinical_flow(
    *,
    request_id: str,
    payload: ChatStreamRequest,
    model_version: str,
) -> AsyncIterator[bytes]:
    """Gera eventos SSE para a requisição em ordem segura para o BFF.

    Sequência:

    1. `meta` - sempre primeiro, com `requestId`/`flowId`/`modelVersion`.
    2. `log`  - um por nó executado (já vem sanitizado pelo trace).
    3. `token`- chunks da resposta final.
    4. `explain` - ExplainBlock construído por `fase4_seguranca`.
    5. `trace` - TraceSummary completo (IA-G3).
    6. `done` - sinaliza encerramento.

    Se algo falha antes de qualquer evento, emite `meta` com urgência
    desconhecida + `error` + `done` para que o consumidor SSE finalize
    de forma previsível.
    """

    loop = asyncio.get_running_loop()

    user_message = _last_user_message(payload)
    if not user_message:
        yield meta_event(request_id, payload.flowId, model_version=model_version).encode("utf-8")
        yield error_event("invalid_request", "messages.user vazio.").encode("utf-8")
        yield done_event().encode("utf-8")
        return

    patient_context = (
        payload.patientContext.model_dump() if payload.patientContext is not None else None
    )

    try:
        result: ClinicalGraphResult = await loop.run_in_executor(
            None,
            lambda: route_clinical_flow(
                flow_id=payload.flowId,
                message=user_message,
                patient_context=patient_context,
                model_version=model_version,
            ),
        )
    except ClinicalRouterError as exc:
        yield meta_event(request_id, payload.flowId, model_version=model_version).encode("utf-8")
        yield error_event("router_error", str(exc)).encode("utf-8")
        yield done_event().encode("utf-8")
        return
    except Exception as exc:  # noqa: BLE001 - precisamos fechar o stream com error
        logger.exception("Falha inesperada no roteador clinico", exc_info=exc)
        yield meta_event(request_id, payload.flowId, model_version=model_version).encode("utf-8")
        yield error_event("internal_error", "Falha interna ao processar fluxo.").encode("utf-8")
        yield done_event().encode("utf-8")
        return

    yield meta_event(
        request_id,
        payload.flowId,
        model_version=model_version,
        urgencia=_safe_urgency(result.urgency),
    ).encode("utf-8")

    for entry in _log_lines_for_trace(result.trace.nodes):
        yield log_event(entry["message"], level=entry["level"], ts=_now_iso()).encode("utf-8")
        if _TOKEN_DELAY_SECONDS:
            await asyncio.sleep(_TOKEN_DELAY_SECONDS)

    for chunk in _tokenize_response(result.response):
        yield token_event(chunk).encode("utf-8")
        if _TOKEN_DELAY_SECONDS:
            await asyncio.sleep(_TOKEN_DELAY_SECONDS)

    yield explain_event(
        fonte=result.explain.fonte,
        confianca=result.explain.confianca,
        lacunas=result.explain.lacunas,
        raciocinio_clinico=result.explain.raciocinioClinico,
    ).encode("utf-8")

    yield _trace_event(result.trace).encode("utf-8")

    yield done_event().encode("utf-8")


def _safe_urgency(urgency: str | None) -> str | None:
    """Converte urgência arbitrária para valores aceitos pelo helper SSE."""

    allowed = {"nenhuma", "moderada", "alta", "emergencia"}
    if not urgency:
        return None
    return urgency if urgency in allowed else None


def _trace_event(trace: TraceSummary) -> str:
    """Compõe o evento SSE `trace` no formato `{flowId, nodes, finalRisk}`.

    Usa `format_event` direto porque o helper especifico `trace_event`
    exigia `list[dict]` desnormalizado; aqui preservamos a serialização
    Pydantic com `model_dump()` para consistência com a UI/persistência.
    """

    payload = trace.model_dump()
    return format_event("trace", payload)


@router.post(
    "/v1/chat/stream",
    summary="Stream SSE clínico (BFF Next.js -> IA Core).",
    response_class=StreamingResponse,
)
async def chat_stream(
    request: Request,
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
    authorization: str | None = Header(default=None, alias="authorization"),
) -> StreamingResponse:
    """Endpoint IA-G1.

    Validações ocorrem antes do início do stream para que o BFF receba 4xx
    convencionais (e não SSE de erro) quando o payload é inválido.
    """

    _check_optional_auth(authorization)

    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 - mensagens HTTP curtas e estáveis
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_json")

    if not isinstance(body, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_body")

    try:
        payload = ChatStreamRequest.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.errors()) from exc

    request_id = _new_request_id(x_request_id)
    model_version = resolve_model_version()

    headers = dict(SSE_HEADERS)
    headers["x-request-id"] = request_id

    return StreamingResponse(
        _stream_clinical_flow(
            request_id=request_id,
            payload=payload,
            model_version=model_version,
        ),
        media_type=SSE_MEDIA_TYPE,
        headers=headers,
    )


__all__ = [
    "router",
    "resolve_model_version",
]
