FROM python:3.11-slim

WORKDIR /app

# Installation de la dépendance système pour LightGBM
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copie des dépendances
COPY api/backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copie du code et des fichiers
COPY api/backend/ ./api/backend/
COPY learning_models/ ./learning_models/
COPY df_home_credit.pkl .

EXPOSE 8000

CMD ["uvicorn", "api.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]