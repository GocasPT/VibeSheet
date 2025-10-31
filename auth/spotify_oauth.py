import os
from fastapi.responses import RedirectResponse
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
from fastapi import APIRouter, Request
from dotenv import load_dotenv
from spotipy.cache_handler import CacheHandler
import logging

from auth.token_manager import load_tokens, save_tokens

load_dotenv()
router = APIRouter()

logger = logging.getLogger(__name__)

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")


class NoCacheHandler(CacheHandler):
    """Cache handler que não cacheia nada"""
    def get_cached_token(self):
        return None
    
    def save_token_to_cache(self, token_info):
        pass


class MultiUserCacheHandler(CacheHandler):
    """Cache handler que suporta múltiplos usuários via JSON"""
    
    def __init__(self, user_id=None):
        self.user_id = user_id
    
    def get_cached_token(self):
        """Retorna token do usuário específico"""
        if not self.user_id:
            return None
        
        data = load_tokens()
        token_info = data.get(self.user_id)
        
        if token_info:
            logger.debug(f"Token encontrado em cache para user: {self.user_id}")
        
        return token_info
    
    def save_token_to_cache(self, token_info):
        """Salva token do usuário específico"""
        if not self.user_id:
            logger.warning("Tentou salvar token sem user_id")
            return
        
        data = load_tokens()
        data[self.user_id] = token_info
        save_tokens(data)
        
        logger.info(f"Token salvo para user: {self.user_id}")

def get_spotify_client(user_id: str):
    """Retorna cliente Spotify para um usuário específico"""
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-read-private,user-read-email,user-read-currently-playing",
        cache_handler=MultiUserCacheHandler(user_id=user_id),
    )
    
    token_info = sp_oauth.get_cached_token()
    
    if not token_info:
        raise Exception(f"User {user_id} não autenticado")
    
    # Refresh automático se expirado
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    
    return Spotify(auth=token_info['access_token'])

@router.get("/login")
async def login():
    sp_oauth_temp = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-read-private,user-read-email,user-read-currently-playing",
        cache_handler=NoCacheHandler(),  # Sem cache ainda
    )
    auth_url = sp_oauth_temp.get_authorize_url()
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

    sp_oauth_temp = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-read-private,user-read-email,user-read-currently-playing",
        cache_handler=NoCacheHandler(),  # Sem cache ainda
    )

    try:
        token_info = sp_oauth_temp.get_access_token(code)
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
