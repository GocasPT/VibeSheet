import os
import json
import time
from typing import Dict, Optional
from threading import Lock
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

TOKENS_FILE = "auth/tokens.json"
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# In-memory cache com thread safety
_token_cache: Dict[str, dict] = {}
_cache_lock = Lock()
_last_file_load = 0
_file_check_interval = 60  # Recarrega arquivo a cada 60s


def _should_reload_from_file() -> bool:
    """Evita leituras excessivas do disco"""
    global _last_file_load
    return (time.time() - _last_file_load) > _file_check_interval


def load_tokens() -> Dict[str, dict]:
    """Carrega tokens com cache inteligente"""
    global _token_cache, _last_file_load
    
    with _cache_lock:
        # Usa cache se ainda válido
        if _token_cache and not _should_reload_from_file():
            return _token_cache.copy()
        
        # Lê do disco apenas quando necessário
        if not os.path.exists(TOKENS_FILE):
            _token_cache = {}
        else:
            try:
                with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                    _token_cache = json.load(f)
            except json.JSONDecodeError:
                _token_cache = {}
        
        _last_file_load = time.time()
        return _token_cache.copy()


def save_tokens(tokens: Dict[str, dict]):
    """Salva tokens e atualiza cache atomicamente"""
    global _token_cache
    
    with _cache_lock:
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2)
        _token_cache = tokens.copy()


def create_oauth_for_refresh(user_id: str) -> SpotifyOAuth:
    """
    CRÍTICO: Cria SpotifyOAuth para REFRESH de token específico.
    Usa MultiUserCacheHandler para ler/escrever do JSON multi-user.
    
    NÃO usar para login/callback (use NoCacheHandler nesse caso).
    """
    from auth.spotify_oauth import MultiUserCacheHandler
    
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-read-currently-playing",
        cache_handler=MultiUserCacheHandler(user_id=user_id)
    )


def ensure_valid_token(user_id: str) -> dict:
    """
    Retorna token válido para fazer requests.
    Faz refresh automático se necessário, usando MultiUserCacheHandler.
    
    IMPORTANTE: Este método é para REQUEST flow, não AUTH flow.
    """
    tokens = load_tokens()
    token_info = tokens.get(user_id)

    if not token_info:
        raise ValueError(f"No token found for user '{user_id}'")

    # Buffer de 5min para evitar race conditions
    expires_in = token_info["expires_at"] - int(time.time())
    
    if expires_in < 300:  # 5 minutos
        # Usa MultiUserCacheHandler para refresh (contexto: já autenticado)
        oauth = create_oauth_for_refresh(user_id)
        
        try:
            refreshed = oauth.refresh_access_token(token_info["refresh_token"])
            # MultiUserCacheHandler já salvou no JSON, mas também atualizamos memória
            token_info.update(refreshed)
            tokens[user_id] = token_info
            save_tokens(tokens)
        except Exception as e:
            # Se refresh falhar, tenta usar token atual se ainda válido
            if expires_in > 0:
                return token_info
            raise e

    return token_info