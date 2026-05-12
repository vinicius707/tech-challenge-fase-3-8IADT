"""Script de fine-tuning LoRA/QLoRA para o IA Core (Fase H).

Cobre IA-H2 e IA-H3 do `docs/sdd/ia-core/tasks.md`. Implementa duas
modos de execucao:

- `--dry-run` (padrao quando dependencias pesadas faltam): valida o
  dataset, fixa hiperparametros e grava `outputs/model/metadata.json`
  com `mode=dry_run`. Permite que avaliadores tenham evidencia
  reproduzivel **sem GPU** e satisfaz o gate `validate_adapters.py`.

- modo completo (`--dry-run` ausente): executa o pipeline real LoRA/QLoRA
  com Transformers + PEFT + TRL. Recomendado rodar em Colab (T4/A100) ou
  workstation com GPU. Pesos sao salvos em `outputs/model/` e o
  `metadata.json` final reflete `mode=trained` com sha256 dos artefatos.

Mantemos o design alinhado a `docs/sdd/ia-core/design.md` §3 e ao
contexto `docs/sdd/ia-core/context.md` (D2): fine-tuning ajusta formato
e linguagem, **nao substitui** RAG, guardrails ou raciocinio clinico.

Uso:

    python fase2_finetuning/train_lora.py --dry-run
    python fase2_finetuning/train_lora.py --base-model meta-llama/Llama-3.2-3B-Instruct

Variaveis de ambiente uteis (passadas ao Trainer em modo completo):

    FT_BASE_MODEL      override do modelo base.
    FT_OUTPUT_DIR      destino dos pesos (default `outputs/model`).
    FT_EPOCHS / FT_LR  override de hiperparametros.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "model"
DEFAULT_TRAIN_PATH = PROJECT_ROOT / "data" / "train.jsonl"
DEFAULT_VAL_PATH = PROJECT_ROOT / "data" / "val.jsonl"
METADATA_PATH = DEFAULT_OUTPUT_DIR / "metadata.json"
SCHEMA_VERSION = "1.0"
DATASET_SOURCE = (
    "MedQuAD (pythonafroz/medquad-medical-question-answer-for-ai-research) + "
    "complementos sinteticos curados (synthetic_protocol_v1)"
)

REQUIRED_DOMAINS = {
    "triagemGinecologica",
    "violenciaDomestica",
    "obstetrico",
    "prevencao",
}


# ---------------------------------------------------------------------------
# Configuracoes (defaults centralizados, reaproveitados pelo notebook Colab)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoraConfig:
    """Hiperparametros LoRA reaproveitados em metadata.json e treino real."""

    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    bias: str = "none"
    task_type: str = "CAUSAL_LM"
    target_modules: tuple[str, ...] = (
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
    )


@dataclass(frozen=True)
class TrainingConfig:
    epochs: int = 2
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    max_seq_length: int = 1024
    warmup_ratio: float = 0.05
    lr_scheduler_type: str = "cosine"
    optim: str = "paged_adamw_8bit"
    bf16: bool = True
    seed: int = 42
    framework: str = "trl.SFTTrainer"


@dataclass
class DatasetSplit:
    path: str
    examples: int
    sha256: str
    domains: list[str] = field(default_factory=list)


@dataclass
class ArtifactsExternal:
    preferred_channel: str = "huggingface_hub"
    huggingface_repo: str = "<org>/femcare-llama32-lora"
    github_release_asset: str = (
        "https://github.com/<org>/<repo>/releases/download/v0.1.0-lora/adapter.zip"
    )
    download_command: str = (
        "huggingface-cli download <org>/femcare-llama32-lora --local-dir outputs/model"
    )
    sha256: str | None = None
    notes: str = (
        "Pesos NAO sao versionados no Git. Veja docs/fine-tuning.md para o "
        "fluxo recomendado de release (HF Hub > GitHub Release > Git LFS)."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _relative_to_project(path: Path) -> str:
    """Retorna o path relativo ao repositorio quando possivel; caso contrario, absoluto.

    Mantemos paths relativos no metadata persistido no Git para legibilidade,
    mas em testes ou execucoes fora do checkout o fallback evita ValueError.
    """

    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(resolved)


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line_no, line in enumerate(fp, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Linha {line_no} de {path} nao e JSON valido: {exc}"
                ) from exc
    return rows


def _validate_split(name: str, path: Path) -> DatasetSplit:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset {name} ausente em {path}. Rode `python fase1_dados/build_dataset.py` "
            "antes do treino (Fase B)."
        )
    rows = _iter_jsonl(path)
    if not rows:
        raise ValueError(f"Dataset {name} vazio em {path}.")

    domains: set[str] = set()
    for row in rows:
        domain = row.get("domain")
        messages = row.get("messages")
        if not isinstance(domain, str) or not domain:
            raise ValueError(f"Linha sem 'domain' em {path}")
        if not isinstance(messages, list) or not messages:
            raise ValueError(f"Linha sem 'messages' em {path}")
        domains.add(domain)

    return DatasetSplit(
        path=_relative_to_project(path),
        examples=len(rows),
        sha256=_sha256_of_file(path),
        domains=sorted(domains),
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _environment_info() -> dict[str, str]:
    """Informacoes minimas e nao sensiveis para auditoria do treino."""

    return {
        "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.release()}",
    }


# ---------------------------------------------------------------------------
# Metadata builder (usado pelo dry-run e pelo treino real)
# ---------------------------------------------------------------------------


def build_metadata(
    *,
    mode: str,
    base_model: str,
    lora: LoraConfig,
    training: TrainingConfig,
    train_split: DatasetSplit,
    val_split: DatasetSplit,
    artifacts_local: dict[str, Any] | None = None,
    artifacts_external: ArtifactsExternal | None = None,
    training_results: dict[str, Any] | None = None,
    notes_extra: list[str] | None = None,
) -> dict[str, Any]:
    """Compoe o dicionario serializado em `outputs/model/metadata.json`.

    O schema e estavel entre dry-run e treino real para que
    `validate_adapters.py` consiga avaliar ambos os modos.
    """

    notes = [
        "Fine-tuning trata formato/linguagem - NAO substitui RAG nem guardrails.",
        "Pesos pesados nao sao versionados no Git; veja docs/fine-tuning.md.",
        "Para reproducao sem GPU use `python fase2_finetuning/train_lora.py --dry-run`.",
    ]
    if notes_extra:
        notes.extend(notes_extra)

    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": _now_iso(),
        "mode": mode,
        "purpose": (
            "Ajuste de formato/linguagem em portugues clinico para os quatro "
            "fluxos de saude da mulher (triagem, violencia, obstetrico, prevencao). "
            "Nao deve ser usado como unica fonte de raciocinio clinico."
        ),
        "base_model": {
            "name": base_model,
            "license": "Consulte o card do modelo no Hugging Face Hub.",
        },
        "lora_config": asdict(lora) | {"target_modules": list(lora.target_modules)},
        "training": asdict(training) | (
            {"results": training_results} if training_results else {"results": None}
        ),
        "dataset": {
            "source": DATASET_SOURCE,
            "kaggle_slug": "pythonafroz/medquad-medical-question-answer-for-ai-research",
            "format": "openai-chat-messages",
            "domains_required": sorted(REQUIRED_DOMAINS),
            "train": asdict(train_split),
            "val": asdict(val_split),
        },
        "artifacts": {
            "local": artifacts_local,
            "external": asdict(artifacts_external) if artifacts_external else None,
        },
        "environment": _environment_info(),
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Dry-run path (sem dependencias pesadas)
# ---------------------------------------------------------------------------


def run_dry(
    *,
    base_model: str,
    train_path: Path,
    val_path: Path,
    output_path: Path,
) -> Path:
    """Valida o dataset e emite metadata.json em modo dry-run.

    Nao instala/usa torch/peft/trl. Util para o gate IA-FT-02 em
    ambientes sem GPU (incluindo CI).
    """

    train_split = _validate_split("train", train_path)
    val_split = _validate_split("val", val_path)

    coverage_train = set(train_split.domains)
    coverage_val = set(val_split.domains)
    missing = REQUIRED_DOMAINS - (coverage_train | coverage_val)

    metadata = build_metadata(
        mode="dry_run",
        base_model=base_model,
        lora=LoraConfig(),
        training=TrainingConfig(),
        train_split=train_split,
        val_split=val_split,
        artifacts_external=ArtifactsExternal(),
        notes_extra=(
            [f"Dominios ausentes nos splits: {sorted(missing)}"] if missing else None
        ),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output_path


# ---------------------------------------------------------------------------
# Treino real (lazy imports para nao quebrar dry-run sem GPU)
# ---------------------------------------------------------------------------


def run_training(
    *,
    base_model: str,
    train_path: Path,
    val_path: Path,
    output_dir: Path,
    lora: LoraConfig,
    training: TrainingConfig,
) -> dict[str, Any]:
    """Roda LoRA/QLoRA usando Transformers + PEFT + TRL.

    Lazy import evita custo de carregar torch no `--dry-run`. O fluxo
    aqui segue a receita canonica recomendada no Colab (`docs/fine-tuning.md`):
    bnb 4-bit + LoRA via PEFT + SFTTrainer + save_pretrained.
    """

    try:
        import torch  # noqa: F401
        from datasets import load_dataset  # type: ignore[import-not-found]
        from peft import LoraConfig as PeftLoraConfig  # type: ignore[import-not-found]
        from peft import get_peft_model  # type: ignore[import-not-found]
        from transformers import (  # type: ignore[import-not-found]
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
        )
        from trl import SFTConfig, SFTTrainer  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "Dependencias de fine-tuning ausentes. Instale com "
            "`pip install -r requirements-finetuning.txt` (precisa de GPU) ou rode "
            "`python fase2_finetuning/train_lora.py --dry-run` para validar o pipeline."
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype="bfloat16",
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
    )

    peft_config = PeftLoraConfig(
        r=lora.r,
        lora_alpha=lora.lora_alpha,
        lora_dropout=lora.lora_dropout,
        bias=lora.bias,
        task_type=lora.task_type,
        target_modules=list(lora.target_modules),
    )
    model = get_peft_model(model, peft_config)

    data_files = {"train": str(train_path), "validation": str(val_path)}
    dataset = load_dataset("json", data_files=data_files)

    sft_config = SFTConfig(
        output_dir=str(output_dir),
        num_train_epochs=training.epochs,
        per_device_train_batch_size=training.per_device_train_batch_size,
        gradient_accumulation_steps=training.gradient_accumulation_steps,
        learning_rate=training.learning_rate,
        warmup_ratio=training.warmup_ratio,
        lr_scheduler_type=training.lr_scheduler_type,
        optim=training.optim,
        bf16=training.bf16,
        max_seq_length=training.max_seq_length,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        seed=training.seed,
        report_to=[],
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        args=sft_config,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
    )

    train_metrics = trainer.train()
    eval_metrics = trainer.evaluate()

    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    return {
        "train_loss": float(getattr(train_metrics, "training_loss", 0.0) or 0.0),
        "eval_loss": float(eval_metrics.get("eval_loss", 0.0) or 0.0),
        "eval_runtime_s": float(eval_metrics.get("eval_runtime", 0.0) or 0.0),
    }


def _collect_local_artifacts(output_dir: Path) -> dict[str, Any] | None:
    """Coleta arquivos relevantes do adapter para checksum + tamanho."""

    expected = [
        "adapter_model.safetensors",
        "adapter_config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
    ]
    files: list[dict[str, Any]] = []
    for name in expected:
        path = output_dir / name
        if not path.exists():
            continue
        files.append(
            {
                "path": _relative_to_project(path),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_of_file(path),
            }
        )
    if not files:
        return None
    return {
        "directory": _relative_to_project(output_dir),
        "files": files,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Treino LoRA/QLoRA para o IA Core (modo dry-run sem GPU disponivel)."
    )
    parser.add_argument(
        "--base-model",
        default=os.environ.get("FT_BASE_MODEL", "meta-llama/Llama-3.2-3B-Instruct"),
        help="Modelo base no Hugging Face Hub.",
    )
    parser.add_argument(
        "--train",
        type=Path,
        default=DEFAULT_TRAIN_PATH,
        help="Caminho para data/train.jsonl.",
    )
    parser.add_argument(
        "--val",
        type=Path,
        default=DEFAULT_VAL_PATH,
        help="Caminho para data/val.jsonl.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("FT_OUTPUT_DIR") or DEFAULT_OUTPUT_DIR),
        help="Diretorio onde os pesos LoRA serao salvos.",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=METADATA_PATH,
        help="Onde gravar metadata.json (default: outputs/model/metadata.json).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida dataset e grava metadata.json sem rodar o treino real.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=int(os.environ.get("FT_EPOCHS", "2")),
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=float(os.environ.get("FT_LR", "2e-4")),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.dry_run:
        path = run_dry(
            base_model=args.base_model,
            train_path=args.train,
            val_path=args.val,
            output_path=args.metadata_path,
        )
        print(f"metadata escrito em {path}")
        return 0

    train_split = _validate_split("train", args.train)
    val_split = _validate_split("val", args.val)

    lora = LoraConfig()
    training = TrainingConfig(
        epochs=args.epochs,
        learning_rate=args.learning_rate,
    )

    results = run_training(
        base_model=args.base_model,
        train_path=args.train,
        val_path=args.val,
        output_dir=args.output_dir,
        lora=lora,
        training=training,
    )

    artifacts_local = _collect_local_artifacts(args.output_dir)
    metadata = build_metadata(
        mode="trained",
        base_model=args.base_model,
        lora=lora,
        training=training,
        train_split=train_split,
        val_split=val_split,
        artifacts_local=artifacts_local,
        artifacts_external=ArtifactsExternal(),
        training_results=results,
    )

    args.metadata_path.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"metadata escrito em {args.metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ArtifactsExternal",
    "LoraConfig",
    "TrainingConfig",
    "DatasetSplit",
    "build_metadata",
    "run_dry",
    "run_training",
    "main",
]
