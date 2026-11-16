from fastapi import HTTPException
import numpy as np
import time
import json
from sqlalchemy import text
from api.backend.core.database import engine

def predict_logic(request_data, user, model, df):
    start = time.time()
    status_code = 200
    error_msg = None
    proba = None
    risque = None
    client_id = request_data.client_id

    try:
        if model is None:
            raise HTTPException(status_code=500, detail="Modèle non chargé")

        feature_names = [str(f) for f in model.feature_names_in_]

        if request_data.client_id is not None:
            if df is None:
                raise HTTPException(status_code=503, detail="Données non disponibles")
            client = df[df["SK_ID_CURR"] == request_data.client_id]
            if client.empty:
                raise HTTPException(status_code=404, detail=f"Client {request_data.client_id} non trouvé")
            X = [client[name].iloc[0] if name in client.columns else np.nan for name in feature_names]
            X = np.array([X])
        elif request_data.features is not None:
            X = [request_data.features.get(name, np.nan) for name in feature_names]
            X = np.array([X])
        else:
            raise HTTPException(status_code=400, detail="Fournir soit client_id, soit features")

        proba = float(model.predict_proba(X)[0, 1])
        risque = 1 if proba >= 0.5 else 0

    except HTTPException as e:
        status_code = e.status_code
        error_msg = e.detail
        raise
    except Exception as e:
        status_code = 500
        error_msg = str(e)
        raise HTTPException(status_code=500, detail="Erreur interne")
    finally:
        exec_time = (time.time() - start) * 1000
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO prediction_logs
                    (username, client_id, features, probabilite_defaut, risque, execution_time_ms, status_code, error_message)
                    VALUES (:username, :client_id, :features, :proba, :risque, :exec_time, :status, :error)
                """), {
                    "username": user["username"],
                    "client_id": client_id,
                    "features": json.dumps(request_data.features) if request_data.features else None,
                    "proba": proba,
                    "risque": risque,
                    "exec_time": exec_time,
                    "status": status_code,
                    "error": error_msg
                })
        except Exception:
            pass

    return {
        "client_id": client_id,
        "probabilite_defaut": round(proba, 4),
        "risque": risque
    }