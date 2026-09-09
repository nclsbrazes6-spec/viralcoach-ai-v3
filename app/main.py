from pathlib import Path
import os
import shutil
import uuid

import requests

from fastapi import (
    FastAPI,
    File,
    Header,
    HTTPException,
    UploadFile,
)

from fastapi.responses import FileResponse


# ============================================================
# SERVICES VIRALCOACH
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
# CONFIGURATION SUPABASE
# ============================================================

SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    "",
).rstrip("/")

SUPABASE_ANON_KEY = os.getenv(
    "SUPABASE_ANON_KEY",
    "",
)

SUPABASE_SECRET_KEY = os.getenv(
    "SUPABASE_SECRET_KEY",
    "",
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


for directory in (
    UPLOAD_DIR,
    FRAMES_DIR,
    AUDIO_DIR,
    OUTPUT_DIR,
):

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# NORMALISATION TRANSCRIPTION
# ============================================================

def normalize_transcription(
    transcription_raw,
) -> str:

    if transcription_raw is None:
        return ""

    if isinstance(
        transcription_raw,
        str,
    ):
        return transcription_raw.strip()

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

            value = transcription_raw.get(
                key
            )

            if isinstance(
                value,
                str,
            ):

                value = value.strip()

                if value:
                    return value

        return ""

    text_attribute = getattr(
        transcription_raw,
        "text",
        None,
    )

    if isinstance(
        text_attribute,
        str,
    ):

        return text_attribute.strip()

    return str(
        transcription_raw
    ).strip()


# ============================================================
# SUPABASE — CONFIGURATION
# ============================================================

def check_supabase_config():

    if not SUPABASE_URL:
        raise RuntimeError(
            "SUPABASE_URL absente."
        )

    if not SUPABASE_ANON_KEY:
        raise RuntimeError(
            "SUPABASE_ANON_KEY absente."
        )

    if not SUPABASE_SECRET_KEY:
        raise RuntimeError(
            "SUPABASE_SECRET_KEY absente."
        )


# ============================================================
# SUPABASE — IDENTIFICATION UTILISATEUR
# ============================================================

def get_authenticated_user(
    authorization: str | None,
) -> dict:

    check_supabase_config()

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Connexion requise.",
        )

    parts = authorization.split(
        " ",
        1,
    )

    if (
        len(parts) != 2
        or parts[0].lower() != "bearer"
    ):

        raise HTTPException(
            status_code=401,
            detail=(
                "Token d'authentification invalide."
            ),
        )

    access_token = (
        parts[1].strip()
    )

    if not access_token:

        raise HTTPException(
            status_code=401,
            detail="Token vide.",
        )

    response = requests.get(
        (
            f"{SUPABASE_URL}"
            "/auth/v1/user"
        ),
        headers={
            "apikey":
                SUPABASE_ANON_KEY,
            "Authorization":
                f"Bearer {access_token}",
        },
        timeout=15,
    )

    if response.status_code != 200:

        raise HTTPException(
            status_code=401,
            detail=(
                "Session expirée ou "
                "utilisateur non connecté."
            ),
        )

    user = response.json()

    if not user.get("id"):

        raise HTTPException(
            status_code=401,
            detail="Utilisateur invalide.",
        )

    return user


# ============================================================
# SUPABASE — HEADERS ADMIN SERVEUR
# ============================================================

def supabase_admin_headers() -> dict:

    check_supabase_config()

    return {
        "apikey":
            SUPABASE_SECRET_KEY,

        "Authorization":
            (
                "Bearer "
                + SUPABASE_SECRET_KEY
            ),

        "Content-Type":
            "application/json",
    }


# ============================================================
# SUPABASE — PROFIL
# ============================================================

def get_user_profile(
    user_id: str,
) -> dict:

    response = requests.get(
        (
            f"{SUPABASE_URL}"
            "/rest/v1/profiles"
        ),
        headers={
            **supabase_admin_headers(),
            "Accept":
                "application/json",
        },
        params={
            "id":
                f"eq.{user_id}",
            "select":
                (
                    "id,email,"
                    "credits,plan,"
                    "created_at"
                ),
        },
        timeout=15,
    )

    if response.status_code not in (
        200,
        206,
    ):

        raise RuntimeError(
            "Impossible de lire "
            "le profil Supabase : "
            + response.text
        )

    profiles = response.json()

    if not profiles:

        raise RuntimeError(
            "Profil utilisateur introuvable."
        )

    return profiles[0]


# ============================================================
# SUPABASE — CONSOMMER UN CRÉDIT
# ============================================================

def consume_credit(
    user_id: str,
) -> int:

    response = requests.post(
        (
            f"{SUPABASE_URL}"
            "/rest/v1/rpc/"
            "consume_credit"
        ),
        headers=(
            supabase_admin_headers()
        ),
        json={
            "p_user_id":
                user_id,
        },
        timeout=15,
    )

    if response.status_code not in (
        200,
        201,
    ):

        text = response.text

        if "NO_CREDITS" in text:

            raise HTTPException(
                status_code=402,
                detail=(
                    "Tu n'as plus "
                    "de crédit disponible."
                ),
            )

        raise RuntimeError(
            "Impossible de consommer "
            "le crédit : "
            + text
        )

    data = response.json()

    try:
        return int(data)

    except Exception:
        return 0


# ============================================================
# SUPABASE — REMBOURSER UN CRÉDIT
# ============================================================

def refund_credit(
    user_id: str,
):

    try:

        response = requests.post(
            (
                f"{SUPABASE_URL}"
                "/rest/v1/rpc/"
                "refund_credit"
            ),
            headers=(
                supabase_admin_headers()
            ),
            json={
                "p_user_id":
                    user_id,
            },
            timeout=15,
        )

        if response.status_code not in (
            200,
            201,
        ):

            print(
                "ERREUR REMBOURSEMENT CREDIT:",
                response.text,
            )

    except Exception as error:

        print(
            "ERREUR REMBOURSEMENT CREDIT:",
            repr(error),
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
                "Interface ViralCoach introuvable."
            ),
        )

    return FileResponse(
        INTERFACE_FILE
    )


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
        "status":
            "healthy",

        "version":
            "5.5.0",

        "app":
            "ViralCoach AI V5.5",

        "remix_engine":
            "global-v3",

        "auth":
            "supabase",
    }


# ============================================================
# CONFIGURATION PUBLIQUE
# ============================================================

@app.get(
    "/api/public-config"
)
def public_config():

    return {
        "supabase_url":
            SUPABASE_URL,

        "supabase_anon_key":
            SUPABASE_ANON_KEY,
    }


# ============================================================
# PROFIL UTILISATEUR
# ============================================================

@app.get(
    "/api/me"
)
def get_me(
    authorization:
        str | None
        = Header(
            default=None
        ),
):

    user = get_authenticated_user(
        authorization
    )

    profile = get_user_profile(
        user["id"]
    )

    return {
        "id":
            user["id"],

        "email":
            user.get("email"),

        "credits":
            profile.get(
                "credits",
                0,
            ),

        "plan":
            profile.get(
                "plan",
                "free",
            ),
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
                "Vidéo remontée introuvable."
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
                "Vidéo originale introuvable."
            ),
        )

    return FileResponse(
        original_file,
        media_type="video/mp4",
    )


# ============================================================
# ANALYSE VIDÉO PROTÉGÉE
# ============================================================

@app.post(
    "/api/upload-video"
)
async def upload_video(
    video:
        UploadFile
        = File(...),

    authorization:
        str | None
        = Header(
            default=None
        ),
):

    user_id = None
    credit_consumed = False

    try:

        # ====================================================
        # 1. AUTHENTIFICATION
        # ====================================================

        user = get_authenticated_user(
            authorization
        )

        user_id = user["id"]

        profile = get_user_profile(
            user_id
        )

        current_credits = int(
            profile.get(
                "credits",
                0,
            )
        )

        if current_credits <= 0:

            raise HTTPException(
                status_code=402,
                detail=(
                    "Tu n'as plus "
                    "de crédit disponible."
                ),
            )


        # ====================================================
        # 2. CONSOMMATION DU CRÉDIT
        # ====================================================

        remaining_credits = (
            consume_credit(
                user_id
            )
        )

        credit_consumed = True

        print(
            "CREDIT CONSOMME:",
            user_id,
            "RESTE:",
            remaining_credits,
        )


        # ====================================================
        # 3. IDENTIFIANT VIDÉO
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
        # 4. SAUVEGARDE VIDÉO
        # ====================================================

        print(
            "VIRALCOACH : sauvegarde vidéo..."
        )

        with video_path.open(
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                video.file,
                buffer,
            )


        # ====================================================
        # 5. EXTRACTION FRAMES
        # ====================================================

        frames = extract_frames(
            video_path,
            frame_directory,
        )

        analyse_visuelle = (
            analyze_frames(
                frames
            )
        )


        # ====================================================
        # 6. EXTRACTION AUDIO
        # ====================================================

        extracted_audio = (
            extract_audio(
                video_path,
                audio_path,
            )
        )


        # ====================================================
        # 7. TRANSCRIPTION
        # ====================================================

        transcription_raw = (
            transcribe(
                str(
                    extracted_audio
                )
            )
        )

        transcription = (
            normalize_transcription(
                transcription_raw
            )
        )

        print(
            "TRANSCRIPTION TYPE:",
            type(
                transcription
            ).__name__,
        )


        # ====================================================
        # 8. ANALYSE TRANSCRIPTION
        # ====================================================

        analyse_transcription = (
            analyze_transcription(
                transcription
            )
        )


        # ====================================================
        # 9. DURÉE
        # ====================================================

        duration_seconds = (
            get_video_duration(
                str(
                    video_path
                )
            )
        )


        # ====================================================
        # 10. MONTAGE
        # ====================================================

        analyse_montage = (
            analyze_montage(
                frames_count=(
                    len(frames)
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
        # 11. RÉTENTION
        # ====================================================

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
        # 12. SCÈNES
        # ====================================================

        analyse_decoupage = (
            analyze_scenes(
                str(
                    video_path
                )
            )
        )


        # ====================================================
        # 13. TIMELINE
        # ====================================================

        analyse_timeline = (
            build_timeline(
                analyse_decoupage
            )
        )

        analyse_decoupage[
            "timeline"
        ] = analyse_timeline

        analyse_decoupage[
            "duration_seconds"
        ] = duration_seconds


        # ====================================================
        # 14. REMONTAGE
        # ====================================================

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
        # 15. ANALYSE SÉMANTIQUE
        # ====================================================

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
        # 16. FUSION SÉMANTIQUE
        # ====================================================

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
        # 17. PLAN REMIX GLOBAL
        # ====================================================

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
        # 18. GÉNÉRATION VIDÉO REMIXÉE
        # ====================================================

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
        # 19. RAPPORT FINAL
        # ====================================================

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
        # 20. INFOS TECHNIQUES
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
        # 21. INFOS COMPTE
        # ====================================================

        rapport[
            "account"
        ] = {
            "user_id":
                user_id,

            "email":
                user.get(
                    "email"
                ),

            "credits_remaining":
                remaining_credits,

            "plan":
                profile.get(
                    "plan",
                    "free",
                ),
        }


        print(
            "VIRALCOACH : ANALYSE TERMINÉE"
        )

        return rapport


    # ========================================================
    # ERREURS HTTP
    # ========================================================

    except HTTPException:

        if (
            credit_consumed
            and user_id
        ):

            refund_credit(
                user_id
            )

        raise


    # ========================================================
    # AUTRES ERREURS
    # ========================================================

    except Exception as error:

        if (
            credit_consumed
            and user_id
        ):

            refund_credit(
                user_id
            )

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
    # FERMETURE
    # ========================================================

    finally:

        await video.close()