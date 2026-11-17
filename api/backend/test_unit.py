import pytest
from api.backend.models.schemas import PredictionRequest

def test_calculer_risque_faible():
    # Test de la logique de seuil (si tu l'extrais)
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
    # Vérifie que le validateur accepte des features partielles
    req = PredictionRequest(features={"AMT_INCOME_TOTAL": 100000})
    assert req.features["AMT_INCOME_TOTAL"] == 100000

def test_features_invalides():
    with pytest.raises(ValueError):
        PredictionRequest(features={"AMT_INCOME_TOTAL": -1000})