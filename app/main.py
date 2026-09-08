from pathlib import Path
import shutil
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse


# ============================================================
# SERVICES
# ============================================================

from app.services.video_processor import (
    extract_audio,
    extract_frames,
)

from app.services.transcriber import transcribe
from app.services.analyzer import analyze_transcription
from app.services.visual_analyzer import analyze_frames

from app.services.montage_analyzer import (
    analyze_montage,
    get_video_duration,
)

from app.services.retention_analyzer import analyze_retention
from app.services.scene_analyzer import analyze_scenes
from app.services.timeline_analyzer import build_timeline
from app.services.remontage_analyzer import analyze_remontage

from app.services.semantic_segment_analyzer import (
    analyze_semantic_segments,
)

from app.services.semantic_remontage_merger import (
    merge_semantic_remontage,
)

from app.services.global_remix_planner import (
    build_global_remix_plan,
)

from app.services.video_remixer import (
    generate_global_remix_video,
)

from app.services.report_builder import (
    build_final_report,
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="ViralCoach AI V5.5",
    version="5.5.0",
    description=(
        "Analyse et remontage automatique "
        "de vidéos courtes pour TikTok/Reels."
    ),
)


# ============================================================
# CHEMINS
# ============================================================

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent

INTERFACE_FILE = (
    APP_DIR
    / "static"
    / "index.html"
)

UPLOAD_DIR = (
    BASE_DIR
    / "uploads"
)

FRAMES_DIR = (
    BASE_DIR
    / "frames"
)

AUDIO_DIR = (
    BASE_DIR
    / "audio"
)

OUTPUT_DIR = (
    BASE_DIR
    / "outputs"
)


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

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# OUTIL : NORMALISATION TRANSCRIPTION
# ============================================================

def normalize_transcription(
    transcription_raw,
) -> str:

    """
    Convertit n'importe quel format de transcription
    en chaîne de caractères.

    Compatible :
    - str
    - dict OpenAI
    - objet avec attribut text
    - None
    """

    if transcription_raw is None:
        return ""

    # --------------------------------------------------------
    # CAS 1 : DÉJÀ UNE CHAÎNE
    # --------------------------------------------------------

    if isinstance(
        transcription_raw,
        str,
    ):

        return (
            transcription_raw
            .strip()
        )

    # --------------------------------------------------------
    # CAS 2 : DICTIONNAIRE
    # --------------------------------------------------------

    if isinstance(
        transcription_raw,
        dict,
    ):

        for key in (
            "text",
            "texte",
            "transcription",
            "transcript",
        ):

            value = (
                transcription_raw
                .get(key)
            )

            if isinstance(
                value,
                str,
            ):

                value = value.strip()

                if value:
                    return value

        # Aucun texte exploitable
        return ""

    # --------------------------------------------------------
    # CAS 3 : OBJET OPENAI
    # --------------------------------------------------------

    text_attribute = getattr(
        transcription_raw,
        "text",
        None,
    )

    if isinstance(
        text_attribute,
        str,
    ):

        return (
            text_attribute
            .strip()
        )

    # --------------------------------------------------------
    # CAS FINAL
    # --------------------------------------------------------

    return (
        str(
            transcription_raw
        )
        .strip()
    )


# ============================================================
# INTERFACE
# ============================================================

@app.get(
    "/",
    include_in_schema=False,
)
def show_interface():

    if not INTERFACE_FILE.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Interface ViralCoach "
                "introuvable."
            ),
        )

    return FileResponse(
        INTERFACE_FILE
    )


# ============================================================
# HEAD /
# ÉVITE LE 405 DES TESTS RENDER
# ============================================================

@app.head(
    "/",
    include_in_schema=False,
)
def head_interface():

    return {
        "status": "ok"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "version": "5.5.0",
        "app": "ViralCoach AI V5.5",
        "remix_engine": "global-v3",
    }


# ============================================================
# TÉLÉCHARGEMENT REMIX
# ============================================================

@app.get(
    "/api/remix/{filename}"
)
def download_remix(
    filename: str,
):

    safe_filename = (
        Path(filename).name
    )

    remix_file = (
        OUTPUT_DIR
        / safe_filename
    )

    if not remix_file.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Vidéo remontée "
                "introuvable."
            ),
        )

    return FileResponse(
        remix_file,
        media_type="video/mp4",
        filename=safe_filename,
    )


# ============================================================
# VIDÉO ORIGINALE
# ============================================================

@app.get(
    "/api/original/{filename}"
)
def view_original(
    filename: str,
):

    safe_filename = (
        Path(filename).name
    )

    original_file = (
        UPLOAD_DIR
        / safe_filename
    )

    if not original_file.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Vidéo originale "
                "introuvable."
            ),
        )

    return FileResponse(
        original_file,
        media_type="video/mp4",
    )


# ============================================================
# UPLOAD + ANALYSE VIDÉO
# ============================================================

@app.post(
    "/api/upload-video"
)
async def upload_video(
    video: UploadFile = File(...),
):

    try:

        # ====================================================
        # 1. IDENTIFIANT VIDÉO
        # ====================================================

        video_id = (
            uuid.uuid4()
            .hex[:8]
        )

        original_filename = (
            video.filename
            or "video.mp4"
        )

        extension = (
            Path(
                original_filename
            )
            .suffix
            .lower()
        )

        if not extension:
            extension = ".mp4"

        filename = (
            f"{video_id}"
            f"{extension}"
        )

        video_path = (
            UPLOAD_DIR
            / filename
        )

        audio_path = (
            AUDIO_DIR
            / f"{video_id}.wav"
        )

        frame_directory = (
            FRAMES_DIR
            / video_id
        )

        frame_directory.mkdir(
            parents=True,
            exist_ok=True,
        )


        # ====================================================
        # 2. SAUVEGARDE VIDÉO
        # ====================================================

        print(
            "VIRALCOACH : "
            "sauvegarde vidéo..."
        )

        with video_path.open(
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                video.file,
                buffer,
            )


        # ====================================================
        # 3. EXTRACTION FRAMES
        # ====================================================

        print(
            "VIRALCOACH : "
            "extraction frames..."
        )

        frames = extract_frames(
            video_path,
            frame_directory,
        )

        print(
            "FRAMES:",
            len(frames),
        )


        # ====================================================
        # 4. ANALYSE VISUELLE
        # ====================================================

        print(
            "VIRALCOACH : "
            "analyse visuelle..."
        )

        analyse_visuelle = (
            analyze_frames(
                frames
            )
        )


        # ====================================================
        # 5. EXTRACTION AUDIO
        # ====================================================

        print(
            "VIRALCOACH : "
            "extraction audio..."
        )

        extracted_audio = (
            extract_audio(
                video_path,
                audio_path,
            )
        )


        # ====================================================
        # 6. TRANSCRIPTION OPENAI
        # ====================================================

        print(
            "VIRALCOACH : "
            "transcription OpenAI..."
        )

        transcription_raw = (
            transcribe(
                str(
                    extracted_audio
                )
            )
        )

        # ----------------------------------------------------
        # NORMALISATION CRITIQUE
        # ----------------------------------------------------

        transcription = (
            normalize_transcription(
                transcription_raw
            )
        )

        print(
            "TRANSCRIPTION RAW TYPE:",
            type(
                transcription_raw
            ).__name__,
        )

        print(
            "TRANSCRIPTION TYPE:",
            type(
                transcription
            ).__name__,
        )

        print(
            "TRANSCRIPTION:",
            transcription[:300],
        )


        # ====================================================
        # 7. ANALYSE TRANSCRIPTION
        # ====================================================

        print(
            "VIRALCOACH : "
            "analyse transcription..."
        )

        analyse_transcription = (
            analyze_transcription(
                transcription
            )
        )


        # ====================================================
        # 8. DURÉE VIDÉO
        # ====================================================

        duration_seconds = (
            get_video_duration(
                str(
                    video_path
                )
            )
        )

        print(
            "DURATION:",
            duration_seconds,
        )


        # ====================================================
        # 9. ANALYSE MONTAGE
        # ====================================================

        print(
            "VIRALCOACH : "
            "analyse montage..."
        )

        analyse_montage = (
            analyze_montage(
                frames_count=len(
                    frames
                ),
                duration_seconds=(
                    duration_seconds
                ),
                transcription=(
                    transcription
                ),
            )
        )


        # ====================================================
        # 10. ANALYSE RÉTENTION
        # ====================================================

        print(
            "VIRALCOACH : "
            "analyse rétention..."
        )

        analyse_retention = (
            analyze_retention(
                analyse_transcription=(
                    analyse_transcription
                ),
                analyse_visuelle=(
                    analyse_visuelle
                ),
                analyse_montage=(
                    analyse_montage
                ),
            )
        )


        # ====================================================
        # 11. DÉTECTION SCÈNES
        # ====================================================

        print(
            "VIRALCOACH : "
            "détection scènes..."
        )

        analyse_decoupage = (
            analyze_scenes(
                str(
                    video_path
                )
            )
        )


        # ====================================================
        # 12. TIMELINE
        # ====================================================

        analyse_timeline = (
            build_timeline(
                analyse_decoupage,
            )
        )

        analyse_decoupage[
            "timeline"
        ] = analyse_timeline

        analyse_decoupage[
            "duration_seconds"
        ] = duration_seconds


        # ====================================================
        # 13. REMONTAGE V5.3
        # ====================================================

        print(
            "VIRALCOACH : "
            "remontage V5.3..."
        )

        analyse_remontage = (
            analyze_remontage(
                analyse_decoupage=(
                    analyse_decoupage
                ),
                analyse_transcription=(
                    analyse_transcription
                ),
                analyse_montage=(
                    analyse_montage
                ),
            )
        )

        analyse_decoupage[
            "remontage_v5_1"
        ] = analyse_remontage

        analyse_decoupage[
            "remontage_v5_3"
        ] = analyse_remontage


        # ====================================================
        # 14. ANALYSE SÉMANTIQUE V5.4
        # ====================================================

        print(
            "VIRALCOACH : "
            "analyse sémantique..."
        )

        analyse_semantique = (
            analyze_semantic_segments(
                transcription=(
                    transcription
                ),
                segments=(
                    analyse_remontage.get(
                        "segments",
                        [],
                    )
                ),
                visual_analysis=(
                    analyse_visuelle
                ),
            )
        )

        analyse_decoupage[
            "semantic_v5_4"
        ] = analyse_semantique


        # ====================================================
        # 15. FUSION TECHNIQUE + SÉMANTIQUE
        # ====================================================

        print(
            "VIRALCOACH : "
            "fusion V5.4..."
        )

        analyse_remontage_v5_4 = (
            merge_semantic_remontage(
                analyse_remontage=(
                    analyse_remontage
                ),
                analyse_semantique=(
                    analyse_semantique
                ),
            )
        )

        analyse_decoupage[
            "remontage_v5_4"
        ] = analyse_remontage_v5_4


        # ====================================================
        # 16. GLOBAL REMIX PLAN V3
        # ====================================================

        print(
            "VIRALCOACH : "
            "création Global Remix V3..."
        )

        plan_remix_v3 = (
            build_global_remix_plan(
                semantic_analysis=(
                    analyse_semantique
                ),
                technical_remontage=(
                    analyse_remontage
                ),
                duration_seconds=(
                    duration_seconds
                ),
            )
        )

        analyse_decoupage[
            "plan_remix_v3"
        ] = plan_remix_v3


        # ====================================================
        # 17. GÉNÉRATION MP4 REMIX
        # ====================================================

        print(
            "VIRALCOACH : "
            "génération MP4..."
        )

        remix_path = (
            OUTPUT_DIR
            / (
                f"{video_id}"
                "_global_v3.mp4"
            )
        )

        analyse_video_remixee = (
            generate_global_remix_video(
                video_path=(
                    video_path
                ),
                plan_remix_v3=(
                    plan_remix_v3
                ),
                output_path=(
                    remix_path
                ),
            )
        )


        # ====================================================
        # 18. RAPPORT FINAL
        # ====================================================

        print(
            "VIRALCOACH : "
            "construction rapport..."
        )

        rapport = (
            build_final_report(
                transcription=(
                    transcription
                ),
                analyse_transcription=(
                    analyse_transcription
                ),
                analyse_visuelle=(
                    analyse_visuelle
                ),
                analyse_montage=(
                    analyse_montage
                ),
                analyse_retention=(
                    analyse_retention
                ),
                analyse_decoupage=(
                    analyse_decoupage
                ),
            )
        )


        # ====================================================
        # 19. DONNÉES REMONTAGE
        # ====================================================

        rapport[
            "remontage_v5_1"
        ] = analyse_remontage

        rapport[
            "remontage_v5_3"
        ] = analyse_remontage

        rapport[
            "remontage_v5_4"
        ] = analyse_remontage_v5_4

        rapport[
            "semantic_v5_4"
        ] = analyse_semantique

        rapport[
            "plan_remix_v3"
        ] = plan_remix_v3

        rapport[
            "video_remixee"
        ] = analyse_video_remixee


        # ====================================================
        # 20. INFORMATIONS TECHNIQUES
        # ====================================================

        rapport[
            "video_id"
        ] = video_id

        rapport[
            "filename"
        ] = filename

        rapport[
            "original_filename"
        ] = original_filename

        rapport[
            "video_path"
        ] = str(
            video_path
        )

        rapport[
            "audio_path"
        ] = str(
            extracted_audio
        )

        rapport[
            "frames_count"
        ] = len(
            frames
        )

        rapport[
            "duration_seconds"
        ] = round(
            duration_seconds,
            2,
        )

        rapport[
            "remix_video_path"
        ] = str(
            remix_path
        )


        # ====================================================
        # 21. RÉSULTAT
        # ====================================================

        print(
            "VIRALCOACH : "
            "ANALYSE TERMINÉE"
        )

        return rapport


    # ========================================================
    # GESTION ERREURS
    # ========================================================

    except Exception as error:

        print(
            "ERREUR VIRALCOACH:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Erreur pendant le traitement "
                f"de la vidéo : {error}"
            ),
        ) from error


    # ========================================================
    # FERMETURE FICHIER
    # ========================================================

    finally:

        await video.close()