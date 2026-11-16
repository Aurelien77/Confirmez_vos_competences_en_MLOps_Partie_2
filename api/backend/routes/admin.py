from fastapi import APIRouter, Depends
from sqlalchemy import text
from api.backend.core.database import engine
from api.backend.core.security import get_current_user, require_admin

router = APIRouter()

@router.get("/my-predictions", summary="Historique des prédictions de l'utilisateur")
def my_predictions(user=Depends(get_current_user)):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT timestamp, client_id, probabilite_defaut, risque, execution_time_ms, status_code
            FROM prediction_logs
            WHERE username = :username
            ORDER BY timestamp DESC
            LIMIT 100
        """), {"username": user["username"]})
        logs = [dict(row._mapping) for row in result]
    return {"predictions": logs}

@router.get("/admin/dashboard", summary="Tableau de bord administrateur")
def admin_dashboard(user=Depends(require_admin)):
    with engine.connect() as conn:
        logs = conn.execute(text("""
            SELECT timestamp, username, client_id, probabilite_defaut, risque, execution_time_ms, status_code
            FROM prediction_logs
            ORDER BY timestamp DESC
            LIMIT 50
        """)).fetchall()

        metrics = conn.execute(text("""
            SELECT COUNT(*) as total, AVG(execution_time_ms) as avg_latency,
                   AVG(probabilite_defaut) as avg_proba,
                   SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors
            FROM prediction_logs
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """)).fetchone()

    return {
        "logs": [dict(r._mapping) for r in logs],
        "metrics": {
            "total_24h": metrics[0] or 0,
            "avg_latency_ms": round(float(metrics[1] or 0), 2),
            "avg_proba": round(float(metrics[2] or 0), 4),
            "errors_24h": metrics[3] or 0
        }
    }