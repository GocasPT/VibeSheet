import os
import json
from fastapi.responses import RedirectResponse
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
from fastapi import APIRouter, Request
from dotenv import load_dotenv

from auth.token_manager import load_tokens, save_tokens

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
        scope="user-read-private,user-read-email",
        cache_path=None,
    )

@router.get("/login")
async def login():
    auth_url = get_spotify_oauth().get_authorize_url()
    return RedirectResponse(auth_url)

@router.get("/callback")
async def callback(request: Request):
    """
    Endpoint que recebe o `code` do Spotify, troca por tokens, salva o
    token associado ao usuário e devolve uma resposta JSON.
    """
    code = request.query_params.get("code")
    if not code:
        return {"error": "Missing authorization code."}, 400

    try:
        token_info = get_spotify_oauth().get_access_token(code)
    except Exception as exc:
        return {"error": f"Failed to get access token: {str(exc)}"}, 400

    if not token_info or "access_token" not in token_info:
        return {"error": "Token information incomplete."}, 500

    sp = Spotify(auth=token_info["access_token"])
    try:
        user = sp.current_user()
    except Exception as exc:
        return {"error": f"Failed to fetch current user: {str(exc)}"}, 500

    if not user:
        return {"error": "Could not retrieve user information."}, 500

    username = user.get("display_name") or user.get("id") or "unknown"

    data = load_tokens()
    data[username] = token_info
    save_tokens(data)

    return {"status": "ok", "user": username}, 200
