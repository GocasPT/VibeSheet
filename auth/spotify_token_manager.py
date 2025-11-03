"""
Spotify Token Manager - Gerencia ciclo de vida de tokens OAuth.
Separação clara entre AUTH flow e REQUEST flow.
"""
import os
from typing import Dict
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from auth.token_cache_manager import TokenCacheManager

load_dotenv()

# Configurações Spotify
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
TOKENS_FILE = "auth/tokens.json"

# Cache singleton
_token_cache = TokenCacheManager(TOKENS_FILE)


class TokenRefreshError(Exception):
    """Erro ao fazer refresh de token"""
    pass


def load_all_tokens() -> Dict[str, dict]:
    """Carrega todos os tokens (usa cache inteligente)"""
    return _token_cache.load()


def save_all_tokens(tokens: Dict[str, dict]):
    """Salva todos os tokens (persiste + atualiza cache)"""
    _token_cache.save(tokens)


def get_user_token(user_id: str) -> dict:
    """
    Retorna token de um usuário específico.
    
    Raises:
        ValueError: Se usuário não está autenticado
    """
    tokens = load_all_tokens()
    token_info = tokens.get(user_id)
    
    if not token_info:
        raise ValueError(f"User '{user_id}' não autenticado. Execute /spotify/login primeiro.")
    
    return token_info


def create_spotify_oauth_for_user(user_id: str) -> SpotifyOAuth:
    """
    Cria SpotifyOAuth para REQUEST flow (refresh de tokens).
    Usa MultiUserCacheHandler para suportar múltiplos usuários.
    
    IMPORTANTE: NÃO usar para AUTH flow (login/callback).
    Para AUTH, use create_spotify_oauth_no_cache().
    """
    from auth.spotify_oauth import MultiUserCacheHandler
    
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-read-currently-playing,user-read-private,user-read-email",
        cache_handler=MultiUserCacheHandler(user_id=user_id)
    )


def ensure_valid_token(user_id: str, refresh_buffer_sec: int = 300) -> dict:
    """
    Garante que o token está válido para fazer requests.
    Faz refresh automático se necessário.
    
    Args:
        user_id: ID do usuário
        refresh_buffer_sec: Renova token X segundos antes de expirar (default: 5min)
    
    Returns:
        Token info válido com access_token
    
    Raises:
        ValueError: Se usuário não autenticado
        TokenRefreshError: Se refresh falhar
    """
    import time
    
    token_info = get_user_token(user_id)
    
    # Calcula tempo até expiração
    expires_in = token_info.get("expires_at", 0) - int(time.time())
    
    # Se ainda válido com buffer, retorna
    if expires_in >= refresh_buffer_sec:
        return token_info
    
    # Precisa refresh
    oauth = create_spotify_oauth_for_user(user_id)
    
    try:
        refreshed = oauth.refresh_access_token(token_info["refresh_token"])
        
        # Atualiza token no storage
        tokens = load_all_tokens()
        tokens[user_id] = refreshed
        save_all_tokens(tokens)
        
        return refreshed
    
    except Exception as e:
        # Última tentativa: usa token atual se ainda não expirou
        if expires_in > 0:
            return token_info
        
        raise TokenRefreshError(f"Failed to refresh token for '{user_id}': {e}")


def save_user_token(user_id: str, token_info: dict):
    """
    Salva/atualiza token de um usuário específico.
    Usado no callback de autenticação.
    """
    tokens = load_all_tokens()
    tokens[user_id] = token_info
    save_all_tokens(tokens)


def get_authenticated_users() -> list:
    """Retorna lista de user_ids autenticados"""
    return list(load_all_tokens().keys())