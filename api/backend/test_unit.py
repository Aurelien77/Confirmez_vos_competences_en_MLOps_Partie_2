import numpy as np
import pytest

# Exemple de fonction à tester (tu peux en extraire une dans main.py si besoin)
def calculer_risque(proba: float, seuil: float = 0.5) -> int:
    return 1 if proba >= seuil else 0

def test_calculer_risque_faible():
    assert calculer_risque(0.3) == 0

def test_calculer_risque_eleve():
    assert calculer_risque(0.7) == 1

def test_calculer_risque_seuil():
    assert calculer_risque(0.5) == 1

def test_features_manquantes():
    features = {"AMT_INCOME_TOTAL": 200000}
    valeur = features.get("EXT_SOURCE_1", np.nan)
    assert np.isnan(valeur)