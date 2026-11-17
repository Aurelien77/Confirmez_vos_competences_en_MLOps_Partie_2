from sqlalchemy import create_engine, text
from api.backend.core.config import DATABASE_URL

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

        # Ajoute la colonne username si elle n'existe pas (migration)
        conn.execute(text("""
            ALTER TABLE prediction_logs 
            ADD COLUMN IF NOT EXISTS username VARCHAR(50)
        """))