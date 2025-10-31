import os
from fastapi.responses import RedirectResponse
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
from fastapi import APIRouter, Request
from fastapi.logger import logger
from dotenv import load_dotenv
import logging

from auth.token_manager import load_tokens, save_tokens

logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

load_dotenv()
router = APIRouter()

logger = logging.getLogger(__name__)

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
    
    logger.debug("OAuth code recebido: %s", code)

    try:
        token_info = get_spotify_oauth().get_access_token(code)
        logger.debug("Token info: %s", token_info)
    except Exception as exc:
        logger.error("Erro ao trocar code por token: %s", exc)
        return {"error": f"Failed to get access token: {str(exc)}"}, 400

    if not token_info or "access_token" not in token_info:
        return {"error": "Token information incomplete."}, 500

    sp = Spotify(auth=token_info["access_token"])
    try:
        user = sp.current_user()
        logger.debug("Dados do usuário: %s", user)
    except Exception as exc:
        logger.error("Falha ao buscar usuário: %s", exc)
        return {"error": f"Failed to fetch current user: {str(exc)}"}, 500

    if not user:
        logger.error("Usuário retornado é None")
        return {"error": "Could not retrieve user information."}, 500

    user_id = user.get("id")
    display_name  = user.get("display_name") or user_id

    logger.info("Usuário autenticado: %s (%s)", display_name, user_id)

    data = load_tokens()
    data[display_name] = token_info
    save_tokens(data)

    return {"status": "ok", "user": display_name }, 200
