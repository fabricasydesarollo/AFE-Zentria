# app/core/security.py
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.crud.usuario import get_usuario_by_id

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    now = datetime.utcnow()
    exp = now + expires_delta
    payload: Dict[str, Any] = {"sub": str(subject), "iat": now, "exp": exp}
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token

def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

def get_current_usuario(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Obtiene el usuario actual desde el token JWT"""
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    # Try numeric id first, fallback to username if conversion fails
    user = None
    try:
        user = get_usuario_by_id(db, int(user_id))
    except (ValueError, TypeError):
        # fallback: sub could be username
        from app.crud.usuario import get_usuario_by_usuario
        user = get_usuario_by_usuario(db, user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


def require_role(role_names):
    """
    Decorator para requerir roles específicos. Valida que el usuario tenga uno de los roles especificados.

    Args:
        role_names: Puede ser un string único o una lista de strings con los roles permitidos.
                   Ejemplo: require_role("admin") o require_role(["superadmin", "admin"])
    """
    # Normalizar a lista si es un string único
    if isinstance(role_names, str):
        role_names = [role_names]

    def inner(current_user = Depends(get_current_usuario)):
        # current_user has role relationship
        if getattr(current_user, "role", None):
            rname = getattr(current_user.role, "nombre", None)
            if rname in role_names:
                return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
    return inner
