from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.video import router as video_router

PUBLIC_DIR = Path("public")
PUBLIC_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="ViralCoach AI V3",
    version="3.0.0",
    description="API vidéo pour analyse TikTok avec FFmpeg + Make."
)

app.mount("/files", StaticFiles(directory=str(PUBLIC_DIR)), name="files")
app.include_router(video_router, prefix="/api")

@app.get("/")
def root():
    return {
        "status": "ok",
        "name": "ViralCoach AI V3",
        "routes": {
            "process_video": "/api/process-video",
            "health": "/api/health"
        }
    }
