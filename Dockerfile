# ── Stage 1 : Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Installer les dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2 : Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copier les dépendances installées depuis le builder
COPY --from=builder /install /usr/local

# Copier le code source et les données
COPY src/ ./src/
COPY data/ ./data/

# Répertoire de persistance ChromaDB (monté en volume en prod)
RUN mkdir -p /app/chroma_db

# Variables d'environnement par défaut (surchargées via --env-file ou -e)
ENV DATA_DIR=/app/data \
    CHROMA_PERSIST_DIR=/app/chroma_db \
    HOST=0.0.0.0 \
    PORT=8000

# Exposer le port de l'API
EXPOSE 8000

# Healthcheck intégré Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Démarrage de l'API
CMD ["sh", "-c", "uvicorn src.api.main:app --host $HOST --port $PORT --workers 1"]
