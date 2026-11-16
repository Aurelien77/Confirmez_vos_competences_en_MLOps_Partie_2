from fastapi import HTTPException
from sqlalchemy import text
from api.backend.core.database import engine
from api.backend.core.security import pwd_context, create_access_token

def register_user(user):
    hashed = pwd_context.hash(user.password)
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (username, hashed_password) VALUES (:u, :p)"),
                {"u": user.username, "p": hashed}
            )
        return {"message": "Compte créé"}
    except Exception:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur déjà utilisé")

def login_user(user):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT hashed_password, is_admin FROM users WHERE username = :u"),
            {"u": user.username}
        ).fetchone()
    
    if not result or not pwd_context.verify(user.password, result[0]):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    
    is_admin = bool(result[1])
    token = create_access_token({
        "sub": user.username,
        "role": "admin" if is_admin else "user"
    })
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "is_admin": is_admin,
        "username": user.username
    }