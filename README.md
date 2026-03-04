# BeccaBot

An AI assistant for Rebecca Metters (Director of Program Experience at Gauntlet AI) — straight to the point, friendly, and a little sassy.

## MVP Features

- **RAG-powered chat**: Answers questions using uploaded documentation
- **Document management**: Upload, view, and delete PDF, Word, PowerPoint, and text files
- **Black & gold UI**: Gauntlet AI branding
- **Fallback messages**: When the bot can't answer, directs users to contact Rebecca

## Quick start

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Create `backend/.env` (copy from `.env.example`) and add:
- `OPENAI_API_KEY` — for embeddings + chat (text-embedding-3-small, gpt-4o-mini)

> **Important:** Use **Python 3.11 or 3.12**. Python 3.14 has compatibility issues with ChromaDB and Pydantic.

```bash
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### 3. First run

- Go to **Documents** and upload a PDF, DOCX, PPTX, or TXT file
- Switch to **Chat** and ask questions about the content

## Project structure

```
beccabot/
├── backend/           # FastAPI + RAG pipeline
│   ├── app/
│   │   ├── main.py    # API routes
│   │   ├── rag.py     # RAG (OpenAI embeddings + gpt-4o-mini)
│   │   ├── documents.py # Document parsing (PDF, DOCX, PPTX, TXT)
│   │   └── config.py
│   └── requirements.txt
├── frontend/          # React + Vite
│   └── src/
│       ├── components/
│       │   ├── ChatView.tsx
│       │   └── DocumentsView.tsx
│       └── App.tsx
└── README.md
```

## Configuration

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Required for embeddings + chat (gpt-4o-mini). |
| `REBECCA_EMAIL` | Contact email in fallback messages |
| `REBECCA_CONTACT` | Custom fallback message text |

## Document support

All content is parsed from documents—no manual knowledge entry required. Tables, headers, and structured data are extracted automatically.

- **PDF** (`.pdf`) — text + table extraction; scanned PDFs via OCR (requires Tesseract)
- **Word** (`.docx`, `.doc`) — paragraphs + tables
- **PowerPoint** (`.pptx`, `.ppt`) — slides + tables
- **Excel** (`.xlsx`) — all sheets
- **CSV** (`.csv`)
- **Plain text** (`.txt`)

### Google Docs, Sheets, Slides (via link)

Add a shareable link instead of uploading. Document must be shared as **"Anyone with the link can view"**:

- Google Docs → exported as DOCX, parsed with full table support
- Google Sheets → exported as CSV
- Google Slides → exported as PDF

Regular web pages are scraped for text (script-heavy pages may have limited content).

### OCR for scanned PDFs

If a PDF has no extractable text (image-based or scanned), BeccaBot will try OCR using Tesseract. Install Tesseract:

- **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH
- **macOS**: `brew install tesseract`
- **Linux**: `apt install tesseract-ocr` or equivalent
