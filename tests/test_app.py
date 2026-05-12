"""Testes do FastAPI app - gate IA-A3 (GET /health)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from fase3_orquestracao.app import SERVICE_NAME, SERVICE_VERSION, create_app


def test_health_endpoint_retorna_ok():
    client = TestClient(create_app())
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["service"] == SERVICE_NAME
    assert body["version"] == SERVICE_VERSION


def test_app_factory_eh_idempotente():
    """`create_app` nao deve produzir efeitos colaterais globais."""
    a, b = create_app(), create_app()
    assert a is not b
    assert a.title == b.title
