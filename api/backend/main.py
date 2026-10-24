from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import pickle
import pandas as pd
import numpy as np
from contextlib import asynccontextmanager
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "learning_models", "modele_lgbm.pkl")
DATA_PATH = os.path.join(BASE_DIR, "df_home_credit.pkl")

model = None
df = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, df
    # Chargement du modèle (obligatoire)
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        print("Modèle chargé")
    else:
        print(f"Modèle non trouvé : {MODEL_PATH}")

    # Chargement des données (optionnel)
    if os.path.exists(DATA_PATH):
        df = pd.read_pickle(DATA_PATH)
        print("Données chargées")
    else:
        print(f"Données non trouvées : {DATA_PATH} (mode features uniquement)")
        df = None

    yield
    model = None
    df = None

app = FastAPI(title="API Scoring Home Credit", lifespan=lifespan)

class PredictionRequest(BaseModel):
    client_id: Optional[int] = None
    features: Optional[Dict[str, Any]] = None

class PredictionResponse(BaseModel):
    client_id: Optional[int] = None
    probabilite_defaut: float
    risque: int

@app.get("/")
def root():
    return {"message": "API Scoring Home Credit"}

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="Modèle non chargé")

    feature_names = [str(f) for f in model.feature_names_in_]

    if request.client_id is not None:
        if df is None:
            raise HTTPException(status_code=503, detail="Données non disponibles")
        client = df[df["SK_ID_CURR"] == request.client_id]
        if client.empty:
            raise HTTPException(status_code=404, detail=f"Client {request.client_id} non trouvé")
        X = [client[name].iloc[0] if name in client.columns else np.nan for name in feature_names]
        X = np.array([X])
        client_id = request.client_id

    elif request.features is not None:
        X = [request.features.get(name, np.nan) for name in feature_names]
        X = np.array([X])
        client_id = None

    else:
        raise HTTPException(status_code=400, detail="Fournir soit client_id, soit features")

    proba = float(model.predict_proba(X)[0, 1])
    risque = 1 if proba >= 0.5 else 0

    return {
        "client_id": client_id,
        "probabilite_defaut": round(proba, 4),
        "risque": risque
    }