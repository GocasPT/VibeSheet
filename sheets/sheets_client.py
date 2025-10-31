import gspread
import os
from dotenv import load_dotenv

load_dotenv()

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT = os.getenv("GOOGLE_SERVICE_ACCOUNT")


def get_sheet():
    """
    Connects to Google Sheets using a Service Account.
    Returns a worksheet handle.
    """
    if not os.path.exists(SERVICE_ACCOUNT):
        raise FileNotFoundError(f"Missing service account file at {SERVICE_ACCOUNT}")

    gc = gspread.service_account(filename=SERVICE_ACCOUNT)
    sh = gc.open_by_key(SHEET_ID)
    worksheet = sh.worksheet("Who's listening NOW?")
    return worksheet


def update_sheet_row(username: str, status: str):
    """
    Updates (or inserts) the user's status row in the sheet.
    """
    ws = get_sheet()
    users = ws.col_values(1)

    # Find existing user row
    if username in users:
        row_index = users.index(username) + 1
        ws.update_cell(row_index, 2, status)
    else:
        ws.append_row([username, status])
