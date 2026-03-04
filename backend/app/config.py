import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
LINKS_PATH = BASE_DIR / "links.json"

# Ensure directories exist
UPLOADS_DIR.mkdir(exist_ok=True)

# API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Fallback contact
REBECCA_EMAIL = os.getenv("REBECCA_EMAIL", "rebecca@gauntlet.ai")
REBECCA_CONTACT = os.getenv(
    "REBECCA_CONTACT",
    f"I'm not sure about that one. Reach out to Rebecca at {REBECCA_EMAIL} and she'll get you sorted!",
)

# Google Sheets (optional)
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
