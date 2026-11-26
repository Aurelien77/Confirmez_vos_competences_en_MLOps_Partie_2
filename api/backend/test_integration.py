import os
os.environ["PGCLIENTENCODING"] = "UTF8"

import pytest
from fastapi.testclient import TestClient
from api.backend.main import app

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

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_register_login(client):
    response = client.post("/register", json={"username": "newuser", "password": "password123"})
    assert response.status_code in [200, 400]

    response = client.post("/login", json={"username": "newuser", "password": "password123"})
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.skipif(not DATA_EXISTS, reason="Fichier df_home_credit.pkl non disponible en CI")
def test_predict_client_id_valide(client):
    response = client.post("/login", json={"username": "newuser", "password": "password123"})
    token = response.json()["access_token"]

    response = client.post(
        "/predict",
        json={"client_id": 100002},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == 100002
    assert 0.0 <= data["probabilite_defaut"] <= 1.0

def test_predict_sans_auth(client):
    response = client.post("/predict", json={"client_id": 100002})
    assert response.status_code == 401

def test_predict_sans_donnees(client):
    response = client.post("/login", json={"username": "newuser", "password": "password123"})
    token = response.json()["access_token"]

    response = client.post(
        "/predict",
        json={},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400

def test_predict_features_invalides(client):
    response = client.post("/login", json={"username": "newuser", "password": "password123"})
    token = response.json()["access_token"]

    response = client.post(
        "/predict",
        json={"features": {"AMT_INCOME_TOTAL": "pas un nombre"}},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code in [200, 422]

def test_my_predictions_auth_required(client):
    response = client.get("/my-predictions")
    assert response.status_code == 401

def test_my_predictions(client):
    response = client.post("/login", json={"username": "newuser", "password": "password123"})
    token = response.json()["access_token"]

    response = client.get(
        "/my-predictions",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "predictions" in response.json()

def test_admin_dashboard_forbidden(client):
    response = client.post("/login", json={"username": "newuser", "password": "password123"})
    token = response.json()["access_token"]

    response = client.get(
        "/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

def test_change_password(client):
    client.post("/register", json={"username": "pwduser", "password": "oldpass123"})

    response = client.post("/login", json={"username": "pwduser", "password": "oldpass123"})
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = client.post(
        "/change-password",
        json={"old_password": "oldpass123", "new_password": "newpass456"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Mot de passe modifié avec succès"

    response = client.post("/login", json={"username": "pwduser", "password": "oldpass123"})
    assert response.status_code == 401

    response = client.post("/login", json={"username": "pwduser", "password": "newpass456"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_delete_account(client):
    client.post("/register", json={"username": "deleteuser", "password": "pass123"})

    response = client.post("/login", json={"username": "deleteuser", "password": "pass123"})
    token = response.json()["access_token"]

    response = client.delete(
        "/account",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Compte supprimé avec succès"

    response = client.post("/login", json={"username": "deleteuser", "password": "pass123"})
    assert response.status_code == 401

def test_frontend_ui(client):
    response = client.get("/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert b"Scoring Home Credit" in response.content or b"<!DOCTYPE html>" in response.content