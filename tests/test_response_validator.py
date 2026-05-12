"""Testes do `ResponseValidator` (Fase E)."""

from __future__ import annotations

from fase4_seguranca.response_validator import ResponseValidator
from fase4_seguranca.safety_guard import SafetyGuard


def _validator() -> ResponseValidator:
    guard = SafetyGuard.from_yaml()
    return ResponseValidator(guard=guard)


def test_validator_blocks_prescription_output():
    validator = _validator()
    result = validator.validate(
        "Recomendo prescrever amoxicilina 500mg para a paciente.",
        flow_id="triagemGinecologica",
    )
    assert result.blocked is True
    assert result.requires_human_review is True
    assert "prescription_blocked" in result.safety_flags
    assert "amoxicilina" not in result.text.lower()


def test_validator_rewrites_definitive_diagnosis():
    validator = _validator()
    result = validator.validate(
        "Voce esta com cancer com certeza.",
        flow_id="triagemGinecologica",
    )
    assert result.rewritten is True
    assert "definitive_diagnosis_blocked" in result.safety_flags
    assert "com certeza" not in result.text.lower() or "cancer" not in result.text.lower()


def test_validator_appends_disclaimer_by_default():
    validator = _validator()
    result = validator.validate(
        "Considere agendar uma consulta presencial.",
        flow_id="triagemGinecologica",
    )
    assert result.disclaimer_applied is True
    assert "validad" in result.text.lower() or "profissional" in result.text.lower()


def test_validator_skips_disclaimer_when_requested():
    validator = _validator()
    result = validator.validate(
        "Considere agendar uma consulta presencial.",
        flow_id="triagemGinecologica",
        append_disclaimer=False,
    )
    assert result.disclaimer_applied is False


def test_input_override_propagates_to_output():
    validator = _validator()
    guard = validator.guard
    input_verdict = guard.evaluate(
        "Quero me matar.",
        scope="input",
        flow_id="triagemGinecologica",
    )
    assert input_verdict.blocked is True
    result = validator.validate(
        "Aqui vai uma orientacao geral sobre auto-cuidado.",
        flow_id="triagemGinecologica",
        input_verdict=input_verdict,
    )
    assert result.blocked is True
    assert result.requires_human_review is True
    assert "self_harm_escalation" in result.safety_flags
    assert "CVV" in result.text or "188" in result.text


def test_empty_output_is_replaced_with_safe_message():
    validator = _validator()
    result = validator.validate("   ", flow_id="triagemGinecologica")
    assert result.text.strip() != ""
    assert "reformule" in result.text.lower() or "presencial" in result.text.lower()
