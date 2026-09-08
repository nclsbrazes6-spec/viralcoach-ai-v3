"""
Moteur de remontage intelligent ViralCoach AI V5.3.

Objectifs :
- couvrir toute la durée de la vidéo ;
- exploiter la timeline réelle ;
- analyser chaque segment ;
- décider quoi conserver, couper ou raccourcir ;
- proposer des actions visuelles concrètes ;
- estimer le risque de décrochage ;
- générer un plan de montage exploitable ;
- rester compatible avec ViralCoach V5.2.
"""

from numbers import Real


# ============================================================
# OUTILS GENERAUX
# ============================================================

def _number(value, default=0.0):
    """Convertit une valeur en nombre."""

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
    """Retourne la première valeur exploitable trouvée."""

    if not isinstance(mapping, dict):
        return default

    for key in keys:
        value = mapping.get(key)

        if value not in (
            None,
            "",
            [],
            {},
        ):
            return value

    return default


def _as_list(value):
    """Transforme une valeur en liste."""

    if isinstance(value, list):
        return value

    if value in (
        None,
        "",
        {},
    ):
        return []

    return [value]


def _unique(items):
    """Supprime les doublons en conservant l'ordre."""

    result = []

    for item in items:
        if item not in result:
            result.append(item)

    return result


def _clamp(
    value,
    minimum,
    maximum,
):
    """Limite une valeur entre un minimum et un maximum."""

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


# ============================================================
# TEMPS
# ============================================================

def _format_time(seconds):
    """Convertit des secondes en MM:SS.xx."""

    seconds = max(
        0.0,
        _number(seconds),
    )

    minutes = int(
        seconds // 60
    )

    remaining = (
        seconds
        -
        minutes * 60
    )

    return (
        f"{minutes:02d}:"
        f"{remaining:05.2f}"
    )


def _format_time_short(seconds):
    """Convertit des secondes en MM:SS."""

    seconds = max(
        0.0,
        _number(seconds),
    )

    minutes = int(
        seconds // 60
    )

    remaining = int(
        seconds
        -
        minutes * 60
    )

    return (
        f"{minutes:02d}:"
        f"{remaining:02d}"
    )


def _time_value(
    item,
    keys,
    default=0.0,
):
    """Cherche un temps dans plusieurs clés possibles."""

    return _number(
        _first(
            item,
            keys,
            default,
        ),
        default,
    )


# ============================================================
# TIMELINE
# ============================================================

def _timeline_items(timeline):
    """Normalise différentes structures de timeline."""

    if isinstance(
        timeline,
        list,
    ):
        return timeline

    if isinstance(
        timeline,
        dict,
    ):
        for key in (
            "timeline",
            "plans",
            "segments",
            "passages",
            "items",
            "scenes",
        ):
            value = timeline.get(
                key
            )

            if isinstance(
                value,
                list,
            ):
                return value

    return []


# ============================================================
# DUREE VIDEO
# ============================================================

def _video_duration(
    analyse_decoupage,
    analyse_montage,
    timeline_items,
):
    """Détermine la durée totale de la vidéo."""

    candidates = []

    if isinstance(
        analyse_decoupage,
        dict,
    ):
        candidates.extend([
            analyse_decoupage.get(
                "duration_seconds"
            ),
            analyse_decoupage.get(
                "duree"
            ),
            analyse_decoupage.get(
                "duration"
            ),
            analyse_decoupage.get(
                "video_duration"
            ),
            analyse_decoupage.get(
                "duree_video"
            ),
        ])

    if isinstance(
        analyse_montage,
        dict,
    ):
        candidates.extend([
            analyse_montage.get(
                "duration_seconds"
            ),
            analyse_montage.get(
                "duree"
            ),
            analyse_montage.get(
                "duration"
            ),
            analyse_montage.get(
                "video_duration"
            ),
        ])

    for value in candidates:
        duration = _number(
            value,
            0,
        )

        if duration > 0:
            return duration

    max_end = 0.0

    for item in timeline_items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        end = _time_value(
            item,
            (
                "fin_secondes",
                "fin",
                "end",
                "temps_fin",
                "end_time",
            ),
            0,
        )

        if end > max_end:
            max_end = end

    return max_end


# ============================================================
# RISQUE
# ============================================================

def _risk_level(item):
    """Normalise un niveau de risque."""

    risk = str(
        _first(
            item,
            (
                "niveau_risque",
                "risque",
                "risk",
                "niveau",
                "priority",
                "priorite",
            ),
            "",
        )
    ).lower()

    if any(
        word in risk
        for word in (
            "élevé",
            "eleve",
            "critique",
            "fort",
            "high",
            "urgent",
        )
    ):
        return "eleve"

    if any(
        word in risk
        for word in (
            "moyen",
            "medium",
            "modéré",
            "modere",
        )
    ):
        return "moyen"

    return "faible"


def _risk_label(level):
    """Retourne le niveau de risque lisible."""

    if level == "eleve":
        return "ÉLEVÉ"

    if level == "moyen":
        return "MOYEN"

    return "FAIBLE"


# ============================================================
# EXTRACTION DU CONTENU D'UN SEGMENT
# ============================================================

def _segment_content(matches):
    """
    Essaie de récupérer ce qui est réellement associé
    au passage de la timeline.
    """

    values = []

    for item in matches:
        if not isinstance(
            item,
            dict,
        ):
            continue

        value = _first(
            item,
            (
                "texte",
                "text",
                "transcription",
                "contenu",
                "content",
                "description",
                "resume",
                "résumé",
                "observation",
            ),
            "",
        )

        if value:
            values.append(
                str(value).strip()
            )

    return " ".join(
        _unique(values)
    ).strip()


# ============================================================
# DIAGNOSTICS DE LA TIMELINE
# ============================================================

def _segment_diagnostics(matches):
    """Récupère les diagnostics réels du passage."""

    diagnostics = []

    for item in matches:
        if not isinstance(
            item,
            dict,
        ):
            continue

        value = _first(
            item,
            (
                "diagnostic",
                "probleme",
                "problème",
                "observation",
                "reason",
                "raison",
            ),
            "",
        )

        if value:
            diagnostics.append(
                str(value).strip()
            )

    return _unique(
        diagnostics
    )


# ============================================================
# FENÊTRES AUTOMATIQUES
# ============================================================

def _automatic_windows(duration):
    """
    Découpe toute la vidéo.

    V5.3 :
    - hook plus court ;
    - fenêtres suffisamment fines pour proposer
      des modifications précises ;
    - conclusion isolée.
    """

    duration = max(
        0.0,
        _number(duration),
    )

    if duration <= 0:
        return []

    windows = []

    # --------------------------------------------------------
    # HOOK
    # --------------------------------------------------------

    first_end = min(
        2.0,
        duration,
    )

    windows.append({
        "debut": 0.0,
        "fin": first_end,
        "phase": "HOOK",
    })

    current = first_end
    segment_index = 0

    # --------------------------------------------------------
    # CORPS
    # --------------------------------------------------------

    while current < duration:

        remaining = (
            duration
            -
            current
        )

        if remaining <= 2.5:
            phase = "CONCLUSION"
            end = duration

        else:
            end = min(
                current + 3.0,
                duration,
            )

            phases = (
                "RELANCE",
                "VALEUR",
                "RÉTENTION",
                "PREUVE",
            )

            phase = phases[
                segment_index
                % len(phases)
            ]

        windows.append({
            "debut": round(
                current,
                2,
            ),
            "fin": round(
                end,
                2,
            ),
            "phase": phase,
        })

        current = end
        segment_index += 1

    return windows


# ============================================================
# CORRESPONDANCE TIMELINE / SEGMENTS
# ============================================================

def _find_overlapping_items(
    start,
    end,
    timeline_items,
):
    """Trouve les éléments de timeline du segment."""

    matches = []

    for item in timeline_items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        item_start = _time_value(
            item,
            (
                "debut_secondes",
                "debut",
                "start",
                "temps_debut",
                "start_time",
            ),
            0,
        )

        item_end = _time_value(
            item,
            (
                "fin_secondes",
                "fin",
                "end",
                "temps_fin",
                "end_time",
            ),
            item_start,
        )

        overlap = (
            item_start < end
            and
            item_end > start
        )

        if overlap:
            matches.append(
                item
            )

    return matches


# ============================================================
# PHASE NARRATIVE
# ============================================================

def _phase_from_position(
    start,
    end,
    duration,
):
    """Détermine la fonction narrative du passage."""

    if start < 2:
        return "HOOK"

    if duration <= 0:
        return "RELANCE"

    ratio = (
        start
        /
        duration
    )

    remaining = (
        duration
        -
        start
    )

    if remaining <= 2.5:
        return "CONCLUSION"

    if ratio < 0.25:
        return "RELANCE"

    if ratio < 0.50:
        return "VALEUR"

    if ratio < 0.75:
        return "RÉTENTION"

    return "PREUVE"


# ============================================================
# OBJECTIF DE RÉTENTION
# ============================================================

def _objective_for_phase(phase):

    objectives = {

        "HOOK":
            "Stopper le scroll et communiquer "
            "immédiatement la promesse.",

        "RELANCE":
            "Introduire une variation avant que "
            "l'attention ne baisse.",

        "VALEUR":
            "Livrer rapidement une information "
            "ou un bénéfice concret.",

        "RÉTENTION":
            "Créer une nouvelle raison de continuer "
            "à regarder.",

        "PREUVE":
            "Montrer l'élément le plus convaincant "
            "ou spectaculaire.",

        "CONCLUSION":
            "Terminer sans longueur avec une "
            "action claire.",
    }

    return objectives.get(
        phase,
        "Maintenir l'attention.",
    )
# ============================================================
# TEXTE ECRAN
# ============================================================

def _screen_text_for_phase(
    phase,
    note_hook,
    content="",
):
    """
    Propose un texte écran adapté à la phase.
    """

    content = str(
        content or ""
    ).strip()

    if phase == "HOOK":

        if note_hook < 6:
            return (
                "Affiche immédiatement la question "
                "ou le bénéfice principal."
            )

        return (
            "Affiche la promesse principale "
            "dès la première seconde."
        )

    if phase == "RELANCE":
        return (
            "Ajoute une phrase courte qui relance "
            "la curiosité."
        )

    if phase == "VALEUR":
        return (
            "Résume l'information clé "
            "en 3 à 7 mots."
        )

    if phase == "RÉTENTION":
        return (
            "Ajoute une question ou une promesse "
            "qui donne envie de rester."
        )

    if phase == "PREUVE":
        return (
            "Mets en avant le résultat ou "
            "l'élément le plus fort."
        )

    if phase == "CONCLUSION":
        return (
            "Ajoute un CTA court : enregistrer, "
            "commenter ou partager."
        )

    return ""


# ============================================================
# SCORE DE RETENTION PAR SEGMENT
# ============================================================

def _retention_score(
    phase,
    duration,
    note_hook,
    note_rythme,
    risk_level,
    diagnostics,
):
    """
    Produit un score de rétention estimé sur 100.

    Plus le score est élevé, plus le passage
    est susceptible de retenir le spectateur.
    """

    score = 78.0

    diagnostic_text = " ".join(
        diagnostics
    ).lower()

    # --------------------------------------------------------
    # HOOK
    # --------------------------------------------------------

    if phase == "HOOK":

        score += (
            note_hook - 7
        ) * 4

        if duration > 2.2:
            score -= 8

    # --------------------------------------------------------
    # RYTHME
    # --------------------------------------------------------

    score += (
        note_rythme - 7
    ) * 2.5

    # --------------------------------------------------------
    # LONGUEUR
    # --------------------------------------------------------

    if duration >= 4.0:
        score -= 8

    elif duration >= 3.5:
        score -= 4

    # --------------------------------------------------------
    # RISQUE
    # --------------------------------------------------------

    if risk_level == "eleve":
        score -= 22

    elif risk_level == "moyen":
        score -= 10

    # --------------------------------------------------------
    # DIAGNOSTICS
    # --------------------------------------------------------

    negative_markers = (
        "sans changement",
        "statique",
        "trop long",
        "longtemps",
        "lent",
        "monotone",
        "silence",
        "répétitif",
        "repetitif",
        "faible",
        "ennui",
        "décrochage",
        "decrochage",
    )

    if any(
        marker in diagnostic_text
        for marker in negative_markers
    ):
        score -= 12

    # --------------------------------------------------------
    # PHASE
    # --------------------------------------------------------

    if phase == "VALEUR":
        score += 3

    elif phase == "PREUVE":
        score += 4

    elif phase == "CONCLUSION":
        score -= 2

    return round(
        _clamp(
            score,
            0,
            100,
        ),
        1,
    )


# ============================================================
# GAIN DE RETENTION ESTIME
# ============================================================

def _estimated_retention_gain(
    decision,
    risk_level,
    retention_score,
):
    """
    Estime le gain potentiel après optimisation.
    """

    gain = 0.0

    if decision == "COUPER":
        gain += 10

    elif decision == "RACCOURCIR":
        gain += 7

    elif decision == "ACCÉLÉRER":
        gain += 5

    elif decision == "RENFORCER":
        gain += 4

    elif decision == "CONSERVER":
        gain += 1


    if risk_level == "eleve":
        gain += 4

    elif risk_level == "moyen":
        gain += 2


    if retention_score < 50:
        gain += 3

    elif retention_score < 70:
        gain += 1


    return round(
        _clamp(
            gain,
            0,
            20,
        ),
        1,
    )


# ============================================================
# DECISION DE MONTAGE
# ============================================================

def _editing_decision(
    phase,
    duration,
    note_hook,
    note_rythme,
    risk_level,
    diagnostics,
    retention_score,
):
    """
    Décide quoi faire du segment.

    Valeurs possibles :
    - CONSERVER
    - COUPER
    - RACCOURCIR
    - ACCÉLÉRER
    - RENFORCER
    """

    diagnostic_text = " ".join(
        diagnostics
    ).lower()

    # --------------------------------------------------------
    # RISQUE CRITIQUE
    # --------------------------------------------------------

    if (
        risk_level == "eleve"
        and
        retention_score < 50
    ):
        return "COUPER"

    # --------------------------------------------------------
    # INTRO / HOOK
    # --------------------------------------------------------

    if phase == "HOOK":

        if note_hook < 5:
            return "RACCOURCIR"

        if note_hook < 7:
            return "RENFORCER"

        return "CONSERVER"

    # --------------------------------------------------------
    # SILENCE / LONGUEUR
    # --------------------------------------------------------

    if any(
        marker in diagnostic_text
        for marker in (
            "silence",
            "vide",
            "inutile",
            "répétitif",
            "repetitif",
        )
    ):
        return "COUPER"

    if any(
        marker in diagnostic_text
        for marker in (
            "trop long",
            "longtemps",
            "lent",
            "monotone",
        )
    ):
        return "RACCOURCIR"

    # --------------------------------------------------------
    # RYTHME FAIBLE
    # --------------------------------------------------------

    if (
        note_rythme < 5.5
        and
        duration >= 2.5
    ):
        return "ACCÉLÉRER"

    # --------------------------------------------------------
    # SEGMENT LONG
    # --------------------------------------------------------

    if duration >= 4.0:
        return "RACCOURCIR"

    # --------------------------------------------------------
    # RISQUE MOYEN
    # --------------------------------------------------------

    if risk_level == "moyen":
        return "RENFORCER"

    # --------------------------------------------------------
    # SCORE RETENTION
    # --------------------------------------------------------

    if retention_score < 60:
        return "RENFORCER"

    return "CONSERVER"


# ============================================================
# PROPOSITION DE COUPE PRECISE
# ============================================================

def _cut_proposal(
    start,
    end,
    decision,
    phase,
    risk_level,
):
    """
    Propose une zone à retirer à l'intérieur du segment.

    Cette proposition reste prudente :
    elle ne supprime jamais tout le segment.
    """

    duration = max(
        0.0,
        end - start,
    )

    cut_start = None
    cut_end = None
    removed = 0.0

    # --------------------------------------------------------
    # COUPER
    # --------------------------------------------------------

    if decision == "COUPER":

        removable = min(
            duration * 0.45,
            1.2,
        )

        removable = max(
            0.2,
            removable,
        )

        if phase == "HOOK":

            cut_start = start
            cut_end = min(
                end,
                start + removable,
            )

        else:

            cut_start = max(
                start,
                end - removable,
            )

            cut_end = end

    # --------------------------------------------------------
    # RACCOURCIR
    # --------------------------------------------------------

    elif decision == "RACCOURCIR":

        removable = min(
            duration * 0.25,
            0.8,
        )

        removable = max(
            0.15,
            removable,
        )

        if phase == "HOOK":

            cut_start = start
            cut_end = min(
                end,
                start + removable,
            )

        else:

            cut_start = max(
                start,
                end - removable,
            )

            cut_end = end


    if (
        cut_start is not None
        and
        cut_end is not None
    ):
        removed = max(
            0.0,
            cut_end - cut_start,
        )


    return {
        "coupe_debut":
            round(
                cut_start,
                2,
            )
            if cut_start is not None
            else None,

        "coupe_fin":
            round(
                cut_end,
                2,
            )
            if cut_end is not None
            else None,

        "duree_a_supprimer":
            round(
                removed,
                2,
            ),
    }


# ============================================================
# B-ROLL
# ============================================================

def _b_roll_suggestion(
    phase,
    decision,
    content,
):
    """
    Propose le type de B-roll à ajouter.
    """

    content = str(
        content or ""
    ).strip()

    if phase == "PREUVE":
        return (
            "Ajouter un plan de preuve, un résultat, "
            "un lieu ou un détail visuel fort."
        )

    if phase == "VALEUR":
        return (
            "Ajouter un B-roll illustrant directement "
            "l'information donnée."
        )

    if phase == "RÉTENTION":
        return (
            "Ajouter un changement visuel ou un B-roll "
            "pour relancer l'attention."
        )

    if decision in (
        "RENFORCER",
        "RACCOURCIR",
    ):
        return (
            "Ajouter un plan secondaire pertinent "
            "pendant la phrase principale."
        )

    return ""


# ============================================================
# ACTIONS TECHNIQUES
# ============================================================

def _build_actions(
    phase,
    duration,
    note_hook,
    note_rythme,
    risk_level,
    diagnostics,
    decision,
):
    """
    Construit les actions techniques recommandées.
    """

    actions = []

    diagnostic_text = " ".join(
        diagnostics
    ).lower()


    # --------------------------------------------------------
    # DECISION PRINCIPALE
    # --------------------------------------------------------

    if decision == "COUPER":
        actions.append(
            "CUT"
        )

    elif decision == "RACCOURCIR":
        actions.extend([
            "CUT",
            "RACCOURCIR",
        ])

    elif decision == "ACCÉLÉRER":
        actions.append(
            "ACCÉLÉRER"
        )

    elif decision == "RENFORCER":
        actions.append(
            "RELANCE VISUELLE"
        )

    else:
        actions.append(
            "CONSERVER"
        )


    # --------------------------------------------------------
    # HOOK
    # --------------------------------------------------------

    if phase == "HOOK":

        if note_hook < 6:
            actions.extend([
                "ZOOM 105-110%",
                "TEXTE ÉCRAN",
                "SOUS-TITRES DYNAMIQUES",
            ])

        elif note_hook < 8:
            actions.extend([
                "ZOOM 105-110%",
                "TEXTE ÉCRAN",
            ])


    # --------------------------------------------------------
    # RISQUE
    # --------------------------------------------------------

    if risk_level == "eleve":
        actions.extend([
            "CUT",
            "ZOOM 105-110%",
            "RELANCE VISUELLE",
        ])

    elif risk_level == "moyen":
        actions.append(
            "RELANCE VISUELLE"
        )


    # --------------------------------------------------------
    # DUREE
    # --------------------------------------------------------

    if duration >= 3.5:
        actions.append(
            "CHANGEMENT DE PLAN"
        )


    # --------------------------------------------------------
    # RYTHME
    # --------------------------------------------------------

    if note_rythme < 6:
        actions.append(
            "ACCÉLÉRER"
        )


    # --------------------------------------------------------
    # DIAGNOSTIC
    # --------------------------------------------------------

    if any(
        expression in diagnostic_text
        for expression in (
            "statique",
            "sans changement",
            "monotone",
        )
    ):
        actions.extend([
            "CHANGEMENT DE CADRAGE",
            "RELANCE VISUELLE",
        ])


    # --------------------------------------------------------
    # PHASE
    # --------------------------------------------------------

    if phase == "RELANCE":
        actions.append(
            "CHANGEMENT DE CADRAGE"
        )

    elif phase == "VALEUR":
        actions.extend([
            "TEXTE ÉCRAN",
            "SOUS-TITRES DYNAMIQUES",
        ])

    elif phase == "RÉTENTION":
        actions.extend([
            "CUT",
            "RELANCE VISUELLE",
        ])

    elif phase == "PREUVE":
        actions.append(
            "B-ROLL"
        )

    elif phase == "CONCLUSION":
        actions.extend([
            "ACCÉLÉRER",
            "CTA",
        ])


    actions = _unique(
        actions
    )


    if not actions:
        actions.append(
            "CONSERVER"
        )


    return actions


# ============================================================
# DIAGNOSTIC
# ============================================================

def _build_diagnostic(
    phase,
    matches,
):
    """
    Utilise le diagnostic réel quand disponible.
    """

    diagnostics = _segment_diagnostics(
        matches
    )

    if diagnostics:
        return " ".join(
            diagnostics
        )

    fallbacks = {

        "HOOK":
            "Le début doit communiquer immédiatement "
            "la promesse de la vidéo.",

        "RELANCE":
            "Cette zone doit introduire une nouvelle "
            "variation visuelle.",

        "VALEUR":
            "Le spectateur doit comprendre rapidement "
            "ce qu'il gagne à continuer.",

        "RÉTENTION":
            "Une relance est recommandée pour éviter "
            "une baisse d'attention.",

        "PREUVE":
            "Ce passage doit montrer l'élément visuel "
            "le plus convaincant.",

        "CONCLUSION":
            "La fin doit être courte et mener vers "
            "une action claire.",
    }

    return fallbacks.get(
        phase,
        "Passage à optimiser.",
    )


# ============================================================
# RECOMMANDATION
# ============================================================

def _build_recommendation(
    decision,
    actions,
    phase,
    cut_data,
):
    """
    Transforme la décision de montage
    en recommandation lisible.
    """

    removed = _number(
        cut_data.get(
            "duree_a_supprimer"
        ),
        0,
    )


    if decision == "COUPER":

        if removed > 0:
            return (
                f"Supprimer environ {removed:.2f} s "
                "de ce passage et aller directement "
                "à l'information suivante."
            )

        return (
            "Supprimer ce passage s'il n'apporte "
            "pas de valeur supplémentaire."
        )


    if decision == "RACCOURCIR":

        if removed > 0:
            return (
                f"Raccourcir ce passage d'environ "
                f"{removed:.2f} s pour accélérer "
                "le rythme."
            )

        return (
            "Raccourcir ce passage et conserver "
            "uniquement l'information essentielle."
        )


    if decision == "ACCÉLÉRER":
        return (
            "Accélérer légèrement ce passage, "
            "réduire les pauses et garder "
            "uniquement le mouvement utile."
        )


    if decision == "RENFORCER":

        if phase == "HOOK":
            return (
                "Conserver l'idée d'ouverture mais "
                "renforcer immédiatement la promesse "
                "avec texte écran, zoom ou changement "
                "de cadrage."
            )

        return (
            "Conserver le contenu mais ajouter une "
            "rupture visuelle pour relancer "
            "l'attention."
        )


    if phase == "CONCLUSION":
        return (
            "Conserver la conclusion mais la terminer "
            "rapidement avec un CTA naturel."
        )


    return (
        "Conserver ce passage : son rythme "
        "et sa fonction sont cohérents."
    )


# ============================================================
# NIVEAU DE RISQUE DU SEGMENT
# ============================================================

def _segment_risk(
    matches,
    phase,
):
    """
    Détermine le risque global du segment.
    """

    levels = [
        _risk_level(
            item
        )
        for item in matches
    ]


    if "eleve" in levels:
        return "eleve"


    if "moyen" in levels:
        return "moyen"


    if phase == "HOOK":
        return "moyen"


    return "faible"


# ============================================================
# CREATION DU SEGMENT V5.3
# ============================================================

def _create_segment(
    index,
    start,
    end,
    phase,
    matches,
    note_hook,
    note_rythme,
):
    """
    Construit un segment V5.3 complet.
    """

    duration = max(
        0.0,
        end - start,
    )


    risk_level = _segment_risk(
        matches,
        phase,
    )


    diagnostics = _segment_diagnostics(
        matches
    )


    content = _segment_content(
        matches
    )


    retention_score = _retention_score(
        phase=phase,
        duration=duration,
        note_hook=note_hook,
        note_rythme=note_rythme,
        risk_level=risk_level,
        diagnostics=diagnostics,
    )


    decision = _editing_decision(
        phase=phase,
        duration=duration,
        note_hook=note_hook,
        note_rythme=note_rythme,
        risk_level=risk_level,
        diagnostics=diagnostics,
        retention_score=retention_score,
    )


    cut_data = _cut_proposal(
        start=start,
        end=end,
        decision=decision,
        phase=phase,
        risk_level=risk_level,
    )


    actions = _build_actions(
        phase=phase,
        duration=duration,
        note_hook=note_hook,
        note_rythme=note_rythme,
        risk_level=risk_level,
        diagnostics=diagnostics,
        decision=decision,
    )


    diagnostic = _build_diagnostic(
        phase,
        matches,
    )


    recommendation = _build_recommendation(
        decision=decision,
        actions=actions,
        phase=phase,
        cut_data=cut_data,
    )


    objective = _objective_for_phase(
        phase
    )


    text_screen = _screen_text_for_phase(
        phase=phase,
        note_hook=note_hook,
        content=content,
    )


    b_roll = _b_roll_suggestion(
        phase=phase,
        decision=decision,
        content=content,
    )


    retention_gain = (
        _estimated_retention_gain(
            decision=decision,
            risk_level=risk_level,
            retention_score=retention_score,
        )
    )


    return {
        "ordre":
            index + 1,

        "debut":
            round(
                start,
                2,
            ),

        "fin":
            round(
                end,
                2,
            ),

        "debut_secondes":
            round(
                start,
                2,
            ),

        "fin_secondes":
            round(
                end,
                2,
            ),

        "duree_secondes":
            round(
                duration,
                2,
            ),

        "timecode":
            (
                f"{_format_time(start)}"
                f" → "
                f"{_format_time(end)}"
            ),

        "timecode_court":
            (
                f"{_format_time_short(start)}"
                f" → "
                f"{_format_time_short(end)}"
            ),

        "phase":
            phase,

        "type":
            phase,

        "decision":
            decision,

        "contenu_segment":
            content,

        "objectif":
            objective,

        "objectif_retention":
            objective,

        "diagnostic":
            diagnostic,

        "score_retention":
            retention_score,

        "gain_retention_estime":
            retention_gain,

        "actions":
            actions,

        "action":
            recommendation,

        "recommandation":
            recommendation,

        "texte_ecran":
            text_screen,

        "b_roll":
            b_roll,

        "coupe_debut":
            cut_data.get(
                "coupe_debut"
            ),

        "coupe_fin":
            cut_data.get(
                "coupe_fin"
            ),

        "duree_a_supprimer":
            cut_data.get(
                "duree_a_supprimer"
            ),

        "niveau_risque":
            _risk_label(
                risk_level
            ),

        "priorite":
            _risk_label(
                risk_level
            ),

        "source_timeline":
            bool(
                matches
            ),
    }
# ============================================================
# GENERATION A PARTIR DE LA TIMELINE REELLE
# ============================================================

def _timeline_segments(
    timeline_items,
    duration,
    note_hook,
    note_rythme,
):
    """
    Transforme la timeline existante
    en segments V5.3.
    """

    result = []

    sorted_items = sorted(
        [
            item
            for item in timeline_items
            if isinstance(
                item,
                dict,
            )
        ],
        key=lambda item: _time_value(
            item,
            (
                "debut_secondes",
                "debut",
                "start",
                "temps_debut",
                "start_time",
            ),
            0,
        ),
    )


    for index, item in enumerate(
        sorted_items
    ):

        start = _time_value(
            item,
            (
                "debut_secondes",
                "debut",
                "start",
                "temps_debut",
                "start_time",
            ),
            0,
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


        if end <= start:
            continue


        phase = _phase_from_position(
            start,
            end,
            duration,
        )


        segment = _create_segment(
            index=index,
            start=start,
            end=end,
            phase=phase,
            matches=[item],
            note_hook=note_hook,
            note_rythme=note_rythme,
        )


        result.append(
            segment
        )


    return result


# ============================================================
# GENERATION COMPLETE SUR TOUTE LA VIDEO
# ============================================================

def _full_video_segments(
    duration,
    timeline_items,
    note_hook,
    note_rythme,
):
    """
    Génère un plan V5.3 couvrant
    toute la durée de la vidéo.
    """

    windows = _automatic_windows(
        duration
    )


    result = []


    for index, window in enumerate(
        windows
    ):

        start = window[
            "debut"
        ]


        end = window[
            "fin"
        ]


        phase = window[
            "phase"
        ]


        matches = _find_overlapping_items(
            start,
            end,
            timeline_items,
        )


        segment = _create_segment(
            index=index,
            start=start,
            end=end,
            phase=phase,
            matches=matches,
            note_hook=note_hook,
            note_rythme=note_rythme,
        )


        result.append(
            segment
        )


    return result


# ============================================================
# ACTIONS PRIORITAIRES
# ============================================================

def _priority_actions(
    segments,
):
    """
    Construit une synthèse des passages
    à modifier en priorité.
    """

    result = []


    for segment in segments:

        level = str(
            segment.get(
                "niveau_risque",
                "",
            )
        ).lower()


        decision = str(
            segment.get(
                "decision",
                "",
            )
        ).upper()


        important = (
            "élev" in level
            or
            "ele" in level
            or
            "moy" in level
            or
            decision in (
                "COUPER",
                "RACCOURCIR",
                "ACCÉLÉRER",
            )
            or
            segment.get(
                "phase"
            ) == "HOOK"
        )


        if not important:
            continue


        result.append({

            "timecode":
                segment.get(
                    "timecode"
                ),

            "phase":
                segment.get(
                    "phase"
                ),

            "decision":
                segment.get(
                    "decision"
                ),

            "actions":
                _as_list(
                    segment.get(
                        "actions"
                    )
                ),

            "action":
                segment.get(
                    "recommandation"
                ),

            "raison":
                segment.get(
                    "diagnostic"
                ),

            "score_retention":
                segment.get(
                    "score_retention"
                ),

            "gain_retention_estime":
                segment.get(
                    "gain_retention_estime"
                ),

            "priorite":
                segment.get(
                    "niveau_risque"
                ),
        })


    return result


# ============================================================
# STATISTIQUES DE MONTAGE
# ============================================================

def _strategy_summary(
    segments,
):
    """
    Produit les indicateurs stratégiques V5.3.
    """

    total = len(
        segments
    )

    cuts = 0
    shorten = 0
    accelerate = 0
    reinforce = 0
    keep = 0

    zooms = 0
    b_rolls = 0
    text_actions = 0
    subtitles = 0

    high_risks = 0

    retention_scores = []
    retention_gains = []

    removed_duration = 0.0


    for segment in segments:

        decision = str(
            segment.get(
                "decision",
                ""
            )
        ).upper()


        if decision == "COUPER":
            cuts += 1

        elif decision == "RACCOURCIR":
            shorten += 1

        elif decision == "ACCÉLÉRER":
            accelerate += 1

        elif decision == "RENFORCER":
            reinforce += 1

        elif decision == "CONSERVER":
            keep += 1


        actions = _as_list(
            segment.get(
                "actions"
            )
        )


        if any(
            "ZOOM" in str(action)
            for action in actions
        ):
            zooms += 1


        if "B-ROLL" in actions:
            b_rolls += 1


        if "TEXTE ÉCRAN" in actions:
            text_actions += 1


        if "SOUS-TITRES DYNAMIQUES" in actions:
            subtitles += 1


        level = str(
            segment.get(
                "niveau_risque",
                "",
            )
        ).lower()


        if (
            "élev" in level
            or
            "ele" in level
        ):
            high_risks += 1


        score = _number(
            segment.get(
                "score_retention"
            ),
            -1,
        )

        if score >= 0:
            retention_scores.append(
                score
            )


        gain = _number(
            segment.get(
                "gain_retention_estime"
            ),
            0,
        )

        retention_gains.append(
            gain
        )


        removed_duration += _number(
            segment.get(
                "duree_a_supprimer"
            ),
            0,
        )


    average_retention = (
        sum(retention_scores)
        /
        len(retention_scores)
        if retention_scores
        else 0
    )


    average_gain = (
        sum(retention_gains)
        /
        len(retention_gains)
        if retention_gains
        else 0
    )


    return {

        "segments":
            total,

        "decisions": {

            "conserver":
                keep,

            "couper":
                cuts,

            "raccourcir":
                shorten,

            "accelerer":
                accelerate,

            "renforcer":
                reinforce,
        },

        "zooms_recommandes":
            zooms,

        "b_rolls_recommandes":
            b_rolls,

        "textes_ecran_recommandes":
            text_actions,

        "sous_titres_dynamiques":
            subtitles,

        "segments_prioritaires":
            high_risks,

        "score_retention_moyen":
            round(
                average_retention,
                1,
            ),

        "gain_retention_moyen_estime":
            round(
                average_gain,
                1,
            ),

        "duree_totale_a_supprimer":
            round(
                removed_duration,
                2,
            ),
    }


# ============================================================
# MEILLEUR HOOK CANDIDAT
# ============================================================

def _best_hook_candidate(
    segments,
):
    """
    Recherche dans la vidéo le segment
    ayant le meilleur potentiel pour servir
    éventuellement d'ouverture.
    """

    candidates = []


    for segment in segments:

        score = _number(
            segment.get(
                "score_retention"
            ),
            0,
        )


        phase = segment.get(
            "phase"
        )


        risk = str(
            segment.get(
                "niveau_risque",
                ""
            )
        ).lower()


        if (
            "élev" in risk
            or
            "ele" in risk
        ):
            continue


        bonus = 0


        if phase == "PREUVE":
            bonus += 8

        elif phase == "VALEUR":
            bonus += 6

        elif phase == "RELANCE":
            bonus += 3


        content = str(
            segment.get(
                "contenu_segment"
                ""
            )
        ).strip()


        if content:
            bonus += 3


        candidates.append(
            (
                score + bonus,
                segment,
            )
        )


    if not candidates:
        return None


    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )


    best = candidates[0][1]


    return {

        "timecode":
            best.get(
                "timecode"
            ),

        "phase":
            best.get(
                "phase"
            ),

        "score_retention":
            best.get(
                "score_retention"
            ),

        "contenu_segment":
            best.get(
                "contenu_segment"
            ),

        "suggestion":
            (
                "Tester ce passage en ouverture "
                "si son image ou sa phrase est "
                "plus forte que le hook actuel."
            ),
    }


# ============================================================
# DUREE ESTIMEE APRES REMONTAGE
# ============================================================

def _estimated_final_duration(
    duration,
    segments,
):
    """
    Estime la durée finale après les
    suppressions proposées.
    """

    removed = sum(
        _number(
            segment.get(
                "duree_a_supprimer"
            ),
            0,
        )
        for segment in segments
    )


    final_duration = max(
        0.0,
        duration - removed,
    )


    return {
        "duree_originale":
            round(
                duration,
                2,
            ),

        "duree_supprimee":
            round(
                removed,
                2,
            ),

        "duree_finale_estimee":
            round(
                final_duration,
                2,
            ),
    }


# ============================================================
# ANALYSE PRINCIPALE
# ============================================================

def analyze_remontage(
    analyse_decoupage,
    analyse_transcription,
    analyse_montage,
):
    """
    ViralCoach AI V5.3

    Le moteur :
    1. récupère la timeline réelle ;
    2. détermine la durée vidéo ;
    3. découpe toute la vidéo ;
    4. croise les passages réels ;
    5. estime la rétention de chaque segment ;
    6. prend une décision de montage ;
    7. propose des coupes précises ;
    8. propose texte écran / B-roll / actions ;
    9. estime le gain potentiel ;
    10. produit le plan final exploitable.
    """

    analyse_decoupage = (
        analyse_decoupage
        or {}
    )


    analyse_transcription = (
        analyse_transcription
        or {}
    )


    analyse_montage = (
        analyse_montage
        or {}
    )


    # --------------------------------------------------------
    # TIMELINE
    # --------------------------------------------------------

    timeline = analyse_decoupage.get(
        "timeline",
        [],
    )


    items = _timeline_items(
        timeline
    )


    # --------------------------------------------------------
    # NOTES
    # --------------------------------------------------------

    note_hook = _number(
        _first(
            analyse_transcription,
            (
                "note_hook",
                "hook_score",
            ),
            0,
        )
    )


    note_rythme = _number(
        _first(
            analyse_montage,
            (
                "note_rythme",
                "note_montage",
                "rythme",
            ),
            0,
        )
    )


    # --------------------------------------------------------
    # DUREE VIDEO
    # --------------------------------------------------------

    duration = _video_duration(
        analyse_decoupage,
        analyse_montage,
        items,
    )


    # --------------------------------------------------------
    # MODE TIMELINE UNIQUEMENT
    # --------------------------------------------------------

    if duration <= 0:

        timeline_plan = _timeline_segments(
            timeline_items=items,
            duration=0,
            note_hook=note_hook,
            note_rythme=note_rythme,
        )


        actions_prioritaires = (
            _priority_actions(
                timeline_plan
            )
        )


        strategie = (
            _strategy_summary(
                timeline_plan
            )
        )


        return {

            "version":
                "5.3",

            "mode":
                "timeline_only",

            "duration_seconds":
                0,

            "nombre_segments":
                len(
                    timeline_plan
                ),

            "segments":
                timeline_plan,

            "actions_prioritaires":
                actions_prioritaires,

            "strategie":
                strategie,

            "meilleur_hook_candidat":
                _best_hook_candidate(
                    timeline_plan
                ),

            "resume":
                (
                    f"{len(timeline_plan)} "
                    "segments analysés par "
                    "ViralCoach V5.3."
                ),
        }


    # --------------------------------------------------------
    # PLAN COMPLET
    # --------------------------------------------------------

    plan = _full_video_segments(
        duration=duration,
        timeline_items=items,
        note_hook=note_hook,
        note_rythme=note_rythme,
    )


    # --------------------------------------------------------
    # SYNTHESE
    # --------------------------------------------------------

    actions_prioritaires = (
        _priority_actions(
            plan
        )
    )


    strategie = (
        _strategy_summary(
            plan
        )
    )


    meilleur_hook = (
        _best_hook_candidate(
            plan
        )
    )


    duration_estimate = (
        _estimated_final_duration(
            duration,
            plan,
        )
    )


    # --------------------------------------------------------
    # RESULTAT FINAL
    # --------------------------------------------------------

    return {

        "version":
            "5.3",

        "mode":
            "full_timeline",

        "duration_seconds":
            round(
                duration,
                2,
            ),

        "nombre_segments":
            len(
                plan
            ),

        "segments":
            plan,

        "actions_prioritaires":
            actions_prioritaires,

        "strategie":
            strategie,

        "meilleur_hook_candidat":
            meilleur_hook,

        "duree_apres_remontage":
            duration_estimate,

        "resume":
            (
                f"{len(plan)} segments générés "
                f"sur {duration:.1f} secondes, "
                f"{len(actions_prioritaires)} "
                "actions prioritaires, "
                f"{strategie.get('duree_totale_a_supprimer', 0):.2f} s "
                "de coupe potentielle."
            ),
    }