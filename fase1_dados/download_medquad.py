"""Baixa/localiza o dataset Kaggle MedQuAD usado pela Fase B.

Gate IA-B1:
    python fase1_dados/download_medquad.py

Por padrao, o script usa `kagglehub.dataset_download` e registra o caminho do
cache em `outputs/reports/medquad_manifest.json`. Ele nao copia arquivos grandes
para o repositorio. Caso a equipe precise materializar uma amostra local para
inspecao, use explicitamente `--copy-to-raw`.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    import kagglehub
except ImportError:  # pragma: no cover - exercitado apenas sem dependencia
    kagglehub = None  # type: ignore[assignment]

from fase1_dados.common import (
    DATASET_SLUG,
    DATASET_URL,
    MANIFEST_PATH,
    RAW_DIR,
    ensure_dirs,
    sorted_data_files,
    utc_now_iso,
    write_json,
)


def _copy_dataset_to_raw(source_dir: Path) -> list[str]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source in sorted_data_files(source_dir):
        relative = source.relative_to(source_dir)
        target = RAW_DIR / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(str(target.relative_to(RAW_DIR)))
    return copied


def build_manifest(cache_path: Path, *, copied_files: list[str] | None = None) -> dict[str, Any]:
    files = sorted_data_files(cache_path)
    return {
        "dataset_slug": DATASET_SLUG,
        "dataset_url": DATASET_URL,
        "downloaded_at": utc_now_iso(),
        "cache_path": str(cache_path),
        "raw_dir": str(RAW_DIR),
        "copied_to_raw": bool(copied_files),
        "copied_files": copied_files or [],
        "files_count": len(files),
        "files_sample": [str(path.relative_to(cache_path)) for path in files[:25]],
        "note": (
            "O dataset bruto permanece no cache do kagglehub por padrao. "
            "Arquivos em data/raw/medquad sao ignorados pelo Git para evitar "
            "versionamento de dados grandes."
        ),
    }


def download_medquad(*, copy_to_raw: bool = False) -> dict[str, Any]:
    ensure_dirs()
    if kagglehub is None:
        raise RuntimeError(
            "Dependencia `kagglehub` nao instalada. Rode `pip install -r requirements.txt`."
        )

    cache_path = Path(kagglehub.dataset_download(DATASET_SLUG)).expanduser().resolve()
    copied_files = _copy_dataset_to_raw(cache_path) if copy_to_raw else []
    manifest = build_manifest(cache_path, copied_files=copied_files)
    write_json(MANIFEST_PATH, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa/localiza o Kaggle MedQuAD.")
    parser.add_argument(
        "--copy-to-raw",
        action="store_true",
        help="Copia os arquivos do cache para data/raw/medquad (ignorado pelo Git).",
    )
    args = parser.parse_args()

    manifest = download_medquad(copy_to_raw=args.copy_to_raw)
    print(f"Dataset: {manifest['dataset_slug']}")
    print(f"Cache: {manifest['cache_path']}")
    print(f"Arquivos localizados: {manifest['files_count']}")
    print(f"Manifesto: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
