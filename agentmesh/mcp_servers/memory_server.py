from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4


def data_dir() -> Path:
    path = Path(os.getenv("AGENTMESH_DATA_DIR", ".agentmesh_data")).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "memory.sqlite3"


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(db_path())
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            tags TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    return connection


def _tokenize(text: str) -> Counter[str]:
    return Counter(token.strip(".,:;!?()[]{}\"'").lower() for token in text.split() if token.strip())


def _score(query: str, text: str, tags: list[str]) -> float:
    q = _tokenize(query)
    t = _tokenize(text + " " + " ".join(tags))
    if not q or not t:
        return 0.0
    return float(sum(min(count, t[token]) for token, count in q.items()))


def _vector_backend() -> tuple[Any, Any] | None:
    if os.getenv("DRY_RUN", "false").lower() in {"1", "true", "yes", "on"}:
        return None
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None
    model_name = os.getenv("AGENTMESH_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    try:
        model = SentenceTransformer(model_name, local_files_only=True)
        client = chromadb.PersistentClient(path=str(data_dir() / "chroma"))
        collection = client.get_or_create_collection("agentmesh_memory")
    except Exception:
        return None
    return collection, model


def _remember_vector(memory_id: str, text: str, tags: list[str], created_at: str) -> None:
    backend = _vector_backend()
    if backend is None:
        return
    collection, model = backend
    embedding = model.encode(text).tolist()
    collection.upsert(
        ids=[memory_id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[{"tags": json.dumps(tags), "created_at": created_at}],
    )


def _recall_vector(query: str, top_k: int) -> list[dict[str, Any]] | None:
    backend = _vector_backend()
    if backend is None:
        return None
    collection, model = backend
    embedding = model.encode(query).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=max(1, min(int(top_k), 20)))
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else [None] * len(ids)
    return [
        {
            "id": memory_id,
            "text": document,
            "tags": json.loads((metadata or {}).get("tags", "[]")),
            "created_at": (metadata or {}).get("created_at"),
            "score": None if distance is None else 1.0 / (1.0 + float(distance)),
        }
        for memory_id, document, metadata, distance in zip(ids, documents, metadatas, distances)
    ]


def remember(text: str, tags: list[str] | None = None) -> dict[str, Any]:
    if not text.strip():
        raise ValueError("text must not be empty")
    memory_id = str(uuid4())
    record_tags = tags or []
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        connection.execute(
            "INSERT INTO memories (id, text, tags, created_at) VALUES (?, ?, ?, ?)",
            (memory_id, text, json.dumps(record_tags), created_at),
        )
    _remember_vector(memory_id, text, record_tags, created_at)
    return {"id": memory_id, "text": text, "tags": record_tags, "created_at": created_at}


def recall(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("query must not be empty")
    vector_results = _recall_vector(query, top_k)
    if vector_results is not None:
        return vector_results
    with _connect() as connection:
        rows = connection.execute("SELECT id, text, tags, created_at FROM memories").fetchall()
    ranked: list[dict[str, Any]] = []
    for memory_id, text, raw_tags, created_at in rows:
        tags = json.loads(raw_tags)
        ranked.append(
            {
                "id": memory_id,
                "text": text,
                "tags": tags,
                "created_at": created_at,
                "score": _score(query, text, tags),
            }
        )
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return [item for item in ranked if item["score"] > 0][: max(1, min(int(top_k), 20))]


def _build_server() -> Any:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("memory_server")
    mcp.tool()(remember)
    mcp.tool()(recall)
    return mcp


def main() -> None:
    _build_server().run()


if __name__ == "__main__":
    main()
