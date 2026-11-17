import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

MODEL_PATH = os.path.join(BASE_DIR, "learning_models", "modele_lgbm.pkl")
DATA_PATH = os.path.join(BASE_DIR, "df_home_credit.pkl")
FRONTEND_PATH = os.path.join(BASE_DIR, "api", "frontend", "index.html")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/scoring")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24