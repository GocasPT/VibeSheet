"""
VibeSheet API - Backend para sincronização Spotify → Google Sheets.

Arquitetura:
- FastAPI com lifespan management
- Background scheduler para sync periódico
- Processamento paralelo de usuários
- Batch updates para Google Sheets
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Routers e services
from auth.spotify_oauth import router as spotify_router
from sheets.sheets_service import get_sheets_service
from utils.scheduler import (
    start_scheduler,
    stop_scheduler,
    get_scheduler_status,
    trigger_manual_sync
)
from services.sync_service import shutdown_sync_executor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia ciclo de vida da aplicação.
    
    Startup:
    - Valida conexão com Google Sheets
    - Inicia scheduler de sync periódico
    
    Shutdown:
    - Para scheduler gracefully
    - Fecha thread pools
    """
    # ============ STARTUP ============
    logger.info("🚀 Iniciando VibeSheet API...")
    
    try:
        # Valida Google Sheets
        sheets_service = get_sheets_service()
        sheets_service.ensure_headers()
        logger.info("✓ Google Sheets conectado e headers validados")
        
        # Inicia scheduler
        start_scheduler()
        logger.info("✓ Scheduler iniciado")
        
    except Exception as e:
        logger.error(f"❌ Falha no startup: {e}")
        raise
    
    yield
    
    # ============ SHUTDOWN ============
    logger.info("🛑 Desligando VibeSheet API...")
    
    try:
        stop_scheduler()
        shutdown_sync_executor()
        logger.info("✓ Shutdown concluído")
    
    except Exception as e:
        logger.error(f"Erro no shutdown: {e}")


# ============ APP ============
app = FastAPI(
    title="VibeSheet API",
    description="Backend service for Spotify-to-Google-Sheets integration",
    version="1.0.0",
    lifespan=lifespan
)

# Registra routers
app.include_router(spotify_router, prefix="/spotify", tags=["spotify-auth"])


# ============ ENDPOINTS ============

@app.get("/", tags=["system"])
def root():
    """Root endpoint com informações básicas"""
    return {
        "service": "VibeSheet API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "login": "/spotify/login",
            "sync": "/sync"
        }
    }


@app.get("/health", tags=["system"])
def health_check():
    """
    Health check detalhado.
    
    Retorna:
    - Status do serviço
    - Número de usuários autenticados
    - Status do scheduler
    - Métricas de sync
    """
    from auth.spotify_token_manager import get_authenticated_users
    
    users = get_authenticated_users()
    scheduler_status = get_scheduler_status()
    
    return {
        "status": "healthy",
        "service": "VibeSheet API",
        "users": {
            "authenticated": len(users),
            "list": users
        },
        "scheduler": scheduler_status
    }


@app.post("/sync", tags=["sync"])
def manual_sync():
    """
    Dispara sincronização manual (bypass do scheduler).
    
    Útil para:
    - Debug e testes
    - Sync sob demanda
    - Validação após autenticação
    """
    try:
        logger.info("Sync manual requisitado via API")
        metrics = trigger_manual_sync()
        
        return {
            "status": "success",
            "message": "Sync concluído",
            "metrics": {
                "total_users": metrics.total,
                "success": metrics.success,
                "failed": metrics.failed,
                "not_playing": metrics.not_playing
            }
        }
    
    except Exception as e:
        logger.error(f"Sync manual falhou: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )


@app.post("/sync/{user_id}", tags=["sync"])
def sync_single_user(user_id: str):
    """
    Sincroniza usuário específico.
    
    Útil para debug ou refresh individual.
    """
    from services.sync_service import SpotifySyncService
    
    try:
        success = SpotifySyncService.sync_single_user(user_id)
        
        if success:
            return {
                "status": "success",
                "user": user_id,
                "message": f"User {user_id} sincronizado"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to sync user {user_id}"
            )
    
    except Exception as e:
        logger.error(f"Sync do usuário {user_id} falhou: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============ ERROR HANDLERS ============

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handler global para exceções não tratadas"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)