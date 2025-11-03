"""
Spotify Client Service - Abstração para interagir com API Spotify.
Encapsula lógica de autenticação e requests.
"""
import logging
from typing import Optional, Dict
from datetime import datetime
from spotipy import Spotify
from auth.spotify_token_manager import ensure_valid_token, TokenRefreshError

logger = logging.getLogger(__name__)


class SpotifyClientError(Exception):
    """Erro ao interagir com Spotify API"""
    pass


class TrackInfo:
    """
    DTO para informações de track.
    Encapsula lógica de parsing e formatação.
    """
    def __init__(
        self,
        track: str,
        artists: str,
        album: str,
        year: str,
        link: str,
        timestamp: str = None
    ):
        self.track = track
        self.artists = artists
        self.album = album
        self.year = year
        self.link = link
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @classmethod
    def not_playing(cls) -> 'TrackInfo':
        """Factory para estado 'não tocando'"""
        return cls(
            track="Not playing",
            artists="—",
            album="—",
            year="—",
            link="—"
        )
    
    @classmethod
    def from_spotify_response(cls, item: dict) -> 'TrackInfo':
        """Factory a partir de resposta da API Spotify"""
        return cls(
            track=item["name"],
            artists=", ".join([a["name"] for a in item["artists"]]),
            album=item["album"]["name"],
            year=item["album"]["release_date"].split("-")[0],
            link=item["external_urls"]["spotify"]
        )
    
    def to_dict(self) -> Dict[str, str]:
        """Converte para dict (compatível com Google Sheets)"""
        return {
            "track": self.track,
            "artists": self.artists,
            "album": self.album,
            "year": self.year,
            "link": self.link,
            "timestamp": self.timestamp
        }


class SpotifyClientService:
    """
    Service para interagir com Spotify API.
    Gerencia autenticação automática e error handling.
    """
    
    @staticmethod
    def get_current_track(user_id: str) -> Optional[TrackInfo]:
        """
        Busca track que o usuário está tocando agora.
        
        Returns:
            TrackInfo ou None se falhar
        """
        try:
            # Garante token válido (refresh automático)
            token_info = ensure_valid_token(user_id)
            
            # Cria cliente Spotify
            sp = Spotify(auth=token_info["access_token"])
            
            # Busca track atual
            current = sp.current_user_playing_track()
            
            # Valida resposta
            if not current or not current.get("is_playing"):
                return TrackInfo.not_playing()
            
            item = current.get("item")
            if not item:
                return TrackInfo.not_playing()
            
            # Parse e retorna
            return TrackInfo.from_spotify_response(item)
        
        except TokenRefreshError as e:
            logger.error(f"Token refresh failed for {user_id}: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Failed to fetch track for {user_id}: {e}")
            return None
    
    @staticmethod
    def get_user_profile(user_id: str) -> Optional[dict]:
        """
        Busca perfil do usuário (útil para validação).
        
        Returns:
            User dict ou None se falhar
        """
        try:
            token_info = ensure_valid_token(user_id)
            sp = Spotify(auth=token_info["access_token"])
            return sp.current_user()
        
        except Exception as e:
            logger.error(f"Failed to fetch profile for {user_id}: {e}")
            return None