from __future__ import annotations

from pathlib import Path
from typing import Any
import os

from openai import OpenAI


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_TRANSCRIBE_MODEL = os.getenv(
    "OPENAI_TRANSCRIBE_MODEL",
    "gpt-4o-mini-transcribe",
).strip()


# ============================================================
# OUTILS
# ============================================================

def _clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return (
        str(value)
        .strip()
    )


# ============================================================
# TRANSCRIPTION OPENAI
# ============================================================

def transcribe(
    audio_path: str | Path,
) -> dict:

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY absente."
        )

    input_path = Path(
        audio_path
    ).resolve()

    if not input_path.exists():
        raise FileNotFoundError(
            f"Fichier audio introuvable : {input_path}"
        )

    client = OpenAI(
        api_key=api_key
    )

    try:

        with input_path.open(
            "rb"
        ) as audio_file:

            response = (
                client.audio.transcriptions.create(
                    model=DEFAULT_TRANSCRIBE_MODEL,
                    file=audio_file,
                    response_format="json",
                )
            )

    except Exception as error:

        raise RuntimeError(
            "Erreur transcription OpenAI : "
            f"{type(error).__name__}: {error}"
        ) from error

    # --------------------------------------------------------
    # TEXTE
    # --------------------------------------------------------

    text = _clean_text(
        getattr(
            response,
            "text",
            "",
        )
    )

    # --------------------------------------------------------
    # FORMAT COMPATIBLE VIRALCOACH
    # --------------------------------------------------------

    return {
        "text": text,
        "texte": text,
        "transcription": text,
        "transcript": text,
        "segments": [],
        "model": DEFAULT_TRANSCRIBE_MODEL,
        "provider": "openai",
    }