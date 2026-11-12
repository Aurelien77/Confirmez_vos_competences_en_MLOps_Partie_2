FROM python:3.11-slim

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY api/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code de l'application
COPY api/backend/ ./api/backend/
COPY api/frontend/ ./api/frontend/

# Dossier pour les modèles (vide dans l'image, monté en volume)
RUN mkdir -p /app/learning_models

EXPOSE 8000

CMD ["uvicorn", "api.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]