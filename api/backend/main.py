from fastapi import FastAPI
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import pickle
import pandas as pd
import os
from api.backend.core.config import MODEL_PATH, DATA_PATH, FRONTEND_PATH
from api.backend.core.database import init_db, save_reference_snapshot
from api.backend.routes import auth, predict, admin
from fastapi.staticfiles import StaticFiles
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    save_reference_snapshot()
    
    model = None
    df = None

    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        print("Modèle chargé")
    else:
        print(f"Modèle non trouvé : {MODEL_PATH}")

    if os.path.exists(DATA_PATH):
        df = pd.read_pickle(DATA_PATH)
        print("Données chargées")
    else:
        print(f"Données non trouvées : {DATA_PATH}")

    app.state.model = model
    app.state.df = df
    yield

app = FastAPI(
    title="API Scoring Home Credit",
    description="API de scoring de risque de défaut pour les clients Home Credit.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/", summary="Vérifier que l'API est en ligne")
def root():
    return {"message": "API Scoring Home Credit"}

@app.get("/ui", response_class=FileResponse, include_in_schema=False)
def serve_frontend():
    return FileResponse(FRONTEND_PATH)

app.include_router(auth.router)
app.include_router(predict.router)
app.include_router(admin.router)
app.mount("/static", StaticFiles(directory="api/frontend"), name="static")