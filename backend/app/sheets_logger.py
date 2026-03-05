"""Log unanswerable questions to Google Sheets for frequency analysis."""

import logging
from datetime import datetime
from pathlib import Path

from app.config import BASE_DIR, GOOGLE_SHEET_ID, GOOGLE_SHEETS_CREDENTIALS_PATH


def log_unanswerable_question(question: str) -> None:
    """Append an unanswerable question to the configured Google Sheet.
    Sheet should have columns: Timestamp, Question (and optionally Count for manual aggregation).
    """
    if not GOOGLE_SHEET_ID or not GOOGLE_SHEETS_CREDENTIALS_PATH:
        return
    creds_path = Path(GOOGLE_SHEETS_CREDENTIALS_PATH)
    if not creds_path.is_absolute():
        creds_path = BASE_DIR / creds_path
    if not creds_path.exists():
        logging.warning("Google Sheets credentials file not found: %s", creds_path)
        return
    try:
        import gspread

        gc = gspread.service_account(filename=str(creds_path))
        sh = gc.open_by_key(GOOGLE_SHEET_ID)
        ws = sh.sheet1
        row = [datetime.utcnow().isoformat(), question.strip()]
        ws.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        logging.warning("Failed to log unanswerable question to Sheets: %s", e)
