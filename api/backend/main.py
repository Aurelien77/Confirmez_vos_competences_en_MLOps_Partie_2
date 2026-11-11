from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import pickle
import pandas as pd
import numpy as np
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
import os
import time
import json
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ====================== CONFIG ======================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "learning_models", "modele_lgbm.pkl")
DATA_PATH = os.path.join(BASE_DIR, "df_home_credit.pkl")
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/scoring")
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"client_encoding": "utf8"}
)

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

model = None
df = None

# ====================== AUTH ======================
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise HTTPException(status_code=401, detail="Token invalide")
        return {"username": username, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

def require_admin(user = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé à l'administrateur")
    return user

# ====================== LOGGING ======================
def log_prediction(username, client_id, features, proba, risque, exec_time_ms, status_code=200, error_message=None):
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO prediction_logs 
                (username, client_id, features, probabilite_defaut, risque, execution_time_ms, status_code, error_message)
                VALUES (:username, :client_id, :features, :proba, :risque, :exec_time, :status, :error)
            """), {
                "username": username,
                "client_id": client_id,
                "features": json.dumps(features) if features else None,
                "proba": proba,
                "risque": risque,
                "exec_time": exec_time_ms,
                "status": status_code,
                "error": error_message
            })
            conn.commit()
    except Exception as e:
        print(f"[LOG ERROR] {e}")

# ====================== LIFESPAN ======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, df

    # Initialisation base de données (tolérante aux erreurs)
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role VARCHAR(20) DEFAULT 'user'
                );
                CREATE TABLE IF NOT EXISTS prediction_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    username VARCHAR(50),
                    client_id INTEGER,
                    features JSONB,
                    probabilite_defaut FLOAT,
                    risque INTEGER,
                    execution_time_ms FLOAT,
                    status_code INTEGER,
                    error_message TEXT
                );
            """))
            conn.commit()
        print("Base de données initialisée")
    except Exception as e:
        print(f"[WARNING] Impossible de se connecter à la base : {e}")

    # Chargement du modèle
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        print("Modèle chargé")
    else:
        print(f"Modèle non trouvé : {MODEL_PATH}")

    # Chargement des données
    if os.path.exists(DATA_PATH):
        df = pd.read_pickle(DATA_PATH)
        print("Données chargées")
    else:
        df = None
        print("Données non chargées")

    yield
    model = None
    df = None

app = FastAPI(title="API Scoring Home Credit", lifespan=lifespan)

# ====================== MODELS ======================
class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class PredictionRequest(BaseModel):
    client_id: Optional[int] = None
    features: Optional[Dict[str, Any]] = None

class PredictionResponse(BaseModel):
    client_id: Optional[int] = None
    probabilite_defaut: float
    risque: int

# ====================== ROUTES ======================
@app.post("/register")
def register(request: RegisterRequest):
    if len(request.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Le nom d'utilisateur doit contenir au moins 3 caractères")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caractères")
    if len(request.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Le mot de passe est trop long (maximum 72 caractères)")

    password_to_hash = request.password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    hashed = pwd_context.hash(password_to_hash)
    role = "admin" if request.username.lower() == "admin" else "user"

    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO users (username, password_hash, role)
                VALUES (:username, :password_hash, :role)
            """), {"username": request.username.strip(), "password_hash": hashed, "role": role})
            conn.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="Ce nom d'utilisateur est déjà utilisé")

    return {"message": "Compte créé avec succès", "role": role}

@app.post("/login")
def login(request: LoginRequest):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT password_hash, role FROM users WHERE username = :username"),
            {"username": request.username}
        ).fetchone()

    if not result or not pwd_context.verify(request.password, result[0]):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    token = create_access_token({"sub": request.username, "role": result[1]})
    return {"access_token": token, "token_type": "bearer", "role": result[1]}

@app.post("/change-password")
def change_password(request: ChangePasswordRequest, user = Depends(get_current_user)):
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit contenir au moins 6 caractères")
    if len(request.new_password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe est trop long")

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT password_hash FROM users WHERE username = :username"),
            {"username": user["username"]}
        ).fetchone()

    if not result or not pwd_context.verify(request.old_password, result[0]):
        raise HTTPException(status_code=400, detail="Ancien mot de passe incorrect")

    new_hash = pwd_context.hash(request.new_password.encode("utf-8")[:72].decode("utf-8", errors="ignore"))

    with engine.connect() as conn:
        conn.execute(
            text("UPDATE users SET password_hash = :hash WHERE username = :username"),
            {"hash": new_hash, "username": user["username"]}
        )
        conn.commit()

    return {"message": "Mot de passe modifié avec succès"}

@app.get("/me")
def get_me(user = Depends(get_current_user)):
    return user

@app.get("/ui", response_class=FileResponse)
def serve_frontend():
    return FileResponse(FRONTEND_PATH)

@app.get("/")
def root():
    return {"message": "API Scoring Home Credit"}

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest, user = Depends(get_current_user)):
    start = time.time()
    username = user["username"]
    client_id = request.client_id
    features = request.features

    try:
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
        elif request.features is not None:
            X = [request.features.get(name, np.nan) for name in feature_names]
            X = np.array([X])
            client_id = None
        else:
            raise HTTPException(status_code=400, detail="Fournir soit client_id, soit features")

        proba = float(model.predict_proba(X)[0, 1])
        risque = 1 if proba >= 0.5 else 0
        exec_time = (time.time() - start) * 1000

        log_prediction(username, client_id, features, proba, risque, exec_time)

        return {
            "client_id": client_id,
            "probabilite_defaut": round(proba, 4),
            "risque": risque
        }

    except HTTPException as e:
        exec_time = (time.time() - start) * 1000
        log_prediction(username, client_id, features, None, None, exec_time, e.status_code, e.detail)
        raise
    except Exception as e:
        exec_time = (time.time() - start) * 1000
        log_prediction(username, client_id, features, None, None, exec_time, 500, str(e))
        raise HTTPException(status_code=500, detail="Erreur interne")

@app.get("/my-predictions")
def my_predictions(user = Depends(get_current_user)):
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

@app.get("/admin/dashboard")
def admin_dashboard(user = Depends(require_admin)):
    with engine.connect() as conn:
        logs = conn.execute(text("""
            SELECT timestamp, username, client_id, probabilite_defaut, risque, execution_time_ms, status_code
            FROM prediction_logs
            ORDER BY timestamp DESC
            LIMIT 50
        """)).fetchall()

        metrics = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                AVG(execution_time_ms) as avg_latency,
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