# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    usuario: str
    area: Optional[str] = None


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=6)


class GrupoSimple(BaseModel):
    """
    Schema simple de grupo para login response.

    ARQUITECTURA KISS 2025-12-09:
    Incluye grupo_padre_id y nivel para identificar el grupo raíz (Vista Global).
    """
    id: int
    nombre: str
    codigo_corto: str
    activo: bool
    nivel: int  # Nivel en jerarquía (1=raíz, 2=hijo, 3=nieto...)
    grupo_padre_id: Optional[int] = None  # NULL = grupo raíz (Vista Global para SuperAdmin)

    class Config:
        from_attributes = True


class UsuarioResponse(UsuarioBase):
    id: int
    rol: str
    activo: bool
    created_at: datetime
    grupos: List[GrupoSimple] = Field(default_factory=list, description="Grupos a los que el usuario tiene acceso")

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    usuario: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioResponse


class MicrosoftAuthResponse(BaseModel):
    """Respuesta de autorización de Microsoft"""
    authorization_url: str
    state: str
