"""Utilitarios compartilhados do pipeline de dados da Fase B."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_SLUG = "pythonafroz/medquad-medical-question-answer-for-ai-research"
DATASET_URL = f"https://www.kaggle.com/datasets/{DATASET_SLUG}"

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "medquad"
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"

MANIFEST_PATH = REPORTS_DIR / "medquad_manifest.json"
PROFILE_PATH = REPORTS_DIR / "data_profile.md"
VALIDATION_REPORT_PATH = REPORTS_DIR / "data_validation.md"

NORMALIZED_PATH = PROCESSED_DIR / "medquad_normalized.jsonl"
SYNTHETIC_PATH = SYNTHETIC_DIR / "womens_health_curated.jsonl"
RAG_DOCUMENTS_PATH = PROJECT_ROOT / "data" / "rag_documents.jsonl"
TRAIN_PATH = PROJECT_ROOT / "data" / "train.jsonl"
VAL_PATH = PROJECT_ROOT / "data" / "val.jsonl"

ALLOWED_DOMAINS = {
    "triagemGinecologica",
    "violenciaDomestica",
    "obstetrico",
    "prevencao",
    "medicinaGeral",
    "excluir",
}

RAG_DOMAINS = ALLOWED_DOMAINS - {"excluir"}


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dirs() -> None:
    for path in (RAW_DIR, SYNTHETIC_DIR, PROCESSED_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: JSON invalido") from exc


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def normalize_whitespace(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def safe_excerpt(text: str, *, max_chars: int = 220) -> str:
    """Gera amostra curta sem emails/telefones para relatorios de exploracao."""

    text = normalize_whitespace(text)
    text = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[email-redigido]", text)
    text = re.sub(r"\+?\d[\d\s().-]{7,}\d", "[telefone-redigido]", text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return read_json(path)


def resolve_dataset_dir(explicit_path: str | None = None) -> Path:
    if explicit_path:
        path = Path(explicit_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Diretorio informado nao existe: {path}")
        return path

    manifest = load_manifest()
    if manifest and manifest.get("cache_path"):
        path = Path(str(manifest["cache_path"])).expanduser().resolve()
        if path.exists():
            return path

    if any(RAW_DIR.iterdir()):
        return RAW_DIR

    raise FileNotFoundError(
        "Dataset MedQuAD nao localizado. Rode `python fase1_dados/download_medquad.py` "
        "ou passe `--source-dir`."
    )


def sorted_data_files(source_dir: Path) -> list[Path]:
    supported = {".xml", ".json", ".jsonl", ".csv", ".tsv", ".txt"}
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in supported
    )
