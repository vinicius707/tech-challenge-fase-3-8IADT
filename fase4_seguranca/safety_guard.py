"""Guardrails clinicos da Fase E (IA-E2).

Avalia entradas e saidas do servico IA Core contra as regras declarativas em
`config/safety_rules.yaml`. Garante que safety e fluxo nao dependam apenas do
LLM (IA-SAFE-01, IA-SAFE-02 de `docs/sdd/ia-core/spec.md`).

Conceitos principais:

- `SafetyRule`: representacao tipada de uma regra do YAML.
- `SafetyVerdict`: resultado da avaliacao de um texto contra um escopo
  (input/output) e um `flow_id`.
- `SafetyGuard`: orquestrador que compila as regras e gera o verdict.

Decisoes:

- Regras com `applies_to=both` valem para input e output.
- `severity=critical` sempre dispara `requires_human_review`.
- Acoes `block_*`, `crisis_escalation`, `violence_protocol` e
  `urgency_escalation` marcam `blocked=True` (a resposta nao pode seguir
  para a paciente sem revisao). `rewrite_with_uncertainty` indica que a
  resposta deve ser ajustada (nao bloqueada).
- O `flow_overrides` permite que o YAML enriqueca os flags por fluxo
  (ex.: `violenciaDomestica` sempre carrega flag `sensitive`).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependencia obrigatoria
    raise RuntimeError(
        "Dependencia `pyyaml` ausente. Rode `python -m pip install -r requirements.txt`."
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = PROJECT_ROOT / "config" / "safety_rules.yaml"

Scope = Literal["input", "output"]
Severity = Literal["low", "medium", "high", "critical"]

_BLOCKING_ACTIONS = frozenset(
    {
        "block_with_human_review",
        "crisis_escalation",
        "violence_protocol",
        "urgency_escalation",
    }
)


class SafetyConfigError(RuntimeError):
    """Erro recuperavel ao carregar/validar `config/safety_rules.yaml`."""


@dataclass(frozen=True)
class Escalation:
    """Canais de encaminhamento associados a uma regra critica."""

    channels: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"channels": list(self.channels), "message": self.message}


@dataclass(frozen=True)
class SafetyRule:
    """Regra de safety compilada a partir do YAML."""

    id: str
    category: str
    severity: Severity
    applies_to: Literal["input", "output", "input_and_output"]
    action: str
    safety_flags: tuple[str, ...]
    replacement: str | None
    escalation: Escalation | None
    _compiled_patterns: tuple[re.Pattern[str], ...] = field(default=(), repr=False)

    def applies_to_scope(self, scope: Scope) -> bool:
        if self.applies_to == "input_and_output":
            return True
        return self.applies_to == scope

    def find_match(self, text: str) -> re.Match[str] | None:
        for pattern in self._compiled_patterns:
            match = pattern.search(text)
            if match is not None:
                return match
        return None


@dataclass(frozen=True)
class SafetyHit:
    """Registro individual de uma regra que disparou."""

    rule_id: str
    category: str
    severity: Severity
    action: str
    excerpt: str
    safety_flags: tuple[str, ...]
    escalation: Escalation | None
    replacement: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "action": self.action,
            "excerpt": self.excerpt,
            "safety_flags": list(self.safety_flags),
            "escalation": self.escalation.to_dict() if self.escalation else None,
        }


@dataclass(frozen=True)
class SafetyVerdict:
    """Resultado da avaliacao de um texto contra as regras de safety."""

    scope: Scope
    flow_id: str | None
    hits: tuple[SafetyHit, ...]
    safety_flags: tuple[str, ...]
    blocked: bool
    requires_human_review: bool
    rewrite: bool
    escalations: tuple[Escalation, ...]
    categories: tuple[str, ...]
    replacement_text: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "flow_id": self.flow_id,
            "hits": [hit.to_dict() for hit in self.hits],
            "safety_flags": list(self.safety_flags),
            "blocked": self.blocked,
            "requires_human_review": self.requires_human_review,
            "rewrite": self.rewrite,
            "escalations": [esc.to_dict() for esc in self.escalations],
            "categories": list(self.categories),
            "replacement_text": self.replacement_text,
        }


def _excerpt_around(text: str, match: re.Match[str], context: int = 24) -> str:
    start = max(match.start() - context, 0)
    end = min(match.end() + context, len(text))
    snippet = text[start:end].strip()
    snippet = re.sub(r"\s+", " ", snippet)
    if len(snippet) > 120:
        snippet = snippet[:117] + "..."
    return snippet


def _normalize_safety_flags(flags: Iterable[str]) -> tuple[str, ...]:
    seen: list[str] = []
    for flag in flags:
        if flag and flag not in seen:
            seen.append(flag)
    return tuple(seen)


def _compile_rule(raw: Mapping[str, Any]) -> SafetyRule:
    rule_id = raw.get("id")
    if not isinstance(rule_id, str) or not rule_id.strip():
        raise SafetyConfigError("Regra sem `id` valido em safety_rules.yaml")

    severity = raw.get("severity", "medium")
    if severity not in ("low", "medium", "high", "critical"):
        raise SafetyConfigError(f"Severidade invalida em `{rule_id}`: {severity!r}")

    applies_to = raw.get("applies_to", "input_and_output")
    if applies_to not in ("input", "output", "input_and_output"):
        raise SafetyConfigError(f"`applies_to` invalido em `{rule_id}`: {applies_to!r}")

    patterns_raw = raw.get("patterns") or []
    if not patterns_raw:
        raise SafetyConfigError(f"Regra `{rule_id}` sem `patterns`")

    compiled: list[re.Pattern[str]] = []
    for pattern in patterns_raw:
        if not isinstance(pattern, str):
            raise SafetyConfigError(f"Padrao invalido em `{rule_id}`: {pattern!r}")
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            raise SafetyConfigError(f"Regex invalida em `{rule_id}` ({pattern!r}): {exc}") from exc

    escalation: Escalation | None = None
    raw_escalation = raw.get("escalation")
    if isinstance(raw_escalation, Mapping):
        channels = raw_escalation.get("channels") or []
        message = raw_escalation.get("message", "")
        if not isinstance(channels, list):
            raise SafetyConfigError(f"`escalation.channels` invalido em `{rule_id}`")
        escalation = Escalation(channels=tuple(str(c) for c in channels), message=str(message))

    return SafetyRule(
        id=rule_id,
        category=str(raw.get("category", rule_id)),
        severity=severity,  # type: ignore[arg-type]
        applies_to=applies_to,  # type: ignore[arg-type]
        action=str(raw.get("action", "flag_only")),
        safety_flags=_normalize_safety_flags(raw.get("safety_flags", [])),
        replacement=(raw.get("replacement") or None) and str(raw["replacement"]).strip(),
        escalation=escalation,
        _compiled_patterns=tuple(compiled),
    )


@dataclass
class SafetyGuard:
    """Avalia inputs/outputs contra as regras de `config/safety_rules.yaml`."""

    rules: tuple[SafetyRule, ...]
    defaults: Mapping[str, Any]
    flow_overrides: Mapping[str, Mapping[str, Any]]

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> "SafetyGuard":
        config_path = path or DEFAULT_RULES_PATH
        if not config_path.exists():
            raise SafetyConfigError(f"Configuracao nao encontrada: {config_path}")
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, Mapping):
            raise SafetyConfigError(f"Conteudo invalido em {config_path}")

        raw_rules = payload.get("rules") or []
        if not isinstance(raw_rules, list) or not raw_rules:
            raise SafetyConfigError(f"`rules` ausente ou vazio em {config_path}")
        rules = tuple(_compile_rule(rule) for rule in raw_rules)

        defaults = payload.get("defaults") or {}
        flow_overrides = payload.get("flow_overrides") or {}
        if not isinstance(defaults, Mapping):
            raise SafetyConfigError("`defaults` deve ser um mapeamento")
        if not isinstance(flow_overrides, Mapping):
            raise SafetyConfigError("`flow_overrides` deve ser um mapeamento")

        return cls(rules=rules, defaults=defaults, flow_overrides=flow_overrides)

    def _flow_default_flags(self, flow_id: str | None) -> tuple[str, ...]:
        if not flow_id:
            return ()
        overrides = self.flow_overrides.get(flow_id) or {}
        raw = overrides.get("default_safety_flags") or []
        if not isinstance(raw, list):
            return ()
        return tuple(str(flag) for flag in raw)

    def redacts_sensitive_text(self, flow_id: str | None) -> bool:
        if not flow_id:
            return False
        overrides = self.flow_overrides.get(flow_id) or {}
        return bool(overrides.get("redact_sensitive_text", False))

    def default_disclaimer(self) -> str:
        disclaimer = self.defaults.get("default_disclaimer") or ""
        return " ".join(str(disclaimer).split())

    def evaluate(
        self,
        text: str,
        *,
        scope: Scope,
        flow_id: str | None = None,
    ) -> SafetyVerdict:
        """Avalia `text` contra as regras compativeis com `scope`."""
        hits: list[SafetyHit] = []
        if isinstance(text, str) and text.strip():
            for rule in self.rules:
                if not rule.applies_to_scope(scope):
                    continue
                match = rule.find_match(text)
                if match is None:
                    continue
                hits.append(
                    SafetyHit(
                        rule_id=rule.id,
                        category=rule.category,
                        severity=rule.severity,
                        action=rule.action,
                        excerpt=_excerpt_around(text, match),
                        safety_flags=rule.safety_flags,
                        escalation=rule.escalation,
                        replacement=rule.replacement,
                    )
                )

        flags = list(self._flow_default_flags(flow_id))
        for hit in hits:
            for flag in hit.safety_flags:
                if flag not in flags:
                    flags.append(flag)
        safety_flags = tuple(flags)

        blocked = any(hit.action in _BLOCKING_ACTIONS for hit in hits)
        rewrite = any(hit.action == "rewrite_with_uncertainty" for hit in hits)
        requires_human_review = (
            blocked
            or rewrite
            or any(hit.severity == "critical" for hit in hits)
            or "human_review_required" in safety_flags
        )
        escalations = tuple(hit.escalation for hit in hits if hit.escalation is not None)
        categories = tuple(dict.fromkeys(hit.category for hit in hits))
        replacement_text: str | None = None
        for hit in hits:
            if hit.replacement:
                replacement_text = hit.replacement
                break

        return SafetyVerdict(
            scope=scope,
            flow_id=flow_id,
            hits=tuple(hits),
            safety_flags=safety_flags,
            blocked=blocked,
            requires_human_review=requires_human_review,
            rewrite=rewrite,
            escalations=escalations,
            categories=categories,
            replacement_text=replacement_text,
        )


__all__ = [
    "DEFAULT_RULES_PATH",
    "Escalation",
    "SafetyConfigError",
    "SafetyGuard",
    "SafetyHit",
    "SafetyRule",
    "SafetyVerdict",
]
