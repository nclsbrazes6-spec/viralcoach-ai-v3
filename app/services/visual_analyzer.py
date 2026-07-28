from pathlib import Path

import cv2
import numpy as np


def _limit_score(value: float) -> int:
    return max(0, min(10, round(value)))


def analyze_frames(frame_paths: list) -> dict:
    brightness_values = []
    sharpness_values = []
    scene_differences = []

    previous_gray = None
    valid_frames = 0

    for frame_path in frame_paths:
        path = Path(frame_path)
        image = cv2.imread(str(path))

        if image is None:
            continue

        valid_frames += 1

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        # Luminosité moyenne
        brightness = float(
            np.mean(gray)
        )
        brightness_values.append(
            brightness
        )

        # Netteté de l’image
        sharpness = float(
            cv2.Laplacian(
                gray,
                cv2.CV_64F,
            ).var()
        )
        sharpness_values.append(
            sharpness
        )

        # Différence avec l’image précédente
        if previous_gray is not None:
            resized = cv2.resize(
                gray,
                (
                    previous_gray.shape[1],
                    previous_gray.shape[0],
                ),
            )

            difference = float(
                np.mean(
                    cv2.absdiff(
                        previous_gray,
                        resized,
                    )
                )
            )

            scene_differences.append(
                difference
            )

        previous_gray = gray

    if valid_frames == 0:
        return {
            "images_analysees": 0,
            "luminosite_moyenne": 0,
            "nettete_moyenne": 0,
            "changements_plans": 0,
            "note_luminosite": 0,
            "note_nettete": 0,
            "note_rythme_visuel": 0,
            "note_visuelle_globale": 0,
            "points_forts": [],
            "points_faibles": [
                "Aucune image exploitable n'a été trouvée."
            ],
        }

    average_brightness = float(
        np.mean(brightness_values)
    )

    average_sharpness = float(
        np.mean(sharpness_values)
    )

    scene_changes = sum(
        difference >= 18
        for difference in scene_differences
    )

    # Une luminosité proche de 128 est équilibrée
    brightness_score = _limit_score(
        10
        - abs(
            128 - average_brightness
        ) / 13
    )

    # Une variance de 500 ou plus
    # correspond à une bonne netteté
    sharpness_score = _limit_score(
        average_sharpness / 50
    )

    if valid_frames <= 1:
        rhythm_score = 0
    else:
        change_ratio = (
            scene_changes
            / (valid_frames - 1)
        )

        rhythm_score = _limit_score(
            change_ratio * 20
        )

    global_score = _limit_score(
        brightness_score * 0.30
        + sharpness_score * 0.35
        + rhythm_score * 0.35
    )

    strengths = []
    weaknesses = []

    if brightness_score >= 7:
        strengths.append(
            "La luminosité est globalement équilibrée."
        )
    elif average_brightness < 75:
        weaknesses.append(
            "La vidéo paraît trop sombre."
        )
    else:
        weaknesses.append(
            "La vidéo paraît trop lumineuse."
        )

    if sharpness_score >= 7:
        strengths.append(
            "Les images sont globalement nettes."
        )
    else:
        weaknesses.append(
            "Certaines images manquent de netteté."
        )

    if rhythm_score >= 7:
        strengths.append(
            "Les changements visuels donnent un rythme dynamique."
        )
    else:
        weaknesses.append(
            "Le montage visuel semble peu dynamique."
        )

    return {
        "images_analysees": valid_frames,
        "luminosite_moyenne": round(
            average_brightness,
            2,
        ),
        "nettete_moyenne": round(
            average_sharpness,
            2,
        ),
        "changements_plans": scene_changes,
        "note_luminosite": brightness_score,
        "note_nettete": sharpness_score,
        "note_rythme_visuel": rhythm_score,
        "note_visuelle_globale": global_score,
        "points_forts": strengths,
        "points_faibles": weaknesses,
    }