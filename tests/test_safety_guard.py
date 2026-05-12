"""Testes unitarios do `SafetyGuard` (Fase E)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from fase4_seguranca.safety_guard import (
    DEFAULT_RULES_PATH,
    SafetyConfigError,
    SafetyGuard,
)


def _minimal_rules() -> dict:
    return {
        "version": "test",
        "defaults": {"default_disclaimer": "Disclaimer de teste."},
        "flow_overrides": {
            "violenciaDomestica": {
                "redact_sensitive_text": True,
                "default_safety_flags": ["sensitive"],
            }
        },
        "rules": [
            {
                "id": "prescription_request",
                "category": "prescription",
                "severity": "high",
                "applies_to": "input_and_output",
                "action": "block_with_human_review",
                "safety_flags": ["prescription_blocked", "human_review_required"],
                "replacement": "Nao posso indicar medicamento.",
                "patterns": [r"(?i)\bme receit", r"(?i)quantos? (mg|comprimid|gota)"],
            },
            {
                "id": "definitive_diagnosis",
                "category": "diagnosis",
                "severity": "high",
                "applies_to": "output",
                "action": "rewrite_with_uncertainty",
                "safety_flags": ["definitive_diagnosis_blocked"],
                "replacement": "Use linguagem com incerteza.",
                "patterns": [r"(?i)voc[eê] (tem|est[aá] com) c[aâ]ncer"],
            },
            {
                "id": "self_harm",
                "category": "self_harm",
                "severity": "critical",
                "applies_to": "input",
                "action": "crisis_escalation",
                "safety_flags": ["self_harm_escalation"],
                "replacement": "Procure o CVV 188.",
                "escalation": {"channels": ["CVV 188"], "message": "Encaminhar para CVV"},
                "patterns": [r"(?i)quero me matar"],
            },
        ],
    }


@pytest.fixture
def guard(tmp_path: Path) -> SafetyGuard:
    rules_path = tmp_path / "safety_rules.yaml"
    rules_path.write_text(yaml.safe_dump(_minimal_rules()), encoding="utf-8")
    return SafetyGuard.from_yaml(rules_path)


def test_loads_default_yaml_real_project():
    """Garante que `config/safety_rules.yaml` real do projeto e valido."""
    guard = SafetyGuard.from_yaml(DEFAULT_RULES_PATH)
    assert len(guard.rules) >= 5
    assert guard.default_disclaimer()


def test_evaluate_input_detects_prescription(guard: SafetyGuard):
    verdict = guard.evaluate(
        "Por favor me receite algo para a dor.",
        scope="input",
        flow_id="triagemGinecologica",
    )
    assert verdict.blocked is True
    assert verdict.requires_human_review is True
    assert "prescription_blocked" in verdict.safety_flags
    assert "human_review_required" in verdict.safety_flags
    assert verdict.replacement_text == "Nao posso indicar medicamento."
    assert "prescription" in verdict.categories


def test_evaluate_output_only_definitive_diagnosis(guard: SafetyGuard):
    text = "Voce esta com cancer."
    output_verdict = guard.evaluate(text, scope="output", flow_id="triagemGinecologica")
    input_verdict = guard.evaluate(text, scope="input", flow_id="triagemGinecologica")
    assert output_verdict.rewrite is True
    assert output_verdict.blocked is False
    assert "definitive_diagnosis_blocked" in output_verdict.safety_flags
    # Regra so se aplica a output; em input nao deve disparar.
    assert input_verdict.hits == ()


def test_self_harm_is_critical_and_escalated(guard: SafetyGuard):
    verdict = guard.evaluate("Quero me matar.", scope="input", flow_id="triagemGinecologica")
    assert verdict.blocked is True
    assert verdict.requires_human_review is True
    assert any(esc.channels == ("CVV 188",) for esc in verdict.escalations)


def test_violence_flow_defaults_apply_even_without_match(guard: SafetyGuard):
    verdict = guard.evaluate(
        "Estou com duvidas sobre meu ciclo.",
        scope="input",
        flow_id="violenciaDomestica",
    )
    assert "sensitive" in verdict.safety_flags
    assert verdict.blocked is False
    assert guard.redacts_sensitive_text("violenciaDomestica") is True
    assert guard.redacts_sensitive_text("triagemGinecologica") is False


def test_benign_input_returns_clean_verdict(guard: SafetyGuard):
    verdict = guard.evaluate(
        "Quando devo agendar meu proximo preventivo de rotina?",
        scope="input",
        flow_id="prevencao",
    )
    assert verdict.hits == ()
    assert verdict.blocked is False
    assert verdict.rewrite is False
    assert verdict.requires_human_review is False
    assert verdict.safety_flags == ()


def test_invalid_pattern_raises_config_error(tmp_path: Path):
    bad = _minimal_rules()
    bad["rules"][0]["patterns"] = ["(?P<broken"]
    path = tmp_path / "broken.yaml"
    path.write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(SafetyConfigError):
        SafetyGuard.from_yaml(path)


def test_missing_yaml_raises_config_error(tmp_path: Path):
    with pytest.raises(SafetyConfigError):
        SafetyGuard.from_yaml(tmp_path / "ausente.yaml")
