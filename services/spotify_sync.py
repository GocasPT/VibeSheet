import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional
from spotipy import Spotify
from auth.token_manager import ensure_valid_token, load_tokens
from sheets.sheets_client import batch_update_sheet
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Thread pool para I/O paralelo
_executor = ThreadPoolExecutor(max_workers=10)


def get_current_track(user_id: str) -> Optional[Dict]:
    """
    Busca track atual com tratamento robusto de erros.
    Retorna None se falhar (não trava o sync).
    
    IMPORTANTE: Usa ensure_valid_token() que internamente usa
    MultiUserCacheHandler para refresh automático.
    """
    try:
        token_info = ensure_valid_token(user_id)
        sp = Spotify(auth=token_info["access_token"])
        current = sp.current_user_playing_track()

        if not current or not current.get("is_playing") or not current.get("item"):
            return {
                "track": "Not playing",
                "artists": "—",
                "album": "—",
                "year": "—",
                "link": "—",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        item = current["item"]
        return {
            "track": item["name"],
            "artists": ", ".join([a["name"] for a in item["artists"]]),
            "album": item["album"]["name"],
            "year": item["album"]["release_date"].split("-")[0],
            "link": item["external_urls"]["spotify"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    
    except Exception as e:
        logger.error(f"Failed to fetch track for {user_id}: {e}")
        return None


def sync_spotify_to_sheets():
    """
    OTIMIZADO: Busca tracks em paralelo + batch update na sheet.
    
    Performance antes: N usuários × (fetch + update) = ~5s para 10 usuários
    Performance agora: max(fetch_paralelo, 1 batch_update) = ~1s para 10 usuários
    """
    tokens = load_tokens()
    if not tokens:
        logger.warning("No authenticated Spotify users found.")
        return

    user_ids = list(tokens.keys())
    logger.info(f"Syncing {len(user_ids)} users in parallel...")

    # FASE 1: Busca tracks em paralelo (ThreadPoolExecutor)
    futures = {_executor.submit(get_current_track, uid): uid for uid in user_ids}
    
    updates = []
    success_count = 0
    fail_count = 0
    
    for future in as_completed(futures):
        user_id = futures[future]
        try:
            track_info = future.result(timeout=5)  # 5s timeout por usuário
            if track_info:
                updates.append((user_id, track_info))
                success_count += 1
                logger.debug(f"✓ {user_id}: {track_info['track']} — {track_info['artists']}")
            else:
                fail_count += 1
        except Exception as e:
            logger.error(f"✗ {user_id}: {e}")
            fail_count += 1
    
    # FASE 2: Batch update (1 única chamada API)
    if updates:
        try:
            batch_update_sheet(updates)
            logger.info(f"✅ Batch updated {success_count} users ({fail_count} failed)")
        except Exception as e:
            logger.error(f"❌ Batch update failed: {e}")
    else:
        logger.warning("No data to update")


def shutdown_executor():
    """Cleanup do thread pool (chamar no shutdown da app)"""
    _executor.shutdown(wait=True)