from fastapi import APIRouter, Depends
from api.backend.models.schemas import UserCreate, Token, ChangePassword
from api.backend.controllers.auth_controller import register_user, login_user, change_password, delete_account
from api.backend.core.security import get_current_user

router = APIRouter()

@router.post("/register", summary="Créer un nouveau compte utilisateur")
def register(user: UserCreate):
    return register_user(user)

@router.post("/login", response_model=Token, summary="Se connecter et obtenir un token")
def login(user: UserCreate):
    return login_user(user)

@router.put("/change-password", summary="Changer son mot de passe")
def change_password_route(
    data: ChangePassword,
    user = Depends(get_current_user)
):
    return change_password(user["username"], data.old_password, data.new_password)

@router.delete("/account", summary="Supprimer son compte")
def delete_account_route(user = Depends(get_current_user)):
    return delete_account(user["username"])