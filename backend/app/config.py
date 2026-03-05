import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
LINKS_PATH = BASE_DIR / "links.json"
STATIC_DIR = BASE_DIR.parent / "frontend" / "dist"

# Ensure directories exist
UPLOADS_DIR.mkdir(exist_ok=True)

# API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Documents access – PIN required to view/edit document library (Rebecca + admin)
DOCUMENTS_PIN = os.getenv("DOCUMENTS_PIN", "")

OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")

# Gauntlet locations (for directions)
HOUSING_ADDRESS = os.getenv("HOUSING_ADDRESS", "710 E 3rd Street, Austin, TX 78701")
OFFICE_ADDRESS = os.getenv("OFFICE_ADDRESS", "416 Congress Ave, Austin, TX 78701")

# Fallback contact
REBECCA_EMAIL = os.getenv("REBECCA_EMAIL", "rebecca@gauntlet.ai")
REBECCA_CONTACT = os.getenv(
    "REBECCA_CONTACT",
    f"Look, even I have limits. That one's above my pay grade—hit up Rebecca at {REBECCA_EMAIL} and she'll get you sorted.",
)

# Google Sheets (optional)
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
