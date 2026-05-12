"""Testes do endpoint `POST /v1/chat/stream` (Fase G - IA-G1, IA-G2, IA-G3, IA-G5).

Cobre:

- Sequência de eventos SSE esperada (`meta` -> `log` -> `token` -> `explain`
  -> `trace` -> `done`).
- `modelVersion` real (jamais `stub-0.1.0`) - IA-G2.
- Propagação de `x-request-id` no cabeçalho da resposta.
- Validação Pydantic do payload (400 limpo em flowId/messages inválidos).
- Authorization opcional via `ORCHESTRATION_API_KEY` (IA-G5).
- Comportamento de `error` quando o roteador falha (sem quebrar SSE).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from fase3_orquestracao.app import create_app
from fase3_orquestracao import chat_stream as chat_stream_module
from fase3_orquestracao.clinical_router import ClinicalGraphResult, ClinicalRouterError
from fase3_orquestracao.schemas import ExplainBlock, TraceNode, TraceSummary


SseEvent = tuple[str, dict[str, Any]]


def _parse_sse(text: str) -> list[SseEvent]:
    """Parser tolerante para `event: NOME\\ndata: JSON\\n\\n` em sequência."""

    events: list[SseEvent] = []
    for raw_block in re.split(r"\n\n+", text.strip()):
        block = raw_block.strip()
        if not block:
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].lstrip())
        joined = "\n".join(data_lines)
        try:
            payload = json.loads(joined) if joined else {}
        except json.JSONDecodeError:
            payload = {"_raw": joined}
        events.append((event_name, payload))
    return events


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv("ORCHESTRATION_API_KEY", raising=False)
    monkeypatch.delenv("IA_TOKEN_DELAY_MS", raising=False)
    app = create_app()
    with TestClient(app) as tc:
        yield tc


def _valid_payload(flow_id: str = "triagemGinecologica") -> dict[str, Any]:
    return {
        "flowId": flow_id,
        "messages": [
            {"role": "user", "content": "Tenho dor pelvica leve ha dois dias, sem febre."}
        ],
        "patientContext": {"resumo": "Paciente ficticia 30 anos, sem PII real."},
    }


def test_chat_stream_emits_full_event_sequence(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/stream",
        json=_valid_payload("triagemGinecologica"),
        headers={"x-request-id": "test-request-1"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers.get("x-request-id") == "test-request-1"

    events = _parse_sse(response.text)
    names = [name for name, _ in events]

    assert names[0] == "meta"
    assert names[-1] == "done"

    meta_payload = events[0][1]
    assert meta_payload["requestId"] == "test-request-1"
    assert meta_payload["flowId"] == "triagemGinecologica"
    assert meta_payload["modelVersion"]
    assert meta_payload["modelVersion"] != "stub-0.1.0"

    assert "log" in names, "esperado pelo menos um evento log por no executado"
    assert names.count("token") >= 1, "esperado pelo menos um token na resposta"
    assert names.count("explain") == 1
    assert names.count("trace") == 1
    assert names.count("done") == 1

    # ordem relativa: meta < log < token < explain < trace < done
    def first_index(target: str) -> int:
        return next(i for i, n in enumerate(names) if n == target)

    assert first_index("meta") < first_index("log")
    assert first_index("log") < first_index("token")
    assert first_index("token") < first_index("explain")
    assert first_index("explain") < first_index("trace")
    assert first_index("trace") < first_index("done")

    explain_payload = events[first_index("explain")][1]
    ExplainBlock.model_validate(explain_payload)

    trace_payload = events[first_index("trace")][1]
    parsed_trace = TraceSummary.model_validate(trace_payload)
    assert parsed_trace.flowId == "triagemGinecologica"
    assert len(parsed_trace.nodes) >= 2


def test_chat_stream_generates_request_id_when_header_missing(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/stream",
        json=_valid_payload("prevencao"),
    )
    assert response.status_code == 200
    assert response.headers.get("x-request-id")
    events = _parse_sse(response.text)
    assert events[0][0] == "meta"
    assert events[0][1]["requestId"] == response.headers["x-request-id"]


@pytest.mark.parametrize(
    "flow_id",
    ["triagemGinecologica", "violenciaDomestica", "obstetrico", "prevencao"],
)
def test_chat_stream_supports_all_clinical_flows(client: TestClient, flow_id: str) -> None:
    payload = _valid_payload(flow_id)
    if flow_id == "violenciaDomestica":
        payload["messages"][0]["content"] = (
            "Meu parceiro me empurrou e estou com medo, preciso de ajuda agora."
        )
    if flow_id == "obstetrico":
        payload["messages"][0]["content"] = (
            "Estou gravida de 30 semanas e nao sinto bebe ha algumas horas."
        )
    if flow_id == "prevencao":
        payload["messages"][0]["content"] = (
            "Tenho 45 anos e quero saber se devo fazer mamografia este ano."
        )

    response = client.post("/v1/chat/stream", json=payload)
    assert response.status_code == 200
    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "meta"
    assert names[-1] == "done"
    assert "trace" in names
    trace_payload = next(payload for name, payload in events if name == "trace")
    parsed = TraceSummary.model_validate(trace_payload)
    assert parsed.flowId == flow_id


def test_chat_stream_rejects_invalid_flow_id(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/stream",
        json={"flowId": "naoExiste", "messages": [{"role": "user", "content": "oi"}]},
    )
    assert response.status_code == 400


def test_chat_stream_rejects_empty_messages(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/stream",
        json={"flowId": "triagemGinecologica", "messages": []},
    )
    assert response.status_code == 400


def test_chat_stream_rejects_invalid_json(client: TestClient) -> None:
    response = client.post(
        "/v1/chat/stream",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


def test_chat_stream_rejects_non_object_body(client: TestClient) -> None:
    response = client.post("/v1/chat/stream", json=[1, 2, 3])
    assert response.status_code == 400


def test_chat_stream_returns_safe_error_when_router_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _broken(**kwargs: Any) -> ClinicalGraphResult:
        raise ClinicalRouterError("flow indisponivel para teste")

    monkeypatch.setattr(chat_stream_module, "route_clinical_flow", _broken)

    response = client.post("/v1/chat/stream", json=_valid_payload("triagemGinecologica"))
    assert response.status_code == 200
    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "meta"
    assert "error" in names
    assert names[-1] == "done"
    err_payload = next(payload for name, payload in events if name == "error")
    assert err_payload["code"] == "router_error"


def test_chat_stream_returns_internal_error_on_unexpected_exception(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _explode(**kwargs: Any) -> ClinicalGraphResult:
        raise RuntimeError("falha sintetica")

    monkeypatch.setattr(chat_stream_module, "route_clinical_flow", _explode)

    response = client.post("/v1/chat/stream", json=_valid_payload("prevencao"))
    assert response.status_code == 200
    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[0] == "meta"
    assert "error" in names
    err_payload = next(payload for name, payload in events if name == "error")
    assert err_payload["code"] == "internal_error"
    # mensagem genérica - não vaza traceback
    assert "trace" not in err_payload["message"].lower()


def test_chat_stream_requires_bearer_when_orchestration_api_key_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORCHESTRATION_API_KEY", "secret-token")
    app = create_app()
    with TestClient(app) as tc:
        # sem header => 401
        no_auth = tc.post("/v1/chat/stream", json=_valid_payload("prevencao"))
        assert no_auth.status_code == 401

        # token errado => 401
        bad = tc.post(
            "/v1/chat/stream",
            json=_valid_payload("prevencao"),
            headers={"Authorization": "Bearer wrong"},
        )
        assert bad.status_code == 401

        # token certo => 200
        ok = tc.post(
            "/v1/chat/stream",
            json=_valid_payload("prevencao"),
            headers={"Authorization": "Bearer secret-token"},
        )
        assert ok.status_code == 200


def test_resolve_model_version_never_returns_ui_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    from fase3_orquestracao import chat_stream as cs
    from fase3_orquestracao import llm_backend as lb

    class _Backend:
        model_version = "stub-0.1.0"

    monkeypatch.setattr(lb, "create_backend", lambda *a, **k: _Backend())
    monkeypatch.setattr(cs, "create_backend", lambda *a, **k: _Backend())

    version = cs.resolve_model_version()
    assert version != "stub-0.1.0"
    assert "fallback" in version or "ia-core" in version


def test_resolve_model_version_uses_backend_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fase3_orquestracao import chat_stream as cs

    class _Backend:
        model_version = "ollama:llama3.2:3b"

    monkeypatch.setattr(cs, "create_backend", lambda *a, **k: _Backend())

    assert cs.resolve_model_version() == "ollama:llama3.2:3b"


def test_emits_meta_with_urgency_for_violent_flow(client: TestClient) -> None:
    payload = _valid_payload("violenciaDomestica")
    payload["messages"][0]["content"] = (
        "Estou em situacao de risco, meu parceiro me ameacou agora."
    )
    response = client.post(
        "/v1/chat/stream",
        json=payload,
        headers={"x-request-id": "violencia-1"},
    )
    assert response.status_code == 200
    events = _parse_sse(response.text)
    meta_payload = events[0][1]
    assert meta_payload["flowId"] == "violenciaDomestica"
    assert meta_payload["urgencia"] in {"moderada", "alta", "emergencia"}


def test_trace_event_node_summary_is_safe(client: TestClient) -> None:
    payload = _valid_payload("violenciaDomestica")
    payload["messages"][0]["content"] = (
        "Conteudo sensivel: meu CPF 123.456.789-00, telefone 11 91234-5678."
    )
    response = client.post("/v1/chat/stream", json=payload)
    assert response.status_code == 200
    events = _parse_sse(response.text)
    trace_payload = next(payload for name, payload in events if name == "trace")
    parsed = TraceSummary.model_validate(trace_payload)
    rendered = json.dumps([node.model_dump() for node in parsed.nodes])
    assert "123.456.789" not in rendered
    assert "91234-5678" not in rendered
