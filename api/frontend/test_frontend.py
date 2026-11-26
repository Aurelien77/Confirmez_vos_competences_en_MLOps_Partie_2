# api/frontend/test_frontend.py
import pytest
from fastapi.testclient import TestClient
from api.backend.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_frontend_ui(client):
    response = client.get("/ui")
    assert response.status_code == 200
    assert "Scoring Home Credit" in response.text
    assert "<html" in response.text.lower()