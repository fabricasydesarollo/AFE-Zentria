from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.role import RoleRead


class GrupoSimple(BaseModel):
    """Schema simple de grupo para mostrar en usuario."""
    id: int
    codigo: str
    nombre: str

    class Config:
        from_attributes = True


class UsuarioBase(BaseModel):
    usuario: str = Field(..., example="juan.perez@empresa.com")
    email: EmailStr
    nombre: Optional[str]
    role_id: Optional[int]


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8)
    area: Optional[str] = None
    telefono: Optional[str] = None


class UsuarioRead(UsuarioBase):
    id: int
    activo: bool
    must_change_password: bool
    last_login: Optional[datetime]
    creado_en: datetime
    area: Optional[str]
    telefono: Optional[str]
    role: Optional[RoleRead] = None
    grupos: List[GrupoSimple] = []

    class Config:
        from_attributes = True


class UsuarioLogin(BaseModel):
    usuario: str
    password: str


class UsuarioUpdate(BaseModel):
    usuario: Optional[str] = None
    email: Optional[EmailStr] = None
    nombre: Optional[str] = None
    area: Optional[str] = None
    telefono: Optional[str] = None
    activo: Optional[bool] = None
    role_id: Optional[int] = None
    password: Optional[str] = Field(None, min_length=8)


