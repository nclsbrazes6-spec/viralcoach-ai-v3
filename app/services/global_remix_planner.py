from __future__ import annotations

import json
import os
import re
from typing import Any


DEFAULT_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite",
).strip()


# ============================================================
# OUTILS
# ============================================================

def _clean_text(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


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

        match = re.search(
            r"-?\d+(?:\.\d+)?",
            text,
        )

        if not match:
            return default

        return float(
            match.group(0)
        )

    except Exception:
        return default


def _json_from_text(
    text: str,
) -> dict:

    if not text:
        raise ValueError(
            "Réponse Gemini vide."
        )

    cleaned = (
        str(text)
        .strip()
        .lstrip("\ufeff")
    )

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    try:

        result = json.loads(
            cleaned
        )

        if isinstance(
            result,
            dict,
        ):
            return result

    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()

    for index, char in enumerate(
        cleaned
    ):

        if char != "{":
            continue

        try:

            result, _ = (
                decoder.raw_decode(
                    cleaned[index:]
                )
            )

            if isinstance(
                result,
                dict,
            ):
                return result

        except json.JSONDecodeError:
            continue

    raise ValueError(
        "Impossible de parser "
        "le plan global Gemini."
    )


# ============================================================
# GEMINI
# ============================================================

def _gemini_generate(
    prompt: str,
    model_name: str,
) -> str:

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY absente."
        )

    try:
        from google import genai
        from google.genai import types

    except ImportError as error:
        raise RuntimeError(
            "SDK google-genai introuvable."
        ) from error

    client = genai.Client(
        api_key=api_key
    )

    response = (
        client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.12,
                response_mime_type=(
                    "application/json"
                ),
                max_output_tokens=8192,
            ),
        )
    )

    text = getattr(
        response,
        "text",
        None,
    )

    if not text:
        raise RuntimeError(
            "Gemini n'a renvoyé "
            "aucun plan de montage."
        )

    return str(
        text
    ).strip()


# ============================================================
# PROMPT GLOBAL
# ============================================================

def _build_prompt(
    semantic_analysis: dict,
    technical_remontage: dict,
    duration_seconds: float,
) -> str:

    semantic_segments = (
        semantic_analysis.get(
            "segments",
            [],
        )
    )

    technical_segments = (
        technical_remontage.get(
            "segments",
            [],
        )
    )

    best_hook = (
        semantic_analysis.get(
            "meilleur_hook",
            {},
        )
    )

    semantic_json = json.dumps(
        semantic_segments,
        ensure_ascii=False,
        indent=2,
    )

    technical_json = json.dumps(
        technical_segments,
        ensure_ascii=False,
        indent=2,
    )

    hook_json = json.dumps(
        best_hook,
        ensure_ascii=False,
        indent=2,
    )

    target_min = (
        duration_seconds
        * 0.60
    )

    target_max = (
        duration_seconds
        * 0.80
    )

    return f"""
Tu es le MONTEUR EN CHEF de ViralCoach AI.

Tu dois créer UN PLAN GLOBAL DE REMONTAGE
pour une vidéo TikTok / Reels / Shorts.

Tu dois améliorer réellement :
- le hook ;
- le rythme ;
- la rétention ;
- la compréhension ;
- la fluidité.

Tu ne dois PAS simplement ajouter des effets.

DURÉE ORIGINALE :
{duration_seconds:.2f} secondes

DURÉE FINALE RECHERCHÉE :
entre {target_min:.2f} et {target_max:.2f} secondes.

Si une réduction aussi forte coupe une phrase
ou détruit le storytelling,
tu peux conserver légèrement plus.

MEILLEUR HOOK SÉMANTIQUE :
{hook_json}

ANALYSE SÉMANTIQUE :
{semantic_json}

ANALYSE TECHNIQUE :
{technical_json}


============================================================
RÈGLES DE REMONTAGE V3.1
============================================================

HOOK

- Les 1,5 premières secondes doivent être immédiatement compréhensibles.
- Le meilleur hook doit être placé en premier.
- Supprime les hésitations et amorces faibles avant le hook.
- Le hook peut recevoir un texte écran court.

COUPES

- Supprime réellement les silences, hésitations, répétitions et longueurs.
- Si un passage n'apporte rien, supprime-le.
- Ne te contente pas d'accélérer un passage inutile.
- RACCOURCIR doit retirer une vraie partie du segment.
- Les timecodes doivent être précis.

PAROLES

- Ne coupe jamais un mot au milieu.
- Ne coupe jamais une phrase si le sens devient incompréhensible.
- Préserve la synchronisation naturelle de la voix.

STORYTELLING

- Fais arriver le bénéfice ou la valeur forte le plus tôt possible.
- Ordre recommandé :
  hook → valeur → preuve → conclusion / CTA.
- Tu peux réorganiser les passages uniquement
  si cela améliore réellement le storytelling.
- Ne duplique jamais un passage.

TEXTES ÉCRAN

- Maximum 3 textes sur toute la vidéo.
- Priorité 1 : hook.
- Priorité 2 : moment de valeur principal.
- Priorité 3 : CTA final.
- Les autres plans doivent rester naturels.
- Le texte doit être court.
- Pas de phrase longue à l'écran.

ZOOMS

- Maximum 2 zooms sur toute la vidéo.
- Zoom maximum : 1.12.
- Un seul zoom fort sur le moment visuel principal.
- Si le zoom n'apporte rien, laisse 1.0.

VITESSE

- Vitesse normale par défaut : 1.0.
- Accélération légère possible :
  entre 1.05 et 1.15.
- Maximum absolu : 1.20.
- N'accélère pas une voix si cela devient artificiel.

TRANSITIONS

- Utilise principalement "cut".
- Pas de transitions décoratives inutiles.
- Un fondu léger est éventuellement autorisé
  sur la conclusion.

IMPORTANT

- montage_final contient uniquement
  les passages réellement gardés.
- segments_supprimes décrit ce qui a été retiré.
- ordre_final est l'ordre réel du MP4 final.
- debut_source et fin_source correspondent
  aux secondes de la vidéo originale.
- Le plan doit être directement utilisable par FFmpeg.


============================================================
FORMAT JSON OBLIGATOIRE
============================================================

Réponds UNIQUEMENT avec un JSON valide :

{{
  "version": "5.5-remix-v3.1",

  "strategie_globale": "",

  "hook_final": {{
    "ordre_source": 1,
    "texte": "",
    "raison": ""
  }},

  "montage_final": [
    {{
      "ordre_final": 1,

      "ordre_source": 1,

      "debut_source": 0.0,

      "fin_source": 1.2,

      "decision": "RACCOURCIR",

      "raison": "",

      "vitesse": 1.0,

      "zoom": 1.0,

      "texte_ecran": "",

      "position_texte": "centre",

      "transition": "cut"
    }}
  ],

  "segments_supprimes": [
    {{
      "ordre_source": 1,
      "raison": ""
    }}
  ],

  "duree_originale": {duration_seconds:.2f},

  "duree_finale_estimee": 0.0,

  "gain_retention_estime": 0,

  "resume": ""
}}
""".strip()


# ============================================================
# NORMALISATION DU PLAN
# ============================================================

def _normalize_plan(
    raw_plan: dict,
    duration_seconds: float,
) -> dict:

    raw_segments = raw_plan.get(
        "montage_final",
        [],
    )

    if not isinstance(
        raw_segments,
        list,
    ):
        raw_segments = []

    final_segments = []

    # --------------------------------------------------------
    # NORMALISATION DES SEGMENTS
    # --------------------------------------------------------

    for index, segment in enumerate(
        raw_segments,
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

        end = min(
            max(
                start,
                end,
            ),
            duration_seconds,
        )

        if end <= start:
            continue

        # ----------------------------------------------------
        # VITESSE
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # ZOOM
        # ----------------------------------------------------

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

        final_segments.append(
            {
                "ordre_final": index,

                "ordre_source": int(
                    _number(
                        segment.get(
                            "ordre_source"
                        ),
                        index,
                    )
                ),

                "debut_source": round(
                    start,
                    3,
                ),

                "fin_source": round(
                    end,
                    3,
                ),

                "decision": (
                    _clean_text(
                        segment.get(
                            "decision"
                        )
                    ).upper()
                    or "CONSERVER"
                ),

                "raison": _clean_text(
                    segment.get(
                        "raison"
                    )
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
                    _clean_text(
                        segment.get(
                            "texte_ecran"
                        )
                    )
                ),

                "position_texte": (
                    _clean_text(
                        segment.get(
                            "position_texte"
                        )
                    ).lower()
                    or "centre"
                ),

                "transition": (
                    _clean_text(
                        segment.get(
                            "transition"
                        )
                    ).lower()
                    or "cut"
                ),
            }
        )

    # ========================================================
    # LIMITATION DES TEXTES
    # ========================================================

    if final_segments:

        text_candidates = []

        total_segments = len(
            final_segments
        )

        for segment in final_segments:

            text = _clean_text(
                segment.get(
                    "texte_ecran"
                )
            )

            if not text:
                continue

            score = 0

            ordre_final = int(
                _number(
                    segment.get(
                        "ordre_final"
                    ),
                    0,
                )
            )

            decision = (
                _clean_text(
                    segment.get(
                        "decision"
                    )
                ).upper()
            )

            zoom = _number(
                segment.get(
                    "zoom"
                ),
                1.0,
            )

            # Hook
            if ordre_final == 1:
                score += 100

            # Moment à renforcer
            if decision == "RENFORCER":
                score += 60

            # Moment visuel important
            if zoom >= 1.08:
                score += 45

            # CTA final
            if (
                ordre_final
                == total_segments
            ):
                score += 65

            text_candidates.append(
                (
                    score,
                    ordre_final,
                    segment,
                )
            )

        text_candidates.sort(
            key=lambda item: (
                item[0],
                -item[1],
            ),
            reverse=True,
        )

        allowed_text_ids = {
            id(item[2])
            for item
            in text_candidates[:3]
        }

        for segment in final_segments:

            if (
                segment.get(
                    "texte_ecran"
                )
                and id(segment)
                not in allowed_text_ids
            ):
                segment[
                    "texte_ecran"
                ] = ""

        # ----------------------------------------------------
        # FORCE LE HOOK SUR LE PREMIER PLAN
        # ----------------------------------------------------

        hook_final = raw_plan.get(
            "hook_final",
            {},
        )

        if isinstance(
            hook_final,
            dict,
        ):

            hook_text = _clean_text(
                hook_final.get(
                    "texte"
                )
            )

            if hook_text:

                final_segments[0][
                    "texte_ecran"
                ] = hook_text

    # ========================================================
    # LIMITATION DES ZOOMS
    # ========================================================

    if final_segments:

        zoom_candidates = []

        for segment in final_segments:

            zoom = _number(
                segment.get(
                    "zoom"
                ),
                1.0,
            )

            if zoom <= 1.001:
                continue

            score = (
                zoom - 1.0
            ) * 100

            ordre_final = int(
                _number(
                    segment.get(
                        "ordre_final"
                    ),
                    0,
                )
            )

            decision = (
                _clean_text(
                    segment.get(
                        "decision"
                    )
                ).upper()
            )

            if decision == "RENFORCER":
                score += 50

            if ordre_final == 1:
                score += 20

            zoom_candidates.append(
                (
                    score,
                    segment,
                )
            )

        zoom_candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        allowed_zoom_ids = {
            id(item[1])
            for item
            in zoom_candidates[:2]
        }

        for segment in final_segments:

            if (
                id(segment)
                not in allowed_zoom_ids
            ):
                segment[
                    "zoom"
                ] = 1.0

    # ========================================================
    # CONTRÔLE DU DYNAMISME
    # ========================================================

    kept_duration = sum(
        max(
            0,
            (
                segment[
                    "fin_source"
                ]
                -
                segment[
                    "debut_source"
                ]
            ),
        )
        for segment
        in final_segments
    )

    ratio_kept = (
        kept_duration
        / duration_seconds
        if duration_seconds > 0
        else 1
    )

    if ratio_kept > 0.85:

        print(
            "\n"
            "REMIX V3.1 : "
            "PLAN TROP CONSERVATEUR "
            f"({ratio_kept * 100:.1f}% conservé)"
            "\n"
        )

    # ========================================================
    # DURÉE ESTIMÉE
    # ========================================================

    estimated_duration = sum(
        (
            segment[
                "fin_source"
            ]
            -
            segment[
                "debut_source"
            ]
        )
        /
        max(
            1.0,
            segment[
                "vitesse"
            ],
        )
        for segment
        in final_segments
    )

    # ========================================================
    # RAPPORT FINAL
    # ========================================================

    return {

        "version": (
            "5.5-remix-v3.1"
        ),

        "strategie_globale": (
            _clean_text(
                raw_plan.get(
                    "strategie_globale"
                )
            )
        ),

        "hook_final": (
            raw_plan.get(
                "hook_final",
                {},
            )
        ),

        "montage_final": (
            final_segments
        ),

        "segments_supprimes": (
            raw_plan.get(
                "segments_supprimes",
                [],
            )
        ),

        "duree_originale": round(
            duration_seconds,
            2,
        ),

        "duree_finale_estimee": round(
            estimated_duration,
            2,
        ),

        "ratio_conserve": round(
            ratio_kept,
            3,
        ),

        "pourcentage_supprime": round(
            max(
                0,
                (
                    1
                    - ratio_kept
                )
                * 100,
            ),
            1,
        ),

        "gain_retention_estime": round(
            max(
                0,
                min(
                    30,
                    _number(
                        raw_plan.get(
                            "gain_retention_estime"
                        ),
                        0,
                    ),
                ),
            ),
            1,
        ),

        "resume": _clean_text(
            raw_plan.get(
                "resume"
            )
        ),
    }


# ============================================================
# PLAN GLOBAL
# ============================================================

def build_global_remix_plan(
    semantic_analysis: dict,
    technical_remontage: dict,
    duration_seconds: float,
    model_name: str | None = None,
) -> dict:

    chosen_model = (
        model_name
        or DEFAULT_MODEL
    )

    prompt = _build_prompt(
        semantic_analysis=(
            semantic_analysis
        ),
        technical_remontage=(
            technical_remontage
        ),
        duration_seconds=(
            duration_seconds
        ),
    )

    try:

        response_text = (
            _gemini_generate(
                prompt=prompt,
                model_name=(
                    chosen_model
                ),
            )
        )

        print(
            "\n"
            "========== REMIX V3.1 GLOBAL RAW =========="
        )

        print(
            response_text
        )

        print(
            "============================================"
            "\n"
        )

        raw_plan = (
            _json_from_text(
                response_text
            )
        )

        plan = _normalize_plan(
            raw_plan=raw_plan,
            duration_seconds=(
                duration_seconds
            ),
        )

        plan[
            "status"
        ] = "ok"

        plan[
            "model"
        ] = chosen_model

        return plan

    except Exception as error:

        print(
            "ERREUR REMIX V3.1 GLOBAL:",
            repr(error),
        )

        return {

            "status": "error",

            "version": (
                "5.5-remix-v3.1"
            ),

            "model": chosen_model,

            "strategie_globale": "",

            "hook_final": {},

            "montage_final": [],

            "segments_supprimes": [],

            "duree_originale": round(
                duration_seconds,
                2,
            ),

            "duree_finale_estimee": 0,

            "ratio_conserve": 0,

            "pourcentage_supprime": 0,

            "gain_retention_estime": 0,

            "resume": "",

            "error": str(
                error
            ),
        }