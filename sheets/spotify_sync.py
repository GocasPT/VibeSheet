import os, json
from spotipy import Spotify
from sheets.sheets_client import update_sheet_row
from datetime import datetime

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

def get_current_track(token_info: dict) -> str:
    """
    Uses Spotify API to fetch the current playing track for a user.
    """
    sp = Spotify(auth=token_info["access_token"])
    current = sp.current_user_playing_track()

    if not current or not current.get("is_playing"):
        return "Not playing"

    item = current.get("item")
    if not item:
        return "Not playing"

    artist = ", ".join([a["name"] for a in item["artists"]])
    track = item["name"]
    return f"{track} — {artist}"


def sync_spotify_to_sheets():
    """
    Iterates through authenticated users and updates their current track
    in Google Sheets.
    """
    tokens = load_tokens()
    if not tokens:
        print("⚠️ No authenticated Spotify users found.")
        return

    print(f"🎧 Syncing {len(tokens)} users...")

    for user_id, token_info in tokens.items():
        try:
            track_info = get_current_track(token_info)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_sheet_row(user_id, f"{track_info} (as of {timestamp})")
            print(f"✅ Updated {user_id}: {track_info}")
        except Exception as e:
            print(f"❌ Failed to update {user_id}: {e}")
