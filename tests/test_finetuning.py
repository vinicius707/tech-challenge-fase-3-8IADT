"""Testes da Fase H (IA-H2/IA-H3/IA-H4).

Cobrem `fase2_finetuning/train_lora.py --dry-run` e
`fase2_finetuning/validate_adapters.py`. Nao executam treino real
(precisa de GPU); o foco e garantir o gate documental + sanidade do
schema do `metadata.json`.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from fase2_finetuning import train_lora, validate_adapters


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def _ensure_data_or_skip() -> None:
    train = DATA_DIR / "train.jsonl"
    val = DATA_DIR / "val.jsonl"
    if not train.exists() or not val.exists():
        pytest.skip(
            "data/train.jsonl ou data/val.jsonl ausentes; rode `python fase1_dados/build_dataset.py` "
            "para popular os splits antes de cobrir Fase H."
        )


def _copy_splits_into(tmp_path: Path) -> tuple[Path, Path]:
    _ensure_data_or_skip()
    train_dst = tmp_path / "train.jsonl"
    val_dst = tmp_path / "val.jsonl"
    shutil.copyfile(DATA_DIR / "train.jsonl", train_dst)
    shutil.copyfile(DATA_DIR / "val.jsonl", val_dst)
    return train_dst, val_dst


def test_run_dry_creates_metadata(tmp_path: Path) -> None:
    train, val = _copy_splits_into(tmp_path)
    metadata_path = tmp_path / "metadata.json"
    train_lora.run_dry(
        base_model="meta-llama/Llama-3.2-3B-Instruct",
        train_path=train,
        val_path=val,
        output_path=metadata_path,
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["schema_version"] == train_lora.SCHEMA_VERSION
    assert metadata["mode"] == "dry_run"
    assert metadata["base_model"]["name"] == "meta-llama/Llama-3.2-3B-Instruct"
    assert metadata["dataset"]["train"]["examples"] >= 1
    assert metadata["dataset"]["val"]["examples"] >= 1
    assert metadata["dataset"]["train"]["sha256"]
    assert metadata["dataset"]["val"]["sha256"]
    assert metadata["lora_config"]["r"] == 16
    assert metadata["artifacts"]["external"]["preferred_channel"] == "huggingface_hub"


def test_validate_accepts_dry_run_metadata(tmp_path: Path) -> None:
    train, val = _copy_splits_into(tmp_path)
    metadata_path = tmp_path / "metadata.json"
    report_path = tmp_path / "report.md"
    train_lora.run_dry(
        base_model="meta-llama/Llama-3.2-3B-Instruct",
        train_path=train,
        val_path=val,
        output_path=metadata_path,
    )
    exit_code, findings = validate_adapters.validate(metadata_path, report_path)
    levels = {entry["level"] for entry in findings}
    assert exit_code == 0
    assert "error" not in levels
    assert report_path.exists()


def test_validate_flags_missing_required_fields(tmp_path: Path) -> None:
    bogus = tmp_path / "metadata.json"
    bogus.write_text(json.dumps({"mode": "dry_run"}), encoding="utf-8")
    exit_code, findings = validate_adapters.validate(bogus, None)
    assert exit_code == 1
    assert any(entry["level"] == "error" for entry in findings)


def test_validate_detects_missing_local_adapter(tmp_path: Path) -> None:
    train, val = _copy_splits_into(tmp_path)
    metadata_path = tmp_path / "metadata.json"
    train_lora.run_dry(
        base_model="meta-llama/Llama-3.2-3B-Instruct",
        train_path=train,
        val_path=val,
        output_path=metadata_path,
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["mode"] = "trained"
    metadata["artifacts"]["local"] = {
        "directory": "outputs/model",
        "files": [
            {
                "path": "outputs/model/adapter_model.safetensors",
                "size_bytes": 12345,
                "sha256": "0" * 64,
            }
        ],
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    exit_code, findings = validate_adapters.validate(metadata_path, None)
    assert exit_code == 1
    assert any(
        "adapter declarado nao encontrado" in entry["message"] for entry in findings
    )


def test_validate_raises_when_metadata_missing(tmp_path: Path) -> None:
    with pytest.raises(validate_adapters.ValidationError):
        validate_adapters.validate(tmp_path / "missing.json", None)


def test_validate_warns_when_external_missing(tmp_path: Path) -> None:
    train, val = _copy_splits_into(tmp_path)
    metadata_path = tmp_path / "metadata.json"
    train_lora.run_dry(
        base_model="meta-llama/Llama-3.2-3B-Instruct",
        train_path=train,
        val_path=val,
        output_path=metadata_path,
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["artifacts"]["external"] = None
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    exit_code, findings = validate_adapters.validate(metadata_path, None)
    assert exit_code == 0  # warning nao quebra o gate
    assert any(entry["level"] == "warning" for entry in findings)


def test_validate_warns_on_dataset_drift(tmp_path: Path) -> None:
    train, val = _copy_splits_into(tmp_path)
    metadata_path = tmp_path / "metadata.json"
    train_lora.run_dry(
        base_model="meta-llama/Llama-3.2-3B-Instruct",
        train_path=train,
        val_path=val,
        output_path=metadata_path,
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["dataset"]["train"]["sha256"] = "f" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    exit_code, findings = validate_adapters.validate(metadata_path, None)
    assert exit_code == 0
    assert any("sha256 atual" in entry["message"] for entry in findings)


def test_run_dry_complains_on_missing_dataset(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        train_lora.run_dry(
            base_model="meta-llama/Llama-3.2-3B-Instruct",
            train_path=tmp_path / "missing.jsonl",
            val_path=tmp_path / "missing.jsonl",
            output_path=tmp_path / "out.json",
        )


def test_committed_metadata_passes_gate() -> None:
    metadata_path = PROJECT_ROOT / "outputs" / "model" / "metadata.json"
    if not metadata_path.exists():
        pytest.skip("outputs/model/metadata.json ausente; rode `train_lora.py --dry-run`.")
    exit_code, findings = validate_adapters.validate(metadata_path, None)
    assert exit_code == 0, [entry for entry in findings if entry["level"] == "error"]
