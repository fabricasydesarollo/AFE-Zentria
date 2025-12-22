from pydantic import BaseModel, Field
from typing import Any, Optional, List, Generic, TypeVar

class ErrorResponse(BaseModel):
    detail: str

class ResponseBase(BaseModel):
    """Esquema base para respuestas de la API"""
    success: bool
    message: str
    data: Optional[Any] = None


# SCHEMAS PARA PAGINACIÓN EMPRESARIAL ✨

class PaginationMetadata(BaseModel):
    """Metadata de paginación para respuestas empresariales"""
    total: int = Field(..., description="Total de registros en la base de datos")
    page: int = Field(..., description="Página actual (base 1)", ge=1)
    per_page: int = Field(..., description="Registros por página", ge=1, le=2000)
    total_pages: int = Field(..., description="Total de páginas disponibles")
    has_next: bool = Field(..., description="Indica si hay página siguiente")
    has_prev: bool = Field(..., description="Indica si hay página anterior")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 5420,
                "page": 1,
                "per_page": 500,
                "total_pages": 11,
                "has_next": True,
                "has_prev": False
            }
        }


T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada genérica para endpoints empresariales"""
    data: List[T] = Field(..., description="Lista de registros de la página actual")
    pagination: PaginationMetadata = Field(..., description="Metadata de paginación")

    class Config:
        json_schema_extra = {
            "example": {
                "data": ["...lista de objetos..."],
                "pagination": {
                    "total": 5420,
                    "page": 1,
                    "per_page": 500,
                    "total_pages": 11,
                    "has_next": True,
                    "has_prev": False
                }
            }
        }


# CURSOR-BASED PAGINATION (Para grandes volúmenes) ✨

class CursorPaginationMetadata(BaseModel):
    """Metadata para cursor-based pagination (escalable para millones de registros)"""
    has_more: bool = Field(..., description="Indica si hay más registros disponibles")
    next_cursor: Optional[str] = Field(None, description="Cursor para la siguiente página")
    prev_cursor: Optional[str] = Field(None, description="Cursor para la página anterior")
    count: int = Field(..., description="Cantidad de registros retornados en esta respuesta")

    class Config:
        json_schema_extra = {
            "example": {
                "has_more": True,
                "next_cursor": "MjAyNS0xMC0wOFQxMDowMDowMHwxMjM0NQ==",
                "prev_cursor": None,
                "count": 500
            }
        }


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """
    Respuesta paginada con cursores para grandes volúmenes (10k+ registros).

    Ventajas sobre offset pagination:
    - Performance constante O(1) independiente del tamaño del dataset
    - No hay "deep pagination problem" (page 10000 sería lento)
    - Ideal para scroll infinito en frontend
    - Usado por: Stripe, Twitter, Facebook, GitHub API
    """
    data: List[T] = Field(..., description="Lista de registros")
    cursor: CursorPaginationMetadata = Field(..., description="Metadata de cursor")

    class Config:
        json_schema_extra = {
            "example": {
                "data": ["...lista de objetos..."],
                "cursor": {
                    "has_more": True,
                    "next_cursor": "MjAyNS0xMC0wOFQxMDowMDowMHwxMjM0NQ==",
                    "prev_cursor": None,
                    "count": 500
                }
            }
        }
