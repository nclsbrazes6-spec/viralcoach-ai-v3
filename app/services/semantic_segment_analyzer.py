"""
ViralCoach AI V5.4
Analyse sémantique des segments vidéo.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

DEFAULT_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite",
).strip()

# L'ancien modèle n'est plus disponible pour les nouveaux utilisateurs.
if DEFAULT_MODEL == "gemini-2.5-flash-lite":
    DEFAULT_MODEL = "gemini-3.5-flash-lite"

ALLOWED_DECISIONS = {
    "CONSERVER",
    "COUPER",
    "RACCOURCIR",
    "ACCÉLÉRER",
    "RENFORCER",
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip().replace(",", ".")
        match = re.search(r"-?\d+(?:\.\d+)?", text)

        if not match:
            return default

        return float(match.group(0))

    except Exception:
        return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


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

    text = str(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_decision(value: Any) -> str:
    decision = _clean_text(value).upper()

    decision = decision.replace("ACCELERER", "ACCÉLÉRER")

    if decision not in ALLOWED_DECISIONS:
        return "RENFORCER"

    return decision


def _json_from_text(text: str) -> dict:
    """
    Extrait un objet JSON depuis la réponse Gemini.
    Tolère les fences Markdown, un BOM et un peu de texte autour.
    """
    if not text:
        raise ValueError("Réponse Gemini vide.")

    cleaned = str(text).strip().lstrip("\ufeff")

    cleaned = re.sub(
        r"^```(?:json)?\\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\\s*```$",
        "",
        cleaned,
    )

    try:
        data = json.loads(cleaned)

        if isinstance(data, dict):
            return data

    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()

    for index, char in enumerate(cleaned):
        if char != "{":
            continue

        try:
            data, _ = decoder.raw_decode(cleaned[index:])

            if isinstance(data, dict):
                return data

        except json.JSONDecodeError:
            continue

    preview = cleaned[:500].replace("\n", " ")

    raise ValueError(
        "Réponse Gemini non JSON. "
        f"Début de réponse : {preview}"
    )

def _transcript_text(transcription: Any) -> str:
    if isinstance(transcription, str):
        return _clean_text(transcription)

    if not isinstance(transcription, dict):
        return _clean_text(transcription)

    for key in ("text", "texte", "transcription", "transcript"):
        value = transcription.get(key)

        if isinstance(value, str):
            return _clean_text(value)

    pieces = []

    for item in _transcript_segments(transcription):
        text = _clean_text(item.get("text"))

        if text:
            pieces.append(text)

    return " ".join(pieces).strip()


def _transcript_segments(transcription: Any) -> list[dict]:
    if not isinstance(transcription, dict):
        return []

    raw_segments = None

    for key in ("segments", "chunks", "utterances", "phrases"):
        candidate = transcription.get(key)

        if isinstance(candidate, list):
            raw_segments = candidate
            break

    if not raw_segments:
        return []

    normalized = []

    for item in raw_segments:
        if not isinstance(item, dict):
            continue

        start = _number(
            item.get(
                "start",
                item.get("debut", item.get("start_time", 0)),
            ),
            0.0,
        )

        end = _number(
            item.get(
                "end",
                item.get("fin", item.get("end_time", start)),
            ),
            start,
        )

        text = _clean_text(
            item.get(
                "text",
                item.get("texte", item.get("content", "")),
            )
        )

        normalized.append(
            {
                "start": start,
                "end": max(start, end),
                "text": text,
            }
        )

    return normalized


def _segment_text_from_timestamps(
    start: float,
    end: float,
    transcript_segments: list[dict],
) -> str:
    pieces = []

    for item in transcript_segments:
        item_start = _number(item.get("start"))
        item_end = _number(item.get("end"), item_start)

        overlaps = item_end > start and item_start < end

        if not overlaps:
            continue

        text = _clean_text(item.get("text"))

        if text:
            pieces.append(text)

    return " ".join(pieces).strip()


def _segment_text_fallback(
    full_text: str,
    index: int,
    total_segments: int,
) -> str:
    if not full_text or total_segments <= 0:
        return ""

    words = full_text.split()

    if not words:
        return ""

    start_index = round(len(words) * index / total_segments)
    end_index = round(len(words) * (index + 1) / total_segments)

    return " ".join(words[start_index:end_index]).strip()


def _normalize_video_segments(
    segments: Any,
    transcription: Any,
) -> list[dict]:
    raw_segments = _as_list(segments)
    transcript_segments = _transcript_segments(transcription)
    full_text = _transcript_text(transcription)

    normalized = []
    total = len(raw_segments)

    for index, raw in enumerate(raw_segments):
        if not isinstance(raw, dict):
            continue

        start = _number(
            raw.get(
                "debut_secondes",
                raw.get("debut", raw.get("start", 0)),
            ),
            0.0,
        )

        end = _number(
            raw.get(
                "fin_secondes",
                raw.get("fin", raw.get("end", start)),
            ),
            start,
        )

        end = max(start, end)

        content = ""

        if transcript_segments:
            content = _segment_text_from_timestamps(
                start,
                end,
                transcript_segments,
            )

        if not content:
            content = _clean_text(
                raw.get(
                    "contenu_segment",
                    raw.get("texte", ""),
                )
            )

        if not content:
            content = _segment_text_fallback(
                full_text,
                index,
                max(total, 1),
            )

        normalized.append(
            {
                "ordre": int(
                    _number(raw.get("ordre", index + 1), index + 1)
                ),
                "debut": round(start, 2),
                "fin": round(end, 2),
                "duree": round(max(0.0, end - start), 2),
                "phase": _clean_text(
                    raw.get("phase", raw.get("type", "MONTAGE"))
                ).upper(),
                "niveau_risque": _clean_text(
                    raw.get("niveau_risque", raw.get("priorite", ""))
                ),
                "decision_actuelle": _clean_text(raw.get("decision", "")),
                "diagnostic_actuel": _clean_text(raw.get("diagnostic", "")),
                "contenu_segment": content,
            }
        )

    return normalized


def _fallback_semantic_result(segment: dict) -> dict:
    text = _clean_text(segment.get("contenu_segment"))
    word_count = len(text.split())
    duration = _number(segment.get("duree"))
    phase = _clean_text(segment.get("phase")).upper()

    decision = "CONSERVER"

    if not text and duration >= 2.8:
        decision = "RACCOURCIR"
    elif word_count <= 3 and duration >= 3.0:
        decision = "ACCÉLÉRER"
    elif phase == "HOOK" and duration >= 1.8:
        decision = "RENFORCER"

    score = 65.0

    if phase == "HOOK":
        score += 5
    if 4 <= word_count <= 18:
        score += 6
    if duration > 4.0:
        score -= 8

    score = round(_clamp(score, 20, 95), 1)

    return {
        "ordre": segment.get("ordre"),
        "decision": decision,
        "contenu_segment": text,
        "message_cle": (
            text if text else "Aucun message verbal clairement isolé."
        ),
        "diagnostic_semantique": (
            "Analyse locale de secours utilisée. "
            "Gemini n'a pas fourni d'analyse sémantique."
        ),
        "valeur_information": "MOYENNE",
        "score_interet": score,
        "probleme": "",
        "action_montage": (
            "Conserver l'idée principale et maintenir un rythme visuel clair."
        ),
        "b_roll": "",
        "texte_ecran": "",
        "hook_potentiel": phase == "HOOK",
        "phrase_hook": "",
        "raison_hook": "",
        "gain_retention_estime": 0.0,
    }


def _gemini_generate(prompt: str, model_name: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY absente.")

    try:
        from google import genai
        from google.genai import types
    except ImportError as error:
        raise RuntimeError(
            "SDK Gemini introuvable. Installe google-genai."
        ) from error

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                max_output_tokens=8192,
            ),
        )
    except Exception as error:
        raise RuntimeError(
            f"Erreur appel Gemini : {type(error).__name__}: {error}"
        ) from error

    text = getattr(response, "text", None)

    if text and str(text).strip():
        return str(text).strip()

    details = []

    candidates = getattr(response, "candidates", None) or []

    for index, candidate in enumerate(candidates):
        finish_reason = getattr(candidate, "finish_reason", None)

        if finish_reason is not None:
            details.append(
                f"candidate {index} finish_reason={finish_reason}"
            )

        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None

        if parts:
            for part in parts:
                part_text = getattr(part, "text", None)

                if part_text and str(part_text).strip():
                    return str(part_text).strip()

    prompt_feedback = getattr(response, "prompt_feedback", None)

    if prompt_feedback is not None:
        details.append(
            f"prompt_feedback={prompt_feedback}"
        )

    detail_text = " | ".join(details) if details else "aucun détail disponible"

    raise RuntimeError(
        "Gemini n'a renvoyé aucun texte exploitable. "
        + detail_text
    )

def _semantic_prompt(
    segments: list[dict],
    visual_analysis: Any = None,
) -> str:
    visual_context = ""

    if visual_analysis:
        try:
            visual_context = json.dumps(
                visual_analysis,
                ensure_ascii=False,
                default=str,
            )

            if len(visual_context) > 6000:
                visual_context = visual_context[:6000] + "..."

        except Exception:
            visual_context = _clean_text(visual_analysis)[:6000]

    payload = json.dumps(
        segments,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
Tu es ViralCoach AI V5.4, expert du montage TikTok, Reels et Shorts.

Analyse SÉMANTIQUEMENT chaque segment ci-dessous.
Tu dois comprendre le MESSAGE du segment, pas seulement sa durée.

Pour chaque segment :
1. résume l'idée réellement communiquée ;
2. juge si cette idée apporte de la valeur ;
3. détecte répétition, lenteur, manque de preuve, manque de contexte ou absence de payoff ;
4. choisis UNE décision parmi :
   CONSERVER, COUPER, RACCOURCIR, ACCÉLÉRER, RENFORCER ;
5. explique précisément ce qu'il faut faire au montage ;
6. propose un B-roll réellement lié au contenu ;
7. propose un texte écran court et concret ;
8. estime l'intérêt du segment sur 100 ;
9. estime le gain potentiel de rétention après correction ;
10. indique si ce passage pourrait devenir un hook plus fort.
11. donne un plan de montage précis :
    - coupe_debut : nombre de secondes à retirer au début du segment ;
    - coupe_fin : nombre de secondes à retirer à la fin du segment ;
    - vitesse : vitesse recommandée entre 1.0 et 1.5 ;
    - zoom : zoom recommandé entre 1.0 et 1.15 ;
    - duree_cible : durée finale souhaitée du segment ;
    - position_texte : haut, centre ou bas ;
    - transition : cut, fondu ou aucune.

RÈGLES :
- Ne propose pas un B-roll générique si le contenu ne le justifie pas.
- N'invente pas de prix, lieu, chiffre, produit ou fait absent du texte.
- Le texte écran doit rester très court.
- "COUPER" uniquement si le segment apporte peu ou répète réellement une information.
- "RACCOURCIR" si l'idée est utile mais trop longue.
- "ACCÉLÉRER" si le contenu doit rester mais manque de rythme.
- "RENFORCER" si l'idée est bonne mais manque d'impact ou de preuve.
- "CONSERVER" si le passage fonctionne déjà.
- Un hook potentiel doit avoir une promesse, curiosité, résultat ou information forte.

CONTEXTE VISUEL GLOBAL ÉVENTUEL :
{visual_context or "Non disponible"}

SEGMENTS :
{payload}

Réponds UNIQUEMENT avec un JSON valide de cette forme :

{{
  "version": "5.4",
  "segments": [
    {{
      "ordre": 1,
      "decision": "RENFORCER",
      "contenu_segment": "texte réellement présent",
      "message_cle": "idée principale",
      "diagnostic_semantique": "explication précise",
      "valeur_information": "FORTE",
      "score_interet": 78,
      "probleme": "le bénéfice arrive trop tard",
      "action_montage": "action concrète",
      "b_roll": "B-roll contextualisé ou chaîne vide",
      "texte_ecran": "texte court",
      "hook_potentiel": false,
      "phrase_hook": "",
      "raison_hook": "",
      "gain_retention_estime": 8,
      "coupe_debut": 0.0,
      "coupe_fin": 0.0,
      "vitesse": 1.0,
      "zoom": 1.0,
      "duree_cible": 2.0,
      "position_texte": "centre",
      "transition": "cut"
    }}
  ],
  "meilleur_hook": {{
    "ordre": 0,
    "phrase": "",
    "raison": "",
    "score": 0
  }},
  "resume_semantique": "résumé global très court"
}}
""".strip()


def _normalize_ai_segment(
    raw: dict,
    source: dict,
) -> dict:
    return {
        "ordre": int(
            _number(
                raw.get(
                    "ordre",
                    source.get("ordre", 0),
                )
            )
        ),
        "decision": _normalize_decision(raw.get("decision")),
        "contenu_segment": _clean_text(
            raw.get(
                "contenu_segment",
                source.get("contenu_segment", ""),
            )
        ),
        "message_cle": _clean_text(raw.get("message_cle")),
        "diagnostic_semantique": _clean_text(
            raw.get("diagnostic_semantique")
        ),
        "valeur_information": _clean_text(
            raw.get("valeur_information", "MOYENNE")
        ).upper(),
        "score_interet": round(
            _clamp(
                _number(raw.get("score_interet"), 60),
                0,
                100,
            ),
            1,
        ),
        "probleme": _clean_text(raw.get("probleme")),
        "action_montage": _clean_text(raw.get("action_montage")),
        "b_roll": _clean_text(raw.get("b_roll")),
        "texte_ecran": _clean_text(raw.get("texte_ecran")),
        "hook_potentiel": bool(raw.get("hook_potentiel", False)),
        "phrase_hook": _clean_text(raw.get("phrase_hook")),
        "raison_hook": _clean_text(raw.get("raison_hook")),
        "gain_retention_estime": round(
            _clamp(
                _number(raw.get("gain_retention_estime"), 0),
                0,
                30,
            ),
            1,
        ),
"coupe_debut": round(
    _clamp(
        _number(raw.get("coupe_debut"), 0),
        0,
        10,
    ),
    2,
),
"coupe_fin": round(
    _clamp(
        _number(raw.get("coupe_fin"), 0),
        0,
        10,
    ),
    2,
),
"vitesse": round(
    _clamp(
        _number(raw.get("vitesse"), 1.0),
        1.0,
        1.5,
    ),
    2,
),
"zoom": round(
    _clamp(
        _number(raw.get("zoom"), 1.0),
        1.0,
        1.15,
    ),
    2,
),
"duree_cible": round(
    max(
        0,
        _number(raw.get("duree_cible"), 0),
    ),
    2,
),
"position_texte": _clean_text(
    raw.get("position_texte", "centre")
).lower(),
"transition": _clean_text(
    raw.get("transition", "cut")
).lower(),
    }


def _missing_orders(
    expected_segments: list[dict],
    received_segments: list[dict],
) -> list[int]:
    expected = {
        int(_number(item.get("ordre"), 0))
        for item in expected_segments
        if int(_number(item.get("ordre"), 0)) > 0
    }

    received = {
        int(_number(item.get("ordre"), 0))
        for item in received_segments
        if isinstance(item, dict)
        and int(_number(item.get("ordre"), 0)) > 0
    }

    return sorted(expected - received)


def _retry_missing_segments(
    missing_orders: list[int],
    normalized_segments: list[dict],
    visual_analysis: Any,
    model_name: str,
) -> list[dict]:
    """
    Relance Gemini séparément pour chaque segment manquant.

    Avantage :
    si un segment échoue, les autres réponses Gemini
    restent utilisables.
    """

    if not missing_orders:
        return []

    visual_context = ""

    if visual_analysis:
        try:
            visual_context = json.dumps(
                visual_analysis,
                ensure_ascii=False,
                default=str,
            )

            if len(visual_context) > 2500:
                visual_context = (
                    visual_context[:2500]
                    + "..."
                )

        except Exception:
            visual_context = _clean_text(
                visual_analysis
            )[:2500]

    results = []

    for order in missing_orders:

        source_segment = next(
            (
                item
                for item in normalized_segments
                if int(
                    _number(
                        item.get("ordre"),
                        0,
                    )
                ) == order
            ),
            None,
        )

        if not source_segment:
            continue

        payload = json.dumps(
            source_segment,
            ensure_ascii=False,
            indent=2,
        )

        prompt = f"""
Tu es ViralCoach AI V5.4,
expert du montage TikTok, Reels et Shorts.

Analyse uniquement CE segment vidéo.

NUMÉRO DE SEGMENT OBLIGATOIRE :
{order}

SEGMENT :
{payload}

CONTEXTE VISUEL GLOBAL :
{visual_context or "Non disponible"}

Tu dois comprendre ce qui est réellement dit
et déterminer comment améliorer ce passage.

Choisis UNE décision parmi :

CONSERVER
COUPER
RACCOURCIR
ACCÉLÉRER
RENFORCER

RÈGLES :

- conserve exactement ordre = {order}
- n'invente aucun fait absent du contenu
- COUPER seulement si le passage apporte très peu
  ou répète inutilement une information
- RACCOURCIR si l'idée est bonne mais trop longue
- ACCÉLÉRER si l'idée doit rester mais manque de rythme
- RENFORCER si l'idée est utile mais manque d'impact
- CONSERVER si le passage fonctionne déjà
- propose un B-roll uniquement s'il est pertinent
- le texte écran doit être court
- estime score_interet entre 0 et 100
- estime gain_retention_estime entre 0 et 30
- indique si ce passage peut devenir un hook

Réponds UNIQUEMENT avec ce JSON :

{{
    "ordre": {order},
    "decision": "RENFORCER",
    "contenu_segment": "",
    "message_cle": "",
    "diagnostic_semantique": "",
    "valeur_information": "MOYENNE",
    "score_interet": 70,
    "probleme": "",
    "action_montage": "",
    "b_roll": "",
    "texte_ecran": "",
    "hook_potentiel": false,
    "phrase_hook": "",
    "raison_hook": "",
    "gain_retention_estime": 5
}}
""".strip()

        try:
            response_text = _gemini_generate(
                prompt=prompt,
                model_name=model_name,
            )

            print(
                f"\n========== GEMINI V5.4 SEGMENT {order} =========="
            )
            print(response_text)
            print(
                "================================================\n"
            )

            data = _json_from_text(
                response_text
            )

            # ------------------------------------------------
            # Gemini peut éventuellement envelopper
            # la réponse dans {"segments": [...]}
            # ------------------------------------------------

            if (
                "segments" in data
                and isinstance(
                    data.get("segments"),
                    list,
                )
            ):

                candidates = [
                    item
                    for item in data["segments"]
                    if isinstance(
                        item,
                        dict,
                    )
                ]

                data = next(
                    (
                        item
                        for item in candidates
                        if int(
                            _number(
                                item.get("ordre"),
                                0,
                            )
                        ) == order
                    ),
                    {},
                )

            # ------------------------------------------------
            # CONTRÔLE DE L'ORDRE
            # ------------------------------------------------

            returned_order = int(
                _number(
                    data.get("ordre"),
                    0,
                )
            )

            if returned_order != order:
                print(
                    "SEGMENT V5.4 IGNORÉ : "
                    f"ordre attendu={order}, "
                    f"ordre reçu={returned_order}"
                )

                continue

            # ------------------------------------------------
            # CONTRÔLE MINIMUM
            # ------------------------------------------------

            if not data.get("decision"):
                print(
                    "SEGMENT V5.4 IGNORÉ : "
                    f"décision absente pour ordre {order}"
                )

                continue

            results.append(
                data
            )

        except Exception as error:
            print(
                f"ERREUR SEMANTIC SEGMENT {order}:",
                repr(error),
            )

            # Important :
            # on continue avec le segment suivant.
            continue

    return results
def _select_best_hook(
    final_segments: list[dict],
    ai_hook: Any,
) -> dict:
    if isinstance(ai_hook, dict):
        order = int(_number(ai_hook.get("ordre"), 0))
        phrase = _clean_text(ai_hook.get("phrase"))
        reason = _clean_text(ai_hook.get("raison"))
        score = _clamp(_number(ai_hook.get("score"), 0), 0, 100)

        if order > 0 or phrase:
            return {
                "ordre": order,
                "phrase": phrase,
                "raison": reason,
                "score": round(score, 1),
            }

    candidates = []

    for segment in final_segments:
        if not isinstance(segment, dict):
            continue

        potential = bool(segment.get("hook_potentiel", False))
        interest = _number(segment.get("score_interet"), 0)
        phrase = (
            _clean_text(segment.get("phrase_hook"))
            or _clean_text(segment.get("message_cle"))
            or _clean_text(segment.get("contenu_segment"))
        )

        if not phrase:
            continue

        score = interest

        if potential:
            score += 12

        if _clean_text(segment.get("valeur_information")).upper() == "FORTE":
            score += 5

        candidates.append((score, segment, phrase))

    if not candidates:
        return {
            "ordre": 0,
            "phrase": "",
            "raison": "",
            "score": 0,
        }

    candidates.sort(key=lambda item: item[0], reverse=True)
    best_score, best_segment, phrase = candidates[0]

    return {
        "ordre": int(_number(best_segment.get("ordre"), 0)),
        "phrase": phrase,
        "raison": (
            _clean_text(best_segment.get("raison_hook"))
            or _clean_text(best_segment.get("diagnostic_semantique"))
            or "Passage à fort potentiel d'ouverture."
        ),
        "score": round(_clamp(best_score, 0, 100), 1),
    }


def analyze_semantic_segments(
    transcription: Any,
    segments: Any,
    visual_analysis: Any = None,
    model_name: str | None = None,
) -> dict:
    normalized_segments = _normalize_video_segments(
        segments=segments,
        transcription=transcription,
    )

    if not normalized_segments:
        return {
            "version": "5.4",
            "mode": "semantic_segments",
            "model": model_name or DEFAULT_MODEL,
            "gemini_status": "empty",
            "segments": [],
            "meilleur_hook": {"ordre": 0, "phrase": "", "raison": "", "score": 0},
            "resume_semantique": "Aucun segment à analyser.",
            "fallback": True,
            "segments_attendus": 0,
            "segments_gemini": 0,
            "segments_fallback": 0,
            "segments_relances": [],
            "segments_manquants": [],
        }

    chosen_model = model_name or DEFAULT_MODEL

    try:
        prompt = _semantic_prompt(normalized_segments, visual_analysis)
        response_text = _gemini_generate(prompt=prompt, model_name=chosen_model)
        ai_data = _json_from_text(response_text)

        raw_results = [
            item
            for item in _as_list(ai_data.get("segments"))
            if isinstance(item, dict)
        ]

        missing_orders = _missing_orders(normalized_segments, raw_results)
        retried_orders = []

        if missing_orders:
            try:
                retry_results = _retry_missing_segments(
                    missing_orders=missing_orders,
                    normalized_segments=normalized_segments,
                    visual_analysis=visual_analysis,
                    model_name=chosen_model,
                )

                if retry_results:
                    raw_results.extend(retry_results)
                    retried_orders = [
                        int(_number(item.get("ordre"), 0))
                        for item in retry_results
                        if int(_number(item.get("ordre"), 0)) > 0
                    ]

            except Exception as retry_error:
                print("ERREUR RELANCE SEMANTIC V5.4:", repr(retry_error))

        by_order = {}

        for raw in raw_results:
            order = int(_number(raw.get("ordre"), 0))
            if order > 0:
                by_order[order] = raw

        final_segments = []
        fallback_count = 0
        gemini_count = 0

        for source in normalized_segments:
            order = int(_number(source.get("ordre"), 0))
            raw = by_order.get(order)

            if raw:
                final = _normalize_ai_segment(raw, source)
                final["source_semantique"] = "gemini"
                gemini_count += 1
            else:
                final = _fallback_semantic_result(source)
                final["source_semantique"] = "fallback_local"
                fallback_count += 1

            final["debut"] = source.get("debut")
            final["fin"] = source.get("fin")
            final["duree"] = source.get("duree")
            final["phase"] = source.get("phase")
            final_segments.append(final)

        meilleur_hook = _select_best_hook(
            final_segments,
            ai_data.get("meilleur_hook"),
        )

        all_gemini = (
            fallback_count == 0
            and gemini_count == len(normalized_segments)
        )

        if all_gemini:
            status = "ok"
        elif gemini_count > 0:
            status = "partial"
        else:
            status = "fallback"

        expected_orders = [
            int(_number(item.get("ordre"), 0))
            for item in normalized_segments
            if int(_number(item.get("ordre"), 0)) > 0
        ]

        missing_after_retry = [
            order
            for order in expected_orders
            if order not in by_order
        ]

        return {
            "version": "5.4",
            "mode": "semantic_segments",
            "model": chosen_model,
            "gemini_status": status,
            "segments": final_segments,
            "meilleur_hook": meilleur_hook,
            "resume_semantique": (
                _clean_text(ai_data.get("resume_semantique", ""))
                or f"{gemini_count}/{len(normalized_segments)} segments analysés par Gemini."
            ),
            "fallback": not all_gemini,
            "segments_attendus": len(normalized_segments),
            "segments_gemini": gemini_count,
            "segments_fallback": fallback_count,
            "segments_relances": sorted(set(retried_orders)),
            "segments_manquants": missing_after_retry,
        }

    except Exception as error:
        print("ERREUR SEMANTIC V5.4:", repr(error))

        fallback_segments = [
            _fallback_semantic_result(segment)
            for segment in normalized_segments
        ]

        for final, source in zip(fallback_segments, normalized_segments):
            final["debut"] = source.get("debut")
            final["fin"] = source.get("fin")
            final["duree"] = source.get("duree")
            final["phase"] = source.get("phase")
            final["source_semantique"] = "fallback_local"

        return {
            "version": "5.4",
            "mode": "semantic_segments",
            "model": chosen_model,
            "gemini_status": "fallback",
            "segments": fallback_segments,
            "meilleur_hook": _select_best_hook(fallback_segments, None),
            "resume_semantique": (
                "Analyse locale utilisée car Gemini "
                "n'a pas pu fournir l'analyse sémantique."
            ),
            "fallback": True,
            "segments_attendus": len(normalized_segments),
            "segments_gemini": 0,
            "segments_fallback": len(normalized_segments),
            "segments_relances": [],
            "segments_manquants": [
                int(_number(item.get("ordre"), 0))
                for item in normalized_segments
                if int(_number(item.get("ordre"), 0)) > 0
            ],
            "error": str(error),
        }

