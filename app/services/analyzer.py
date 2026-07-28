import re
import unicodedata
from collections import Counter


STOPWORDS = {
    "alors", "avec", "avoir", "bonjour", "cette", "comme", "dans", "des",
    "elle", "elles", "encore", "est", "faire", "fait", "fois", "ici", "ils",
    "mais", "nous", "notre", "pour", "plus", "que", "qui", "sans", "ses",
    "sur", "tes", "toi", "ton", "tous", "tout", "une", "vous", "votre",
}

HOOK_MARKERS = {
    "attention", "astuce", "erreur", "jamais", "pourquoi", "regarde",
    "secret", "stop", "voici", "comment", "incroyable", "important",
}


def _words(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", normalized)


def _sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text.strip())
        if sentence.strip()
    ]


def _clamp(value: float) -> int:
    return max(1, min(10, round(value)))


def _summary(sentences: list[str]) -> str:
    return " ".join(sentences[:2])[:320]


def analyze_transcription(transcription: str) -> dict:
    text = (transcription or "").strip()

    if not text:
        return {
            "résumé": "Aucune parole fiable n'a été détectée.",
            "note_hook": 0,
            "note_clarte": 0,
            "note_potentiel_viral": 0,
            "points_forts": [],
            "points_faibles": [
                "L'audio ne contient pas assez de parole claire pour être analysé.",
            ],
            "hooks_améliores": [],
            "description_tiktok": "",
            "hashtags": [],
        }

    words = _words(text)
    sentences = _sentences(text)
    word_count = len(words)
    opening_words = words[:25]

    hook_hits = sum(word in HOOK_MARKERS for word in opening_words)
    has_question = "?" in (sentences[0] if sentences else "")
    hook_score = _clamp(3 + hook_hits * 1.5 + (2 if has_question else 0) + (1 if word_count >= 20 else 0))

    average_sentence_length = word_count / len(sentences) if sentences else word_count
    clarity_score = _clamp(
        9 - max(0, average_sentence_length - 18) * 0.2 - (2 if word_count < 10 else 0)
    )
    viral_score = _clamp(
        hook_score * 0.45 + clarity_score * 0.35 + (2 if 25 <= word_count <= 180 else 1)
    )

    strengths = []
    weaknesses = []

    if hook_score >= 7:
        strengths.append("L'ouverture attire rapidement l'attention.")
    else:
        weaknesses.append("L'ouverture manque d'une promesse ou d'une curiosité immédiate.")

    if clarity_score >= 7:
        strengths.append("Le message est globalement simple et facile à suivre.")
    else:
        weaknesses.append("Les phrases gagneraient à être plus courtes et plus directes.")

    if 25 <= word_count <= 180:
        strengths.append("La quantité de contenu est adaptée à une vidéo courte.")
    elif word_count < 25:
        weaknesses.append("La transcription est trop courte pour développer clairement la valeur promise.")
    else:
        weaknesses.append("Le discours est dense pour une vidéo courte ; supprime les répétitions.")

    if not strengths:
        strengths.append("Le sujet peut servir de base à une version plus directe.")
    if not weaknesses:
        weaknesses.append("Ajoute une preuve concrète ou un appel à l'action plus net.")

    content_words = [word for word in words if len(word) > 3 and word not in STOPWORDS]
    keywords = [word for word, _ in Counter(content_words).most_common(5)]
    topic = " ".join(keywords[:3]) or "ce sujet"

    hooks = [
        f"Tu fais peut-être cette erreur avec {topic} — voici comment la corriger.",
        f"Voici la méthode la plus simple pour améliorer {topic} dès aujourd'hui.",
        f"Avant de continuer avec {topic}, regarde ces 3 points essentiels.",
    ]

    hashtags = ["#tiktokfr", "#conseils", "#createurcontenu"]
    hashtags.extend(f"#{word}" for word in keywords[:3])

    return {
        "résumé": _summary(sentences),
        "note_hook": hook_score,
        "note_clarte": clarity_score,
        "note_potentiel_viral": viral_score,
        "points_forts": strengths,
        "points_faibles": weaknesses,
        "hooks_améliores": hooks,
        "description_tiktok": (
            f"{_summary(sentences)}\n\n"
            "Dis-moi en commentaire ce que tu veux améliorer dans ta prochaine vidéo."
        ),
        "hashtags": list(dict.fromkeys(hashtags)),
            }