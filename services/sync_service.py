"""
Sync Service - Orquestra sincronização Spotify → Google Sheets.
Processamento paralelo + batch updates.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional
from auth.spotify_token_manager import get_authenticated_users
from services.spotify_client import SpotifyClientService, TrackInfo
from sheets.sheets_service import get_sheets_service

logger = logging.getLogger(__name__)

# Thread pool global para I/O paralelo
_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="SpotifySync")


class SyncMetrics:
    """DTO para métricas de sincronização"""
    def __init__(self):
        self.total = 0
        self.success = 0
        self.failed = 0
        self.not_playing = 0
    
    def __repr__(self):
        return f"SyncMetrics(total={self.total}, success={self.success}, failed={self.failed}, not_playing={self.not_playing})"


def _fetch_user_track(user_id: str) -> Tuple[str, Optional[TrackInfo]]:
    """
    Busca track de 1 usuário (função auxiliar para parallelização).
    
    Returns:
        (user_id, TrackInfo ou None)
    """
    try:
        track_info = SpotifyClientService.get_current_track(user_id)
        return (user_id, track_info)
    except Exception as e:
        logger.error(f"Unexpected error fetching track for {user_id}: {e}")
        return (user_id, None)


class SpotifySyncService:
    """
    Service principal de sincronização.
    Coordena fetch paralelo + batch update.
    """
    
    @staticmethod
    def sync_all_users() -> SyncMetrics:
        """
        Sincroniza todos os usuários autenticados.
        
        Estratégia:
        1. Busca lista de usuários autenticados
        2. Fetch paralelo de tracks (ThreadPoolExecutor)
        3. Batch update na Google Sheet (1 API call)
        
        Returns:
            SyncMetrics com estatísticas da operação
        """
        metrics = SyncMetrics()
        
        # Lista usuários autenticados
        user_ids = get_authenticated_users()
        metrics.total = len(user_ids)
        
        if not user_ids:
            logger.warning("Nenhum usuário autenticado encontrado")
            return metrics
        
        logger.info(f"Iniciando sync de {metrics.total} usuários...")
        
        # FASE 1: Fetch paralelo de tracks
        updates: List[Tuple[str, dict]] = []
        
        futures = {
            _executor.submit(_fetch_user_track, uid): uid
            for uid in user_ids
        }
        
        for future in as_completed(futures, timeout=30):
            user_id = futures[future]
            
            try:
                user_id, track_info = future.result(timeout=5)
                
                if track_info is None:
                    metrics.failed += 1
                    logger.warning(f"✗ {user_id}: Failed to fetch")
                    continue
                
                # Prepara update
                updates.append((user_id, track_info.to_dict()))
                
                # Métricas
                if track_info.track == "Not playing":
                    metrics.not_playing += 1
                    logger.debug(f"◯ {user_id}: Not playing")
                else:
                    metrics.success += 1
                    logger.debug(f"✓ {user_id}: {track_info.track} — {track_info.artists}")
            
            except Exception as e:
                metrics.failed += 1
                logger.error(f"✗ {user_id}: {e}")
        
        # FASE 2: Batch update na sheet
        if updates:
            try:
                sheets_service = get_sheets_service()
                sheets_service.batch_update(updates)
                logger.info(f"✅ Sync concluído: {metrics}")
            except Exception as e:
                logger.error(f"❌ Batch update falhou: {e}")
                raise
        else:
            logger.warning("Nenhum dado para atualizar")
        
        return metrics
    
    @staticmethod
    def sync_single_user(user_id: str) -> bool:
        """
        Sincroniza 1 usuário específico (útil para testes).
        
        Returns:
            True se sucesso, False se falhou
        """
        try:
            track_info = SpotifyClientService.get_current_track(user_id)
            
            if track_info is None:
                logger.error(f"Failed to fetch track for {user_id}")
                return False
            
            sheets_service = get_sheets_service()
            sheets_service.update_single(user_id, track_info.to_dict())
            
            logger.info(f"✓ {user_id}: {track_info.track} — {track_info.artists}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to sync {user_id}: {e}")
            return False


def shutdown_sync_executor():
    """Cleanup do thread pool (chamar no shutdown da app)"""
    _executor.shutdown(wait=True, cancel_futures=False)
    logger.info("Sync executor shutdown")