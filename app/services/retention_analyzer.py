def analyze_retention(
    analyse_transcription: dict,
    analyse_visuelle: dict,
    analyse_montage: dict,
) -> dict:

    note_hook = analyse_transcription.get(
        "note_hook",
        5,
    )

    note_rythme = analyse_montage.get(
        "note_rythme",
        5,
    )

    retention_montage = analyse_montage.get(
        "retention_estimee_pourcent",
        50,
    )

    note_visuelle = analyse_visuelle.get(
    "note_visuelle_globale",
    analyse_visuelle.get(
        "note_video",
        analyse_visuelle.get(
            "note_visuelle",
            5,
        ),
    ),
)

    # Fusion des différents signaux
    retention_finale = round(
        retention_montage * 0.45
        + note_hook * 10 * 0.30
        + note_visuelle * 10 * 0.25
    )

    retention_finale = max(
        0,
        min(100, retention_finale),
    )

    if retention_finale >= 80:
        niveau = "Excellente"

    elif retention_finale >= 65:
        niveau = "Bonne"

    elif retention_finale >= 50:
        niveau = "Moyenne"

    else:
        niveau = "Faible"

    risques = []
    recommandations = []

    if note_hook < 7:
        risques.append(
            "Le début risque de ne pas retenir suffisamment l'attention."
        )

        recommandations.append(
            "Renforcer les 3 premières secondes avec une promesse ou une curiosité immédiate."
        )

    if note_rythme < 7:
        risques.append(
            "Le rythme du montage peut provoquer une baisse de rétention."
        )

        recommandations.append(
            "Raccourcir les plans trop longs et augmenter la fréquence des changements visuels."
        )

    if note_visuelle < 7:
        risques.append(
            "L'impact visuel est insuffisant pour maintenir l'attention."
        )

        recommandations.append(
            "Utiliser des plans plus forts, plus lumineux ou plus dynamiques."
        )

    if not risques:
        risques.append(
            "Aucun risque majeur détecté automatiquement."
        )

    if not recommandations:
        recommandations.append(
            "Tester plusieurs variantes du hook pour chercher encore plus de rétention."
        )

    return {
        "retention_estimee": retention_finale,
        "niveau_retention": niveau,
        "note_hook": note_hook,
        "note_rythme": note_rythme,
        "note_visuelle": note_visuelle,
        "risques": risques,
        "recommandations": recommandations,
    }