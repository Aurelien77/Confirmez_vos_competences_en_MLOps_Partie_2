from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import pickle
import pandas as pd
import numpy as np
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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

# ====================== LIFESPAN ======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, df
    print("Chargement du modèle...")
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    try:
        df = pd.read_pickle(DATA_PATH)
        print("Données chargées")
    except Exception as e:
        print(f"Données non chargées: {e}")
        df = None
    yield
    print("Arrêt de l'API")

# Création de l'application
app = FastAPI(lifespan=lifespan, title="API Scoring Home Credit")

# Montage des fichiers statiques
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "frontend")), name="static")

# ====================== MODELS ======================
class PredictionRequest(BaseModel):
    client_id: Optional[int] = None
    features: Optional[Dict[str, Any]] = None

class PredictionResponse(BaseModel):
    client_id: Optional[int] = None
    probabilite_defaut: float
    risque: int

class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

# ====================== AUTH ======================
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

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
        if username is None:
            raise HTTPException(status_code=401, detail="Token invalide")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT username, is_admin FROM users WHERE username = :username"),
            {"username": username}
        ).fetchone()
    
    if result is None:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    
    return {"username": result[0], "is_admin": result[1]}

def require_admin(user = Depends(get_current_user)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès admin requis")
    return user

# ====================== ROUTES ======================
@app.get("/ui", response_class=FileResponse)
def serve_frontend():
    return FileResponse(FRONTEND_PATH)

@app.get("/")
def root():
    return {"message": "API Scoring Home Credit"}

@app.post("/register")
def register(user: UserCreate):
    hashed = get_password_hash(user.password)
    try:
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO users (username, hashed_password, is_admin) VALUES (:username, :password, false)"),
                {"username": user.username, "password": hashed}
            )
            conn.commit()
        return {"message": "Utilisateur créé"}
    except Exception:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur déjà utilisé")

@app.post("/login", response_model=Token)
def login(user: UserCreate):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT hashed_password FROM users WHERE username = :username"),
            {"username": user.username}
        ).fetchone()
    
    print(f"=== LOGIN DEBUG ===")
    print(f"Username: {user.username}")
    print(f"User found: {result is not None}")
    if result:
        print(f"Hash exists: {result[0] is not None}")
        print(f"Hash start: {str(result[0])[:30]}...")
        print(f"Password verify: {verify_password(user.password, result[0])}")
    print(f"===================")
    
    if not result or not verify_password(user.password, result[0]):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/change-password")
def change_password(data: PasswordChange, user=Depends(get_current_user)):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT hashed_password FROM users WHERE username = :username"),
            {"username": user["username"]}
        ).fetchone()
    
    if not result or not verify_password(data.old_password, result[0]):
        raise HTTPException(status_code=400, detail="Ancien mot de passe incorrect")
    
    new_hash = get_password_hash(data.new_password)
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE users SET hashed_password = :password WHERE username = :username"),
            {"password": new_hash, "username": user["username"]}
        )
        conn.commit()
    
    return {"message": "Mot de passe modifié"}

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest, user=Depends(get_current_user)):
    start_total = time.perf_counter()

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

    # Temps d'inférence
    start_inference = time.perf_counter()
    proba = float(model.predict_proba(X)[0, 1])
    inference_time_ms = (time.perf_counter() - start_inference) * 1000

    total_time_ms = (time.perf_counter() - start_total) * 1000
    risque = 1 if proba >= 0.5 else 0

    # Logging
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO prediction_logs 
                (username, client_id, features, probabilite_defaut, risque, 
                 execution_time_ms, inference_time_ms, status_code, error_message)
                VALUES (:username, :client_id, :features, :proba, :risque, 
                        :exec_time, :inf_time, :status, :error)
            """), {
                "username": user["username"],
                "client_id": client_id,
                "features": json.dumps(request.features) if request.features else None,
                "proba": proba,
                "risque": risque,
                "exec_time": round(total_time_ms, 2),
                "inf_time": round(inference_time_ms, 2),
                "status": 200,
                "error": None
            })
            conn.commit()
    except Exception as e:
        print(f"Erreur logging: {e}")

    return {
        "client_id": client_id,
        "probabilite_defaut": round(proba, 4),
        "risque": risque
    }

@app.get("/my-predictions")
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

@app.get("/admin/dashboard")
def admin_dashboard(user=Depends(require_admin)):
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