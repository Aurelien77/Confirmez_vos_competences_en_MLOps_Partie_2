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

def test_predict_client_id_valide(client):
    response = client.post("/predict", json={"client_id": 100002})
    assert response.status_code == 200
    data = response.json()
    assert data["client_id"] == 100002
    assert 0.0 <= data["probabilite_defaut"] <= 1.0
    assert data["risque"] in [0, 1]

def test_predict_client_id_invalide(client):
    response = client.post("/predict", json={"client_id": 999999})
    assert response.status_code == 404

def test_predict_avec_features(client):
    payload = {
        "features": {
            "AMT_INCOME_TOTAL": 180000,
            "AMT_CREDIT": 400000,
            "DAYS_BIRTH": -13000
        }
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "probabilite_defaut" in data

def test_predict_sans_donnees(client):
    response = client.post("/predict", json={})
    assert response.status_code == 400