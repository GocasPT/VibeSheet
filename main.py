from fastapi import FastAPI
from auth.spotify_oauth import router as spotify_router
from services.user_status import sync_users_to_sheet
from services.spotify_sync import sync_spotify_to_sheets
from utils.scheduler import start_scheduler
import logging

logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="VibeSheet API",
    description="Backend service for Spotify-to-Google-Sheets integration",
    version="0.1.0",
)

app.include_router(spotify_router, prefix="/spotify")

@app.on_event("startup")
def startup_event():
    start_scheduler()

@app.get("/health", tags=["system"])
def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok", "message": "VibeSheet API running"}

@app.post("/sync/users", tags=["sheets"])
def sync_sheet_users():
    sync_users_to_sheet()
    return {"status": "ok", "message": "Google Sheet updated with users"}


@app.post("/sync/tracks", tags=["spotify"])
def sync_tracks():
    sync_spotify_to_sheets()
    return {"status": "ok", "message": "Google Sheet updated with Spotify data"}
