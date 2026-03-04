"""RAG pipeline: chunking, embeddings, retrieval, and generation.

Uses OpenAI embeddings + JSON storage (no ChromaDB) for Python 3.14 compatibility.
"""

import json
import re
from pathlib import Path
from typing import Optional

from openai import OpenAI

from app.config import OPENAI_API_KEY, REBECCA_CONTACT
from app.documents import parse_document

# Chunk settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Storage path
STORE_PATH = Path(__file__).resolve().parent.parent / "rag_store.json"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    if not text or not text.strip():
        return []
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if current_len + len(para) + 2 <= CHUNK_SIZE:
            current.append(para)
            current_len += len(para) + 2
        else:
            if current:
                chunks.append("\n\n".join(current))
            if len(para) > CHUNK_SIZE:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                current = []
                current_len = 0
                for s in sentences:
                    if current_len + len(s) + 1 <= CHUNK_SIZE:
                        current.append(s)
                        current_len += len(s) + 1
                    else:
                        if current:
                            chunks.append(" ".join(current))
                        current = [s]
                        current_len = len(s) + 1
            else:
                current = [para]
                current_len = len(para) + 2

    if current:
        chunks.append("\n\n".join(current))
    return chunks


class RAGStore:
    """Simple vector store using OpenAI embeddings + JSON persistence."""

    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required. Add it to .env")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.chunks: list[str] = []
        self.embeddings: list[list[float]] = []
        self.sources: list[str] = []
        self._load()

    def _load(self) -> None:
        """Load store from disk."""
        if STORE_PATH.exists():
            data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
            self.chunks = data.get("chunks", [])
            self.embeddings = data.get("embeddings", [])
            self.sources = data.get("sources", [])
        else:
            self.chunks = []
            self.embeddings = []
            self.sources = []

    def _save(self) -> None:
        """Persist store to disk."""
        data = {
            "chunks": self.chunks,
            "embeddings": self.embeddings,
            "sources": self.sources,
        }
        STORE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings from OpenAI."""
        if not texts:
            return []
        resp = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        by_idx = {e.index: e.embedding for e in resp.data}
        return [by_idx[i] for i in range(len(texts))]

    def add_document(self, file_path: Path, doc_id: Optional[str] = None) -> int:
        """Parse, chunk, embed, and store a document. Returns chunk count."""
        source_id = doc_id or str(file_path.name)
        self.remove_document(source_id)  # Replace if re-uploading

        text = parse_document(file_path)
        chunks = chunk_text(text)
        if not chunks:
            return 0

        embeds = self._embed(chunks)

        self.chunks.extend(chunks)
        self.embeddings.extend(embeds)
        self.sources.extend([source_id] * len(chunks))
        self._save()
        return len(chunks)

    def add_from_text(self, text: str, source_id: str) -> int:
        """Add chunks from raw text (e.g. from a URL). Returns chunk count."""
        self.remove_document(source_id)
        chunks = chunk_text(text)
        if not chunks:
            return 0
        embeds = self._embed(chunks)
        self.chunks.extend(chunks)
        self.embeddings.extend(embeds)
        self.sources.extend([source_id] * len(chunks))
        self._save()
        return len(chunks)

    def remove_document(self, doc_id: str) -> None:
        """Remove all chunks for a document."""
        keep = [i for i, s in enumerate(self.sources) if s != doc_id]
        self.chunks = [self.chunks[i] for i in keep]
        self.embeddings = [self.embeddings[i] for i in keep]
        self.sources = [self.sources[i] for i in keep]
        self._save()

    def query(
        self, question: str, n_results: int = 10, min_score: Optional[float] = None
    ) -> tuple[list[str], bool]:
        """Retrieve relevant chunks. Returns (context_chunks, found_relevant)."""
        if not self.chunks:
            return [], False

        q_embed = self._embed([question])[0]
        scores = [
            (i, _cosine_similarity(q_embed, emb))
            for i, emb in enumerate(self.embeddings)
        ]
        scores.sort(key=lambda x: x[1], reverse=True)
        top = scores[: min(n_results, 15)]

        if min_score is not None:
            top = [(i, s) for i, s in top if s >= min_score]

        chunks = [self.chunks[i] for i, _ in top]
        return chunks, len(chunks) > 0


def generate_response(
    question: str, context_chunks: list[str], use_fallback: bool = False
) -> str:
    """Generate a reply using OpenAI, or return fallback message."""
    if use_fallback and not context_chunks:
        return REBECCA_CONTACT
    if not context_chunks:
        return REBECCA_CONTACT

    if not OPENAI_API_KEY:
        return (
            "I'd love to help, but the AI isn't configured yet. "
            + REBECCA_CONTACT
        )

    client = OpenAI(api_key=OPENAI_API_KEY)
    context = "\n\n---\n\n".join(context_chunks)

    system = """You are BeccaBot, an AI assistant with Rebecca Metters' personality. 
Rebecca is the Director of Program Experience at Gauntlet AI. She's straight to the point, friendly, and a little sassy.
Answer questions based on the provided context. Extract and share the relevant info—addresses, dates, names, etc. Be concise and personable.
Only suggest reaching out to Rebecca if the context truly does not contain the answer. Do not make up information."""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=500,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Context from documentation:\n\n{context}\n\n---\n\nQuestion: {question}",
            },
        ],
    )
    text = resp.choices[0].message.content or ""
    # Only use fallback if the response is predominantly "I don't know" (starts with it or is very short)
    lower = text.lower().strip()
    if len(text) < 80 and any(
        p in lower for p in ["i'm not sure", "i don't know", "i cannot", "not in the context"]
    ):
        return REBECCA_CONTACT
    return text
