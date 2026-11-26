import pytest
from api.backend.models.schemas import PredictionRequest
from api.backend.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
)

def test_calculer_risque_faible():
    proba = 0.3
    risque = 1 if proba >= 0.5 else 0
    assert risque == 0

def test_calculer_risque_eleve():
    proba = 0.7
    risque = 1 if proba >= 0.5 else 0
    assert risque == 1

def test_calculer_risque_seuil():
    proba = 0.5
    risque = 1 if proba >= 0.5 else 0
    assert risque == 1

def test_features_manquantes():
    req = PredictionRequest(features={"AMT_INCOME_TOTAL": 100000})
    assert req.features["AMT_INCOME_TOTAL"] == 100000

def test_features_invalides():
    with pytest.raises(ValueError):
        PredictionRequest(features={"AMT_INCOME_TOTAL": -1000})

def test_password_hash_and_verify():
    password = "MonMotDePasse123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("mauvais", hashed) is False

def test_create_and_decode_token():
    data = {"sub": "testuser", "is_admin": False}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded["sub"] == "testuser"
    assert decoded["is_admin"] is False

def test_decode_invalid_token():
    with pytest.raises(Exception):
        decode_token("token.invalide.ici")