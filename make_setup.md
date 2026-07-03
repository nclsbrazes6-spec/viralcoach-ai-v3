# Configuration Make

## Scénario recommandé

Telegram Watch Updates
↓
Telegram Download a File
↓
HTTP Make a request
↓
OpenAI Transcribe audio
↓
OpenAI Vision
↓
OpenAI Final Analysis
↓
Telegram Send Message

## Module HTTP

Méthode : POST  
URL : https://ton-api.onrender.com/api/process-video

Body type : Multipart/form-data

Champs :
- video : fichier Telegram téléchargé
- fps : 1
- max_frames : 12

La réponse contient :
- audio_url
- frames[]
- metadata_url
