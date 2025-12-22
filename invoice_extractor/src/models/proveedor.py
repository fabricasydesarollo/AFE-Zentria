from pydantic import BaseModel

class Proveedor(BaseModel):
    nit: str
    razon_social: str
