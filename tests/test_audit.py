"""Testes do `AuditLogger` minimizado (Fase E, IA-E5)."""

from __future__ import annotations

import json
from pathlib import Path

from fase4_seguranca.audit import (
    AuditLogger,
    SENSITIVE_FLOWS,
    redact_text,
    utc_now_isoformat,
)


def test_redact_text_returns_none_for_none():
    assert redact_text(None) is None


def test_redact_text_masks_pii_in_general_flow():
    masked = redact_text(
        "Paciente CPF 123.456.789-00 telefone 11 91234-5678 email a@b.com",
        flow_id="triagemGinecologica",
    )
    assert masked is not None
    assert "123.456.789-00" not in masked
    assert "91234-5678" not in masked
    assert "a@b.com" not in masked
    assert "[REDACTED:cpf]" in masked
    assert "[REDACTED:email]" in masked


def test_redact_text_blocks_full_content_for_violence_flow():
    masked = redact_text(
        "Meu marido me bate em casa.",
        flow_id="violenciaDomestica",
    )
    assert masked == "[REDACTED:sensitive_content]"
    assert "violenciaDomestica" in SENSITIVE_FLOWS


def test_redact_text_blocks_content_when_category_is_self_harm():
    masked = redact_text(
        "Mensagem qualquer",
        flow_id="triagemGinecologica",
        categories=["self_harm"],
    )
    assert masked == "[REDACTED:sensitive_content]"


def test_audit_logger_writes_one_line_per_request(tmp_path: Path):
    log_path = tmp_path / "audit.log"
    logger = AuditLogger(log_path)
    payload = logger.log_request(
        request_id="req-1",
        flow_id="triagemGinecologica",
        model_version="ollama:llama3.2:3b",
        sources_count=3,
        safety_flags=["human_review_required"],
        urgency="moderada",
        blocked=False,
        sensitive_redacted=False,
        duration_ms=1234,
    )
    assert payload["request_id"] == "req-1"
    assert payload["sources_count"] == 3
    raw = log_path.read_text(encoding="utf-8")
    assert raw.count("\n") == 1
    parsed = json.loads(raw.strip())
    assert parsed["model_version"] == "ollama:llama3.2:3b"
    assert parsed["safety_flags"] == ["human_review_required"]
    assert parsed["urgency"] == "moderada"


def test_audit_logger_violence_does_not_contain_text(tmp_path: Path):
    log_path = tmp_path / "audit.log"
    logger = AuditLogger(log_path)
    logger.log_request(
        request_id="req-violencia",
        flow_id="violenciaDomestica",
        model_version="stub-safe-0.1.0",
        sources_count=0,
        safety_flags=["violence_protocol", "sensitive"],
        urgency="alta",
        blocked=True,
        sensitive_redacted=True,
        duration_ms=42,
        extra={"summary": "[REDACTED:sensitive_content]"},
    )
    raw = log_path.read_text(encoding="utf-8")
    parsed = json.loads(raw.strip())
    assert parsed["sensitive_redacted"] is True
    assert parsed["blocked"] is True
    assert "marido" not in raw
    assert parsed["summary"] == "[REDACTED:sensitive_content]"


def test_audit_logger_appends_multiple_lines(tmp_path: Path):
    log_path = tmp_path / "audit.log"
    logger = AuditLogger(log_path)
    for idx in range(3):
        logger.log_request(
            request_id=f"req-{idx}",
            flow_id="triagemGinecologica",
            model_version="ollama:llama3.2:3b",
            sources_count=idx,
            safety_flags=[],
            urgency="nenhuma",
            blocked=False,
            sensitive_redacted=False,
        )
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln]
    assert len(lines) == 3
    for line in lines:
        json.loads(line)


def test_utc_timestamp_is_iso_z():
    ts = utc_now_isoformat()
    assert ts.endswith("Z")
    assert "T" in ts
