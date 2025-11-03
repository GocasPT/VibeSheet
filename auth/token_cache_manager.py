"""
Token Cache Manager - Gerencia cache em memória de tokens Spotify.
Reduz I/O do disco e melhora performance.
"""
import json
import os
import time
from threading import Lock
from typing import Dict


class TokenCacheManager:
    """
    Singleton para cache thread-safe de tokens Spotify.
    
    Estratégia:
    - Cache em memória para leituras rápidas
    - Recarrega do disco apenas a cada X segundos
    - Escrita sempre persiste no disco + atualiza memória
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls, tokens_file: str, reload_interval: int = 60):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize(tokens_file, reload_interval)
        return cls._instance
    
    def _initialize(self, tokens_file: str, reload_interval: int):
        """Inicializa estado interno (chamado apenas 1x)"""
        self.tokens_file = tokens_file
        self.reload_interval = reload_interval
        self._cache: Dict[str, dict] = {}
        self._last_load_time = 0
        self._cache_lock = Lock()
    
    def _should_reload(self) -> bool:
        """Verifica se cache deve ser recarregado do disco"""
        return (time.time() - self._last_load_time) > self.reload_interval
    
    def load(self) -> Dict[str, dict]:
        """
        Carrega tokens (cache ou disco).
        Thread-safe e otimizado para leituras frequentes.
        """
        with self._cache_lock:
            # Retorna cache se ainda válido
            if self._cache and not self._should_reload():
                return self._cache.copy()
            
            # Recarrega do disco
            if not os.path.exists(self.tokens_file):
                self._cache = {}
            else:
                try:
                    with open(self.tokens_file, 'r', encoding='utf-8') as f:
                        self._cache = json.load(f)
                except (json.JSONDecodeError, IOError):
                    self._cache = {}
            
            self._last_load_time = time.time()
            return self._cache.copy()
    
    def save(self, tokens: Dict[str, dict]):
        """
        Persiste tokens no disco e atualiza cache.
        Thread-safe e atômico.
        """
        with self._cache_lock:
            # Cria diretório se não existir
            os.makedirs(os.path.dirname(self.tokens_file), exist_ok=True)
            
            # Salva no disco
            with open(self.tokens_file, 'w', encoding='utf-8') as f:
                json.dump(tokens, f, indent=2)
            
            # Atualiza cache
            self._cache = tokens.copy()
            self._last_load_time = time.time()
    
    def invalidate_cache(self):
        """Force reload no próximo load() - útil para testes"""
        with self._cache_lock:
            self._last_load_time = 0