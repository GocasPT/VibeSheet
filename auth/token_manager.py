import os
import json
import time
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

TOKENS_FILE = "auth/tokens.json"

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")


def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        return {}
    with open(TOKENS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_tokens(tokens):
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)


def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-read-currently-playing",
    )


def ensure_valid_token(user_id: str) -> dict:
    """Returns a valid token for the user, refreshing if needed."""
    tokens = load_tokens()
    token_info = tokens.get(user_id)

    if not token_info:
        raise ValueError(f"No token found for user '{user_id}'")

    # If expired, refresh
    if token_info["expires_at"] - int(time.time()) < 60:
        print(f"🔄 Refreshing token for {user_id}...")
        oauth = get_spotify_oauth()
        refreshed = oauth.refresh_access_token(token_info["refresh_token"])
        token_info.update(refreshed)
        tokens[user_id] = token_info
        save_tokens(tokens)
        print(f"✅ Token refreshed for {user_id}")

    return token_info
