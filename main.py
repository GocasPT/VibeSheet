from fastapi import FastAPI
from auth.spotify_oauth import router as spotify_router

app = FastAPI(
    title="VibeSheet API",
    description="Backend service for Spotify-to-Google-Sheets integration",
    version="0.1.0",
)

app.include_router(spotify_router, prefix="/spotify")

@app.get("/health", tags=["system"])
def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok", "message": "VibeSheet API running"}
