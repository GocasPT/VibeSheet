"""
Spotify OAuth Router - Endpoints de autenticação.
AUTH flow com NoCacheHandler (single-user temporário).
"""
import os
import logging
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify
from spotipy.cache_handler import CacheHandler
from dotenv import load_dotenv
from auth.spotify_token_manager import save_user_token

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
OAUTH_SCOPE = "user-read-private,user-read-email,user-read-currently-playing"


class NoCacheHandler(CacheHandler):
    """
    Cache handler que não persiste (usado no AUTH flow).
    Evita criar arquivo .cache padrão do Spotipy.
    """
    def get_cached_token(self):
        return None
    
    def save_token_to_cache(self, token_info):
        pass


class MultiUserCacheHandler(CacheHandler):
    """
    Cache handler multi-user para REQUEST flow.
    Lê/escreve no tokens.json usando TokenCacheManager.
    """
    def __init__(self, user_id: str = None):
        self.user_id = user_id
    
    def get_cached_token(self):
        """Lê token do usuário do storage compartilhado"""
        if not self.user_id:
            return None
        
        from auth.spotify_token_manager import load_all_tokens
        tokens = load_all_tokens()
        return tokens.get(self.user_id)
    
    def save_token_to_cache(self, token_info):
        """Salva token do usuário no storage compartilhado"""
        if not self.user_id:
            logger.warning("MultiUserCacheHandler: tentou salvar sem user_id")
            return
        
        from auth.spotify_token_manager import save_user_token
        save_user_token(self.user_id, token_info)
        logger.info(f"Token salvo via MultiUserCacheHandler: {self.user_id}")


def create_spotify_oauth_no_cache() -> SpotifyOAuth:
    """
    Cria SpotifyOAuth para AUTH flow (login/callback).
    NoCacheHandler evita criar .cache padrão.
    """
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=OAUTH_SCOPE,
        cache_handler=NoCacheHandler()
    )


@router.get("/login")
async def login():
    """
    Inicia fluxo OAuth do Spotify.
    Redireciona usuário para página de autorização.
    """
    sp_oauth = create_spotify_oauth_no_cache()
    auth_url = sp_oauth.get_authorize_url()
    
    logger.info("Redirecionando para Spotify OAuth")
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(request: Request):
    """
    Callback do OAuth - recebe code e troca por tokens.
    Salva tokens associados ao display_name do usuário.
    """
    code = request.query_params.get("code")
    
    if not code:
        logger.error("Callback sem code")
        return {"error": "Missing authorization code"}, 400
    
    logger.debug(f"OAuth code recebido: {code[:10]}...")
    
    # Troca code por tokens
    sp_oauth = create_spotify_oauth_no_cache()
    
    try:
        token_info = sp_oauth.get_access_token(code)
    except Exception as e:
        logger.error(f"Erro ao trocar code por token: {e}")
        return {"error": f"Failed to get access token: {str(e)}"}, 400
    
    if not token_info or "access_token" not in token_info:
        logger.error("Token info incompleto")
        return {"error": "Token information incomplete"}, 500
    
    # Busca informações do usuário
    sp = Spotify(auth=token_info["access_token"])
    
    try:
        user = sp.current_user()
    except Exception as e:
        logger.error(f"Falha ao buscar current_user: {e}")
        return {"error": f"Failed to fetch user info: {str(e)}"}, 500
    
    if not user:
        logger.error("current_user() retornou None")
        return {"error": "Could not retrieve user information"}, 500
    
    # Identifica usuário
    user_id = user.get("id")
    display_name = user.get("display_name") or user_id
    
    logger.info(f"Usuário autenticado: {display_name} (id: {user_id})")
    
    # Salva token associado ao display_name
    save_user_token(display_name, token_info)
    
    return {
        "status": "ok",
        "user": display_name,
        "message": f"Autenticação bem-sucedida! User: {display_name}"
    }


@router.get("/users")
async def list_authenticated_users():
    """Lista usuários autenticados (útil para debug)"""
    from auth.spotify_token_manager import get_authenticated_users
    
    users = get_authenticated_users()
    return {
        "status": "ok",
        "users": users,
        "count": len(users)
    }