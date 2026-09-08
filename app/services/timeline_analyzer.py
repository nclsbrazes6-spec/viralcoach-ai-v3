def _format_time(
    seconds: float,
) -> str:
    seconds = max(
        0,
        float(seconds),
    )

    minutes = int(
        seconds // 60
    )

    remaining_seconds = (
        seconds % 60
    )

    return (
        f"{minutes:02d}:"
        f"{remaining_seconds:05.2f}"
    )


def build_timeline(
    analyse_decoupage: dict,
) -> dict:
    """
    Transforme les coupes détectées en recommandations
    de montage horodatées.
    """

    duration = float(
        analyse_decoupage.get(
            "duree_video_secondes",
            0,
        )
    )

    cut_timestamps = list(
        analyse_decoupage.get(
            "temps_coupes_secondes",
            [],
        )
    )

    boundaries = [
        0.0,
        *cut_timestamps,
        duration,
    ]

    plans = []
    moments_to_fix = []

    for index in range(
        len(boundaries) - 1
    ):
        start = round(
            boundaries[index],
            2,
        )

        end = round(
            boundaries[index + 1],
            2,
        )

        plan_duration = round(
            end - start,
            2,
        )

        if plan_duration <= 0:
            continue

        risk_level = "faible"
        diagnostic = (
            "Durée de plan adaptée."
        )
        recommendation = (
            "Conserver ce rythme."
        )

        # Les trois premières secondes
        if (
            start < 3
            and plan_duration > 2.5
        ):
            risk_level = "élevé"

            diagnostic = (
                "Le hook visuel reste trop "
                "longtemps sans changement."
            )

            recommendation = (
                "Ajoute une coupe, un zoom ou "
                "un texte avant 2 secondes."
            )

        # Plan long
        elif plan_duration > 5:
            risk_level = "élevé"

            diagnostic = (
                "Plan beaucoup trop long pour "
                "une vidéo courte."
            )

            recommendation = (
                "Découpe ce passage en plusieurs "
                "plans ou ajoute du B-roll."
            )

        elif plan_duration > 3:
            risk_level = "moyen"

            diagnostic = (
                "Ce plan risque de ralentir "
                "la rétention."
            )

            recommendation = (
                "Ajoute un changement visuel "
                "au milieu de ce passage."
            )

        # Plan très court
        elif plan_duration < 0.6:
            risk_level = "moyen"

            diagnostic = (
                "Changement visuel très rapide."
            )

            recommendation = (
                "Vérifie que le spectateur a le "
                "temps de comprendre l'image."
            )

        plan = {
            "numero_plan": index + 1,

            "debut_secondes": start,
            "fin_secondes": end,
            "duree_secondes": (
                plan_duration
            ),

            "periode": (
                f"{_format_time(start)}"
                f" - "
                f"{_format_time(end)}"
            ),

            "niveau_risque": (
                risk_level
            ),

            "diagnostic": (
                diagnostic
            ),

            "recommandation": (
                recommendation
            ),
        }

        plans.append(
            plan
        )

        if risk_level in {
            "moyen",
            "élevé",
        }:
            moments_to_fix.append(
                plan
            )

    high_risk_count = sum(
        plan["niveau_risque"]
        == "élevé"
        for plan in plans
    )

    medium_risk_count = sum(
        plan["niveau_risque"]
        == "moyen"
        for plan in plans
    )

    if high_risk_count > 0:
        global_diagnostic = (
            f"{high_risk_count} passage(s) "
            "présentent un risque élevé "
            "de perte d'attention."
        )

    elif medium_risk_count > 0:
        global_diagnostic = (
            f"{medium_risk_count} passage(s) "
            "peuvent être dynamisés."
        )

    else:
        global_diagnostic = (
            "Le rythme des plans est "
            "globalement adapté."
        )

    return {
        "plans": plans,

        "moments_a_corriger": (
            moments_to_fix
        ),

        "nombre_risques_eleves": (
            high_risk_count
        ),

        "nombre_risques_moyens": (
            medium_risk_count
        ),

        "diagnostic_global": (
            global_diagnostic
        ),
    }