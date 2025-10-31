from fastapi import FastAPI
from auth.spotify_oauth import router as spotify_router
from services.user_status import sync_users_to_sheet


app = FastAPI(
    title="VibeSheet API",
    description="Backend service for Spotify-to-Google-Sheets integration",
    version="0.1.0",
)

app.include_router(spotify_router, prefix="/spotify")
app.include_router(spotify_router)

@app.get("/health", tags=["system"])
def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok", "message": "VibeSheet API running"}

@app.post("/sync", tags=["sheets"])
def sync_sheet():
    """
    Force manual sync of authenticated users to Google Sheets.
    """
    sync_users_to_sheet()
    return {"status": "ok", "message": "Google Sheet updated"}
