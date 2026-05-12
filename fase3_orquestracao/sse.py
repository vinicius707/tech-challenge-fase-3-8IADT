"""Helpers para Server-Sent Events (SSE).

Atende IA-A4 (Fase A). Formata eventos no contrato documentado em
`docs/api.md` e em `docs/sdd/ia-core/design.md` secao 4.

Eventos suportados:
    meta, log, token, explain, trace, done, error

Cada evento e codificado como:

    event: <nome>\n
    data: <json>\n
    \n

JSON e serializado em uma unica linha (sem newlines internos). Se o `data`
contiver newlines, cada linha e prefixada com `data: ` conforme o protocolo
SSE (`https://html.spec.whatwg.org/multipage/server-sent-events.html`).
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Literal, Mapping

SseEventName = Literal[
    "meta",
    "log",
    "token",
    "explain",
    "trace",
    "done",
    "error",
]

UrgencyLevel = Literal["nenhuma", "moderada", "alta", "emergencia"]
LogLevel = Literal["debug", "info", "warning", "error"]


def format_event(event: str, data: Mapping[str, Any] | str | None = None) -> str:
    """Serializa um evento SSE no formato `event: ...\\ndata: ...\\n\\n`.

    `data` pode ser dict (serializado como JSON compacto) ou string crua.
    Se `data` for None, envia `{}`. Quebras de linha internas no JSON sao
    impossiveis porque usamos `separators=(',', ':')` e ASCII-safe; caso
    o caller passe string com `\\n`, dividimos em multiplas linhas `data:`.
    """

    if not event or "\n" in event or "\r" in event:
        raise ValueError(f"Nome de evento SSE invalido: {event!r}")

    if data is None:
        payload = "{}"
    elif isinstance(data, str):
        payload = data
    else:
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    lines = [f"event: {event}"]
    for line in payload.split("\n"):
        lines.append(f"data: {line}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


def meta_event(
    request_id: str,
    flow_id: str,
    *,
    model_version: str | None = None,
    urgencia: UrgencyLevel | None = None,
) -> str:
    """Evento `meta` inicial - sempre o primeiro a ser emitido."""
    payload: dict[str, Any] = {"requestId": request_id, "flowId": flow_id}
    if model_version is not None:
        payload["modelVersion"] = model_version
    if urgencia is not None:
        payload["urgencia"] = urgencia
    return format_event("meta", payload)


def log_event(message: str, *, level: LogLevel = "info", ts: str | None = None) -> str:
    """Evento `log` - mensagens curtas para o painel da UI."""
    payload: dict[str, Any] = {"level": level, "message": message}
    if ts is not None:
        payload["ts"] = ts
    return format_event("log", payload)


def token_event(delta: str) -> str:
    """Evento `token` - chunk parcial da resposta gerada."""
    return format_event("token", {"delta": delta})


def explain_event(
    *,
    fonte: str,
    confianca: float,
    lacunas: Iterable[str] | None = None,
    raciocinio_clinico: str | None = None,
) -> str:
    """Evento `explain` - ExplainBlock conforme docs/api.md."""
    payload: dict[str, Any] = {
        "fonte": fonte,
        "confianca": confianca,
        "lacunas": list(lacunas) if lacunas is not None else [],
    }
    if raciocinio_clinico is not None:
        payload["raciocinioClinico"] = raciocinio_clinico
    return format_event("explain", payload)


def trace_event(
    *,
    flow_id: str,
    nodes: list[dict[str, Any]],
    final_risk: str | None = None,
) -> str:
    """Evento `trace` - resumo dos nos LangGraph executados.

    Conforme design.md secao 4, o BFF ignora eventos desconhecidos, entao
    enviar `trace` nao quebra a UI antes da Fase G4.
    """
    payload: dict[str, Any] = {"flowId": flow_id, "nodes": nodes}
    if final_risk is not None:
        payload["finalRisk"] = final_risk
    return format_event("trace", payload)


def done_event() -> str:
    """Evento `done` - sinaliza fim da stream com sucesso."""
    return format_event("done", {})


def error_event(code: str, message: str) -> str:
    """Evento `error` - falha estruturada; o BFF traduz para o cliente."""
    return format_event("error", {"code": code, "message": message})


SSE_MEDIA_TYPE = "text/event-stream"

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
