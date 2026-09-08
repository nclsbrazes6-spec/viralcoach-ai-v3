from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

ALLOWED_DECISIONS = {
    "CONSERVER",
    "COUPER",
    "RACCOURCIR",
    "ACCÉLÉRER",
    "RENFORCER",
}


# Police Windows épaisse
FONT_FILE = "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"


# ============================================================
# OUTILS
# ============================================================

def _number(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        if value is None:
            return default

        if isinstance(
            value,
            (int, float),
        ):
            return float(value)

        text = (
            str(value)
            .strip()
            .replace(",", ".")
        )

        return float(text)

    except Exception:
        return default


def _clean_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    return (
        str(value)
        .strip()
    )


def _normalize_decision(
    value: Any,
) -> str:

    decision = (
        str(
            value
            or "CONSERVER"
        )
        .strip()
        .upper()
    )

    decision = decision.replace(
        "ACCELERER",
        "ACCÉLÉRER",
    )

    if decision not in ALLOWED_DECISIONS:
        return "CONSERVER"

    return decision


# ============================================================
# FFMPEG
# ============================================================

def _run_ffmpeg(
    command: list[str],
) -> None:

    print(
        "\n"
        "========== VIDEO REMIXER FFMPEG =========="
    )

    print(
        " ".join(command)
    )

    print(
        "=========================================="
        "\n"
    )

    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if process.returncode != 0:

        raise RuntimeError(
            "Erreur FFmpeg Video Remixer :\n"
            + process.stderr[-6000:]
        )


# ============================================================
# POSITION DU TEXTE
# ============================================================

def _text_y_position(
    position: str,
) -> str:

    position = (
        str(
            position
            or "centre"
        )
        .strip()
        .lower()
    )

    if position in {
        "haut",
        "top",
    }:
        return "h*0.16"

    if position in {
        "bas",
        "bottom",
    }:
        return "h*0.76"

    return "(h-text_h)/2"


# ============================================================
# TEXTE VIRAL
# ============================================================

def _viral_text(
    text: str,
) -> str:

    """
    Transforme le texte proposé par Gemini
    en texte écran plus TikTok/Reels.
    """

    cleaned = (
        str(
            text
            or ""
        )
        .strip()
        .upper()
    )

    if not cleaned:
        return ""

    # Évite les textes beaucoup trop longs.
    if len(cleaned) > 60:

        cleaned = (
            cleaned[:57]
            .rstrip()
            + "..."
        )

    return cleaned


# ============================================================
# EXTRACTION / EFFETS D'UN SEGMENT
# ============================================================

def _extract_segment(
    input_path: Path,
    output_path: Path,
    start: float,
    end: float,
    speed: float = 1.0,
    zoom: float = 1.0,
    texte_ecran: str = "",
    position_texte: str = "centre",
    is_hook: bool = False,
) -> None:

    duration = max(
        0.05,
        end - start,
    )

    speed = max(
        0.50,
        min(
            float(speed or 1.0),
            2.0,
        ),
    )

    zoom = max(
        1.0,
        min(
            float(zoom or 1.0),
            1.20,
        ),
    )

    texte_ecran = _viral_text(
        texte_ecran
    )

    # --------------------------------------------------------
    # FILTRES VIDÉO
    # --------------------------------------------------------

    filters = []

    # Vitesse vidéo
    filters.append(
        f"setpts=PTS/{speed:.3f}"
    )

    # --------------------------------------------------------
    # ZOOM
    # --------------------------------------------------------

    if zoom > 1.001:

        filters.append(
            (
                f"scale=iw*{zoom:.3f}:"
                f"ih*{zoom:.3f}"
            )
        )

        filters.append(
            (
                "crop="
                "iw/"
                f"{zoom:.3f}:"
                "ih/"
                f"{zoom:.3f}"
                ":"
                "(iw-ow)/2:"
                "(ih-oh)/2"
            )
        )

    # --------------------------------------------------------
    # TEXTE VIRAL
    # --------------------------------------------------------

    text_file = None

    if texte_ecran:

        text_file = (
            output_path
            .with_suffix(".txt")
        )

        text_file.write_text(
            texte_ecran,
            encoding="utf-8",
        )

        text_file_ffmpeg = (
            str(
                text_file.resolve()
            )
            .replace(
                "\\",
                "/",
            )
        )

        # Échappement du C:
        text_file_ffmpeg = (
            text_file_ffmpeg
            .replace(
                ":",
                "\\:",
                1,
            )
        )

        y_position = (
            _text_y_position(
                position_texte
            )
        )

        # Hook = plus gros
        if is_hook:

            font_size = "h/10"
            border_width = 7
            shadow_x = 5
            shadow_y = 5
            box_border = 20

        else:

            font_size = "h/14"
            border_width = 5
            shadow_x = 3
            shadow_y = 3
            box_border = 15

        drawtext_filter = (
            "drawtext="
            f"fontfile='{FONT_FILE}':"
            f"textfile='{text_file_ffmpeg}':"

            # Lettres blanches
            "fontcolor=white:"

            # Taille
            f"fontsize={font_size}:"

            # Contour TikTok
            f"borderw={border_width}:"
            "bordercolor=black@0.98:"

            # Ombre
            "shadowcolor=black@0.85:"
            f"shadowx={shadow_x}:"
            f"shadowy={shadow_y}:"

            # Fond léger
            "box=1:"
            "boxcolor=black@0.30:"
            f"boxborderw={box_border}:"

            # Centré horizontalement
            "x=(w-text_w)/2:"

            # Position verticale
            f"y={y_position}"
        )

        filters.append(
            drawtext_filter
        )

    video_filter = ",".join(
        filters
    )

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    audio_filter = (
        f"atempo={speed:.3f}"
    )

    # --------------------------------------------------------
    # COMMANDE
    # --------------------------------------------------------

    command = [
        "ffmpeg",
        "-y",

        "-ss",
        f"{start:.3f}",

        "-i",
        str(input_path),

        "-t",
        f"{duration:.3f}",

        "-filter_complex",
        (
            f"[0:v]{video_filter}[v];"
            f"[0:a]{audio_filter}[a]"
        ),

        "-map",
        "[v]",

        "-map",
        "[a]",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "19",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-movflags",
        "+faststart",

        str(output_path),
    ]

    try:

        _run_ffmpeg(
            command
        )

    finally:

        if (
            text_file
            and text_file.exists()
        ):

            try:
                text_file.unlink()

            except Exception:
                pass


# ============================================================
# CONCATÉNATION
# ============================================================

def _concat_segments(
    segment_paths: list[Path],
    output_path: Path,
    temp_directory: Path,
) -> None:

    if not segment_paths:

        raise RuntimeError(
            "Aucun segment disponible "
            "pour créer la vidéo remontée."
        )

    concat_file = (
        temp_directory
        / "concat.txt"
    )

    lines = []

    for segment_path in segment_paths:

        safe_path = (
            str(
                segment_path.resolve()
            )
            .replace(
                "\\",
                "/",
            )
            .replace(
                "'",
                "'\\''",
            )
        )

        lines.append(
            f"file '{safe_path}'"
        )

    concat_file.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(concat_file),

        "-c",
        "copy",

        "-movflags",
        "+faststart",

        str(output_path),
    ]

    _run_ffmpeg(
        command
    )


# ============================================================
# ANCIEN MOTEUR V5.4
# ============================================================

def _segment_times(
    segment: dict,
) -> tuple[float, float]:

    start = _number(
        segment.get(
            "debut_secondes",
            segment.get(
                "debut",
                segment.get(
                    "start",
                    0,
                ),
            ),
        ),
        0.0,
    )

    end = _number(
        segment.get(
            "fin_secondes",
            segment.get(
                "fin",
                segment.get(
                    "end",
                    start,
                ),
            ),
        ),
        start,
    )

    if end < start:
        end = start

    return (
        start,
        end,
    )


def _prepare_segment(
    segment: dict,
) -> dict:

    start, end = (
        _segment_times(
            segment
        )
    )

    decision = (
        _normalize_decision(
            segment.get(
                "decision"
            )
        )
    )

    duration = max(
        0.0,
        end - start,
    )

    speed = _number(
        segment.get(
            "vitesse"
        ),
        1.0,
    )

    zoom = _number(
        segment.get(
            "zoom"
        ),
        1.0,
    )

    new_start = start
    new_end = end

    if decision == "COUPER":

        return {
            "skip": True,
            "decision": decision,
            "start": start,
            "end": end,
            "duration": duration,
            "speed": 1.0,
            "zoom": 1.0,
            "texte_ecran": "",
            "position_texte": "centre",
        }

    # Compatibilité avec les anciens plans
    # lorsqu'aucune coupe précise n'existe.
    if (
        decision == "RACCOURCIR"
        and not segment.get(
            "coupe_fin"
        )
        and not segment.get(
            "fin_source"
        )
    ):

        target_duration = max(
            0.6,
            duration * 0.70,
        )

        target_duration = min(
            target_duration,
            duration,
        )

        new_end = (
            new_start
            + target_duration
        )

    if decision == "ACCÉLÉRER":

        if speed <= 1.0:
            speed = 1.15

    return {
        "skip": False,

        "decision": decision,

        "start": new_start,

        "end": new_end,

        "duration": max(
            0.0,
            new_end - new_start,
        ),

        "speed": speed,

        "zoom": zoom,

        "texte_ecran": _clean_text(
            segment.get(
                "texte_ecran"
            )
        ),

        "position_texte": (
            _clean_text(
                segment.get(
                    "position_texte"
                )
            )
            or "centre"
        ),
    }


# ============================================================
# GÉNÉRATION LEGACY V5.4
# ============================================================

def generate_remixed_video(
    video_path: str | Path,
    remontage_v5_4: dict,
    output_path: str | Path,
) -> dict:

    input_path = Path(
        video_path
    ).resolve()

    final_path = Path(
        output_path
    ).resolve()

    if not input_path.exists():

        raise FileNotFoundError(
            "Vidéo source introuvable : "
            f"{input_path}"
        )

    segments = (
        remontage_v5_4.get(
            "segments",
            [],
        )
    )

    if not isinstance(
        segments,
        list,
    ):

        raise ValueError(
            "remontage_v5_4['segments'] "
            "doit être une liste."
        )

    if not segments:

        raise ValueError(
            "Aucun segment V5.4 "
            "à remonter."
        )

    final_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_segments = []

    with tempfile.TemporaryDirectory(
        prefix="viralcoach_remix_"
    ) as temp_dir:

        temp_directory = Path(
            temp_dir
        )

        rendered_segments = []

        for index, segment in enumerate(
            segments,
            start=1,
        ):

            if not isinstance(
                segment,
                dict,
            ):
                continue

            prepared = (
                _prepare_segment(
                    segment
                )
            )

            decision = prepared[
                "decision"
            ]

            start = prepared[
                "start"
            ]

            end = prepared[
                "end"
            ]

            speed = prepared[
                "speed"
            ]

            zoom = prepared[
                "zoom"
            ]

            texte_ecran = (
                prepared[
                    "texte_ecran"
                ]
            )

            position_texte = (
                prepared[
                    "position_texte"
                ]
            )

            if prepared["skip"]:

                report_segments.append(
                    {
                        "ordre": index,
                        "decision": decision,
                        "status": "supprime",
                    }
                )

                continue

            if end <= start:
                continue

            segment_output = (
                temp_directory
                / f"segment_{index:03d}.mp4"
            )

            _extract_segment(
                input_path=input_path,
                output_path=segment_output,
                start=start,
                end=end,
                speed=speed,
                zoom=zoom,
                texte_ecran=texte_ecran,
                position_texte=position_texte,
                is_hook=(index == 1),
            )

            rendered_segments.append(
                segment_output
            )

            report_segments.append(
                {
                    "ordre": index,
                    "decision": decision,
                    "status": "genere",
                    "debut": round(
                        start,
                        2,
                    ),
                    "fin": round(
                        end,
                        2,
                    ),
                    "vitesse": round(
                        speed,
                        2,
                    ),
                    "zoom": round(
                        zoom,
                        2,
                    ),
                    "texte_ecran": (
                        texte_ecran
                    ),
                }
            )

        if not rendered_segments:

            raise RuntimeError(
                "Tous les segments ont été "
                "supprimés ou ignorés."
            )

        _concat_segments(
            segment_paths=(
                rendered_segments
            ),
            output_path=final_path,
            temp_directory=(
                temp_directory
            ),
        )

    return {
        "status": "ok",
        "version": "5.5-remix-v2",
        "video_path": str(
            final_path
        ),
        "filename": (
            final_path.name
        ),
        "size_bytes": (
            final_path
            .stat()
            .st_size
        ),
        "segments_generes": len(
            rendered_segments
        ),
        "segments": (
            report_segments
        ),
    }


# ============================================================
# GLOBAL REMIX V3 / V3.1
# ============================================================

def generate_global_remix_video(
    video_path: str | Path,
    plan_remix_v3: dict,
    output_path: str | Path,
) -> dict:

    """
    Génère le MP4 final à partir
    du plan Global Remix V3/V3.1.
    """

    input_path = Path(
        video_path
    ).resolve()

    final_path = Path(
        output_path
    ).resolve()

    if not input_path.exists():

        raise FileNotFoundError(
            "Vidéo source introuvable : "
            f"{input_path}"
        )

    if not isinstance(
        plan_remix_v3,
        dict,
    ):

        raise ValueError(
            "plan_remix_v3 doit "
            "être un dictionnaire."
        )

    segments = (
        plan_remix_v3.get(
            "montage_final",
            [],
        )
    )

    if not isinstance(
        segments,
        list,
    ):

        raise ValueError(
            "montage_final doit "
            "être une liste."
        )

    if not segments:

        raise ValueError(
            "Aucun segment dans "
            "montage_final."
        )

    # Ordre réel du montage final
    segments = sorted(
        segments,
        key=lambda item: _number(
            item.get(
                "ordre_final"
            ),
            9999,
        ),
    )

    final_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rendered_segments = []
    report_segments = []

    with tempfile.TemporaryDirectory(
        prefix="viralcoach_global_v3_"
    ) as temp_dir:

        temp_directory = Path(
            temp_dir
        )

        for index, segment in enumerate(
            segments,
            start=1,
        ):

            if not isinstance(
                segment,
                dict,
            ):
                continue

            start = max(
                0.0,
                _number(
                    segment.get(
                        "debut_source"
                    ),
                    0.0,
                ),
            )

            end = _number(
                segment.get(
                    "fin_source"
                ),
                start,
            )

            if end <= start:
                continue

            speed = max(
                1.0,
                min(
                    _number(
                        segment.get(
                            "vitesse"
                        ),
                        1.0,
                    ),
                    1.20,
                ),
            )

            zoom = max(
                1.0,
                min(
                    _number(
                        segment.get(
                            "zoom"
                        ),
                        1.0,
                    ),
                    1.12,
                ),
            )

            texte_ecran = (
                _clean_text(
                    segment.get(
                        "texte_ecran"
                    )
                )
            )

            position_texte = (
                _clean_text(
                    segment.get(
                        "position_texte"
                    )
                )
                or "centre"
            )

            decision = (
                _normalize_decision(
                    segment.get(
                        "decision"
                    )
                )
            )

            segment_output = (
                temp_directory
                / f"global_{index:03d}.mp4"
            )

            print(
                "GLOBAL REMIX "
                f"{index} | "
                f"{start:.2f}s → "
                f"{end:.2f}s | "
                f"{decision} | "
                f"x{speed:.2f} | "
                f"zoom {zoom:.2f} | "
                f"text={texte_ecran!r}"
            )

            _extract_segment(
                input_path=input_path,
                output_path=(
                    segment_output
                ),
                start=start,
                end=end,
                speed=speed,
                zoom=zoom,
                texte_ecran=(
                    texte_ecran
                ),
                position_texte=(
                    position_texte
                ),
                is_hook=(
                    index == 1
                ),
            )

            rendered_segments.append(
                segment_output
            )

            estimated_duration = (
                (end - start)
                / speed
            )

            report_segments.append(
                {
                    "ordre_final": index,

                    "ordre_source": (
                        segment.get(
                            "ordre_source",
                            index,
                        )
                    ),

                    "decision": decision,

                    "status": "genere",

                    "debut_source": round(
                        start,
                        3,
                    ),

                    "fin_source": round(
                        end,
                        3,
                    ),

                    "vitesse": round(
                        speed,
                        2,
                    ),

                    "zoom": round(
                        zoom,
                        2,
                    ),

                    "texte_ecran": (
                        texte_ecran
                    ),

                    "position_texte": (
                        position_texte
                    ),

                    "duree_estimee": round(
                        estimated_duration,
                        2,
                    ),
                }
            )

        if not rendered_segments:

            raise RuntimeError(
                "Aucun segment Global V3 "
                "n'a pu être généré."
            )

        _concat_segments(
            segment_paths=(
                rendered_segments
            ),
            output_path=(
                final_path
            ),
            temp_directory=(
                temp_directory
            ),
        )

    if not final_path.exists():

        raise RuntimeError(
            "FFmpeg n'a pas créé "
            "la vidéo finale."
        )

    final_size = (
        final_path
        .stat()
        .st_size
    )

    if final_size <= 0:

        raise RuntimeError(
            "La vidéo finale est vide."
        )

    return {
        "status": "ok",

        "version": (
            plan_remix_v3.get(
                "version",
                "5.5-remix-v3.1",
            )
        ),

        "video_path": str(
            final_path
        ),

        "filename": (
            final_path.name
        ),

        "size_bytes": (
            final_size
        ),

        "strategie_globale": (
            plan_remix_v3.get(
                "strategie_globale",
                "",
            )
        ),

        "hook_final": (
            plan_remix_v3.get(
                "hook_final",
                {},
            )
        ),

        "segments_planifies": len(
            segments
        ),

        "segments_generes": len(
            rendered_segments
        ),

        "duree_finale_estimee": (
            plan_remix_v3.get(
                "duree_finale_estimee",
                round(
                    sum(
                        item.get(
                            "duree_estimee",
                            0,
                        )
                        for item
                        in report_segments
                    ),
                    2,
                ),
            )
        ),

        "segments_supprimes": (
            plan_remix_v3.get(
                "segments_supprimes",
                [],
            )
        ),

        "segments": (
            report_segments
        ),
    }