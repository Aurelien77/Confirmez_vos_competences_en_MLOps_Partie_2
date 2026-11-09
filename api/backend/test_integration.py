import os
import time
import pytest
from fastapi.testclient import TestClient
from api.backend.main import app

# Vérifie si le fichier de données existe
DATA_PATHS = [
    "df_home_credit.pkl",
    "../../df_home_credit.pkl",
    os.path.join(os.path.dirname(__file__), "..", "..", "df_home_credit.pkl"),
]
DATA_EXISTS = any(os.path.exists(p) for p in DATA_PATHS)

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def auth_token(client):
    """Crée un utilisateur de test et retourne son token"""
    username = f"testuser_{int(time.time())}"
    client.post("/register", json={"username": username, "password": "pass1234"})
    res = client.post("/login", json={"username": username, "password": "pass1234"})
    return res.json()["access_token"]

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_frontend_ui(client):
    response = client.get("/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert b"Scoring Home Credit" in response.content

@pytest.mark.skipif(not DATA_EXISTS, reason="Fichier df_home_credit.pkl non disponible")
def test_predict_client_id_valide(client, auth_token):
    response = client.post(
        "/predict",
        json={"client_id": 100002},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == 100002
    assert 0.0 <= data["probabilite_defaut"] <= 1.0

@pytest.mark.skipif(not DATA_EXISTS, reason="Fichier df_home_credit.pkl non disponible")
def test_predict_client_id_invalide(client, auth_token):
    response = client.post(
        "/predict",
        json={"client_id": 999999},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 404

def test_predict_avec_features(client, auth_token):
    payload = {
        "features": {
            "AMT_INCOME_TOTAL": 180000,
            "AMT_CREDIT": 400000,
            "DAYS_BIRTH": -13000
        }
    }
    response = client.post(
        "/predict",
        json=payload,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert "probabilite_defaut" in response.json()

def test_predict_sans_donnees(client, auth_token):
    response = client.post(
        "/predict",
        json={},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 400

def test_predict_features_manquantes(client, auth_token):
    payload = {"features": {"AMT_INCOME_TOTAL": 150000}}
    response = client.post(
        "/predict",
        json=payload,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200

def test_predict_valeurs_hors_plage(client, auth_token):
    payload = {
        "features": {
            "AMT_INCOME_TOTAL": -1000,
            "DAYS_BIRTH": 100,
            "CNT_CHILDREN": -1
        }
    }
    response = client.post(
        "/predict",
        json=payload,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200

def test_predict_types_incorrects(client, auth_token):
    payload = {
        "features": {
            "AMT_INCOME_TOTAL": "cent mille",
            "DAYS_BIRTH": "hier"
        }
    }
    response = client.post(
        "/predict",
        json=payload,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code in [200, 422]

def test_predict_client_id_negatif(client, auth_token):
    response = client.post(
        "/predict",
        json={"client_id": -5},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code in [404, 422]

def test_predict_payload_vide_features(client, auth_token):
    response = client.post(
        "/predict",
        json={"features": {}},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200

def test_register_login_change_password(client):
    username = f"changepw_{int(time.time())}"
    # Register
    res = client.post("/register", json={"username": username, "password": "pass1234"})
    assert res.status_code == 200

    # Login
    res = client.post("/login", json={"username": username, "password": "pass1234"})
    assert res.status_code == 200
    token = res.json()["access_token"]

    # Change password
    res = client.post(
        "/change-password",
        json={"old_password": "pass1234", "new_password": "newpass567"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200

def test_my_predictions_auth_required(client):
    res = client.get("/my-predictions")
    assert res.status_code == 403  # HTTPBearer renvoie 403 si pas de token

def test_admin_dashboard_forbidden(client):
    username = f"normal_{int(time.time())}"
    client.post("/register", json={"username": username, "password": "pass1234"})
    login = client.post("/login", json={"username": username, "password": "pass1234"})
    token = login.json()["access_token"]

    res = client.get(
        "/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403