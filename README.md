# BeccaBot

An AI assistant for Rebecca Metters (Director of Program Experience at Gauntlet AI) — straight to the point, friendly, and a little sassy.

## MVP Features

- **RAG-powered chat**: Answers questions using uploaded documentation
- **Document management**: Upload, view, and delete PDF, Word, PowerPoint, and text files
- **Black & gold UI**: Gauntlet AI branding
- **Fallback messages**: When the bot can't answer, directs users to contact Rebecca
- **Tools**: Weather (Austin), directions (housing ↔ office), current time
- **Source citations**: Bot shows which documents were used for each answer
- **Conversation history**: Follow-up questions use prior context
- **Unanswerable questions catalog**: Logged to Google Sheets (optional) for frequency analysis
- **Slack integration**: Optional Slack bot (Socket Mode)
- **Mobile-friendly**: Responsive layout, touch targets

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
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | Path to service account JSON (catalog unanswerable questions) |
| `GOOGLE_SHEET_ID` | Google Sheet ID for unanswerable questions |
| `SLACK_BOT_TOKEN` | For Slack integration (`python -m app.slack_bot`) |
| `SLACK_APP_TOKEN` | For Slack Socket Mode |

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

### Slack integration

1. Create a [Slack App](https://api.slack.com/apps) and enable Socket Mode.
2. Add `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` to `.env`.
3. Run the Slack bot: `python -m app.slack_bot` (in addition to the FastAPI server).
4. Invite the bot to channels or DM it. Use `@BeccaBot` for mentions.

### Unanswerable questions catalog

Set `GOOGLE_SHEETS_CREDENTIALS_PATH` and `GOOGLE_SHEET_ID`. Create a Google Sheet with columns `Timestamp` and `Question`, and share it with the service account email from your credentials JSON.

## Deploy to Render

1. Push this repo to GitHub.
2. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect your GitHub repo. Render will detect `render.yaml`.
4. Add environment variables in the Render dashboard: `OPENAI_API_KEY` (required), and optionally `DOCUMENTS_PIN`, `OPENWEATHERMAP_API_KEY`, `HOUSING_ADDRESS`, `OFFICE_ADDRESS`, `REBECCA_EMAIL`.
5. Deploy. The app will be live at `https://beccabot.onrender.com` (or your chosen name).

> **Note:** On Render's free tier, the filesystem is ephemeral—uploads and RAG store are reset on each deploy. Use a Persistent Disk (paid) for production if you need to retain documents.

### OCR for scanned PDFs

If a PDF has no extractable text (image-based or scanned), BeccaBot will try OCR using Tesseract. Install Tesseract:

- **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH
- **macOS**: `brew install tesseract`
- **Linux**: `apt install tesseract-ocr` or equivalent
