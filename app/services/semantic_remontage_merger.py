"""
ViralCoach AI V5.4
Fusion du plan de remontage V5.3 avec l'analyse sémantique V5.4.

Ce module ne remplace pas le moteur V5.3.
Il prend son plan temporel déjà fonctionnel et enrichit chaque segment
avec les décisions issues de l'analyse sémantique Gemini.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


DECISION_ACTIONS = {
    "CONSERVER": [],
    "COUPER": ["CUT"],
    "RACCOURCIR": ["CUT"],
    "ACCÉLÉRER": ["ACCÉLÉRER"],
    "RENFORCER": ["RELANCE VISUELLE"],
}


def _as_list(value: Any) -> list:
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    return [value]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _number(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def _unique(values: list) -> list:
    result = []
    seen = set()

    for value in values:
        text = _clean_text(value)

        if not text:
            continue

        key = text.upper()

        if key in seen:
            continue

        seen.add(key)
        result.append(text)

    return result


def _normalize_decision(value: Any) -> str:
    decision = _clean_text(value).upper()

    aliases = {
        "ACCELERER": "ACCÉLÉRER",
        "ACCÉLÉRER": "ACCÉLÉRER",
        "RACCOURCIR": "RACCOURCIR",
        "COUPER": "COUPER",
        "CONSERVER": "CONSERVER",
        "RENFORCER": "RENFORCER",
    }

    return aliases.get(
        decision,
        "RENFORCER",
    )


def _semantic_by_order(
    analyse_semantique: dict,
) -> dict[int, dict]:
    result = {}

    for item in _as_list(
        analyse_semantique.get(
            "segments"
        )
    ):
        if not isinstance(item, dict):
            continue

        order = int(
            _number(
                item.get("ordre"),
                0,
            )
        )

        if order <= 0:
            continue

        result[order] = item

    return result


def _merge_actions(
    current_actions: Any,
    semantic: dict,
    decision: str,
) -> list:
    actions = list(
        _as_list(
            current_actions
        )
    )

    # La décision sémantique devient l'action principale.
    actions.extend(
        DECISION_ACTIONS.get(
            decision,
            [],
        )
    )

    if _clean_text(
        semantic.get("b_roll")
    ):
        actions.append(
            "B-ROLL"
        )

    if _clean_text(
        semantic.get("texte_ecran")
    ):
        actions.append(
            "TEXTE ÉCRAN"
        )

    # Évite qu'un ancien CUT V5.3 reste présent si Gemini
    # décide finalement de conserver ou renforcer le passage.
    if decision in {
        "CONSERVER",
        "RENFORCER",
        "ACCÉLÉRER",
    }:
        actions = [
            action
            for action in actions
            if _clean_text(action).upper()
            != "CUT"
        ]

    return _unique(
        actions
    )


def _merge_segment(
    segment: dict,
    semantic: dict,
) -> dict:
    merged = deepcopy(
        segment
    )

    decision = _normalize_decision(
        semantic.get(
            "decision",
            merged.get(
                "decision",
                "RENFORCER",
            ),
        )
    )

    merged["decision_v5_3"] = (
        merged.get("decision")
    )

    merged["decision"] = decision
    merged["decision_semantique"] = decision

    content = _clean_text(
        semantic.get(
            "contenu_segment"
        )
    )

    if content:
        merged["contenu_segment"] = content

    message_key = _clean_text(
        semantic.get(
            "message_cle"
        )
    )

    if message_key:
        merged["message_cle"] = message_key

    diagnostic = _clean_text(
        semantic.get(
            "diagnostic_semantique"
        )
    )

    if diagnostic:
        merged["diagnostic_v5_3"] = (
            merged.get("diagnostic")
        )

        merged["diagnostic"] = diagnostic
        merged["diagnostic_semantique"] = diagnostic

    problem = _clean_text(
        semantic.get(
            "probleme"
        )
    )

    if problem:
        merged["probleme_semantique"] = problem

    recommendation = _clean_text(
        semantic.get(
            "action_montage"
        )
    )

    if recommendation:
        merged["recommandation_v5_3"] = (
            merged.get("recommandation")
        )

        merged["recommandation"] = recommendation
        merged["action"] = recommendation
        merged["action_semantique"] = recommendation

    b_roll = _clean_text(
        semantic.get(
            "b_roll"
        )
    )

    if b_roll:
        merged["b_roll"] = b_roll

    text_screen = _clean_text(
        semantic.get(
            "texte_ecran"
        )
    )

    if text_screen:
        merged["texte_ecran"] = text_screen

    semantic_score = _number(
        semantic.get(
            "score_interet"
        ),
        0,
    )

    if semantic_score > 0:
        merged["score_semantique"] = round(
            semantic_score,
            1,
        )

    semantic_gain = _number(
        semantic.get(
            "gain_retention_estime"
        ),
        0,
    )

    if semantic_gain > 0:
        merged[
            "gain_retention_estime_v5_3"
        ] = merged.get(
            "gain_retention_estime"
        )

        merged[
            "gain_retention_estime"
        ] = round(
            semantic_gain,
            1,
        )

    merged["valeur_information"] = (
        _clean_text(
            semantic.get(
                "valeur_information"
            )
        )
        or "MOYENNE"
    )

    merged["hook_potentiel"] = bool(
        semantic.get(
            "hook_potentiel",
            False,
        )
    )

    merged["phrase_hook"] = _clean_text(
        semantic.get(
            "phrase_hook"
        )
    )

    merged["raison_hook"] = _clean_text(
        semantic.get(
            "raison_hook"
        )
    )

    merged["actions"] = _merge_actions(
        merged.get("actions"),
        semantic,
        decision,
    )

    merged["source_semantique"] = True

    return merged


def _best_semantic_hook(
    plan: list[dict],
    analyse_semantique: dict,
    fallback_hook: Any,
) -> Any:
    hook = analyse_semantique.get(
        "meilleur_hook"
    )

    if not isinstance(hook, dict):
        return fallback_hook

    order = int(
        _number(
            hook.get("ordre"),
            0,
        )
    )

    phrase = _clean_text(
        hook.get("phrase")
    )

    reason = _clean_text(
        hook.get("raison")
    )

    score = _number(
        hook.get("score"),
        0,
    )

    if order <= 0 and not phrase:
        return fallback_hook

    selected = None

    for segment in plan:
        if int(
            _number(
                segment.get("ordre"),
                0,
            )
        ) == order:
            selected = segment
            break

    if selected is None:
        selected = {}

    return {
        "ordre": order,
        "timecode": selected.get(
            "timecode",
            "",
        ),
        "phase": selected.get(
            "phase",
            "",
        ),
        "score_retention": (
            score
            or selected.get(
                "score_retention",
                0,
            )
        ),
        "score_semantique": selected.get(
            "score_semantique",
            score,
        ),
        "contenu_segment": (
            phrase
            or selected.get(
                "contenu_segment",
                "",
            )
        ),
        "phrase_hook": phrase,
        "raison": reason,
        "suggestion": (
            reason
            or "Tester ce passage en ouverture."
        ),
        "source": "semantic_v5_4",
    }


def _semantic_strategy(
    plan: list[dict],
    base_strategy: dict,
) -> dict:
    strategy = deepcopy(
        base_strategy
        or {}
    )

    decisions = {
        "conserver": 0,
        "couper": 0,
        "raccourcir": 0,
        "accelerer": 0,
        "renforcer": 0,
    }

    semantic_scores = []
    semantic_gains = []
    b_roll_count = 0

    for segment in plan:
        decision = _normalize_decision(
            segment.get(
                "decision"
            )
        )

        key = (
            decision
            .lower()
            .replace(
                "é",
                "e",
            )
        )

        if key in decisions:
            decisions[key] += 1

        score = _number(
            segment.get(
                "score_semantique"
            ),
            0,
        )

        if score > 0:
            semantic_scores.append(
                score
            )

        gain = _number(
            segment.get(
                "gain_retention_estime"
            ),
            0,
        )

        if gain > 0:
            semantic_gains.append(
                gain
            )

        if _clean_text(
            segment.get(
                "b_roll"
            )
        ):
            b_roll_count += 1

    strategy["decisions"] = decisions

    strategy[
        "score_semantique_moyen"
    ] = (
        round(
            sum(semantic_scores)
            / len(semantic_scores),
            1,
        )
        if semantic_scores
        else 0
    )

    strategy[
        "gain_retention_semantique_moyen"
    ] = (
        round(
            sum(semantic_gains)
            / len(semantic_gains),
            1,
        )
        if semantic_gains
        else 0
    )

    strategy[
        "b_rolls_contextualises"
    ] = b_roll_count

    return strategy


def merge_semantic_remontage(
    analyse_remontage: dict,
    analyse_semantique: dict,
) -> dict:
    """
    Fusionne le plan V5.3 avec les résultats Gemini V5.4.

    Retourne une nouvelle structure complète sous version 5.4.
    """

    base = deepcopy(
        analyse_remontage
        or {}
    )

    semantic = (
        analyse_semantique
        or {}
    )

    base_segments = _as_list(
        base.get(
            "segments"
        )
    )

    semantic_map = _semantic_by_order(
        semantic
    )

    merged_segments = []

    for index, segment in enumerate(
        base_segments
    ):
        if not isinstance(segment, dict):
            continue

        order = int(
            _number(
                segment.get(
                    "ordre",
                    index + 1,
                ),
                index + 1,
            )
        )

        semantic_segment = semantic_map.get(
            order
        )

        if semantic_segment:
            merged = _merge_segment(
                segment,
                semantic_segment,
            )
        else:
            merged = deepcopy(
                segment
            )
            merged[
                "source_semantique"
            ] = False

        merged_segments.append(
            merged
        )

    base["version"] = "5.4"
    base["mode"] = "semantic_remontage"
    base["segments"] = merged_segments
    base["nombre_segments"] = len(
        merged_segments
    )

    base["semantic_fallback"] = bool(
        semantic.get(
            "fallback",
            False,
        )
    )

    base["semantic_model"] = (
        semantic.get(
            "model"
        )
    )

    base["resume_semantique"] = (
        semantic.get(
            "resume_semantique",
            "",
        )
    )

    base["strategie"] = (
        _semantic_strategy(
            merged_segments,
            base.get(
                "strategie",
                {},
            ),
        )
    )

    base["meilleur_hook_candidat"] = (
        _best_semantic_hook(
            merged_segments,
            semantic,
            base.get(
                "meilleur_hook_candidat"
            ),
        )
    )

    base["analyse_semantique"] = semantic

    base["resume"] = (
        f"{len(merged_segments)} segments fusionnés en V5.4 "
        f"avec analyse sémantique "
        f"({'fallback local' if base['semantic_fallback'] else 'Gemini'})."
    )

    return base
