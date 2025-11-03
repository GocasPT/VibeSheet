"""
Google Sheets Service - Abstração para interagir com Google Sheets API.
Otimizado com batch operations e cache.
"""
import os
import time
import logging
from typing import Dict, List, Tuple
from threading import Lock
import gspread
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT = os.getenv("GOOGLE_SERVICE_ACCOUNT")
WORKSHEET_TITLE = os.getenv("GOOGLE_SHEET_WORKSHEET_TITLE")

# Headers da planilha
SHEET_HEADERS = ["Pessoa", "Música", "Artistas/Banda", "Álbum", "Ano", "Link", "Last Update"]


class SheetCache:
    """Cache thread-safe da estrutura da sheet"""
    def __init__(self, ttl: int = 30):
        self.ttl = ttl
        self.user_index: Dict[str, int] = {}  # {username: row_index}
        self.last_update = 0
        self.lock = Lock()
    
    def is_expired(self) -> bool:
        """Verifica se cache expirou"""
        return (time.time() - self.last_update) > self.ttl
    
    def get(self) -> Dict[str, int]:
        """Retorna cache (pode estar expirado)"""
        with self.lock:
            return self.user_index.copy()
    
    def set(self, user_index: Dict[str, int]):
        """Atualiza cache"""
        with self.lock:
            self.user_index = user_index
            self.last_update = time.time()
    
    def invalidate(self):
        """Força expiração do cache"""
        with self.lock:
            self.last_update = 0


class GoogleSheetsService:
    """Service para interagir com Google Sheets API"""
    
    def __init__(self):
        self._cache = SheetCache()
        self._worksheet = None
    
    def _get_worksheet(self):
        """
        Retorna worksheet handle (reutiliza conexão).
        Lazy loading + singleton pattern.
        """
        if self._worksheet is None:
            gc = gspread.service_account(filename=SERVICE_ACCOUNT)
            sh = gc.open_by_key(SHEET_ID)
            self._worksheet = sh.worksheet(WORKSHEET_TITLE)
            logger.info(f"Conectado ao Google Sheets: {WORKSHEET_TITLE}")
        
        return self._worksheet
    
    def _refresh_cache(self) -> Dict[str, int]:
        """
        Carrega estrutura da sheet no cache.
        Retorna mapeamento {username: row_index}.
        """
        ws = self._get_worksheet()
        users = ws.col_values(1)
        
        # Cria índice (ignora header na row 1)
        user_index = {
            user: idx + 1
            for idx, user in enumerate(users)
            if idx > 0  # Skip header
        }
        
        logger.debug(f"Cache atualizado: {len(user_index)} usuários")
        return user_index
    
    def ensure_headers(self):
        """
        Garante que headers estão corretos.
        Deve ser chamado 1x no startup.
        """
        ws = self._get_worksheet()
        current_headers = ws.row_values(1)
        
        if current_headers != SHEET_HEADERS:
            logger.info("Atualizando headers da planilha")
            ws.delete_rows(1)
            ws.insert_row(SHEET_HEADERS, 1)
    
    def batch_update(self, updates: List[Tuple[str, dict]]):
        """
        Atualiza múltiplos usuários em batch (1 API call).
        
        Args:
            updates: Lista de (username, track_data)
        
        Performance:
            - Antes: N chamadas API (1 por usuário)
            - Depois: 1-2 chamadas API (batch_update + append_rows)
        """
        if not updates:
            logger.warning("Batch update vazio")
            return
        
        ws = self._get_worksheet()
        
        # Revalida cache se necessário
        if self._cache.is_expired():
            user_index = self._refresh_cache()
            self._cache.set(user_index)
        else:
            user_index = self._cache.get()
        
        # Separa updates existentes vs novos usuários
        batch_updates = []
        new_rows = []
        
        for username, track_data in updates:
            row_data = [
                username,
                track_data.get("track", "—"),
                track_data.get("artists", "—"),
                track_data.get("album", "—"),
                track_data.get("year", "—"),
                track_data.get("link", "—"),
                track_data.get("timestamp", "—")
            ]
            
            if username in user_index:
                # Update existente
                row_idx = user_index[username]
                batch_updates.append({
                    'range': f'A{row_idx}:G{row_idx}',
                    'values': [row_data]
                })
            else:
                # Novo usuário
                new_rows.append(row_data)
        
        # Executa batch update (1 API call)
        if batch_updates:
            ws.batch_update(batch_updates)
            logger.info(f"Batch update: {len(batch_updates)} usuários atualizados")
        
        # Append novos usuários (1 API call)
        if new_rows:
            ws.append_rows(new_rows)
            logger.info(f"Novos usuários adicionados: {len(new_rows)}")
            
            # Atualiza cache com novos usuários
            next_row = len(user_index) + 2  # +1 header, +1 base-1
            for i, row in enumerate(new_rows):
                user_index[row[0]] = next_row + i
            
            self._cache.set(user_index)
    
    def update_single(self, username: str, track_data: dict):
        """
        Atualiza 1 usuário (wrapper para compatibilidade).
        RECOMENDADO: Use batch_update() para melhor performance.
        """
        self.batch_update([(username, track_data)])


# Singleton instance
_sheets_service = GoogleSheetsService()


def get_sheets_service() -> GoogleSheetsService:
    """Factory para Google Sheets Service (singleton)"""
    return _sheets_service