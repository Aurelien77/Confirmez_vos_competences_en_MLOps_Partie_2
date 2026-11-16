from fastapi import APIRouter
from api.backend.models.schemas import UserCreate, Token
from api.backend.controllers.auth_controller import register_user, login_user

router = APIRouter()

@router.post("/register", summary="Créer un nouveau compte utilisateur")
def register(user: UserCreate):
    return register_user(user)

@router.post("/login", response_model=Token, summary="Se connecter et obtenir un token")
def login(user: UserCreate):
    return login_user(user)