from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import pickle
import pandas as pd
import numpy as np
from contextlib import asynccontextmanager
import os

# Chemins
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "learning_models", "modele_lgbm.pkl")
DATA_PATH = os.path.join(BASE_DIR, "df_home_credit.pkl")

model = None
df = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, df
    # Chargement du modèle
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    # Chargement des données
    df = pd.read_pickle(DATA_PATH)
    print("Modèle et données chargés")
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
    return {"message": "API Scoring Home Credit - modèle et données chargés"}

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    if model is None or df is None:
        raise HTTPException(status_code=500, detail="Modèle ou données non chargés")

    feature_names = [str(f) for f in model.feature_names_in_]

    # Cas 1 : on reçoit un client_id
    if request.client_id is not None:
        client = df[df["SK_ID_CURR"] == request.client_id]
        if client.empty:
            raise HTTPException(status_code=404, detail=f"Client {request.client_id} non trouvé")
        
        # On construit le vecteur de features
        X = []
        for name in feature_names:
            if name in client.columns:
                X.append(client[name].iloc[0])
            else:
                X.append(np.nan)
        X = np.array([X])
        client_id = request.client_id

    # Cas 2 : on reçoit directement les features
    elif request.features is not None:
        X = []
        for name in feature_names:
            X.append(request.features.get(name, np.nan))
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