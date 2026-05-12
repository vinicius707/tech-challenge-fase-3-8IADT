"""Validacao de respostas geradas pelo LLM (IA-E3, Fase E).

Recebe um rascunho de resposta produzido pelo LLM (ou pelo fluxo LangGraph) e
aplica as regras de output do `SafetyGuard` para:

- Bloquear conteudo proibido (prescricao, diagnostico definitivo).
- Reescrever afirmacoes definitivas para linguagem com incerteza.
- Marcar `requires_human_review` quando a politica exigir revisao humana.
- Anexar disclaimer padrao previsto em `config/safety_rules.yaml`.

O resultado preserva os flags de safety produzidos pela avaliacao de input,
para que o `audit.py` e o `ExplainBlock` recebam a uniao das marcas.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase4_seguranca.safety_guard import (
    SafetyGuard,
    SafetyVerdict,
)


@dataclass(frozen=True)
class ValidationResult:
    """Resultado da validacao de uma resposta candidata."""

    text: str
    blocked: bool
    rewritten: bool
    requires_human_review: bool
    safety_flags: tuple[str, ...]
    output_verdict: SafetyVerdict
    disclaimer_applied: bool
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "blocked": self.blocked,
            "rewritten": self.rewritten,
            "requires_human_review": self.requires_human_review,
            "safety_flags": list(self.safety_flags),
            "disclaimer_applied": self.disclaimer_applied,
            "notes": list(self.notes),
        }


@dataclass
class ResponseValidator:
    """Validador de respostas que reusa o `SafetyGuard` da Fase E."""

    guard: SafetyGuard

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> "ResponseValidator":
        return cls(guard=SafetyGuard.from_yaml(path))

    def validate(
        self,
        text: str,
        *,
        flow_id: str | None = None,
        input_verdict: SafetyVerdict | None = None,
        append_disclaimer: bool = True,
    ) -> ValidationResult:
        candidate = (text or "").strip()
        if not candidate:
            candidate = (
                "Nao foi possivel gerar uma resposta neste momento. "
                "Por favor, reformule a pergunta ou procure atendimento presencial."
            )

        verdict = self.guard.evaluate(candidate, scope="output", flow_id=flow_id)

        notes: list[str] = []
        rewritten = False
        blocked = verdict.blocked
        final_text = candidate

        if blocked and verdict.replacement_text:
            final_text = verdict.replacement_text.strip()
            notes.append(f"output_blocked_by:{','.join(h.rule_id for h in verdict.hits)}")
            rewritten = True
        elif verdict.rewrite and verdict.replacement_text:
            final_text = verdict.replacement_text.strip()
            notes.append(f"output_rewritten_by:{','.join(h.rule_id for h in verdict.hits)}")
            rewritten = True

        # Se a entrada ja tinha sido escalada por safety, garantimos que a
        # resposta seguinte herde o tom e a mensagem de seguranca.
        if input_verdict and input_verdict.blocked and input_verdict.replacement_text:
            final_text = input_verdict.replacement_text.strip()
            blocked = True
            rewritten = True
            notes.append(
                "input_safety_override:" + ",".join(h.rule_id for h in input_verdict.hits)
            )

        disclaimer_applied = False
        if append_disclaimer:
            disclaimer = self.guard.default_disclaimer()
            if disclaimer and disclaimer not in final_text:
                final_text = f"{final_text}\n\n{disclaimer}"
                disclaimer_applied = True

        merged_flags = _merge_flags(
            input_verdict.safety_flags if input_verdict else (),
            verdict.safety_flags,
        )

        requires_review = (
            verdict.requires_human_review
            or (input_verdict.requires_human_review if input_verdict else False)
            or blocked
        )

        return ValidationResult(
            text=final_text,
            blocked=blocked,
            rewritten=rewritten,
            requires_human_review=requires_review,
            safety_flags=merged_flags,
            output_verdict=verdict,
            disclaimer_applied=disclaimer_applied,
            notes=tuple(notes),
        )


def _merge_flags(*sources: Iterable[str]) -> tuple[str, ...]:
    merged: list[str] = []
    for source in sources:
        for flag in source or ():
            if flag and flag not in merged:
                merged.append(flag)
    return tuple(merged)


__all__ = ["ResponseValidator", "ValidationResult"]
