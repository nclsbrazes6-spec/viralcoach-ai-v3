import json
import os
from pathlib import Path

from google import genai
from google.genai import types


MODEL_NAME = "gemini-2.5-flash-lite"
MAX_IMAGES = 6


def _empty_result(message: str) -> dict:
    return {
        "disponible": False,
        "erreur": message,
        "resume_video": "",
        "sujet_principal": "",
        "hook_visuel": "",
        "score_hook": 0,
        "score_potentiel_viral": 0,
        "points_forts": [],
        "points_faibles": [],
        "priorites": [],
        "recommandations": [],
        "hooks_ameliores": [],
        "description_tiktok": "",
        "hashtags": [],
    }


def _select_images(
    frame_paths: list,
) -> list[Path]:
    valid_paths = [
        Path(path)
        for path in frame_paths
        if Path(path).exists()
    ]

    if len(valid_paths) <= MAX_IMAGES:
        return valid_paths

    last_index = len(valid_paths) - 1

    indexes = [
        round(
            position * last_index
            / (MAX_IMAGES - 1)
        )
        for position in range(MAX_IMAGES)
    ]

    return [
        valid_paths[index]
        for index in indexes
    ]


def _clean_json(text: str) -> dict:
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]

    if cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return json.loads(cleaned.strip())


def analyze_video_semantics(
    frame_paths: list,
    transcription: str,
) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return _empty_result(
            "La variable GEMINI_API_KEY est absente."
        )

    selected_images = _select_images(
        frame_paths
    )

    if not selected_images:
        return _empty_result(
            "Aucune image exploitable."
        )

    prompt = f"""
Tu es ViralCoach AI, spécialiste des vidéos TikTok.

Analyse les images extraites d'une même vidéo, dans leur ordre
chronologique. Utilise également la transcription si elle est fiable.

Transcription :
{transcription or "Aucune transcription fiable."}

Règles :
- Décris uniquement ce qui est réellement visible ou entendu.
- N'invente aucun lieu, produit, événement ou intention.
- Si une information est incertaine, indique qu'elle est incertaine.
- Évalue le hook des trois premières secondes.
- Analyse le sujet, le cadrage, les textes visibles, les changements
  de plans et le potentiel de rétention.
- Réponds uniquement avec un objet JSON valide en français.

Structure JSON obligatoire :
{{
  "resume_video": "résumé fidèle",
  "sujet_principal": "sujet réellement identifié",
  "hook_visuel": "description du hook",
  "score_hook": 0,
  "score_potentiel_viral": 0,
  "points_forts": ["point fort"],
  "points_faibles": ["point faible"],
  "priorites": ["priorité"],
  "recommandations": ["recommandation concrète"],
  "hooks_ameliores": ["hook 1", "hook 2", "hook 3"],
  "description_tiktok": "description fidèle",
  "hashtags": ["#hashtag"]
}}

Les scores doivent être compris entre 0 et 10.
"""

    contents = [prompt]

    for image_path in selected_images:
        contents.append(
            types.Part.from_bytes(
                data=image_path.read_bytes(),
                mime_type="image/jpeg",
            )
        )

    try:
        client = genai.Client(
            api_key=api_key
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type=(
                    "application/json"
                ),
            ),
        )

        if not response.text:
            return _empty_result(
                "Gemini n'a retourné aucun texte."
            )

        result = _clean_json(
            response.text
        )

        result["disponible"] = True
        result["images_envoyees"] = len(
            selected_images
        )

        return result

    except Exception as error:
        return _empty_result(
            f"Erreur Gemini : {error}"
        )