from pathlib import Path

from faster_whisper import WhisperModel


HALLUCINATIONS = {
    "sous-titres réalisés par la communauté d'amara.org",
    "sous-titres par la communauté d'amara.org",
    "merci d'avoir regardé cette vidéo",
    "merci d'avoir regardé",
}


model = WhisperModel(
    "tiny",
    device="cpu",
    compute_type="int8",
)


def transcribe(audio_path: str) -> str:
    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(f"Fichier audio introuvable : {path}")

    segments, _ = model.transcribe(
        str(path),
        language="fr",
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 250,
        },
        beam_size=5,
        condition_on_previous_text=False,
    )

    texts = []

    for segment in segments:
        text = segment.text.strip()
        normalized = text.lower().rstrip(".!?")

        if segment.no_speech_prob > 0.60 or segment.avg_logprob < -1.0:
            continue

        if normalized in HALLUCINATIONS:
            continue

        if text and (not texts or text != texts[-1]):
            texts.append(text)

    return " ".join(texts)