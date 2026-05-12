"""Extratores tolerantes para diferentes formatos encontrados no MedQuAD."""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fase1_dados.common import normalize_whitespace, stable_id


QUESTION_KEYS = (
    "question",
    "Question",
    "q",
    "Q",
    "pergunta",
    "QuestionText",
    "question_text",
)

ANSWER_KEYS = (
    "answer",
    "Answer",
    "a",
    "A",
    "resposta",
    "AnswerText",
    "answer_text",
)


def _first_text(record: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and normalize_whitespace(value):
            return normalize_whitespace(value)
    return ""


def _flatten_json(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _flatten_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _flatten_json(child)


def extract_from_xml(path: Path) -> Iterator[dict[str, str]]:
    tree = ET.parse(path)
    root = tree.getroot()
    qa_pairs = root.findall(".//QAPair")
    if not qa_pairs:
        qa_pairs = root.findall(".//qa_pair") + root.findall(".//QA")

    for idx, pair in enumerate(qa_pairs, start=1):
        question_el = pair.find(".//Question") or pair.find(".//question")
        answer_el = pair.find(".//Answer") or pair.find(".//answer")
        question = normalize_whitespace("".join(question_el.itertext())) if question_el is not None else ""
        answer = normalize_whitespace("".join(answer_el.itertext())) if answer_el is not None else ""
        if question and answer:
            yield {
                "source_file": str(path),
                "source_row": str(idx),
                "question": question,
                "answer": answer,
            }


def extract_from_json(path: Path) -> Iterator[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    for idx, record in enumerate(_flatten_json(data), start=1):
        question = _first_text(record, QUESTION_KEYS)
        answer = _first_text(record, ANSWER_KEYS)
        if question and answer:
            yield {
                "source_file": str(path),
                "source_row": str(idx),
                "question": question,
                "answer": answer,
            }


def extract_from_jsonl(path: Path) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                continue
            question = _first_text(record, QUESTION_KEYS)
            answer = _first_text(record, ANSWER_KEYS)
            if question and answer:
                yield {
                    "source_file": str(path),
                    "source_row": str(idx),
                    "question": question,
                    "answer": answer,
                }


def extract_from_table(path: Path, *, delimiter: str) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for idx, record in enumerate(reader, start=1):
            question = _first_text(record, QUESTION_KEYS)
            answer = _first_text(record, ANSWER_KEYS)
            if question and answer:
                yield {
                    "source_file": str(path),
                    "source_row": str(idx),
                    "question": question,
                    "answer": answer,
                }


def extract_from_text(path: Path) -> Iterator[dict[str, str]]:
    text = normalize_whitespace(path.read_text(encoding="utf-8", errors="ignore"))
    if "?" not in text or len(text) < 80:
        return
    question, answer = text.split("?", 1)
    question = normalize_whitespace(question + "?")
    answer = normalize_whitespace(answer)
    if question and answer:
        yield {
            "source_file": str(path),
            "source_row": "1",
            "question": question,
            "answer": answer,
        }


def extract_qa_records(path: Path) -> Iterator[dict[str, str]]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".xml":
            yield from extract_from_xml(path)
        elif suffix == ".json":
            yield from extract_from_json(path)
        elif suffix == ".jsonl":
            yield from extract_from_jsonl(path)
        elif suffix == ".csv":
            yield from extract_from_table(path, delimiter=",")
        elif suffix == ".tsv":
            yield from extract_from_table(path, delimiter="\t")
        elif suffix == ".txt":
            yield from extract_from_text(path)
    except (ET.ParseError, UnicodeDecodeError, json.JSONDecodeError, csv.Error):
        return


def normalized_record_id(question: str, answer: str) -> str:
    return stable_id("medquad", question.lower(), answer.lower())
