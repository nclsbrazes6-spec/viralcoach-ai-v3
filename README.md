# ViralCoach AI V3

API vidéo pour Make / Telegram.

Fonctions :
- reçoit un MP4
- extrait l'audio
- extrait des images
- récupère les métadonnées
- renvoie les URLs à Make

## Déploiement Render

1. Crée un repository GitHub.
2. Upload tous ces fichiers décompressés.
3. Va sur Render.
4. New > Web Service.
5. Connecte le repo.
6. Choisis Docker.
7. Ajoute les variables :
   - APP_BASE_URL=https://ton-api.onrender.com
   - MAX_FRAMES=12
   - FPS_EXTRACT=1
8. Deploy.

## Test

Ouvre :

https://ton-api.onrender.com/

Tu dois voir :

```json
{"status":"ok","name":"ViralCoach AI V3"}
```

## Endpoint principal

POST /api/process-video

Form-data :
- video : fichier MP4
- fps : 1
- max_frames : 12
