import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
import os

# Récupère la DATABASE_URL depuis l'environnement
# (définie dans le docker-compose ou dans un .env)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("La variable d'environnement DATABASE_URL n'est pas définie")

engine = create_engine(
    DATABASE_URL,
    connect_args={"client_encoding": "utf8"}
)

# Récupération des données
query = """
SELECT 
    execution_time_ms,
    status_code,
    timestamp,
    username
FROM prediction_logs
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC
"""

df = pd.read_sql(query, engine)

if df.empty:
    print("Aucune donnée de log trouvée")
    exit()

# Statistiques
stats = {
    "nombre_requetes": len(df),
    "temps_moyen_ms": round(df["execution_time_ms"].mean(), 2),
    "temps_median_ms": round(df["execution_time_ms"].median(), 2),
    "temps_max_ms": round(df["execution_time_ms"].max(), 2),
    "temps_min_ms": round(df["execution_time_ms"].min(), 2),
    "erreurs": len(df[df["status_code"] >= 400]),
    "taux_erreur": round(len(df[df["status_code"] >= 400]) / len(df) * 100, 2)
}

# Génération du HTML
html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Rapport Profiling - API Scoring</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: auto; background: white; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #333; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-box strong {{ display: block; font-size: 1.4em; color: #2196F3; }}
        canvas {{ margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Rapport de Profiling - API Scoring</h1>
        <p>Généré le {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
        
        <div class="stats">
            <div class="stat-box"><strong>{stats['nombre_requetes']}</strong>Requêtes</div>
            <div class="stat-box"><strong>{stats['temps_moyen_ms']} ms</strong>Temps moyen</div>
            <div class="stat-box"><strong>{stats['temps_median_ms']} ms</strong>Temps médian</div>
            <div class="stat-box"><strong>{stats['temps_max_ms']} ms</strong>Temps max</div>
            <div class="stat-box"><strong>{stats['erreurs']}</strong>Erreurs ({stats['taux_erreur']}%)</div>
        </div>

        <canvas id="timeChart" height="100"></canvas>
    </div>

    <script>
        const ctx = document.getElementById('timeChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {df['timestamp'].dt.strftime('%d/%m %H:%M').tolist()[-50:]},
                datasets: [{{
                    label: 'Temps d\\'exécution (ms)',
                    data: {df['execution_time_ms'].tolist()[-50:]},
                    borderColor: '#2196F3',
                    tension: 0.3,
                    fill: false
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{ display: true, text: 'Temps de réponse (50 dernières requêtes)' }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

with open("profiling_report.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Rapport généré : profiling_report.html")