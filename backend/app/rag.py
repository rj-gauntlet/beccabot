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
from app.tools import get_directions, get_weather

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


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location. Use when user asks about weather, temperature, or conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City/location (e.g. Austin, housing, office). Default to Austin for Gauntlet.",
                    },
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_directions",
            "description": "Get Google Maps directions. Origin and destination can be: 'housing' (PlaceMakr, 710 E 3rd St), 'office' (416 Congress Ave), or any address/place in Austin (e.g. 'Zilker Park', '600 Congress Ave', 'Franklin Barbecue'). Use when user asks how to get somewhere or for directions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Starting point: 'housing', 'office', or an address/place in Austin",
                    },
                    "destination": {
                        "type": "string",
                        "description": "End point: 'housing', 'office', or an address/place in Austin",
                    },
                    "travel_mode": {
                        "type": "string",
                        "enum": ["driving", "walking", "transit", "bicycling"],
                        "description": "Mode of travel. Default driving for longer trips, walking for short ones.",
                    },
                },
                "required": ["origin", "destination"],
            },
        },
    },
]


def _execute_tool(name: str, args: dict) -> str:
    if name == "get_weather":
        return get_weather(args.get("location", "Austin"))
    if name == "get_directions":
        return get_directions(
            args.get("origin", ""),
            args.get("destination", ""),
            args.get("travel_mode", "walking"),
        )
    return f"Unknown tool: {name}"


def generate_response(
    question: str, context_chunks: list[str], use_fallback: bool = False
) -> str:
    """Generate a reply using OpenAI, or return fallback message."""
    if not OPENAI_API_KEY:
        return (
            "Would love to help, but someone forgot to plug in the AI. "
            + REBECCA_CONTACT
        )

    client = OpenAI(api_key=OPENAI_API_KEY)
    context = "\n\n---\n\n".join(context_chunks) if context_chunks else "(No relevant documentation for this question. Use your tools if the user asks about weather or directions.)"

    system = """You are BeccaBot, an AI assistant with Rebecca Metters' personality.
Rebecca is the Director of Program Experience at Gauntlet AI. She's straight to the point, friendly, and noticeably sassy.
Tone: Use dry humor, light roasting, and playful teasing. Drop in occasional eye-rolls, "obviously," "here's the fun part," or gentle sarcasm. Don't be mean—be the friend who keeps you honest and makes you laugh.
Answer questions based on the provided context. Extract and share the relevant info—addresses, dates, names, etc. Be concise and personable.
You have tools: get_weather (for weather) and get_directions (for anywhere in Austin—housing, office, or any address/place). Use them when users ask. For directions, include the link in your reply so they can tap/click it.
Only suggest reaching out to Rebecca if the context and tools truly do not have the answer. Do not make up information."""

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"Context from documentation:\n\n{context}\n\n---\n\nQuestion: {question}",
        },
    ]
    max_tool_rounds = 3
    for _ in range(max_tool_rounds):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=500,
            messages=messages,
            tools=TOOLS,
        )
        choice = resp.choices[0]
        if choice.finish_reason == "stop":
            text = choice.message.content or ""
            break
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            messages.append(choice.message)
            for tc in choice.message.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                result = _execute_tool(name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )
            continue
        text = choice.message.content or ""
        break
    else:
        text = choice.message.content or "Took too many turns. Try again?"

    lower = text.lower().strip()
    if len(text) < 80 and any(
        p in lower for p in ["i'm not sure", "i don't know", "i cannot", "not in the context"]
    ):
        return REBECCA_CONTACT
    return text
