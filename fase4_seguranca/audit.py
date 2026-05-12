"""Auditoria minimizada (IA-E5, Fase E).

Escreve `logs/audit.log` em JSON Lines conforme `docs/sdd/ia-core/design.md`
secao 11. Regras chave:

- Cada requisicao gera UMA linha JSON.
- Nunca registra conteudo sensivel completo (violencia, autoagressao).
- Conteudo livre passa por redator (`redact_text`) antes de chegar ao log.
- `sensitive_redacted=True` indica que houve redacao explicita do prompt.

A interface e sincrona e thread-safe (lock simples). Para evitar criar o
arquivo em ambientes onde nao queremos efeitos colaterais (ex.: testes que
nao especificam um caminho), o construtor exige `log_path` explicito.
"""

from __future__ import annotations

import json
import re
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))


SENSITIVE_CATEGORIES = frozenset({"violence", "self_harm"})
SENSITIVE_FLOWS = frozenset({"violenciaDomestica"})
_FULL_REDACTION_PLACEHOLDER = "[REDACTED:sensitive_content]"

_PII_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "[REDACTED:cpf]"),
    (re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b"), "[REDACTED:email]"),
    (
        re.compile(r"(?:\(?\d{2}\)?[\s-]?)?9?\d{4}[-\s]?\d{4}\b"),
        "[REDACTED:phone]",
    ),
    (
        re.compile(r"\b\d{2,3}\.?\d{3}\.?\d{3}/?\d{0,4}-?\d{0,2}\b"),
        "[REDACTED:doc]",
    ),
)


def utc_now_isoformat() -> str:
    """Timestamp em UTC com sufixo Z, conforme exemplo do design.md."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def redact_text(
    text: str | None,
    *,
    flow_id: str | None = None,
    categories: Iterable[str] | None = None,
    redact_sensitive: bool = False,
) -> str | None:
    """Aplica redacao minimizada de PII e/ou bloqueio total de conteudo sensivel.

    - Se `flow_id` estiver em `SENSITIVE_FLOWS` ou alguma categoria de regra
      pertencer a `SENSITIVE_CATEGORIES`, ou `redact_sensitive=True`, retorna
      placeholder integral.
    - Caso contrario, aplica apenas mascaramento de padroes de PII.
    """
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    cat_set = {c for c in (categories or ()) if isinstance(c, str)}
    if (
        redact_sensitive
        or (flow_id in SENSITIVE_FLOWS)
        or (cat_set & SENSITIVE_CATEGORIES)
    ):
        return _FULL_REDACTION_PLACEHOLDER
    redacted = text
    for pattern, placeholder in _PII_PATTERNS:
        redacted = pattern.sub(placeholder, redacted)
    return redacted


def _normalize_flags(flags: Iterable[str] | None) -> list[str]:
    result: list[str] = []
    for flag in flags or ():
        if isinstance(flag, str) and flag and flag not in result:
            result.append(flag)
    return result


@dataclass
class AuditEvent:
    """Representacao tipada de uma linha do `logs/audit.log`."""

    request_id: str
    flow_id: str | None
    model_version: str | None
    sources_count: int = 0
    safety_flags: list[str] = field(default_factory=list)
    urgency: str | None = None
    blocked: bool = False
    sensitive_redacted: bool = False
    duration_ms: int | None = None
    ts: str = field(default_factory=utc_now_isoformat)
    extra: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ts": self.ts,
            "request_id": self.request_id,
            "flow_id": self.flow_id,
            "model_version": self.model_version,
            "sources_count": int(self.sources_count or 0),
            "safety_flags": list(self.safety_flags),
            "urgency": self.urgency,
            "blocked": bool(self.blocked),
            "sensitive_redacted": bool(self.sensitive_redacted),
            "duration_ms": int(self.duration_ms) if self.duration_ms is not None else None,
        }
        if self.extra:
            safe_extra = {k: v for k, v in dict(self.extra).items() if k not in payload}
            payload.update(safe_extra)
        return payload


class AuditLogger:
    """Escritor JSON Lines minimizado para `logs/audit.log`."""

    def __init__(self, log_path: Path) -> None:
        if not isinstance(log_path, Path):
            log_path = Path(str(log_path))
        self._log_path = log_path
        self._lock = threading.Lock()

    @property
    def log_path(self) -> Path:
        return self._log_path

    def _ensure_parent(self) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: AuditEvent) -> dict[str, Any]:
        """Persiste `event` em uma linha JSON e devolve o payload escrito."""
        payload = event.to_dict()
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with self._lock:
            self._ensure_parent()
            with self._log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        return payload

    def log_request(
        self,
        *,
        request_id: str,
        flow_id: str | None,
        model_version: str | None,
        sources_count: int,
        safety_flags: Iterable[str] | None,
        urgency: str | None,
        blocked: bool,
        sensitive_redacted: bool,
        duration_ms: int | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = AuditEvent(
            request_id=str(request_id),
            flow_id=flow_id,
            model_version=model_version,
            sources_count=int(sources_count or 0),
            safety_flags=_normalize_flags(safety_flags),
            urgency=urgency,
            blocked=bool(blocked),
            sensitive_redacted=bool(sensitive_redacted),
            duration_ms=duration_ms,
            extra=extra,
        )
        return self.write(event)


__all__ = [
    "AuditEvent",
    "AuditLogger",
    "SENSITIVE_CATEGORIES",
    "SENSITIVE_FLOWS",
    "redact_text",
    "utc_now_isoformat",
]
