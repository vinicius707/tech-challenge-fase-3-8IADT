"""Normaliza MedQuAD e gera arquivos internos para RAG/fine-tuning.

Gates IA-B3 a IA-B7:
    python fase1_dados/build_dataset.py

Saidas geradas (ignoradas pelo Git quando potencialmente volumosas):
    data/processed/medquad_normalized.jsonl
    data/rag_documents.jsonl
    data/train.jsonl
    data/val.jsonl

Entrada versionada e pequena:
    data/synthetic/womens_health_curated.jsonl
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from fase1_dados.common import (
    DATASET_SLUG,
    DATASET_URL,
    NORMALIZED_PATH,
    RAG_DOCUMENTS_PATH,
    SYNTHETIC_PATH,
    TRAIN_PATH,
    VAL_PATH,
    ensure_dirs,
    iter_jsonl,
    normalize_whitespace,
    resolve_dataset_dir,
    sorted_data_files,
    stable_id,
    utc_now_iso,
    write_jsonl,
)
from fase1_dados.extract_medquad import extract_qa_records, normalized_record_id

SYSTEM_PROMPT = "Voce e um assistente de apoio clinico em saude da mulher."

DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "violenciaDomestica": (
        "abuse",
        "assault",
        "coercion",
        "domestic violence",
        "fear of partner",
        "intimate partner",
        "violence",
        "agressao",
        "agressor",
        "medo do parceiro",
        "violencia",
    ),
    "obstetrico": (
        "birth",
        "fetal",
        "gestation",
        "gestational",
        "labor",
        "miscarriage",
        "obstetric",
        "pregnancy",
        "pregnant",
        "prenatal",
        "amamentacao",
        "gestante",
        "gravidez",
        "pre-natal",
    ),
    "prevencao": (
        "breast cancer",
        "cervical cancer",
        "hpv",
        "mammogram",
        "pap smear",
        "screening",
        "vaccine",
        "vaccination",
        "cancer de colo",
        "mamografia",
        "preventivo",
        "rastreamento",
    ),
    "triagemGinecologica": (
        "candidiasis",
        "contraception",
        "endometriosis",
        "fibroid",
        "gynecologic",
        "menopause",
        "menstrual",
        "ovarian",
        "pelvic pain",
        "vaginal",
        "corrimento",
        "dor pelvica",
        "menstrual",
        "vaginal",
    ),
}

GENERAL_MEDICAL_KEYWORDS = (
    "diagnosis",
    "disease",
    "health",
    "medicine",
    "symptom",
    "treatment",
)

HIGH_SENSITIVITY_KEYWORDS = (
    "abuse",
    "assault",
    "domestic violence",
    "intimate partner",
    "violence",
    "agressao",
    "agressor",
    "violencia",
)

MEDIUM_SENSITIVITY_KEYWORDS = (
    "pregnancy",
    "pregnant",
    "gestante",
    "gravidez",
    "obstetric",
)


def classify_domain(question: str, answer: str) -> str:
    text = f"{question} {answer}".lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword in text)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    best_domain, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        return best_domain
    if any(keyword in text for keyword in GENERAL_MEDICAL_KEYWORDS):
        return "medicinaGeral"
    return "excluir"


def infer_sensitivity(question: str, answer: str, domain: str) -> str:
    text = f"{question} {answer}".lower()
    if domain == "violenciaDomestica" or any(keyword in text for keyword in HIGH_SENSITIVITY_KEYWORDS):
        return "high"
    if domain == "obstetrico" or any(keyword in text for keyword in MEDIUM_SENSITIVITY_KEYWORDS):
        return "medium"
    return "low"


def normalize_medquad(source_dir: Path, *, max_records: int | None = None) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    seen: set[str] = set()
    for path in sorted_data_files(source_dir):
        for raw in extract_qa_records(path):
            question = normalize_whitespace(raw["question"])
            answer = normalize_whitespace(raw["answer"])
            if len(question) < 8 or len(answer) < 20:
                continue
            record_id = normalized_record_id(question, answer)
            if record_id in seen:
                continue
            seen.add(record_id)
            domain = classify_domain(question, answer)
            sensitivity = infer_sensitivity(question, answer, domain)
            records.append(
                {
                    "id": record_id,
                    "question": question,
                    "answer": answer,
                    "domain": domain,
                    "source": "kaggle_medquad",
                    "dataset_slug": DATASET_SLUG,
                    "dataset_url": DATASET_URL,
                    "citation": "Kaggle MedQuAD - registro normalizado",
                    "sensitivity": sensitivity,
                    "include_for_training": domain not in {"excluir", "medicinaGeral"},
                    "include_for_rag": domain != "excluir",
                    "source_file": str(Path(raw["source_file"]).relative_to(source_dir)),
                    "source_row": raw["source_row"],
                    "normalized_at": utc_now_iso(),
                }
            )
            if max_records and len(records) >= max_records:
                return records
    return records


def load_synthetic_records(path: Path = SYNTHETIC_PATH) -> list[dict[str, object]]:
    records = list(iter_jsonl(path))
    for record in records:
        record.setdefault("dataset_slug", "synthetic_protocol_v1")
        record.setdefault("dataset_url", "")
        record.setdefault("include_for_training", True)
        record.setdefault("include_for_rag", True)
    return records


def to_rag_document(record: dict[str, object]) -> dict[str, object]:
    source = str(record["source"])
    domain = str(record["domain"])
    title_prefix = "MedQuAD" if source == "kaggle_medquad" else "Protocolo sintetico"
    content = (
        f"Pergunta: {record['question']}\n"
        f"Resposta curada: {record['answer']}\n"
        "Nota: material de apoio para triagem/educacao; nao substitui avaliacao profissional."
    )
    return {
        "doc_id": stable_id("rag", str(record["id"]), domain),
        "title": f"{title_prefix} - {domain}",
        "domain": domain,
        "version": "2026.05",
        "source": source,
        "sensitivity": record["sensitivity"],
        "content": content,
        "citation": record["citation"],
        "record_id": record["id"],
    }


def to_training_example(record: dict[str, object]) -> dict[str, object]:
    return {
        "id": stable_id("train", str(record["id"])),
        "domain": record["domain"],
        "sensitivity": record["sensitivity"],
        "source": record["source"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": str(record["question"])},
            {
                "role": "assistant",
                "content": (
                    f"{record['answer']}\n\n"
                    "Encaminhe para avaliacao profissional quando houver sinais de alarme, "
                    "lacunas clinicas ou necessidade de diagnostico/conduta individualizada."
                ),
            },
        ],
    }


def split_train_val(records: list[dict[str, object]], *, val_ratio: float = 0.2) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    by_domain: dict[str, list[dict[str, object]]] = {}
    for record in records:
        by_domain.setdefault(str(record["domain"]), []).append(record)

    train: list[dict[str, object]] = []
    val: list[dict[str, object]] = []
    for domain_records in by_domain.values():
        domain_records = sorted(domain_records, key=lambda item: str(item["id"]))
        val_count = 1 if len(domain_records) > 1 else 0
        if len(domain_records) >= 5:
            val_count = max(1, round(len(domain_records) * val_ratio))
        val.extend(domain_records[:val_count])
        train.extend(domain_records[val_count:])
    return train, val


def build_outputs(
    *,
    source_dir: Path | None,
    max_medquad_records: int | None = None,
    synthetic_only: bool = False,
) -> dict[str, object]:
    ensure_dirs()
    medquad_records: list[dict[str, object]] = []
    if not synthetic_only:
        if source_dir is None:
            raise ValueError("source_dir e obrigatorio quando synthetic_only=False")
        medquad_records = normalize_medquad(source_dir, max_records=max_medquad_records)

    synthetic_records = load_synthetic_records()
    normalized_count = write_jsonl(NORMALIZED_PATH, medquad_records)

    all_records = [*medquad_records, *synthetic_records]
    rag_records = [record for record in all_records if record.get("include_for_rag") and record["domain"] != "excluir"]
    training_records = [
        record
        for record in all_records
        if record.get("include_for_training") and record["domain"] not in {"excluir", "medicinaGeral"}
    ]

    rag_docs = [to_rag_document(record) for record in rag_records]
    train_source, val_source = split_train_val(training_records)
    train_examples = [to_training_example(record) for record in train_source]
    val_examples = [to_training_example(record) for record in val_source]

    write_jsonl(RAG_DOCUMENTS_PATH, rag_docs)
    write_jsonl(TRAIN_PATH, train_examples)
    write_jsonl(VAL_PATH, val_examples)

    domain_counts = Counter(str(record["domain"]) for record in all_records)
    return {
        "medquad_normalized": normalized_count,
        "synthetic_records": len(synthetic_records),
        "rag_documents": len(rag_docs),
        "train_examples": len(train_examples),
        "val_examples": len(val_examples),
        "domain_counts": dict(sorted(domain_counts.items())),
        "outputs": {
            "normalized": str(NORMALIZED_PATH),
            "rag_documents": str(RAG_DOCUMENTS_PATH),
            "train": str(TRAIN_PATH),
            "val": str(VAL_PATH),
        },
    }


def _print_summary(summary: dict[str, object]) -> None:
    print("Resumo do build_dataset.py")
    print(f"- MedQuAD normalizado: {summary['medquad_normalized']}")
    print(f"- Sinteticos/curados: {summary['synthetic_records']}")
    print(f"- RAG documents: {summary['rag_documents']}")
    print(f"- Train examples: {summary['train_examples']}")
    print(f"- Val examples: {summary['val_examples']}")
    print(f"- Dominios: {summary['domain_counts']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normaliza MedQuAD e gera dados IA Core.")
    parser.add_argument("--source-dir", help="Diretorio do dataset, se nao usar manifesto/cache.")
    parser.add_argument("--max-medquad-records", type=int, help="Limite opcional para smoke tests.")
    parser.add_argument(
        "--synthetic-only",
        action="store_true",
        help="Gera outputs apenas com dados sinteticos/curados (uso local quando Kaggle indisponivel).",
    )
    args = parser.parse_args()

    source_dir = None if args.synthetic_only else resolve_dataset_dir(args.source_dir)
    summary = build_outputs(
        source_dir=source_dir,
        max_medquad_records=args.max_medquad_records,
        synthetic_only=args.synthetic_only,
    )
    _print_summary(summary)


if __name__ == "__main__":
    main()
