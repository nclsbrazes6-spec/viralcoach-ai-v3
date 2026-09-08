"""Construction du rapport final ViralCoach AI."""

from numbers import Real


def _number(value, default=0.0):
    """Convertit une valeur numérique sans laisser une entrée invalide casser l'API."""
    if isinstance(value, bool):
        return default

    if isinstance(value, Real):
        return float(value)

    if isinstance(value, str):
        try:
            return float(
                value.strip()
                .replace("%", "")
                .replace(",", ".")
            )
        except ValueError:
            pass

    return default


def _first(mapping, keys, default=None):
    for key in keys:
        value = mapping.get(key)

        if value not in (None, "", [], {}):
            return value

    return default


def _as_list(value):
    if value in (None, ""):
        return []

    if isinstance(value, (list, tuple)):
        return list(value)

    return [value]


def _unique(values):
    result = []

    for value in values:
        if value not in (None, "") and value not in result:
            result.append(value)

    return result


def _timeline_items(timeline):
    """Accepte une timeline sous forme de liste ou de dictionnaire."""

    if isinstance(timeline, list):
        return timeline

    if isinstance(timeline, dict):
        for key in (
            "plans",
            "segments",
            "passages",
            "items",
            "timeline",
        ):
            if isinstance(timeline.get(key), list):
                return timeline[key]

        if timeline and all(
            isinstance(value, dict)
            for value in timeline.values()
        ):
            return list(timeline.values())

    return []


def _is_risky(item):
    if not isinstance(item, dict):
        return False

    risk = str(
        _first(
            item,
            (
                "niveau_risque",
                "risque",
                "risk",
                "niveau",
            ),
            "",
        )
    ).lower()

    if any(
        word in risk
        for word in (
            "moyen",
            "élevé",
            "eleve",
            "haut",
            "fort",
            "critique",
            "medium",
            "high",
        )
    ):
        return True

    score = _first(
        item,
        (
            "score_risque",
            "risk_score",
        ),
    )

    if score is not None and _number(score) >= 5:
        return True

    return bool(
        item.get("a_risque")
        or item.get("is_risky")
    )


def _time_value(item, keys, default=0.0):
    return _number(
        _first(
            item,
            keys,
            default,
        ),
        default,
    )


def _client_passage(item):
    start = _time_value(
        item,
        (
            "debut_secondes",
            "debut",
            "start",
            "temps_debut",
            "start_time",
        ),
    )

    end = _time_value(
        item,
        (
            "fin_secondes",
            "fin",
            "end",
            "temps_fin",
            "end_time",
        ),
        start,
    )

    timecode = _first(
        item,
        (
            "periode",
            "timecode",
        ),
        f"{start:.1f}s–{end:.1f}s",
    )

    return {
        "debut": start,
        "fin": end,
        "timecode": timecode,
        "niveau_risque": _first(
            item,
            (
                "niveau_risque",
                "risque",
                "risk",
                "niveau",
            ),
            "à surveiller",
        ),
        "diagnostic": _first(
            item,
            (
                "diagnostic",
                "probleme",
                "observation",
                "reason",
            ),
            "Passage susceptible de faire baisser l'attention.",
        ),
        "recommandation": _first(
            item,
            (
                "recommandation",
                "action",
                "suggestion",
            ),
            "Raccourcir le passage ou ajouter une relance visuelle.",
        ),
    }


def _opening_diagnostic(
    note_hook,
    timeline_items,
    analyse_transcription,
    analyse_decoupage,
):
    explicit = _first(
        analyse_transcription,
        (
            "diagnostic_3_premieres_secondes",
            "diagnostic_hook",
            "diagnostic_ouverture",
        ),
    ) or _first(
        analyse_decoupage,
        (
            "diagnostic_3_premieres_secondes",
            "diagnostic_ouverture",
        ),
    )

    opening = []

    for item in timeline_items:
        if not isinstance(item, dict):
            continue

        start = _time_value(
            item,
            (
                "debut_secondes",
                "debut",
                "start",
                "temps_debut",
                "start_time",
            ),
        )

        if start < 3:
            opening.append(item)

    if explicit:
        diagnostic = explicit

    elif note_hook >= 8:
        diagnostic = (
            "L'ouverture capte rapidement l'attention "
            "et communique une promesse claire."
        )

    elif note_hook >= 6:
        diagnostic = (
            "L'ouverture est compréhensible, mais la "
            "promesse peut être rendue plus immédiate."
        )

    else:
        diagnostic = (
            "Les 3 premières secondes manquent d'une "
            "promesse, d'une tension ou d'une curiosité immédiate."
        )

    return {
        "periode": "0:00–0:03",
        "note_hook": note_hook,
        "diagnostic": diagnostic,
        "passages_timeline": opening,
        "action_prioritaire": (
            "Conserver l'ouverture et renforcer le texte à l'écran."
            if note_hook >= 8
            else
            "Commencer directement par le bénéfice, "
            "le résultat ou la question forte."
        ),
    }


def build_final_report(
    transcription,
    analyse_transcription,
    analyse_visuelle,
    analyse_montage,
    analyse_retention,
    analyse_decoupage,
):
    """Construit le rapport final ViralCoach AI V5, compatible avec la V4.3."""

    analyse_transcription = analyse_transcription or {}
    analyse_visuelle = analyse_visuelle or {}
    analyse_montage = analyse_montage or {}
    analyse_retention = analyse_retention or {}
    analyse_decoupage = analyse_decoupage or {}

    # ========================================================
    # NOTES DE BASE
    # ========================================================

    note_texte = _number(
        analyse_transcription.get(
            "note_potentiel_viral"
        )
    )

    note_visuelle = _number(
        _first(
            analyse_visuelle,
            (
                "note_visuelle_globale",
                "note_video",
                "note_visuelle",
            ),
            0,
        )
    )

    note_hook = _number(
        analyse_transcription.get(
            "note_hook"
        )
    )

    note_rythme = _number(
        _first(
            analyse_montage,
            (
                "note_rythme",
                "note_montage",
            ),
            0,
        )
    )

    retention = _number(
        _first(
            analyse_retention,
            (
                "retention_estimee",
                "retention_estimee_pourcent",
            ),
            _first(
                analyse_montage,
                (
                    "retention_estimee_pourcent",
                    "retention_estimee",
                ),
                0,
            ),
        )
    )

    # ========================================================
    # HOOKS / PUBLICATION
    # ========================================================

    hooks = _as_list(
        _first(
            analyse_transcription,
            (
                "hooks_améliores",
                "hooks_ameliores",
            ),
            [],
        )
    )[:3]

    meilleur_hook = hooks[0] if hooks else ""

    description = _first(
        analyse_transcription,
        (
            "description_tiktok",
            "description",
        ),
        "",
    )

    hashtags = _unique(
        _as_list(
            analyse_transcription.get(
                "hashtags"
            )
        )
    )

    # ========================================================
    # POINTS FORTS / FAIBLES
    # ========================================================

    points_forts = _unique(
        _as_list(
            analyse_transcription.get(
                "points_forts"
            )
        )
        + _as_list(
            analyse_visuelle.get(
                "points_forts"
            )
        )
        + _as_list(
            analyse_montage.get(
                "points_forts"
            )
        )
    )

    points_faibles = _unique(
        _as_list(
            analyse_transcription.get(
                "points_faibles"
            )
        )
        + _as_list(
            analyse_visuelle.get(
                "points_faibles"
            )
        )
        + _as_list(
            analyse_montage.get(
                "points_faibles"
            )
        )
    )

    recommandations = _unique(
        _as_list(
            analyse_montage.get(
                "recommandations"
            )
        )
        + _as_list(
            analyse_retention.get(
                "recommandations"
            )
        )
        + _as_list(
            analyse_decoupage.get(
                "recommandations"
            )
        )
    )

    # ========================================================
    # TIMELINE
    # ========================================================

    timeline = analyse_decoupage.get(
        "timeline",
        [],
    )

    timeline_items = _timeline_items(
        timeline
    )

    nombre_coupes = int(
        _number(
            _first(
                analyse_decoupage,
                (
                    "coupes_detectees",
                    "nombre_coupes",
                    "cuts_count",
                ),
                0,
            )
        )
    )

    nombre_plans = int(
        _number(
            _first(
                analyse_decoupage,
                (
                    "plans_detectes",
                    "nombre_plans",
                ),
                len(timeline_items),
            )
        )
    )

    duree_moyenne_plan = _number(
        _first(
            analyse_decoupage,
            (
                "duree_moyenne_plan_secondes",
                "duree_moyenne_plan",
                "average_scene_duration",
            ),
            0,
        )
    )

    # ========================================================
    # NOTE HISTORIQUE /10
    # ========================================================

    note_globale = round(
        note_texte * 0.20
        + note_visuelle * 0.20
        + note_hook * 0.20
        + note_rythme * 0.20
        + (retention / 10) * 0.20,
        1,
    )

    note_globale = max(
        0,
        min(
            10,
            note_globale,
        ),
    )

    # ========================================================
    # SCORE VIRAL /100
    # ========================================================

    score_hook = round(
        max(
            0,
            min(
                10,
                note_hook,
            ),
        ) * 2
    )

    score_texte = round(
        max(
            0,
            min(
                10,
                note_texte,
            ),
        ) * 2
    )

    score_visuel = round(
        max(
            0,
            min(
                10,
                note_visuelle,
            ),
        ) * 2
    )

    score_rythme = round(
        max(
            0,
            min(
                10,
                note_rythme,
            ),
        ) * 2
    )

    score_retention = round(
        max(
            0,
            min(
                100,
                retention,
            ),
        ) / 5
    )

    score_viral = (
        score_hook
        + score_texte
        + score_visuel
        + score_rythme
        + score_retention
    )

    score_viral = max(
        0,
        min(
            100,
            score_viral,
        ),
    )

    # ========================================================
    # POTENTIEL VIRAL
    # ========================================================

    if score_viral >= 85:
        potentiel_viral = "EXCELLENT"

    elif score_viral >= 75:
        potentiel_viral = "TRÈS BON"

    elif score_viral >= 65:
        potentiel_viral = "BON"

    elif score_viral >= 50:
        potentiel_viral = "MOYEN"

    else:
        potentiel_viral = "À RETRAVAILLER"

    # ========================================================
    # VERDICT
    # ========================================================

    if note_globale >= 8.5:
        verdict = "Excellent potentiel viral"

    elif note_globale >= 7.5:
        verdict = "Très bon potentiel viral"

    elif note_globale >= 6.5:
        verdict = "Bon potentiel viral"

    elif note_globale >= 5:
        verdict = "Potentiel correct mais améliorable"

    else:
        verdict = "Vidéo à retravailler avant publication"

    # ========================================================
    # PASSAGES À RISQUE
    # ========================================================

    passages_a_risque = [
        _client_passage(item)
        for item in timeline_items
        if _is_risky(item)
    ]

    # ========================================================
    # PLAN DE REMONTAGE
    # ========================================================

    plan_remontage = _unique(
        [
            passage["recommandation"]
            for passage in passages_a_risque
        ]
        + recommandations
    )

    # ========================================================
    # DIAGNOSTIC OUVERTURE
    # ========================================================

    diagnostic_ouverture = _opening_diagnostic(
        note_hook,
        timeline_items,
        analyse_transcription,
        analyse_decoupage,
    )

    # ========================================================
    # RAPPORT FINAL
    # ========================================================

    return {
        "viralcoach": {
            "version": "5.0",

            # Ancienne note conservée
            "note_globale": note_globale,

            # Nouveau score
            "score_viral": score_viral,
            "potentiel_viral": potentiel_viral,

            "verdict": verdict,

            "scores": {
                "hook": score_hook,
                "texte": score_texte,
                "visuel": score_visuel,
                "rythme": score_rythme,
                "retention": score_retention,
            },

            # Clés directes utiles au front
            "score_hook": score_hook,
            "score_texte": score_texte,
            "score_visuel": score_visuel,
            "score_rythme": score_rythme,
            "score_retention": score_retention,

            # Anciennes notes conservées
            "note_hook": note_hook,
            "note_visuelle": note_visuelle,
            "note_rythme": note_rythme,
            "retention_estimee": retention,

            "niveau_retention": analyse_retention.get(
                "niveau_retention",
                "",
            ),
        },

        "rapport_client": {
            "note_globale": note_globale,

            "score_viral": score_viral,
            "potentiel_viral": potentiel_viral,

            "score_hook": score_hook,
            "score_texte": score_texte,
            "score_visuel": score_visuel,
            "score_rythme": score_rythme,
            "score_retention": score_retention,

            "scores": {
                "hook": score_hook,
                "texte": score_texte,
                "visuel": score_visuel,
                "rythme": score_rythme,
                "retention": score_retention,
            },

            "verdict": verdict,

            "notes": {
                "hook": note_hook,
                "visuel": note_visuelle,
                "rythme": note_rythme,
                "retention_estimee": retention,
            },

            "diagnostic_3_premieres_secondes": (
                diagnostic_ouverture
            ),

            "passages_a_risque": passages_a_risque,

            "hooks_ameliores": hooks,

            "plan_remontage": plan_remontage,

            "publication": {
                "description_tiktok": description,
                "hashtags": hashtags,
            },
        },

        "montage": {
            "nombre_coupes": nombre_coupes,
            "nombre_plans": nombre_plans,
            "duree_moyenne_plan": duree_moyenne_plan,
            "timeline": timeline,
        },

        "meilleur_hook": meilleur_hook,

        "points_forts": points_forts,

        "points_faibles": points_faibles,

        "risques_retention": analyse_retention.get(
            "risques",
            [],
        ),

        "recommandations": recommandations,

        "publication": {
            "description_tiktok": description,
            "hashtags": hashtags,
        },

        "details": {
            "transcription": transcription,
            "analyse_transcription": analyse_transcription,
            "analyse_visuelle": analyse_visuelle,
            "analyse_montage": analyse_montage,
            "analyse_retention": analyse_retention,
            "analyse_decoupage": analyse_decoupage,
        },
    }