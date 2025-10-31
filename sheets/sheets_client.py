import gspread
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT = os.getenv("GOOGLE_SERVICE_ACCOUNT")
WORKSHEET = os.getenv("GOOGLE_SHEET_WORKSHEET_TITLE")


def get_sheet():
    """
    Connects to Google Sheets using a Service Account.
    Returns a worksheet handle.
    """
    gc = gspread.service_account(filename=SERVICE_ACCOUNT)
    sh = gc.open_by_key(SHEET_ID)
    worksheet = sh.worksheet(WORKSHEET)
    return worksheet


def ensure_headers(ws):
    """Ensures the first row has the correct headers."""
    headers = ["Pessoa", "Música", "Artistas/Banda", "Álbum", "Ano", "Link", "Last Update"]
    current_headers = ws.row_values(1)
    if current_headers != headers:
        ws.delete_rows(1)
        ws.insert_row(headers, 1)
        

def update_sheet_row(username: str, track_data: dict):
    """
    Updates (or inserts) the user's row in the sheet with full track metadata.
    track_data = {
        "track": str,
        "artists": str,
        "album": str,
        "year": str,
        "link": str,
        "timestamp": str
    }
    """
    ws = get_sheet()
    ensure_headers(ws)
    users = ws.col_values(1)

    row_data = [
        username,
        track_data.get("track", "—"),
        track_data.get("artists", "—"),
        track_data.get("album", "—"),
        track_data.get("year", "—"),
        track_data.get("link", "—"),
        track_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ]

    # Update existing or append new
    if username in users:
        row_index = users.index(username) + 1
        ws.update(f"A{row_index}:G{row_index}", [row_data])
    else:
        ws.append_row(row_data)