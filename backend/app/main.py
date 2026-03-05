"""BeccaBot API - FastAPI application."""

import json
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import DOCUMENTS_PIN, LINKS_PATH, REBECCA_CONTACT, STATIC_DIR, UPLOADS_DIR
from app.links import fetch_google_document, fetch_url_text, is_valid_url
from app.rag import RAGStore, generate_response

app = FastAPI(title="BeccaBot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API router (mounted at /api)
api = APIRouter()

# Global RAG store (in production, use proper DI)
rag = RAGStore()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".pptx", ".ppt", ".xlsx", ".csv"}


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    fallback: bool = False


class AddLinkRequest(BaseModel):
    url: str
    title: str | None = None


class ManualIngestRequest(BaseModel):
    text: str


def _load_links() -> list[dict]:
    """Load stored links from disk."""
    if LINKS_PATH.exists():
        return json.loads(LINKS_PATH.read_text(encoding="utf-8"))
    return []


def _save_links(links: list[dict]) -> None:
    LINKS_PATH.write_text(json.dumps(links, indent=2), encoding="utf-8")


def _is_link_id(doc_id: str) -> bool:
    """Check if doc_id refers to a link (vs uploaded file)."""
    return doc_id.startswith("link:")


def _require_documents_auth(x_documents_pin: str | None = Header(None)):
    """Require valid Documents PIN when DOCUMENTS_PIN is configured."""
    if not DOCUMENTS_PIN:
        return
    if not x_documents_pin or x_documents_pin != DOCUMENTS_PIN:
        raise HTTPException(status_code=403, detail="Documents access requires authentication")


@api.get("/")
def root():
    return {"name": "BeccaBot API", "status": "ok"}


@api.get("/health")
def health():
    return {"status": "healthy"}


@api.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Answer a question using RAG. Returns fallback if no relevant context."""
    question = req.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        chunks, found = rag.query(question)
        use_fallback = not found
        reply = generate_response(question, chunks, use_fallback=use_fallback)
    except Exception as e:
        logging.exception("Chat error")
        return ChatResponse(
            reply=f"Well, that backfired. Something broke on my end—{REBECCA_CONTACT}",
            fallback=True,
        )

    return ChatResponse(reply=reply, fallback=use_fallback)


@api.get("/documents/locked")
def documents_locked():
    """Return whether Documents tab requires PIN. Frontend uses this to show lock UI."""
    return {"locked": bool(DOCUMENTS_PIN)}


@api.get("/documents", dependencies=[Depends(_require_documents_auth)])
def list_documents():
    """List all documents (uploaded files + links)."""
    docs = []
    for f in UPLOADS_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
            docs.append(
                {
                    "id": f.name,
                    "name": f.name,
                    "size": f.stat().st_size,
                    "type": "file",
                }
            )
    for link in _load_links():
        docs.append(
            {
                "id": link["id"],
                "name": link.get("title") or link["url"],
                "url": link["url"],
                "type": "link",
            }
        )
    manual_text = None
    if "manual" in set(rag.sources):
        docs.append({"id": "manual", "name": "Manual notes", "type": "manual"})
        manual_text = rag.get_document_text("manual") or ""
    return {"documents": docs, "manualText": manual_text}


@api.post("/documents/upload", dependencies=[Depends(_require_documents_auth)])
def upload_document(file: UploadFile = File(...)):
    """Upload a document (PDF, DOCX, TXT, PPTX)."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    dest = UPLOADS_DIR / (file.filename or "document")
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    chunk_count = rag.add_document(dest, doc_id=file.filename)
    return {
        "id": file.filename,
        "name": file.filename,
        "chunks": chunk_count,
        "type": "file",
        "warning": "No text could be extracted. For scanned PDFs, install Tesseract OCR (see README). Otherwise try a PDF with selectable text." if chunk_count == 0 else None,
    }


@api.post("/documents/manual", dependencies=[Depends(_require_documents_auth)])
def ingest_manual(req: ManualIngestRequest):
    """Ingest manually entered text into the RAG store."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    chunk_count = rag.add_from_text(text, "manual")
    return {"id": "manual", "name": "Manual notes", "chunks": chunk_count, "type": "manual"}


@api.post("/documents/link", dependencies=[Depends(_require_documents_auth)])
def add_link(req: AddLinkRequest):
    """Add a URL to the document library. Supports web pages, Google Docs, Sheets, Slides."""
    url = req.url.strip()
    if not is_valid_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL. Use http:// or https://")

    # Try Google Docs/Sheets/Slides export first (proper parsing, no JS needed)
    text = None
    title = ""
    try:
        result = fetch_google_document(url)
        if result:
            text, title = result
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )

    # Fall back to HTML scraping for regular web pages
    if text is None:
        try:
            text, title = fetch_url_text(url)
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"Could not fetch URL: {str(e)}",
            )

    if not text or len(text) < 50:
        raise HTTPException(
            status_code=422,
            detail="Page has too little text to index. Try a different URL.",
        )

    source_id = f"link:{url}"
    chunk_count = rag.add_from_text(text, source_id)

    links = _load_links()
    links = [l for l in links if l["id"] != source_id]
    links.append({
        "id": source_id,
        "url": url,
        "title": req.title or title,
    })
    _save_links(links)

    return {
        "id": source_id,
        "name": req.title or title,
        "url": url,
        "chunks": chunk_count,
        "type": "link",
        "warning": "Little or no content was found." if chunk_count < 3 else None,
    }


class DeleteRequest(BaseModel):
    id: str


@api.post("/documents/delete", dependencies=[Depends(_require_documents_auth)])
def delete_document_by_id(req: DeleteRequest):
    """Delete a document (file, link, or manual notes) by ID. Uses POST+body to avoid URL encoding issues with link IDs."""
    doc_id = req.id
    if doc_id == "manual":
        rag.remove_document("manual")
        return {"deleted": "manual"}
    if _is_link_id(doc_id):
        links = _load_links()
        links = [l for l in links if l["id"] != doc_id]
        if len(links) == len(_load_links()):
            raise HTTPException(status_code=404, detail="Link not found")
        _save_links(links)
        rag.remove_document(doc_id)
        return {"deleted": doc_id}

    # File: block path traversal
    if ".." in doc_id or "/" in doc_id or "\\" in doc_id:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    path = UPLOADS_DIR / doc_id
    if not path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    path.unlink()
    rag.remove_document(doc_id)
    return {"deleted": doc_id}




class ReindexRequest(BaseModel):
    id: str


@api.post("/documents/reindex", dependencies=[Depends(_require_documents_auth)])
def reindex_document_by_id(req: ReindexRequest):
    """Re-index a document (file or link) by ID. Uses POST+body to avoid URL encoding issues."""
    doc_id = req.id
    if _is_link_id(doc_id):
        links = _load_links()
        link = next((l for l in links if l["id"] == doc_id), None)
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        result = fetch_google_document(link["url"])
        if result:
            text, _ = result
        else:
            text, _ = fetch_url_text(link["url"])
        chunk_count = rag.add_from_text(text, doc_id)
        return {"id": doc_id, "chunks": chunk_count}

    if ".." in doc_id or "/" in doc_id or "\\" in doc_id:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    path = UPLOADS_DIR / doc_id
    if not path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    rag.remove_document(doc_id)
    chunk_count = rag.add_document(path, doc_id=doc_id)
    return {"id": doc_id, "chunks": chunk_count}


app.include_router(api, prefix="/api")

INDEX_HTML = STATIC_DIR / "index.html"


def _serve_index():
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return {"detail": "Static files not built. Run: cd frontend && npm run build"}


@app.get("/")
def serve_root():
    return _serve_index()


@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    # Serve static file if it exists (e.g. /assets/foo.js)
    static_file = STATIC_DIR / full_path
    if static_file.is_file():
        return FileResponse(static_file)
    return _serve_index()
