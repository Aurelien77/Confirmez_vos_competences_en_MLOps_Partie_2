import pytest
from fastapi.testclient import TestClient
from api.backend.main import app

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

def test_predict_client_id_valide(client):
    # Login first
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