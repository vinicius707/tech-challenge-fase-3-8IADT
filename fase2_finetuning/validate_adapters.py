"""Validacao dos artefatos LoRA gerados pela Fase H.

Cobre IA-FT-02 (`docs/sdd/ia-core/spec.md`) e IA-H4
(`docs/sdd/ia-core/tasks.md`). Exemplo de uso:

    python fase2_finetuning/validate_adapters.py
    python fase2_finetuning/validate_adapters.py --metadata caminho/alternativo.json

Comportamento:

- Carrega `outputs/model/metadata.json` (default) e valida o schema.
- Em modo `trained`: confere que `artifacts.local.files[].path` existem e
  que os sha256 atuais batem com os declarados.
- Em modo `dry_run` ou quando apenas `artifacts.external` existe: emite
  status `external` ou `dry_run` com instrucoes claras para download
  (sem tentar baixar nada).
- Gera relatorio em `outputs/reports/finetuning_validation.md`.

Saida: exit code `0` quando o metadata respeita o contrato e qualquer
artefato local declarado realmente existe; `1` quando ha problemas
criticos. O modo `dry_run` retorna `0` porque atende ao gate documental
(IA-FT-02 permite "explica artefato externo").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA = PROJECT_ROOT / "outputs" / "model" / "metadata.json"
DEFAULT_REPORT = PROJECT_ROOT / "outputs" / "reports" / "finetuning_validation.md"

REQUIRED_TOP_KEYS = {
    "schema_version",
    "created_at",
    "mode",
    "purpose",
    "base_model",
    "lora_config",
    "training",
    "dataset",
    "artifacts",
}

VALID_MODES = {"dry_run", "trained", "external"}


class ValidationError(RuntimeError):
    """Falha critica na validacao do metadata."""


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _format_findings(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "_(sem ocorrencias)_\n"
    lines = []
    for entry in findings:
        level = entry.get("level", "info").upper()
        message = entry.get("message", "")
        lines.append(f"- **{level}** {message}")
    return "\n".join(lines) + "\n"


def _check_top_level(metadata: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    missing = REQUIRED_TOP_KEYS - set(metadata)
    if missing:
        findings.append(
            {"level": "error", "message": f"Campos obrigatorios ausentes: {sorted(missing)}"}
        )
    mode = metadata.get("mode")
    if mode not in VALID_MODES:
        findings.append(
            {"level": "error", "message": f"`mode` invalido: {mode!r}. Esperado {sorted(VALID_MODES)}."}
        )


def _check_dataset(metadata: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    dataset = metadata.get("dataset") or {}
    for split in ("train", "val"):
        info = dataset.get(split)
        if not isinstance(info, dict):
            findings.append({"level": "error", "message": f"Dataset.{split} ausente."})
            continue
        path = info.get("path")
        examples = info.get("examples")
        sha = info.get("sha256")
        if not path:
            findings.append({"level": "error", "message": f"Dataset.{split}.path ausente."})
            continue
        full_path = PROJECT_ROOT / path
        if not full_path.exists():
            findings.append(
                {
                    "level": "warning",
                    "message": (
                        f"Dataset.{split} declarado em `{path}` nao existe no checkout. "
                        "Rode `python fase1_dados/build_dataset.py` antes de reproduzir o treino."
                    ),
                }
            )
            continue
        if isinstance(examples, int) and examples <= 0:
            findings.append({"level": "error", "message": f"Dataset.{split} tem 0 exemplos."})
        if isinstance(sha, str) and sha:
            current = _sha256_of_file(full_path)
            if current != sha:
                findings.append(
                    {
                        "level": "warning",
                        "message": (
                            f"sha256 atual de `{path}` ({current[:12]}...) difere do declarado "
                            f"({sha[:12]}...). Regere o metadata com `--dry-run`."
                        ),
                    }
                )


def _check_local_artifacts(metadata: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    artifacts = metadata.get("artifacts") or {}
    local = artifacts.get("local")
    if not isinstance(local, dict):
        return
    files = local.get("files") or []
    if not files:
        findings.append(
            {"level": "warning", "message": "`artifacts.local.files` vazio em modo trained."}
        )
        return
    for item in files:
        rel_path = item.get("path")
        if not rel_path:
            findings.append({"level": "error", "message": "Arquivo de adapter sem `path`."})
            continue
        full_path = PROJECT_ROOT / rel_path
        if not full_path.exists():
            findings.append(
                {
                    "level": "error",
                    "message": f"Arquivo de adapter declarado nao encontrado: `{rel_path}`.",
                }
            )
            continue
        declared = item.get("sha256")
        if isinstance(declared, str) and declared:
            current = _sha256_of_file(full_path)
            if current != declared:
                findings.append(
                    {
                        "level": "error",
                        "message": (
                            f"sha256 inconsistente para `{rel_path}` "
                            f"(atual {current[:12]}... vs declarado {declared[:12]}...)."
                        ),
                    }
                )


def _check_external_artifacts(metadata: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    artifacts = metadata.get("artifacts") or {}
    external = artifacts.get("external")
    if not isinstance(external, dict):
        findings.append(
            {
                "level": "warning",
                "message": (
                    "`artifacts.external` ausente. Para artefatos grandes, documente o canal "
                    "(HF Hub, GitHub release, Git LFS) em docs/fine-tuning.md."
                ),
            }
        )
        return
    required = {"preferred_channel", "download_command", "notes"}
    missing = required - set(external)
    if missing:
        findings.append(
            {
                "level": "warning",
                "message": f"`artifacts.external` faltando campos: {sorted(missing)}.",
            }
        )


def _render_report(metadata: dict[str, Any], findings: list[dict[str, Any]], exit_code: int) -> str:
    lines = [
        "# Validacao do fine-tuning (Fase H)",
        "",
        f"- **schema_version:** `{metadata.get('schema_version', '?')}`",
        f"- **mode:** `{metadata.get('mode', '?')}`",
        f"- **base_model:** `{(metadata.get('base_model') or {}).get('name', '?')}`",
        f"- **created_at:** `{metadata.get('created_at', '?')}`",
        f"- **exit_code:** `{exit_code}`",
        "",
        "## Achados",
        "",
        _format_findings(findings),
        "## Proximos passos",
        "",
        "1. Se `mode=dry_run`, rode o notebook Colab `fase2_finetuning/FemCare_FineTuning_Colab.ipynb` "
        "ou `python fase2_finetuning/train_lora.py` em ambiente com GPU.",
        "2. Publique o adapter em Hugging Face Hub ou anexe ao GitHub Release (veja `docs/fine-tuning.md`).",
        "3. Atualize `outputs/model/metadata.json` com o canal real e novos sha256.",
        "",
    ]
    return "\n".join(lines)


def validate(metadata_path: Path, report_path: Path | None = None) -> tuple[int, list[dict[str, Any]]]:
    if not metadata_path.exists():
        raise ValidationError(
            f"metadata nao encontrado em {metadata_path}. Rode "
            "`python fase2_finetuning/train_lora.py --dry-run` para gerar."
        )
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"metadata JSON invalido: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ValidationError("metadata.json deve ser um objeto JSON.")

    findings: list[dict[str, Any]] = []
    _check_top_level(metadata, findings)
    _check_dataset(metadata, findings)

    mode = metadata.get("mode")
    if mode == "trained":
        _check_local_artifacts(metadata, findings)
    _check_external_artifacts(metadata, findings)

    has_error = any(entry.get("level") == "error" for entry in findings)
    exit_code = 1 if has_error else 0

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_render_report(metadata, findings, exit_code), encoding="utf-8")
    return exit_code, findings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida o metadata + artefatos LoRA (Fase H).")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--no-report", action="store_true", help="Nao gera o relatorio markdown.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report_path = None if args.no_report else args.report
    try:
        exit_code, findings = validate(args.metadata, report_path)
    except ValidationError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    print(f"metadata: {args.metadata}")
    print(f"achados: {len(findings)}")
    for entry in findings:
        print(f"- [{entry['level']}] {entry['message']}")
    if report_path is not None:
        print(f"relatorio: {report_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["validate", "main", "ValidationError"]
