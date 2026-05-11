"""Testes unitarios para fase3_orquestracao/sse.py (gate IA-A4)."""

from __future__ import annotations

import json

import pytest

from fase3_orquestracao import sse


def _parse_event(raw: str) -> tuple[str, dict]:
    """Parse pequenissimo de um bloco SSE: retorna (event_name, data_dict)."""
    assert raw.endswith("\n\n"), "Evento SSE deve terminar com linha em branco"
    lines = [line for line in raw.split("\n") if line]
    event_line = next(line for line in lines if line.startswith("event: "))
    data_lines = [line[len("data: "):] for line in lines if line.startswith("data: ")]
    return event_line[len("event: "):], json.loads("\n".join(data_lines))


def test_format_event_serializa_dict_em_uma_linha():
    raw = sse.format_event("meta", {"foo": "bar", "n": 1})
    assert raw == "event: meta\ndata: {\"foo\":\"bar\",\"n\":1}\n\n"


def test_format_event_aceita_string_crua_com_quebras_de_linha():
    raw = sse.format_event("log", "linha1\nlinha2")
    assert "data: linha1\ndata: linha2\n" in raw
    assert raw.endswith("\n\n")


def test_format_event_payload_default_eh_objeto_vazio():
    raw = sse.format_event("done")
    name, data = _parse_event(raw)
    assert name == "done"
    assert data == {}


def test_format_event_recusa_nome_invalido():
    with pytest.raises(ValueError):
        sse.format_event("ev\nilcontent")


def test_meta_event_inclui_campos_obrigatorios():
    raw = sse.meta_event("req-1", "triagemGinecologica", model_version="m1", urgencia="moderada")
    name, data = _parse_event(raw)
    assert name == "meta"
    assert data == {
        "requestId": "req-1",
        "flowId": "triagemGinecologica",
        "modelVersion": "m1",
        "urgencia": "moderada",
    }


def test_meta_event_omite_campos_opcionais():
    raw = sse.meta_event("req-1", "prevencao")
    _, data = _parse_event(raw)
    assert "modelVersion" not in data
    assert "urgencia" not in data


def test_token_event_formato():
    raw = sse.token_event("Ola ")
    name, data = _parse_event(raw)
    assert name == "token"
    assert data == {"delta": "Ola "}


def test_log_event_default_level_info():
    raw = sse.log_event("ping")
    _, data = _parse_event(raw)
    assert data["level"] == "info"
    assert data["message"] == "ping"


def test_explain_event_normaliza_lacunas_em_lista():
    raw = sse.explain_event(
        fonte="INCA 2025",
        confianca=0.7,
        lacunas=("sem exame fisico",),
        raciocinio_clinico="resumo",
    )
    name, data = _parse_event(raw)
    assert name == "explain"
    assert data == {
        "fonte": "INCA 2025",
        "confianca": 0.7,
        "lacunas": ["sem exame fisico"],
        "raciocinioClinico": "resumo",
    }


def test_trace_event_inclui_final_risk_quando_passado():
    raw = sse.trace_event(
        flow_id="triagemGinecologica",
        nodes=[{"name": "collectSymptoms", "status": "ok", "summary": "", "safetyFlags": []}],
        final_risk="moderada",
    )
    _, data = _parse_event(raw)
    assert data["flowId"] == "triagemGinecologica"
    assert data["finalRisk"] == "moderada"
    assert isinstance(data["nodes"], list) and len(data["nodes"]) == 1


def test_error_event_codifica_codigo_e_mensagem():
    raw = sse.error_event("upstream_error", "LLM indisponivel")
    name, data = _parse_event(raw)
    assert name == "error"
    assert data == {"code": "upstream_error", "message": "LLM indisponivel"}


def test_done_event_eh_objeto_vazio():
    raw = sse.done_event()
    name, data = _parse_event(raw)
    assert name == "done"
    assert data == {}


def test_sse_headers_tem_no_cache_e_no_buffering():
    assert sse.SSE_HEADERS["Cache-Control"].startswith("no-cache")
    assert sse.SSE_HEADERS["X-Accel-Buffering"] == "no"
    assert sse.SSE_MEDIA_TYPE == "text/event-stream"
