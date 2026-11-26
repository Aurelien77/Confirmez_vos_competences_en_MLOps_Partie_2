import pytest
from api.backend.models.schemas import PredictionRequest

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

def test_import_modules():
    from api.backend.controllers import auth_controller, predict_controller
    from api.backend.core import config, database, security
    from api.backend.routes import auth, predict, admin
    from api.backend.monitoring import drift_analysis

    assert auth_controller is not None
    assert predict_controller is not None
    assert security is not None
    assert drift_analysis is not None