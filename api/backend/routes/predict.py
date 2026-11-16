from fastapi import APIRouter, Depends, Request
from api.backend.models.schemas import PredictionRequest, PredictionResponse
from api.backend.controllers.predict_controller import predict_logic
from api.backend.core.security import get_current_user

router = APIRouter()

@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Prédire le risque de défaut d'un client",
    description="Calcule la probabilité qu'un client fasse défaut sur son crédit."
)
def predict(request: PredictionRequest, req: Request, user=Depends(get_current_user)):
    return predict_logic(
        request_data=request,
        user=user,
        model=req.app.state.model,
        df=req.app.state.df
    )