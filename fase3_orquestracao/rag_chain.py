"""RAG com LangChain sobre `data/rag_documents.jsonl`.

Fase C (IA-C1 a IA-C3):

- IA-C1: loader de documentos RAG com metadados obrigatorios.
- IA-C2: indexador de embeddings/vector store em `outputs/vectorstore`.
- IA-C3: `retrieve_context(query, flow_id, k)` retornando fonte, score e trecho.

O index usa embeddings deterministas implementados pela interface LangChain
`Embeddings`. Isso evita download de modelos externos durante a demo local e
mantem a origem das respostas restrita a `data/rag_documents.jsonl`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
except ImportError as exc:  # pragma: no cover - depende do ambiente local
    raise RuntimeError(
        "Dependencias LangChain ausentes. Instale com `python -m pip install -r requirements.txt` "
        "antes de rodar a Fase C."
    ) from exc

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAG_DOCUMENTS_PATH = PROJECT_ROOT / "data" / "rag_documents.jsonl"
VECTORSTORE_DIR = PROJECT_ROOT / "outputs" / "vectorstore"
VECTORSTORE_INDEX_PATH = VECTORSTORE_DIR / "rag_index.json"

REQUIRED_METADATA = {"doc_id", "domain", "source", "version", "sensitivity", "citation"}
ALLOWED_DOMAINS = {
    "triagemGinecologica",
    "violenciaDomestica",
    "obstetrico",
    "prevencao",
    "medicinaGeral",
}


class RagDataError(RuntimeError):
    """Erro de dados ausentes/invalidos na Fase B."""


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise RagDataError(f"{path}:{line_number}: JSON invalido em data/rag_documents.jsonl") from exc


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _snippet(text: str, *, max_chars: int = 360) -> str:
    text = _normalize_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def load_rag_documents(path: Path = RAG_DOCUMENTS_PATH) -> list[Document]:
    """Carrega `data/rag_documents.jsonl` preservando metadados obrigatorios."""

    if not path.exists():
        raise RagDataError(
            f"Arquivo RAG nao encontrado: {path}. Rode a Fase B antes: "
            "`python fase1_dados/build_dataset.py` e `python fase1_dados/validate_data.py`."
        )

    documents: list[Document] = []
    seen_doc_ids: set[str] = set()
    for index, record in enumerate(_read_jsonl(path), start=1):
        missing = sorted(field for field in REQUIRED_METADATA if not record.get(field))
        if missing:
            raise RagDataError(f"{path}:{index}: metadados obrigatorios ausentes: {', '.join(missing)}")

        content = _normalize_text(str(record.get("content", "")))
        if not content:
            raise RagDataError(f"{path}:{index}: campo `content` vazio")

        doc_id = str(record["doc_id"])
        if doc_id in seen_doc_ids:
            raise RagDataError(f"{path}:{index}: doc_id duplicado: {doc_id}")
        seen_doc_ids.add(doc_id)

        domain = str(record["domain"])
        if domain not in ALLOWED_DOMAINS:
            raise RagDataError(f"{path}:{index}: domain invalido para RAG: {domain}")

        metadata = {
            "doc_id": doc_id,
            "domain": domain,
            "source": str(record["source"]),
            "version": str(record["version"]),
            "sensitivity": str(record["sensitivity"]),
            "citation": str(record["citation"]),
            "title": str(record.get("title", "")),
            "record_id": str(record.get("record_id", "")),
        }
        documents.append(Document(page_content=content, metadata=metadata))

    if not documents:
        raise RagDataError(f"{path}: nenhum documento RAG encontrado")
    return documents


def split_documents(documents: Sequence[Document], *, chunk_size: int = 900, overlap: int = 120) -> list[Document]:
    """Divide documentos em chunks pequenos preservando os metadados originais."""

    if overlap >= chunk_size:
        raise ValueError("overlap deve ser menor que chunk_size")

    chunks: list[Document] = []
    for document in documents:
        text = document.page_content
        if len(text) <= chunk_size:
            metadata = {**document.metadata, "chunk_index": 0}
            chunks.append(Document(page_content=text, metadata=metadata))
            continue

        start = 0
        chunk_index = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk_text = text[start:end].strip()
            if chunk_text:
                metadata = {**document.metadata, "chunk_index": chunk_index}
                chunks.append(Document(page_content=chunk_text, metadata=metadata))
                chunk_index += 1
            if end == len(text):
                break
            start = max(0, end - overlap)
    return chunks


class HashingEmbeddings(Embeddings):
    """Embeddings lexicais deterministas para MVP local sem download de modelo."""

    def __init__(self, *, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[\wÀ-ÿ]+", text.lower())
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))


@dataclass(frozen=True)
class IndexedChunk:
    page_content: str
    metadata: dict[str, Any]
    embedding: list[float]


def build_vectorstore(
    *,
    documents_path: Path = RAG_DOCUMENTS_PATH,
    vectorstore_dir: Path = VECTORSTORE_DIR,
    embeddings: Embeddings | None = None,
) -> dict[str, Any]:
    """Cria/persiste vector store JSON em `outputs/vectorstore`."""

    base_documents = load_rag_documents(documents_path)
    chunks = split_documents(base_documents)
    embedder = embeddings or HashingEmbeddings()
    vectors = embedder.embed_documents([chunk.page_content for chunk in chunks])

    index = {
        "schema_version": 1,
        "embedding": {
            "provider": "langchain_hashing_embeddings",
            "dimensions": len(vectors[0]) if vectors else 0,
        },
        "source_path": str(documents_path),
        "documents_count": len(base_documents),
        "chunks_count": len(chunks),
        "chunks": [
            {
                "page_content": chunk.page_content,
                "metadata": chunk.metadata,
                "embedding": vector,
            }
            for chunk, vector in zip(chunks, vectors, strict=True)
        ],
    }

    vectorstore_dir.mkdir(parents=True, exist_ok=True)
    index_path = vectorstore_dir / VECTORSTORE_INDEX_PATH.name
    index_path.write_text(json.dumps(index, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "index_path": str(index_path),
        "documents_count": len(base_documents),
        "chunks_count": len(chunks),
    }


def _load_index(index_path: Path = VECTORSTORE_INDEX_PATH) -> list[IndexedChunk]:
    if not index_path.exists():
        raise RagDataError(
            f"Vector store nao encontrado: {index_path}. Rode `python fase3_orquestracao/rag_chain.py --build`."
        )
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RagDataError(f"Vector store invalido: {index_path}") from exc

    chunks = payload.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise RagDataError(f"Vector store sem chunks recuperaveis: {index_path}")

    indexed: list[IndexedChunk] = []
    for idx, chunk in enumerate(chunks, start=1):
        try:
            indexed.append(
                IndexedChunk(
                    page_content=str(chunk["page_content"]),
                    metadata=dict(chunk["metadata"]),
                    embedding=[float(value) for value in chunk["embedding"]],
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RagDataError(f"Vector store com chunk invalido na posicao {idx}") from exc
    return indexed


def _candidate_chunks(chunks: Sequence[IndexedChunk], flow_id: str) -> list[IndexedChunk]:
    same_domain = [chunk for chunk in chunks if chunk.metadata.get("domain") == flow_id]
    if same_domain:
        return same_domain

    # Fallback conservador: medicina geral + documentos nao sensiveis.
    return [
        chunk
        for chunk in chunks
        if chunk.metadata.get("domain") == "medicinaGeral" or chunk.metadata.get("sensitivity") == "low"
    ]


def retrieve_context(
    query: str,
    flow_id: str,
    k: int = 4,
    *,
    index_path: Path = VECTORSTORE_INDEX_PATH,
    embeddings: Embeddings | None = None,
) -> list[dict[str, Any]]:
    """Recupera top-k contextos com fonte, score e trecho."""

    query = _normalize_text(query)
    if not query:
        raise ValueError("query nao pode ser vazia")
    if flow_id not in ALLOWED_DOMAINS - {"medicinaGeral"}:
        raise ValueError(f"flow_id invalido: {flow_id}")
    if k <= 0:
        raise ValueError("k deve ser maior que zero")

    chunks = _candidate_chunks(_load_index(index_path), flow_id)
    if not chunks:
        return []

    embedder = embeddings or HashingEmbeddings()
    query_embedding = embedder.embed_query(query)
    ranked = sorted(
        (
            (_cosine_similarity(query_embedding, chunk.embedding), chunk)
            for chunk in chunks
        ),
        key=lambda item: item[0],
        reverse=True,
    )

    results: list[dict[str, Any]] = []
    for score, chunk in ranked[:k]:
        metadata = chunk.metadata
        results.append(
            {
                "doc_id": metadata["doc_id"],
                "domain": metadata["domain"],
                "source": metadata["source"],
                "version": metadata["version"],
                "sensitivity": metadata["sensitivity"],
                "citation": metadata["citation"],
                "fonte": metadata["citation"],
                "score": round(float(score), 6),
                "trecho": _snippet(chunk.page_content),
                "content": chunk.page_content,
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG LangChain sobre data/rag_documents.jsonl.")
    parser.add_argument("--build", action="store_true", help="Cria outputs/vectorstore/rag_index.json.")
    parser.add_argument("--query", help="Consulta manual para testar retrieval.")
    parser.add_argument("--flow-id", default="prevencao", help="Fluxo clinico para filtro de dominio.")
    parser.add_argument("-k", type=int, default=4, help="Quantidade de resultados.")
    args = parser.parse_args()

    if args.build:
        summary = build_vectorstore()
        print(f"Vector store: {summary['index_path']}")
        print(f"Documentos: {summary['documents_count']}")
        print(f"Chunks: {summary['chunks_count']}")

    if args.query:
        for result in retrieve_context(args.query, args.flow_id, args.k):
            print(json.dumps(result, ensure_ascii=False))

    if not args.build and not args.query:
        parser.error("Use --build e/ou --query.")


if __name__ == "__main__":
    main()
