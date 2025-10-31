from auth.token_manager import load_tokens
from sheets.sheets_client import update_sheet_row

def sync_users_to_sheet():
    """
    Pushes the list of authenticated users to Google Sheets.
    Each user gets a row with their auth status.
    """
    tokens = load_tokens()
    for user_id in tokens.keys():
        update_sheet_row(user_id, "Authenticated ✅")
