# Devcontainer / Codespaces Setup

## Basis

Verwende `mcr.microsoft.com/devcontainers/base:ubuntu`  
oder den Codex-Container „universal“ mit vorinstallierten Paketen.

## Schritte

1. `.devcontainer/devcontainer.json`
   ```json
   {
     "name": "mitschreiber",
     "image": "mcr.microsoft.com/devcontainers/base:ubuntu",
     "features": {
       "ghcr.io/devcontainers/features/python:1": { "version": "3.11" }
     },
     "postCreateCommand": "bash .devcontainer/postCreate.sh"
   }
```

2. `.devcontainer/postCreate.sh`

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   sudo apt-get update && sudo apt-get install -y just
   uv sync --frozen || uv sync
   ```
3. `.env.example` kopieren und Secrets anpassen
4. Start: `just dev`

## Secrets

| Name                          | Beschreibung                |
| ----------------------------- | --------------------------- |
| `LEITSTAND_INGEST_URL`        | Ziel-Endpoint               |
| `LEITSTAND_TOKEN`             | Auth-Token                  |
| `LEITSTAND_MTLS_CERT` / `KEY` | Base64-codierte Zertifikate |
| `OPENAI_API_KEY`              | optional für Embeddings     |
