"""
Esquemas Pydantic para Grupos (Multi-Tenant con Jerarquía).

Soporta:
- Jerarquía de grupos (padre-hijo)
- Soft delete
- Auditoría completa
- Validaciones de negocio
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


# =====================================================
# REQUEST SCHEMAS
# =====================================================

class GrupoCreate(BaseModel):
    """Schema para crear un nuevo grupo."""
    nombre: str = Field(..., min_length=1, max_length=150, description="Nombre del grupo/sede")
    codigo_corto: str = Field(..., min_length=1, max_length=20, description="Código único (CAM, CAI, AVID, etc.)")
    descripcion: Optional[str] = Field(None, description="Descripción detallada del grupo")
    grupo_padre_id: Optional[int] = Field(None, description="ID del grupo padre (NULL si es raíz)")
    correos_corporativos: Optional[List[str]] = Field(default_factory=list, description="Lista de correos corporativos")
    permite_subsedes: bool = Field(True, description="¿Puede tener hijos?")
    max_nivel_subsedes: int = Field(3, ge=1, le=10, description="Profundidad máxima permitida")
    activo: bool = Field(True, description="Estado activo/inactivo")

    @field_validator('correos_corporativos')
    @classmethod
    def validate_emails(cls, v):
        """Valida que los correos tengan formato básico."""
        if v:
            for email in v:
                if '@' not in email or '.' not in email:
                    raise ValueError(f"Correo inválido: {email}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Clínica Avidanti Pereira",
                "codigo_corto": "CAP",
                "descripcion": "Sede Pereira de Clínica Avidanti",
                "grupo_padre_id": 1,
                "correos_corporativos": ["facturacionelectronica@avidanti.com"],
                "permite_subsedes": True,
                "max_nivel_subsedes": 3,
                "activo": True
            }
        }


class GrupoUpdate(BaseModel):
    """Schema para actualizar un grupo existente."""
    nombre: Optional[str] = Field(None, min_length=1, max_length=150)
    codigo_corto: Optional[str] = Field(None, min_length=1, max_length=20)
    descripcion: Optional[str] = None
    correos_corporativos: Optional[List[str]] = None
    permite_subsedes: Optional[bool] = None
    max_nivel_subsedes: Optional[int] = Field(None, ge=1, le=10)
    activo: Optional[bool] = None

    @field_validator('correos_corporativos')
    @classmethod
    def validate_emails(cls, v):
        """Valida que los correos tengan formato básico."""
        if v:
            for email in v:
                if '@' not in email or '.' not in email:
                    raise ValueError(f"Correo inválido: {email}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Clínica Avidanti Pereira - Actualizado",
                "activo": True
            }
        }


# =====================================================
# RESPONSE SCHEMAS
# =====================================================

class GrupoBase(BaseModel):
    """Schema base de grupo para respuestas."""
    id: int
    nombre: str
    codigo_corto: str
    descripcion: Optional[str] = None
    grupo_padre_id: Optional[int] = None
    nivel: int
    ruta_jerarquica: Optional[str] = None
    correos_corporativos: Optional[List[str]] = None
    permite_subsedes: bool
    max_nivel_subsedes: int
    activo: bool
    eliminado: bool

    class Config:
        from_attributes = True


class GrupoResponse(GrupoBase):
    """Schema completo de grupo con auditoría."""
    fecha_eliminacion: Optional[datetime] = None
    eliminado_por: Optional[str] = None
    creado_en: datetime
    creado_por: str
    actualizado_en: datetime
    actualizado_por: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 5,
                "nombre": "CLINICA AVIDANTI MANIZALES",
                "codigo_corto": "CAM",
                "descripcion": "Clínica Avidanti - Sede Manizales",
                "grupo_padre_id": 1,
                "nivel": 2,
                "ruta_jerarquica": "1/5",
                "correos_corporativos": ["facturacionelectronica@avidanti.com"],
                "permite_subsedes": True,
                "max_nivel_subsedes": 3,
                "activo": True,
                "eliminado": False,
                "fecha_eliminacion": None,
                "eliminado_por": None,
                "creado_en": "2025-12-02T10:00:00Z",
                "creado_por": "SYSTEM",
                "actualizado_en": "2025-12-02T10:00:00Z",
                "actualizado_por": None
            }
        }


class GrupoHierarchical(GrupoBase):
    """Schema de grupo con información jerárquica expandida."""
    grupo_padre: Optional['GrupoBase'] = None
    hijos: List['GrupoBase'] = []
    es_raiz: bool = Field(description="True si no tiene padre")
    puede_tener_hijos: bool = Field(description="True si puede tener subsedes")

    class Config:
        from_attributes = True


class GrupoListResponse(BaseModel):
    """Schema para lista de grupos."""
    total: int
    grupos: List[GrupoResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "total": 7,
                "grupos": [
                    {
                        "id": 1,
                        "nombre": "AVIDANTI",
                        "codigo_corto": "AVID",
                        "nivel": 1,
                        "activo": True
                    }
                ]
            }
        }


# =====================================================
# FILTER SCHEMAS
# =====================================================

class GrupoFilter(BaseModel):
    """Schema para filtrar grupos."""
    activo: Optional[bool] = None
    eliminado: Optional[bool] = Field(False, description="Mostrar eliminados")
    grupo_padre_id: Optional[int] = Field(None, description="Filtrar por grupo padre")
    nivel: Optional[int] = Field(None, ge=1, description="Filtrar por nivel")
    codigo_corto: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "activo": True,
                "eliminado": False,
                "grupo_padre_id": 1,
                "nivel": 2
            }
        }


# =====================================================
# RESPONSABLE GRUPO SCHEMAS
# =====================================================

class ResponsableGrupoCreate(BaseModel):
    """Schema para asignar un responsable a un grupo."""
    responsable_id: int = Field(..., description="ID del usuario responsable")
    activo: bool = Field(True, description="Estado de la asignación")

    class Config:
        json_schema_extra = {
            "example": {
                "responsable_id": 5,
                "activo": True
            }
        }


class ResponsableGrupoUpdate(BaseModel):
    """Schema para actualizar asignación responsable-grupo."""
    activo: bool = Field(..., description="Estado de la asignación")

    class Config:
        json_schema_extra = {
            "example": {
                "activo": False
            }
        }


class ResponsableGrupoResponse(BaseModel):
    """Schema de respuesta para asignación responsable-grupo."""
    id: int
    responsable_id: int
    grupo_id: int
    activo: bool
    asignado_en: datetime
    asignado_por: Optional[str] = None
    actualizado_en: Optional[datetime] = None
    actualizado_por: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "responsable_id": 5,
                "grupo_id": 1,
                "activo": True,
                "asignado_en": "2025-12-02T10:00:00Z",
                "asignado_por": "admin",
                "actualizado_en": "2025-12-02T10:00:00Z",
                "actualizado_por": None
            }
        }


class ResponsableGrupoDetalle(ResponsableGrupoResponse):
    """Schema extendido con información del usuario y grupo."""
    responsable_usuario: Optional[str] = Field(None, description="Usuario/login del responsable")
    responsable_nombre: Optional[str] = Field(None, description="Nombre del responsable")
    responsable_email: Optional[str] = Field(None, description="Email del responsable")
    responsable_rol: Optional[str] = Field(None, description="Rol del responsable")
    responsable_area: Optional[str] = Field(None, description="Área del responsable")
    grupo_nombre: Optional[str] = Field(None, description="Nombre del grupo")
    grupo_codigo: Optional[str] = Field(None, description="Código del grupo")
    grupo_nivel: Optional[int] = Field(None, description="Nivel jerárquico del grupo")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "responsable_id": 5,
                "grupo_id": 1,
                "activo": True,
                "responsable_usuario": "juan.perez",
                "responsable_nombre": "Juan Pérez",
                "responsable_email": "juan.perez@avidanti.com",
                "grupo_nombre": "AVIDANTI",
                "grupo_codigo": "AVID",
                "asignado_en": "2025-12-02T10:00:00Z",
                "asignado_por": "admin"
            }
        }
