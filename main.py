import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from auth.spotify_oauth import router as spotify_router
from services.spotify_sync import shutdown_executor
from utils.scheduler import start_scheduler, stop_scheduler

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia startup e shutdown da aplicação"""
    # Startup
    logger.info("🚀 Starting VibeSheet API...")
    start_scheduler()
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down VibeSheet API...")
    stop_scheduler()
    shutdown_executor()


app = FastAPI(
    title="VibeSheet API",
    description="Backend service for Spotify-to-Google-Sheets integration",
    version="0.2.0",
    lifespan=lifespan
)

app.include_router(spotify_router, prefix="/spotify")


@app.get("/health", tags=["system"])
def health_check():
    """Health check com informações do sistema"""
    from auth.token_manager import load_tokens
    from utils.scheduler import get_scheduler_status
    
    tokens = load_tokens()
    return {
        "status": "ok",
        "message": "VibeSheet API running",
        "users_authenticated": len(tokens),
        "scheduler": get_scheduler_status()
    }
