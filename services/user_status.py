import json
import os
from sheets.sheets_client import update_sheet_row

TOKENS_FILE = "auth/tokens.json"

def load_tokens() -> dict:
    """Loads tokens from disk."""
    if not os.path.exists(TOKENS_FILE):
        return {}
    with open(TOKENS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def sync_users_to_sheet():
    """
    Pushes the list of authenticated users to Google Sheets.
    Each user gets a row with their auth status.
    """
    tokens = load_tokens()
    for user_id in tokens.keys():
        update_sheet_row(user_id, "Authenticated ✅")
