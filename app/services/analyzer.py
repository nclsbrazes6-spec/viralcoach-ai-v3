"""Analyse sémantique des paroles ViralCoach AI V5 avec Gemini."""

import json
import os
import re

from google import genai
from google.genai import types
from dotenv import load_dotenv


load_dotenv()

MODEL_NAME = "gemini-3.5-flash-lite"


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "resume": {"type": "string"},
        "sujet_principal": {"type": "string"},
        "audience_cible": {"type": "string"},
        "hook_reel": {"type": "string"},
        "note_hook": {"type": "integer", "minimum": 0, "maximum": 10},
        "note_clarte": {"type": "integer", "minimum": 0, "maximum": 10},
        "note_structure": {"type": "integer", "minimum": 0, "maximum": 10},
        "note_potentiel_viral": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10,
        },
        "diagnostic_3_premieres_secondes": {"type": "string"},
        "promesse": {"type": "string"},
        "preuve": {"type": "string"},
        "appel_action": {"type": "string"},
        "mots_remplissage": {
            "type": "array",
            "items": {"type": "string"},
        },
        "repetitions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "phrases_a_supprimer": {
            "type": "array",
            "items": {"type": "string"},
        },
        "points_forts": {
            "type": "array",
            "items": {"type": "string"},
        },
        "points_faibles": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommandations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "hooks_ameliores": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3,
        },
        "description_tiktok": {"type": "string"},
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "resume",
        "sujet_principal",
        "audience_cible",
        "hook_reel",
        "note_hook",
        "note_clarte",
        "note_structure",
        "note_potentiel_viral",
        "diagnostic_3_premieres_secondes",
        "promesse",
        "preuve",
        "appel_action",
        "mots_remplissage",
        "repetitions",
        "phrases_a_supprimer",
        "points_forts",
        "points_faibles",
        "recommandations",
        "hooks_ameliores",
        "description_tiktok",
        "hashtags",
    ],
}


def _score(value) -> int:
    try:
        return max(0, min(10, round(float(value))))
    except (TypeError, ValueError):
        return 0


def _list(value, limit=None) -> list[str]:
    if not isinstance(value, list):
        return []

    result = []

    for item in value:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)

    return result[:limit] if limit else result


def _hashtags(value) -> list[str]:
    result = []

    for hashtag in _list(value, 8):
        cleaned = re.sub(r"\s+", "", hashtag)
        if not cleaned.startswith("#"):
            cleaned = f"#{cleaned}"
        if cleaned != "#" and cleaned not in result:
            result.append(cleaned)

    return result


def _fallback(transcription: str, message: str) -> dict:
    """Retour compatible si Gemini ou la transcription est indisponible."""
    text = (transcription or "").strip()
    first_sentence = re.split(r"(?<=[.!?])\s+|\n+", text)[0] if text else ""

    return {
        "resume": text[:320] if text else "Aucune parole fiable n'a été détectée.",
        "sujet_principal": "",
        "audience_cible": "",
        "hook_reel": first_sentence,
        "note_hook": 0,
        "note_clarte": 0,
        "note_structure": 0,
        "note_potentiel_viral": 0,
        "diagnostic_3_premieres_secondes": (
            "L'analyse sémantique des paroles n'est pas disponible."
        ),
        "promesse": "",
        "preuve": "",
        "appel_action": "",
        "points_forts": [],
        "points_faibles": [message],
        "recommandations": [
            "Vérifier la transcription et la connexion à Gemini, puis relancer l'analyse."
        ],
        "hooks_ameliores": [],
        "description_tiktok": "",
        "hashtags": [],
        "analyse_paroles": {
            "disponible": False,
            "erreur": message,
            "mots_remplissage": [],
            "repetitions": [],
            "phrases_a_supprimer": [],
        },
    }


def analyze_transcription(transcription: str) -> dict:
    """Analyse les paroles avec Gemini sans modifier la signature historique."""
    text = (transcription or "").strip()

    if not text:
        return _fallback(
            text,
            "Aucune parole suffisamment claire n'a été transcrite.",
        )

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return _fallback(
            text,
            "La variable GEMINI_API_KEY est absente.",
        )

    prompt = f"""
Tu es l'analyste éditorial de ViralCoach AI, spécialisé dans les vidéos
TikTok, Reels et Shorts en français.

Analyse uniquement la transcription fournie. Ne déduis aucun fait qui n'est
pas prononcé. Si la transcription semble contenir un mot mal reconnu, ne le
réutilise pas comme sujet sans contexte suffisant.

TRANSCRIPTION EXACTE :
---
{text}
---

Consignes :
- Le hook réel correspond aux premiers mots effectivement prononcés.
- Évalue la promesse, la clarté, la progression, la preuve et l'appel à l'action.
- Identifie les hésitations, répétitions et phrases réellement supprimables.
- Les trois hooks améliorés doivent être naturels, spécifiques au sujet réel et
  immédiatement prononçables. N'assemble jamais une liste de mots-clés.
- N'invente ni chiffre, ni résultat, ni bénéfice absent de la transcription.
- Si le sujet reste incertain, écris des hooks prudents sans nom propre inventé.
- La description TikTok doit rester fidèle au contenu.
- Donne des recommandations concrètes et courtes.
- Tous les scores sont sur 10.
"""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.15,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )

        if not response.text:
            return _fallback(text, "Gemini n'a retourné aucune analyse.")

        data = json.loads(response.text)
    except Exception as error:
        return _fallback(text, f"Erreur Gemini : {error}")

    hooks = _list(data.get("hooks_ameliores"), 3)

    return {
        "resume": str(data.get("resume", "")).strip(),
        "sujet_principal": str(data.get("sujet_principal", "")).strip(),
        "audience_cible": str(data.get("audience_cible", "")).strip(),
        "hook_reel": str(data.get("hook_reel", "")).strip(),
        "note_hook": _score(data.get("note_hook")),
        "note_clarte": _score(data.get("note_clarte")),
        "note_structure": _score(data.get("note_structure")),
        "note_potentiel_viral": _score(data.get("note_potentiel_viral")),
        "diagnostic_3_premieres_secondes": str(
            data.get("diagnostic_3_premieres_secondes", "")
        ).strip(),
        "promesse": str(data.get("promesse", "")).strip(),
        "preuve": str(data.get("preuve", "")).strip(),
        "appel_action": str(data.get("appel_action", "")).strip(),
        "points_forts": _list(data.get("points_forts")),
        "points_faibles": _list(data.get("points_faibles")),
        "recommandations": _list(data.get("recommandations")),
        "hooks_ameliores": hooks,
        "description_tiktok": str(data.get("description_tiktok", "")).strip(),
        "hashtags": _hashtags(data.get("hashtags")),
        "analyse_paroles": {
            "disponible": True,
            "modele": MODEL_NAME,
            "hook_reel": str(data.get("hook_reel", "")).strip(),
            "promesse": str(data.get("promesse", "")).strip(),
            "preuve": str(data.get("preuve", "")).strip(),
            "appel_action": str(data.get("appel_action", "")).strip(),
            "mots_remplissage": _list(data.get("mots_remplissage")),
            "repetitions": _list(data.get("repetitions")),
            "phrases_a_supprimer": _list(data.get("phrases_a_supprimer")),
        },
    }
