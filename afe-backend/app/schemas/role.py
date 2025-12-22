# app/schemas/role.py
from pydantic import BaseModel

class RoleBase(BaseModel):
    nombre: str

class RoleRead(RoleBase):
    id: int
    class Config:
        from_attributes = True
