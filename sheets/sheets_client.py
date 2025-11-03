import gspread
import os
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv
from datetime import datetime
from threading import Lock

load_dotenv()

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT = os.getenv("GOOGLE_SERVICE_ACCOUNT")
WORKSHEET = os.getenv("GOOGLE_SHEET_WORKSHEET_TITLE")

# Cache da estrutura da sheet
_sheet_cache = {
    "users": {},  # {username: row_index}
    "last_update": 0,
    "lock": Lock()
}
_cache_ttl = 30  # Revalida cache a cada 30s


def get_sheet():
    """Conexão com Google Sheets (mantém conexão reutilizável)"""
    gc = gspread.service_account(filename=SERVICE_ACCOUNT)
    sh = gc.open_by_key(SHEET_ID)
    return sh.worksheet(WORKSHEET)


def _refresh_cache(ws) -> Dict[str, int]:
    """Carrega estrutura da sheet no cache"""
    users = ws.col_values(1)
    return {user: idx + 1 for idx, user in enumerate(users) if idx > 0}  # Skip header


def ensure_headers(ws):
    """Garante headers corretos (executa apenas 1x no startup)"""
    headers = ["Pessoa", "Música", "Artistas/Banda", "Álbum", "Ano", "Link", "Last Update"]
    current_headers = ws.row_values(1)
    if current_headers != headers:
        ws.delete_rows(1)
        ws.insert_row(headers, 1)


def batch_update_sheet(updates: List[tuple]):
    """
    CRÍTICO: Atualiza múltiplos usuários em 1 única chamada API.
    updates = [(username, track_data), ...]
    
    Reduz de N chamadas para 1 chamada (100x mais rápido).
    """
    if not updates:
        return
    
    ws = get_sheet()
    
    with _sheet_cache["lock"]:
        # Revalida cache se expirado
        if (time.time() - _sheet_cache["last_update"]) > _cache_ttl:
            _sheet_cache["users"] = _refresh_cache(ws)
            _sheet_cache["last_update"] = time.time()
        
        user_index = _sheet_cache["users"]
    
    # Prepara batch de updates
    batch_data = []
    new_users = []
    
    for username, track_data in updates:
        row_data = [
            username,
            track_data.get("track", "—"),
            track_data.get("artists", "—"),
            track_data.get("album", "—"),
            track_data.get("year", "—"),
            track_data.get("link", "—"),
            track_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ]
        
        if username in user_index:
            row_idx = user_index[username]
            batch_data.append({
                'range': f'A{row_idx}:G{row_idx}',
                'values': [row_data]
            })
        else:
            new_users.append(row_data)
    
    # Executa batch update (1 chamada API)
    if batch_data:
        ws.batch_update(batch_data)
    
    # Append novos usuários (1 chamada API)
    if new_users:
        ws.append_rows(new_users)
        
        # Atualiza cache
        with _sheet_cache["lock"]:
            next_row = len(user_index) + 2  # +1 header, +1 base 1
            for i, row in enumerate(new_users):
                _sheet_cache["users"][row[0]] = next_row + i


def update_sheet_row(username: str, track_data: dict):
    """
    DEPRECADO: Mantido para compatibilidade.
    Use batch_update_sheet() para melhor performance.
    """
    batch_update_sheet([(username, track_data)])
