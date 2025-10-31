import os, json
from spotipy.oauth2 import SpotifyOAuth
from fastapi import APIRouter, Request
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-read-currently-playing",
        cache_path=None,
    )

@router.get("/login")
async def login():
    auth_url = get_spotify_oauth().get_authorize_url()
    return {"auth_url": auth_url}

@router.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    token_info = get_spotify_oauth().get_access_token(code)
    with open("auth/tokens.json", "r+") as f:
        try:
            data = json.load(f)
        except:
            data = {}
        data["user_1"] = token_info
        f.seek(0)
        json.dump(data, f, indent=2)
    return {"status": "ok", "user": "user_1"}
