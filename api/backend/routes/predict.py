from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd
import time
import json
from sqlalchemy import text
from api.backend.core.database import engine
from api.backend.core.security import get_current_user

router = APIRouter()

class PredictionRequest(BaseModel):
    client_id: Optional[int] = None
    features: Optional[Dict[str, Any]] = None

class PredictionResponse(BaseModel):
    client_id: Optional[int] = None
    probabilite_defaut: float
    risque: int

def log_prediction(username, client_id, features_dict, proba, risque, exec_time, status, error):
    """Écriture asynchrone des logs pour ne pas bloquer la réponse."""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO prediction_logs 
                (username, client_id, features, probabilite_defaut, risque, execution_time_ms, status_code, error_message)
                VALUES (:username, :client_id, :features, :proba, :risque, :exec_time, :status, :error)
            """), {
                "username": username,
                "client_id": client_id,
                "features": json.dumps(features_dict) if features_dict else None,
                "proba": proba,
                "risque": risque,
                "exec_time": exec_time,
                "status": status,
                "error": error
            })
            conn.commit()
    except Exception:
        pass

@router.post("/predict", response_model=PredictionResponse)
def predict(
    request: PredictionRequest, 
    req: Request, 
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user)
):
    model = req.app.state.model
    client_dict = req.app.state.client_dict

    if model is None:
        raise HTTPException(status_code=500, detail="Modèle non chargé")

    start = time.time()
    feature_names = [str(f) for f in model.feature_names_in_]
    features_dict = None
    client_id = None
    proba = 0.0
    risque = 0
    status = 200
    error = None

    try:
        t1 = time.time()
        if request.client_id is not None:
            if client_dict is None:
                raise HTTPException(status_code=503, detail="Données non disponibles")

            client = client_dict.get(request.client_id)
            if client is None:
                raise HTTPException(status_code=404, detail=f"Client {request.client_id} non trouvé")

            features_dict = {}
            X = []
            for name in feature_names:
                val = client.get(name, np.nan)
                X.append(val)
                features_dict[name] = float(val) if pd.notna(val) else None
            X = np.array([X])
            client_id = request.client_id
            print(f"[TIMING] Lookup client: {(time.time() - t1)*1000:.1f} ms")

        elif request.features is not None:
            features_dict = request.features
            X = [request.features.get(name, np.nan) for name in feature_names]
            X = np.array([X])
            client_id = None

        else:
            raise HTTPException(status_code=400, detail="Fournir soit client_id, soit features")

        t2 = time.time()
        proba = float(model.predict_proba(X)[0, 1])
        risque = 1 if proba >= 0.5 else 0
        print(f"[TIMING] Prediction: {(time.time() - t2)*1000:.1f} ms")

    except HTTPException as e:
        status = e.status_code
        error = e.detail
        raise
    except Exception as e:
        status = 500
        error = str(e)
        raise HTTPException(status_code=500, detail="Erreur interne")
    finally:
        exec_time = (time.time() - start) * 1000
        print(f"[TIMING] Total avant logging: {exec_time:.1f} ms")
        background_tasks.add_task(
            log_prediction,
            user["username"], client_id, features_dict,
            proba, risque, exec_time, status, error
        )

    return {
        "client_id": client_id,
        "probabilite_defaut": round(proba, 4),
        "risque": risque
    }