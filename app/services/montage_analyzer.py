import re
import subprocess


def get_video_duration(video_path: str) -> float:
    """Retourne la durée de la vidéo en secondes avec ffprobe."""

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    try:
        return max(0.0, float(result.stdout.strip()))
    except ValueError as error:
        raise RuntimeError(
            "Durée vidéo illisible avec ffprobe."
        ) from error


def _clamp(
    value: float,
    minimum: float = 0,
    maximum: float = 10,
) -> float:
    return max(minimum, min(maximum, value))


def _word_count(transcription: str) -> int:
    return len(
        re.findall(
            r"\b[\wÀ-ÿ'-]+\b",
            transcription or "",
        )
    )


def analyze_montage(
    frames_count: int,
    duration_seconds: float,
    transcription: str,
) -> dict:
    """
    Estime localement le rythme et la rétention.

    Cette fonction n'utilise aucune API payante.
    """

    duration = max(
        0.0,
        float(duration_seconds or 0),
    )

    frames = max(
        0,
        int(frames_count or 0),
    )

    words = _word_count(transcription)

    frames_per_second = (
        frames / duration
        if duration
        else 0.0
    )

    words_per_minute = (
        words * 60 / duration
        if duration
        else 0.0
    )

    # Les images sont actuellement extraites
    # à environ une image par seconde.
    coverage_score = _clamp(
        frames_per_second * 10
    )

    # Analyse du débit de parole
    if words == 0:
        speech_score = 4.0

    elif words_per_minute < 80:
        speech_score = (
            4.0
            + (words_per_minute / 80) * 2
        )

    elif words_per_minute <= 190:
        speech_score = 8.5

    elif words_per_minute <= 230:
        speech_score = 7.0

    else:
        speech_score = 5.0

    # Analyse de la durée
    if 8 <= duration <= 35:
        duration_score = 9.0

    elif (
        4 <= duration < 8
        or 35 < duration <= 60
    ):
        duration_score = 7.0

    elif duration > 0:
        duration_score = 5.0

    else:
        duration_score = 0.0

    # Note de rythme globale
    rhythm_score = round(
        _clamp(
            coverage_score * 0.30
            + speech_score * 0.40
            + duration_score * 0.30
        ),
        1,
    )

    # Estimation indicative de la rétention
    retention_percent = round(
        _clamp(
            35 + rhythm_score * 5.5,
            minimum=0,
            maximum=90,
        )
    )

    strengths = []
    weaknesses = []
    recommendations = []

    # Durée
    if 8 <= duration <= 35:
        strengths.append(
            "La durée est adaptée à un format vidéo court."
        )

    elif duration > 60:
        weaknesses.append(
            "La durée élevée augmente le risque d'abandon."
        )

        recommendations.append(
            "Réduis la vidéo ou découpe-la en plusieurs épisodes."
        )

    # Couverture visuelle
    if frames_per_second >= 0.85:
        strengths.append(
            "La vidéo dispose d'une bonne couverture "
            "visuelle pour l'analyse."
        )

    else:
        weaknesses.append(
            "La couverture d'images est incomplète "
            "par rapport à la durée."
        )

        recommendations.append(
            "Vérifie l'extraction à une image par seconde."
        )

    # Débit de parole
    if 120 <= words_per_minute <= 190:
        strengths.append(
            "Le débit de parole est dynamique "
            "sans sembler excessif."
        )

    elif words == 0:
        weaknesses.append(
            "Aucune parole exploitable n'a été détectée."
        )

        recommendations.append(
            "Ajoute une voix off ou du texte à l'écran "
            "pour porter le message."
        )

    elif words_per_minute < 100:
        weaknesses.append(
            "Le débit paraît lent pour retenir "
            "l'attention sur un format court."
        )

        recommendations.append(
            "Raccourcis les silences et resserre les phrases."
        )

    elif words_per_minute > 210:
        weaknesses.append(
            "Le débit paraît très rapide et peut "
            "nuire à la compréhension."
        )

        recommendations.append(
            "Ajoute des respirations et simplifie le script."
        )

    # Recommandation globale
    if rhythm_score < 7:
        recommendations.append(
            "Ajoute un changement visuel, un zoom, "
            "un texte ou un B-roll toutes les 2 à 3 secondes."
        )

    else:
        strengths.append(
            "Les signaux de durée et de densité "
            "suggèrent un rythme efficace."
        )

    if not weaknesses:
        weaknesses.append(
            "Le rythme réel des coupes reste à confirmer "
            "par une analyse plan par plan."
        )

    if not recommendations:
        recommendations.append(
            "Conserve ce rythme et renforce surtout "
            "les trois premières secondes."
        )

    return {
        "duree_secondes": round(duration, 2),
        "frames_count": frames,
        "mots_transcrits": words,
        "mots_par_minute": round(
            words_per_minute,
            1,
        ),
        "note_rythme": rhythm_score,
        "retention_estimee_pourcent": (
            retention_percent
        ),
        "points_forts": strengths,
        "points_faibles": weaknesses,
        "recommandations": recommendations,
        "methode": (
            "Estimation locale basée sur la durée, "
            "les frames extraites et la transcription."
        ),
    }