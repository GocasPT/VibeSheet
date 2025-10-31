from spotipy import Spotify
from auth.token_manager import ensure_valid_token, load_tokens
from sheets.sheets_client import update_sheet_row
from datetime import datetime

def get_current_track(user_id: str) -> dict:
    """
    Fetches the current track with full metadata.
    Returns a dict for Google Sheets.
    """
    token_info = ensure_valid_token(user_id)
    sp = Spotify(auth=token_info["access_token"])
    current = sp.current_user_playing_track()

    if not current or not current.get("is_playing") or not current.get("item"):
        return {
            "track": "Not playing",
            "artists": "—",
            "album": "—",
            "year": "—",
            "link": "—",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    item = current["item"]
    track_name = item["name"]
    artists = ", ".join([a["name"] for a in item["artists"]])
    album = item["album"]["name"]
    release_date = item["album"]["release_date"]
    year = release_date.split("-")[0]
    link = item["external_urls"]["spotify"]

    return {
        "track": track_name,
        "artists": artists,
        "album": album,
        "year": year,
        "link": link,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def sync_spotify_to_sheets():
    """
    Iterates through authenticated users and updates their current track metadata.
    """
    tokens = load_tokens()
    if not tokens:
        print("⚠️ No authenticated Spotify users found.")
        return

    print(f"🎧 Syncing {len(tokens)} users...")

    for user_id, token_info in tokens.items():
        try:
            track_info = get_current_track(user_id)
            update_sheet_row(user_id, track_info)
            print(f"✅ Updated {user_id}: {track_info['track']} — {track_info['artists']}")
        except Exception as e:
            print(f"❌ Failed to update {user_id}: {e}")
