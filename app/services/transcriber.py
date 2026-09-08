"""Transcription française V5 pour ViralCoach AI."""

import re
from pathlib import Path

from faster_whisper import WhisperModel


# Le modèle "small" reste raisonnable sur CPU. Passer à "medium" améliore
# généralement la précision, mais ralentit fortement l'analyse sans GPU.
model = WhisperModel(
    "large-v3-turbo",
    device="cpu",
    compute_type="int8",
    cpu_threads=8,
)


def _clean_text(text: str) -> str:
    """Nettoie la ponctuation et les répétitions produites par Whisper."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([!?.,])\1{2,}", r"\1", text)
    return text.strip()


def _deduplicate_segments(texts: list[str]) -> list[str]:
    """Supprime uniquement les segments consécutifs presque identiques."""
    result = []

    for text in texts:
        normalised = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

        if not normalised:
            continue

        if result:
            previous = re.sub(
                r"[^a-z0-9]+",
                " ",
                result[-1].lower(),
            ).strip()

            if normalised == previous:
                continue

        result.append(text)

    return result


def transcribe(audio_path: str) -> str:
    """Transcrit un fichier audio en français sans changer l'API existante."""
    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Fichier audio introuvable : {path}"
        )

    segments, _ = model.transcribe(
        str(path),
        language="fr",
        task="transcribe",
        beam_size=5,
        temperature=0.0,
        vad_filter=True,
        vad_parameters={
            "threshold": 0.5,
            "min_speech_duration_ms": 200,
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 250,
        },
        condition_on_previous_text=False,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
        no_speech_threshold=0.6,
        initial_prompt=(
            "Transcription fidèle en français. "
            "Respecter les noms propres, les nombres et la ponctuation. "
            "Ne pas traduire et ne pas inventer de texte pendant les silences."
        ),
    )

    texts = []

    for segment in segments:
        # Rejette un segment seulement quand silence probable et confiance faible
        # sont présents ensemble, afin de ne pas supprimer une parole utile.
        if (
            segment.no_speech_prob > 0.75
            and segment.avg_logprob < -1.0
        ):
            continue

        text = _clean_text(segment.text)

        if text:
            texts.append(text)

    texts = _deduplicate_segments(texts)

    return _clean_text(" ".join(texts))
