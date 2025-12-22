# app/schemas/proveedor.py
from pydantic import BaseModel
from typing import Optional

class ProveedorBase(BaseModel):
    nit: str
    razon_social: str
    contacto_email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    area: Optional[str] = None
    activo: bool = True

class ProveedorRead(ProveedorBase):
    id: int
    class Config:
        from_attributes = True
