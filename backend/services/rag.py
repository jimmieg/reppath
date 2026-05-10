import os
import json
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader

load_dotenv()

CORPUS_DIR = Path(__file__).parent.parent / "corpus"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "reppath_methodology"

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"],
        model_name="text-embedding-3-small",
    )

    _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=openai_ef,
    )
    return _collection


def _extract_text(path: Path) -> str:
    if path.suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def _chunk(text: str, size: int = 400, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + size]))
        i += size - overlap
    return chunks


def ingest_corpus():
    """
    Call once on startup (or via a /ingest endpoint during dev).
    Skips files already in the collection so re-runs are safe.
    """
    col = _get_collection()
    existing = set(col.get()["ids"])

    for doc_path in CORPUS_DIR.iterdir():
        if doc_path.suffix not in {".txt", ".pdf", ".md"}:
            continue

        raw = _extract_text(doc_path)
        chunks = _chunk(raw)

        new_ids, new_docs = [], []
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{doc_path.stem}_{idx}"
            if chunk_id not in existing:
                new_ids.append(chunk_id)
                new_docs.append(chunk)

        if new_ids:
            col.add(documents=new_docs, ids=new_ids)
            print(f"[RAG] Ingested {len(new_ids)} chunks from {doc_path.name}")


def retrieve(query: str, n_results: int = 4) -> tuple[str, list[str]]:
    col = _get_collection()
    results = col.query(query_texts=[query], n_results=n_results)

    docs = results["documents"][0]
    ids = results["ids"][0]

    # ← add this block
    print(f"\n[RAG] Query: '{query}'")
    print(f"[RAG] Retrieved chunks: {ids}")
    for i, (chunk_id, doc) in enumerate(zip(ids, docs)):
        print(f"[RAG] Chunk {i+1} ({chunk_id}): {doc[:100]}...")
    print()

    context = "\n\n---\n\n".join(
        f"[SOURCE: {chunk_id}]\n{doc}" for chunk_id, doc in zip(ids, docs)
    )
    return context, ids