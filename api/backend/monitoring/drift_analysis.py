import pandas as pd
import json
import os
from sqlalchemy import create_engine, text

def generate_drift_report() -> str:
    from api.backend.core.config import DATA_PATH, DATABASE_URL
    
    if not os.path.exists(DATA_PATH):
        return "<h1>Fichier de référence introuvable</h1>"
    
    df_ref = pd.read_pickle(DATA_PATH)
    engine = create_engine(DATABASE_URL)
    
    # ========== 1. Drift live (référence vs production) ==========
    query = text("""
        SELECT features FROM prediction_logs
        WHERE status_code = 200 AND features IS NOT NULL
        ORDER BY timestamp DESC LIMIT 1000
    """)
    logs = pd.read_sql(query, engine)
    
    html_live = ""
    if logs.empty:
        html_live = "<p>Pas de données de production. Fais quelques prédictions.</p>"
    else:
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
        common = [c for c in df_ref.columns if c in df_prod.columns][:8]
        
        html_live = """
        <h2>Drift Live (référence vs production)</h2>
        <table border="1" cellpadding="8" style="border-collapse:collapse;">
        <tr style="background:#f0f0f0;"><th>Feature</th><th>Moyenne Réf.</th><th>Moyenne Prod.</th><th>Écart %</th></tr>
        """
        for col in common:
            if pd.api.types.is_numeric_dtype(df_ref[col]) and pd.api.types.is_numeric_dtype(df_prod[col]):
                mean_ref = df_ref[col].mean()
                mean_prod = df_prod[col].mean()
                diff = abs(mean_prod - mean_ref) / (abs(mean_ref) + 1e-8) * 100
                color = "red" if diff > 20 else "orange" if diff > 10 else "green"
                html_live += f"<tr><td>{col}</td><td>{mean_ref:.2f}</td><td>{mean_prod:.2f}</td><td style='color:{color}'>{diff:.1f}%</td></tr>"
        html_live += "</table>"
    
    # ========== 2. Drift fichier (snapshot original vs fichier actuel) ==========
    html_file = ""
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT means FROM reference_snapshots ORDER BY created_at LIMIT 1
        """)).fetchone()
    
    if not row:
        html_file = "<p>Pas de snapshot de référence (redémarre l'API une fois).</p>"
    else:
        means_ref = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        means_current = df_ref.select_dtypes(include="number").mean().to_dict()
        
        html_file = """
        <h2>Drift Fichier (snapshot original vs fichier actuel)</h2>
        <table border="1" cellpadding="8" style="border-collapse:collapse;">
        <tr style="background:#f0f0f0;"><th>Feature</th><th>Moyenne Originale</th><th>Moyenne Actuelle</th><th>Écart %</th></tr>
        """
        for col in list(means_ref.keys())[:8]:
            if col in means_current:
                mean_orig = means_ref[col]
                mean_curr = means_current[col]
                diff = abs(mean_curr - mean_orig) / (abs(mean_orig) + 1e-8) * 100
                color = "red" if diff > 20 else "orange" if diff > 10 else "green"
                html_file += f"<tr><td>{col}</td><td>{mean_orig:.2f}</td><td>{mean_curr:.2f}</td><td style='color:{color}'>{diff:.1f}%</td></tr>"
        html_file += "</table>"
    
    html = f"""
    <h1>Analyse de Data Drift</h1>
    {html_live}
    <br><hr><br>
    {html_file}
    <p style='margin-top:20px;font-size:14px;color:#666;'>Écart > 20% en rouge, > 10% en orange</p>
    """
    return html