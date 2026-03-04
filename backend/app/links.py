"""Fetch and extract text from web URLs, including Google Docs/Sheets/Slides."""

import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Google Drive export URL patterns (requires doc shared as "Anyone with link can view")
_GOOGLE_DOCS_RE = re.compile(
    r"https?://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)"
)
_GOOGLE_SHEETS_RE = re.compile(
    r"https?://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)"
)
_GOOGLE_SLIDES_RE = re.compile(
    r"https?://docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)"
)


def fetch_google_document(url: str, timeout: int = 30) -> tuple[str, str] | None:
    """
    Fetch and parse Google Docs, Sheets, or Slides via export URLs.
    Returns (extracted_text, title) or None if not a supported Google URL.
    Document must be shared as "Anyone with the link can view".
    """
    url = url.strip()
    # Google Docs -> export as DOCX
    m = _GOOGLE_DOCS_RE.match(url)
    if m:
        doc_id = m.group(1)
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=docx"
        return _fetch_and_parse_export(export_url, ".docx", "Google Doc", timeout)

    # Google Sheets -> export as CSV (no extra deps, good for tabular data)
    m = _GOOGLE_SHEETS_RE.match(url)
    if m:
        doc_id = m.group(1)
        export_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"
        return _fetch_and_parse_export(export_url, ".csv", "Google Sheet", timeout)

    # Google Slides -> export as PDF
    m = _GOOGLE_SLIDES_RE.match(url)
    if m:
        doc_id = m.group(1)
        export_url = f"https://docs.google.com/presentation/d/{doc_id}/export/pdf"
        return _fetch_and_parse_export(export_url, ".pdf", "Google Slides", timeout)

    return None


def _fetch_and_parse_export(
    export_url: str, suffix: str, default_title: str, timeout: int
) -> tuple[str, str]:
    """Fetch binary export and parse with document parser."""
    from app.documents import parse_document

    resp = requests.get(export_url, timeout=timeout)
    resp.raise_for_status()
    content = resp.content
    if not content or len(content) < 100:
        raise ValueError(
            f"Export returned little or no content. Ensure the {default_title} is shared "
            "as 'Anyone with the link can view'."
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(content)
        tmp_path = Path(f.name)
    try:
        text = parse_document(tmp_path)
        return text.strip(), default_title
    finally:
        tmp_path.unlink(missing_ok=True)


def fetch_url_text(url: str, timeout: int = 15) -> tuple[str, str]:
    """
    Fetch a URL and extract main text content.
    Returns (extracted_text, page_title).
    """
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title and soup.find("h1"):
        h1 = soup.find("h1")
        if h1 and h1.get_text():
            title = h1.get_text(strip=True)

    body = soup.find("body") or soup
    text = body.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(), title or _url_to_title(url)


def _url_to_title(url: str) -> str:
    """Derive a short title from URL."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if path:
        return path.split("/")[-1][:50]
    return parsed.netloc[:50]


def is_valid_url(url: str) -> bool:
    """Check if string looks like a valid HTTP(S) URL."""
    if not url or not url.strip():
        return False
    url = url.strip()
    return url.startswith("http://") or url.startswith("https://")
