from pydantic import BaseModel

class Cliente(BaseModel):
    nit: str
    razon_social: str
