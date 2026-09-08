from pathlib import Path

import cv2
import numpy as np

def _clamp(
    value: float,
    minimum: float = 0,
    maximum: float = 10,
) -> float:
    return max(
        minimum,
        min(maximum, value),
    )
def analyze_scenes(
    video_path: str,
) -> dict:
    path = Path(video_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Vidéo introuvable : {path}"
        )

    capture = cv2.VideoCapture(
        str(path)
    )

    if not capture.isOpened():
        raise RuntimeError(
            "Impossible d'ouvrir la vidéo."
        )

    fps = capture.get(
        cv2.CAP_PROP_FPS
    )

    total_frames = int(
        capture.get(
            cv2.CAP_PROP_FRAME_COUNT
        )
    )

    if fps <= 0:
        capture.release()

        raise RuntimeError(
            "FPS vidéo invalide."
        )

    duration = (
        total_frames / fps
        if total_frames > 0
        else 0
    )

    # Quatre vérifications par seconde
    sample_interval = max(
        1,
        round(fps / 4),
    )

    previous_gray = None
    cut_timestamps = []
    frame_number = 0
    last_cut_time = 0.0

    while True:
        success, frame = capture.read()

        if not success:
            break

        if frame_number % sample_interval != 0:
            frame_number += 1
            continue

        current_time = (
            frame_number / fps
        )

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY,
        )

        gray = cv2.resize(
            gray,
            (320, 180),
        )

        if previous_gray is not None:
            pixel_difference = float(
                np.mean(
                    cv2.absdiff(
                        previous_gray,
                        gray,
                    )
                )
            )

            time_since_last_cut = (
                current_time
                - last_cut_time
            )

            # Changement important entre
            # deux images successives
            if (
                pixel_difference >= 18
                and time_since_last_cut >= 0.5
            ):
                cut_timestamps.append(
                    round(current_time, 2)
                )

                last_cut_time = (
                    current_time
                )

        previous_gray = gray
        frame_number += 1

    capture.release()

    boundaries = [
        0.0,
        *cut_timestamps,
        round(duration, 2),
    ]

    plan_durations = []

    for index in range(
        len(boundaries) - 1
    ):
        plan_duration = round(
            boundaries[index + 1]
            - boundaries[index],
            2,
        )

        if plan_duration > 0:
            plan_durations.append(
                plan_duration
            )

    plans_count = len(
        plan_durations
    )

    average_plan_duration = (
        float(
            np.mean(plan_durations)
        )
        if plan_durations
        else duration
    )

    longest_plan = (
        max(plan_durations)
        if plan_durations
        else duration
    )

    long_plans = []

    for index, plan_duration in enumerate(
        plan_durations
    ):
        if plan_duration > 3:
            long_plans.append(
                {
                    "numero_plan": index + 1,
                    "debut_secondes": round(
                        boundaries[index],
                        2,
                    ),
                    "fin_secondes": round(
                        boundaries[index + 1],
                        2,
                    ),
                    "duree_secondes": (
                        plan_duration
                    ),
                }
            )

    cuts_per_minute = (
        len(cut_timestamps)
        * 60
        / duration
        if duration > 0
        else 0
    )

    if 1 <= average_plan_duration <= 3:
        rhythm_score = 9.0

    elif 0.5 <= average_plan_duration < 1:
        rhythm_score = 7.5

    elif 3 < average_plan_duration <= 5:
        rhythm_score = 6.5

    elif average_plan_duration > 5:
        rhythm_score = 4.0

    else:
        rhythm_score = 5.0

    if long_plans:
        rhythm_score -= min(
            2,
            len(long_plans) * 0.4,
        )

    rhythm_score = round(
        _clamp(rhythm_score),
        1,
    )

    strengths = []
    weaknesses = []
    recommendations = []

    if 1 <= average_plan_duration <= 3:
        strengths.append(
            "La durée moyenne des plans "
            "est dynamique."
        )

    elif average_plan_duration > 3:
        weaknesses.append(
            "Les plans restent longtemps "
            "à l'écran."
        )

        recommendations.append(
            "Ajoute des coupes, zooms ou "
            "changements visuels toutes "
            "les 2 à 3 secondes."
        )

    elif average_plan_duration < 1:
        weaknesses.append(
            "Les changements visuels "
            "sont très rapides."
        )

        recommendations.append(
            "Laisse davantage de temps pour "
            "comprendre les informations."
        )

    if long_plans:
        weaknesses.append(
            f"{len(long_plans)} plan(s) "
            "dépassent trois secondes."
        )

        recommendations.append(
            "Découpe ou dynamise les plans "
            "longs identifiés."
        )

    else:
        strengths.append(
            "Aucun plan supérieur à trois "
            "secondes n'a été détecté."
        )

    if not recommendations:
        recommendations.append(
            "Conserve ce rythme et renforce "
            "les trois premières secondes."
        )

    return {
        "duree_video_secondes": round(
            duration,
            2,
        ),
        "fps": round(
            fps,
            2,
        ),
        "coupes_detectees": len(
            cut_timestamps
        ),
        "plans_detectes": plans_count,
        "coupes_par_minute": round(
            cuts_per_minute,
            1,
        ),
        "temps_coupes_secondes": (
            cut_timestamps
        ),
        "durees_plans_secondes": (
            plan_durations
        ),
        "duree_moyenne_plan_secondes": round(
            average_plan_duration,
            2,
        ),
        "plan_le_plus_long_secondes": round(
            longest_plan,
            2,
        ),
        "plans_trop_longs": (
            long_plans
        ),
        "note_decoupage": (
            rhythm_score
        ),
        "points_forts": strengths,
        "points_faibles": weaknesses,
        "recommandations": recommendations,
        "methode": (
            "Détection locale par différence "
            "entre les pixels avec OpenCV."
        ),
    }