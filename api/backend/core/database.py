from sqlalchemy import create_engine, text
from api.backend.core.config import DATABASE_URL
import pandas as pd
import json
import os
import hashlib

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={
        "client_encoding": "utf8",
        "options": "-c client_encoding=utf8"
    }
)

def init_db():
    with engine.begin() as conn:
        # Table users
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Table prediction_logs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prediction_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                username VARCHAR(50),
                client_id INTEGER,
                features JSONB,
                probabilite_defaut FLOAT,
                risque INTEGER,
                execution_time_ms FLOAT,
                status_code INTEGER,
                error_message TEXT
            )
        """))

        conn.execute(text("""
            ALTER TABLE prediction_logs 
            ADD COLUMN IF NOT EXISTS username VARCHAR(50)
        """))

        # Table reference_snapshots
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reference_snapshots (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_hash VARCHAR(64),
                means JSONB
            )
        """))

def save_reference_snapshot():
    """Sauvegarde les moyennes du fichier df_home_credit.pkl au premier lancement"""
    from api.backend.core.config import DATA_PATH
    
    if not os.path.exists(DATA_PATH):
        print("DATA_PATH introuvable, snapshot ignoré")
        return
    
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT 1 FROM reference_snapshots LIMIT 1")).fetchone()
        if exists:
            print("Snapshot déjà existant")
            return
        
        df = pd.read_pickle(DATA_PATH)
        means = df.select_dtypes(include="number").mean().to_dict()
        file_hash = hashlib.md5(open(DATA_PATH, "rb").read()).hexdigest()
        
        conn.execute(text("""
            INSERT INTO reference_snapshots (file_hash, means)
            VALUES (:hash, :means)
        """), {"hash": file_hash, "means": json.dumps(means)})
        print("Snapshot de référence créé")