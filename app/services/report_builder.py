def _limit_score(value: float) -> int:
    return max(0, min(10, round(value)))


def build_final_report(
    transcription: str,
    text_analysis: dict,
    visual_analysis: dict,
) -> dict:
    text_score = text_analysis.get(
        "note_potentiel_viral",
        0,
    )

    hook_score = text_analysis.get(
        "note_hook",
        0,
    )

    clarity_score = text_analysis.get(
        "note_clarte",
        0,
    )

    visual_score = visual_analysis.get(
        "note_visuelle_globale",
        0,
    )

    brightness_score = visual_analysis.get(
        "note_luminosite",
        0,
    )

    sharpness_score = visual_analysis.get(
        "note_nettete",
        0,
    )

    rhythm_score = visual_analysis.get(
        "note_rythme_visuel",
        0,
    )

    has_transcription = bool(
        transcription.strip()
    )

    if has_transcription:
        global_score = _limit_score(
            text_score * 0.55
            + visual_score * 0.45
        )
    else:
        global_score = visual_score

    if global_score >= 8:
        verdict = (
            "Très bon potentiel. La vidéo possède "
            "plusieurs éléments favorables à la rétention."
        )
    elif global_score >= 6:
        verdict = (
            "Bon potentiel, mais quelques améliorations "
            "peuvent renforcer son efficacité."
        )
    elif global_score >= 4:
        verdict = (
            "Potentiel moyen. La vidéo doit être "
            "retravaillée avant publication."
        )
    else:
        verdict = (
            "Potentiel faible dans sa version actuelle. "
            "Une nouvelle version est recommandée."
        )

    priorities = []
    recommendations = []

    if has_transcription:
        if hook_score < 7:
            priorities.append(
                "Renforcer les trois premières secondes."
            )
            recommendations.append(
                "Commence par une question, une erreur "
                "fréquente ou une promesse précise."
            )

        if clarity_score < 7:
            priorities.append(
                "Simplifier le message."
            )
            recommendations.append(
                "Utilise des phrases plus courtes et "
                "supprime les répétitions."
            )
    else:
        priorities.append(
            "Ajouter une accroche parlée ou écrite."
        )
        recommendations.append(
            "Ajoute dès la première seconde un texte "
            "qui explique clairement la promesse."
        )

    if brightness_score < 7:
        priorities.append(
            "Corriger la luminosité."
        )
        recommendations.append(
            "Éclaircis les plans sombres ou réduis "
            "les zones surexposées."
        )

    if sharpness_score < 7:
        priorities.append(
            "Améliorer la netteté."
        )
        recommendations.append(
            "Utilise une vidéo source de meilleure "
            "qualité et évite les zooms numériques."
        )

    if rhythm_score < 7:
        priorities.append(
            "Dynamiser le montage."
        )
        recommendations.append(
            "Ajoute des changements de plans, des zooms "
            "ou des éléments visuels toutes les 1 à 3 secondes."
        )

    if not priorities:
        priorities.append(
            "Conserver la structure actuelle."
        )
        recommendations.append(
            "Teste plusieurs versions du hook pour "
            "identifier celle qui retient le mieux."
        )

    all_strengths = []

    all_strengths.extend(
        text_analysis.get(
            "points_forts",
            [],
        )
    )

    all_strengths.extend(
        visual_analysis.get(
            "points_forts",
            [],
        )
    )

    all_weaknesses = []

    all_weaknesses.extend(
        text_analysis.get(
            "points_faibles",
            [],
        )
    )

    all_weaknesses.extend(
        visual_analysis.get(
            "points_faibles",
            [],
        )
    )

    return {
        "score_viral_global": global_score,
        "verdict": verdict,
        "notes": {
            "hook": hook_score,
            "clarte": clarity_score,
            "potentiel_texte": text_score,
            "luminosite": brightness_score,
            "nettete": sharpness_score,
            "rythme_visuel": rhythm_score,
            "qualite_visuelle": visual_score,
        },
        "points_forts": all_strengths,
        "points_faibles": all_weaknesses,
        "priorites": priorities,
        "recommandations": recommendations,
        "hooks_ameliores": text_analysis.get(
            "hooks_améliores",
            [],
        ),
        "description_tiktok": text_analysis.get(
            "description_tiktok",
            "",
        ),
        "hashtags": text_analysis.get(
            "hashtags",
            [],
        ),
    }