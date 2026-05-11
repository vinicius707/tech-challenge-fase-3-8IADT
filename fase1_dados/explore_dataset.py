"""Explora o dataset MedQuAD e gera perfil anonimizavel.

Gate IA-B2:
    python fase1_dados/explore_dataset.py

O script nao persiste perguntas/respostas completas no relatorio. As amostras
sao truncadas e passam por redacao simples de email/telefone.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase1_dados.common import (
    DATASET_SLUG,
    PROFILE_PATH,
    ensure_dirs,
    resolve_dataset_dir,
    safe_excerpt,
    sorted_data_files,
    utc_now_iso,
)
from fase1_dados.extract_medquad import extract_qa_records


def profile_dataset(source_dir: Path) -> dict[str, object]:
    files = sorted_data_files(source_dir)
    by_extension = Counter(path.suffix.lower() for path in files)
    qa_by_extension: Counter[str] = Counter()
    samples: list[dict[str, str]] = []
    total_qa = 0

    for path in files:
        count_for_file = 0
        for record in extract_qa_records(path):
            total_qa += 1
            count_for_file += 1
            if len(samples) < 12:
                samples.append(
                    {
                        "file": str(path.relative_to(source_dir)),
                        "question": safe_excerpt(record["question"]),
                        "answer": safe_excerpt(record["answer"]),
                    }
                )
        if count_for_file:
            qa_by_extension[path.suffix.lower()] += count_for_file

    return {
        "dataset_slug": DATASET_SLUG,
        "source_dir": str(source_dir),
        "generated_at": utc_now_iso(),
        "files_count": len(files),
        "by_extension": dict(sorted(by_extension.items())),
        "qa_pairs_count": total_qa,
        "qa_by_extension": dict(sorted(qa_by_extension.items())),
        "samples": samples,
    }


def write_profile_markdown(profile: dict[str, object]) -> None:
    lines = [
        "# Perfil do Dataset MedQuAD",
        "",
        f"- Dataset: `{profile['dataset_slug']}`",
        f"- Diretório analisado: `{profile['source_dir']}`",
        f"- Gerado em: `{profile['generated_at']}`",
        f"- Arquivos encontrados: **{profile['files_count']}**",
        f"- Pares pergunta/resposta extraídos: **{profile['qa_pairs_count']}**",
        "",
        "## Distribuição por extensão",
        "",
        "| Extensão | Arquivos | Pares QA extraídos |",
        "|---|---:|---:|",
    ]
    by_extension = profile["by_extension"]  # type: ignore[assignment]
    qa_by_extension = profile["qa_by_extension"]  # type: ignore[assignment]
    for extension, count in by_extension.items():
        lines.append(f"| `{extension}` | {count} | {qa_by_extension.get(extension, 0)} |")

    lines.extend(
        [
            "",
            "## Amostras redigidas",
            "",
            "As amostras abaixo são truncadas e redigidas para evitar exposição de dados sensíveis.",
            "",
        ]
    )
    samples = profile["samples"]  # type: ignore[assignment]
    if not samples:
        lines.append("- Nenhum par pergunta/resposta foi extraído dos arquivos disponíveis.")
    for sample in samples:
        lines.extend(
            [
                f"### `{sample['file']}`",
                "",
                f"- Pergunta: {sample['question']}",
                f"- Resposta: {sample['answer']}",
                "",
            ]
        )

    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Explora arquivos MedQuAD localizados.")
    parser.add_argument("--source-dir", help="Diretorio do dataset, se nao usar manifesto/cache.")
    args = parser.parse_args()

    ensure_dirs()
    source_dir = resolve_dataset_dir(args.source_dir)
    profile = profile_dataset(source_dir)
    write_profile_markdown(profile)
    print(f"Arquivos: {profile['files_count']}")
    print(f"Pares QA extraidos: {profile['qa_pairs_count']}")
    print(f"Perfil: {PROFILE_PATH}")


if __name__ == "__main__":
    main()
