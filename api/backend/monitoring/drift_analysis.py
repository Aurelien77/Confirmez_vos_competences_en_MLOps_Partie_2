import pandas as pd
import json
import os
from sqlalchemy import create_engine, text

def generate_drift_report() -> str:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    DATA_PATH = os.path.join(BASE_DIR, "df_home_credit.pkl")
    
    if not os.path.exists(DATA_PATH):
        return "<h1>Fichier de référence introuvable</h1>"
    
    df_ref = pd.read_pickle(DATA_PATH)
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/scoring")
    engine = create_engine(DATABASE_URL)
    
    query = text("""
        SELECT features FROM prediction_logs
        WHERE status_code = 200 AND features IS NOT NULL
        ORDER BY timestamp DESC LIMIT 1000
    """)
    logs = pd.read_sql(query, engine)
    
    if logs.empty:
        return "<h1>Pas de données de production</h1><p>Fais quelques prédictions avec features.</p>"
    
    # Gère les deux cas : str JSON ou dict déjà parsé
    def safe_parse(x):
        if isinstance(x, dict):
            return x
        if isinstance(x, str):
            try:
                return json.loads(x)
            except:
                return {}
        return {}
    
    df_prod = pd.json_normalize(logs["features"].apply(safe_parse))
    
    if df_prod.empty:
        return "<h1>Pas de features exploitables</h1>"
    
    common = [c for c in df_ref.columns if c in df_prod.columns][:8]
    
    html = """
    <h1>Analyse du Data Drift</h1>
    <p>Comparaison des moyennes (référence vs production)</p>
    <table border="1" cellpadding="8" style="border-collapse:collapse;">
    <tr style="background:#f0f0f0;"><th>Feature</th><th>Moyenne Réf.</th><th>Moyenne Prod.</th><th>Écart %</th></tr>
    """
    
    for col in common:
        if pd.api.types.is_numeric_dtype(df_ref[col]) and pd.api.types.is_numeric_dtype(df_prod[col]):
            mean_ref = df_ref[col].mean()
            mean_prod = df_prod[col].mean()
            diff = abs(mean_prod - mean_ref) / (abs(mean_ref) + 1e-8) * 100
            color = "red" if diff > 20 else "orange" if diff > 10 else "green"
            html += f"<tr><td>{col}</td><td>{mean_ref:.2f}</td><td>{mean_prod:.2f}</td><td style='color:{color}'>{diff:.1f}%</td></tr>"
    
    html += "</table><p style='margin-top:20px;font-size:14px;color:#666;'>Écart > 20% en rouge, > 10% en orange</p>"
    return html