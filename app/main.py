from pathlib import Path
import shutil
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.services.video_processor import extract_audio, extract_frames
from app.services.transcriber import transcribe
from app.services.analyzer import analyze_transcription
from app.services.visual_analyzer import analyze_frames
from app.services.report_builder import build_final_report


app = FastAPI(
    title="ViralCoach AI V3",
    version="3.3.0",
)


UPLOAD_DIR = Path("uploads")
FRAMES_DIR = Path("frames")
AUDIO_DIR = Path("audio")

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

FRAMES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AUDIO_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "ViralCoach AI V3 fonctionne",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.post("/api/upload-video")
async def upload_video(
    video: UploadFile = File(...),
):
    filename = video.filename or "video.mp4"
    extension = Path(filename).suffix.lower()

    formats_acceptes = {
        ".mp4",
        ".mov",
        ".m4v",
        ".webm",
    }

    if extension not in formats_acceptes:
        raise HTTPException(
            status_code=400,
            detail=(
                "Format non accepté. "
                "Utilise MP4, MOV, M4V ou WEBM."
            ),
        )

    video_id = uuid.uuid4().hex[:8]

    video_path = (
        UPLOAD_DIR
        / f"{video_id}{extension}"
    )

    frames_folder = (
        FRAMES_DIR
        / video_id
    )

    audio_path = (
        AUDIO_DIR
        / f"{video_id}.wav"
    )

    try:
        # Enregistrement de la vidéo
        with video_path.open("wb") as destination:
            shutil.copyfileobj(
                video.file,
                destination,
            )

        # Extraction des images
        frames = extract_frames(
            video_path,
            frames_folder,
        )

        # Analyse visuelle locale
        analyse_visuelle = analyze_frames(
            frames
        )

        # Extraction de l'audio
        extracted_audio = extract_audio(
            video_path,
            audio_path,
        )

        # Transcription locale
        transcription = transcribe(
            str(extracted_audio)
        )

        # Analyse de la transcription
        analyse_transcription = (
            analyze_transcription(
                transcription
            )
        )

        # Fusion des analyses
        rapport_final = build_final_report(
            transcription=transcription,
            text_analysis=analyse_transcription,
            visual_analysis=analyse_visuelle,
        )

        return {
            "success": True,
            "video_id": video_id,
            "filename": filename,
            "video_path": str(video_path),
            "audio_path": str(
                extracted_audio
            ),
            "frames_count": len(frames),
            "frames": [
                str(frame)
                for frame in frames
            ],
            "transcription": transcription,
            "analyse_transcription": (
                analyse_transcription
            ),
            "analyse_visuelle": (
                analyse_visuelle
            ),
            "rapport_final": rapport_final,
        }

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Fichier introuvable : "
                f"{error}"
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Erreur pendant le traitement : "
                f"{error}"
            ),
        ) from error

    finally:
        await video.close()