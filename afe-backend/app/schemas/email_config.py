# app/schemas/email_config.py
"""
Schemas Pydantic para configuración de extracción de correos.

Validación de datos para cuentas de correo, NITs y configuraciones.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


# ==================== NIT Configuración ====================

class NitConfiguracionBase(BaseModel):
    """Base para configuración de NIT"""
    nit: str = Field(..., min_length=5, max_length=20, description="NIT del proveedor (formato: XXXXXXXXX-D con dígito verificador)")
    nombre_proveedor: Optional[str] = Field(None, max_length=255, description="Nombre del proveedor (opcional)")
    activo: bool = Field(True, description="Si este NIT está activo para filtrado")
    notas: Optional[str] = Field(None, max_length=500)

    @field_validator('nit')
    @classmethod
    def validate_nit(cls, v: str) -> str:
        """Valida que el NIT tenga formato normalizado (5-9 dígitos + DV) o sea numérico sin guión"""
        import re
        cleaned = v.strip()

        # Permite dos formatos:
        # 1. Formato normalizado: "XXXXX-D" a "XXXXXXXXX-D" (5-9 dígitos + guión + 1 dígito)
        # 2. Formato numérico: solo dígitos (para compatibilidad con entrada antigua)

        if re.match(r'^\d{5,9}-\d$', cleaned):
            # Formato normalizado: 5-9 dígitos + guión + DV
            return cleaned
        elif cleaned.isdigit() and 5 <= len(cleaned) <= 9:
            # Formato numérico sin DV (para compatibilidad)
            return cleaned
        else:
            raise ValueError(f"NIT inválido: debe ser 'XXXXX-D' a 'XXXXXXXXX-D' (5-9 dígitos + DV) o solo dígitos (5-9)")


class NitConfiguracionCreate(NitConfiguracionBase):
    """Schema para crear un NIT"""
    cuenta_correo_id: int = Field(..., gt=0, description="ID de la cuenta de correo")
    creado_por: str = Field(..., min_length=1, max_length=100)


class NitConfiguracionUpdate(BaseModel):
    """Schema para actualizar un NIT"""
    nombre_proveedor: Optional[str] = Field(None, max_length=255)
    activo: Optional[bool] = None
    notas: Optional[str] = Field(None, max_length=500)
    actualizado_por: str = Field(..., min_length=1, max_length=100)


class NitConfiguracionResponse(NitConfiguracionBase):
    """Schema de respuesta con información completa del NIT"""
    id: int
    cuenta_correo_id: int
    creado_en: datetime
    actualizado_en: datetime
    creado_por: str
    actualizado_por: Optional[str]

    class Config:
        from_attributes = True


# ==================== Cuenta Correo ====================

class CuentaCorreoBase(BaseModel):
    """Base para configuración de cuenta de correo"""
    email: EmailStr = Field(..., description="Email corporativo (Microsoft Graph)")
    nombre_descriptivo: Optional[str] = Field(None, max_length=255, description="Nombre amigable")
    max_correos_por_ejecucion: int = Field(10000, ge=1, le=100000, description="Límite de seguridad por ejecución (1-100000)")
    ventana_inicial_dias: int = Field(30, ge=1, le=365, description="Días hacia atrás en primera ejecución (1-365)")
    activa: bool = Field(True, description="Si está activa para extracción")
    organizacion: Optional[str] = Field(None, max_length=100, description="Organización asociada")


class CuentaCorreoCreate(CuentaCorreoBase):
    """Schema para crear una cuenta de correo"""
    creada_por: str = Field(..., min_length=1, max_length=100, description="Usuario que crea la configuración")
    grupo_id: Optional[int] = Field(None, gt=0, description="ID del grupo empresarial al que pertenece")
    nits: List[str] = Field(default_factory=list, description="Lista de NITs a agregar inicialmente")

    @field_validator('nits')
    @classmethod
    def validate_nits_list(cls, v: List[str]) -> List[str]:
        """Valida lista de NITs"""
        if not v:
            return []

        cleaned_nits = []
        for nit in v:
            nit_clean = nit.strip()
            if not nit_clean.isdigit():
                raise ValueError(f"NIT inválido '{nit}': debe contener solo números")
            if len(nit_clean) < 5 or len(nit_clean) > 20:
                raise ValueError(f"NIT inválido '{nit}': debe tener entre 5 y 20 dígitos")
            cleaned_nits.append(nit_clean)

        # Verificar duplicados
        if len(cleaned_nits) != len(set(cleaned_nits)):
            raise ValueError("Hay NITs duplicados en la lista")

        return cleaned_nits


class CuentaCorreoUpdate(BaseModel):
    """Schema para actualizar una cuenta de correo"""
    email: Optional[EmailStr] = Field(None, description="Email corporativo (solo admin/super admin)")
    nombre_descriptivo: Optional[str] = Field(None, max_length=255)
    max_correos_por_ejecucion: Optional[int] = Field(None, ge=1, le=100000)
    ventana_inicial_dias: Optional[int] = Field(None, ge=1, le=365)
    activa: Optional[bool] = None
    organizacion: Optional[str] = Field(None, max_length=100)
    actualizada_por: str = Field(..., min_length=1, max_length=100)


class CuentaCorreoResponse(CuentaCorreoBase):
    """Schema de respuesta con información completa de la cuenta"""
    id: int
    grupo_id: Optional[int] = Field(None, description="ID del grupo empresarial")
    creada_en: datetime
    actualizada_en: datetime
    creada_por: str
    actualizada_por: Optional[str]
    ultima_ejecucion_exitosa: Optional[datetime]
    fecha_ultimo_correo_procesado: Optional[datetime]
    nits: List[NitConfiguracionResponse] = []

    class Config:
        from_attributes = True


class CuentaCorreoSummary(BaseModel):
    """Resumen de cuenta de correo (sin NITs) con información de grupo"""
    id: int
    email: str
    nombre_descriptivo: Optional[str]
    activa: bool
    organizacion: Optional[str]
    grupo_id: Optional[int] = Field(None, description="ID del grupo empresarial")
    grupo_codigo: Optional[str] = Field(None, description="Código corto del grupo")
    grupo_nombre: Optional[str] = Field(None, description="Nombre del grupo")
    total_nits: int = Field(..., description="Cantidad de NITs configurados")
    total_nits_activos: int = Field(..., description="Cantidad de NITs activos")
    creada_en: datetime

    class Config:
        from_attributes = True


# ==================== Actualización de Ejecución ====================

class ActualizarUltimaEjecucionRequest(BaseModel):
    """Schema para actualizar timestamp de última ejecución exitosa"""
    cuenta_id: int = Field(..., gt=0, description="ID de la cuenta de correo")
    fecha_ejecucion: datetime = Field(..., description="Timestamp de última ejecución exitosa (UTC)")
    fecha_ultimo_correo: Optional[datetime] = Field(None, description="Timestamp del último correo procesado (opcional)")


class ActualizarUltimaEjecucionResponse(BaseModel):
    """Respuesta de actualización de ejecución"""
    cuenta_id: int
    email: str
    ultima_ejecucion_exitosa: Optional[datetime]
    fecha_ultimo_correo_procesado: Optional[datetime]
    actualizado_en: datetime

    class Config:
        from_attributes = True


# ==================== Historial Extracción ====================

class HistorialExtraccionCreate(BaseModel):
    """Schema para registrar una extracción"""
    cuenta_correo_id: int = Field(..., gt=0)
    correos_procesados: int = Field(0, ge=0)
    facturas_encontradas: int = Field(0, ge=0)
    facturas_creadas: int = Field(0, ge=0)
    facturas_actualizadas: int = Field(0, ge=0)
    facturas_ignoradas: int = Field(0, ge=0)
    exito: bool = True
    mensaje_error: Optional[str] = Field(None, max_length=1000)
    tiempo_ejecucion_ms: Optional[int] = Field(None, ge=0)
    fetch_limit_usado: Optional[int] = None
    fetch_days_usado: Optional[int] = None
    nits_usados: Optional[int] = Field(None, ge=0)
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None
    es_primera_ejecucion: bool = False


class HistorialExtraccionResponse(BaseModel):
    """Schema de respuesta del historial"""
    id: int
    cuenta_correo_id: int
    fecha_ejecucion: datetime
    correos_procesados: int
    facturas_encontradas: int
    facturas_creadas: int
    facturas_actualizadas: int
    facturas_ignoradas: int
    exito: bool
    mensaje_error: Optional[str]
    tiempo_ejecucion_ms: Optional[int]
    fetch_limit_usado: Optional[int]
    fetch_days_usado: Optional[int]
    nits_usados: Optional[int]
    fecha_desde: Optional[datetime]
    fecha_hasta: Optional[datetime]
    es_primera_ejecucion: bool

    class Config:
        from_attributes = True


# ==================== Configuración para Extractor ====================

class ConfiguracionExtractorEmail(BaseModel):
    """
    Configuración usada por el invoice_extractor para Microsoft Graph.
    Formato compatible con extracción incremental + cuenta_id para registrar historial.
    """
    cuenta_id: int = Field(..., description="ID de la cuenta (para registrar historial)")
    email: str
    nits: List[str]
    max_correos_por_ejecucion: int
    ventana_inicial_dias: int
    ultima_ejecucion_exitosa: Optional[datetime] = None
    fecha_ultimo_correo_procesado: Optional[datetime] = None


class ConfiguracionExtractorResponse(BaseModel):
    """Respuesta con todas las configuraciones activas para el extractor"""
    users: List[ConfiguracionExtractorEmail]
    total_cuentas: int
    total_nits: int
    generado_en: datetime


# ==================== Bulk Operations ====================

class BulkNitsCreate(BaseModel):
    """Schema para agregar múltiples NITs a una cuenta"""
    cuenta_correo_id: int = Field(..., gt=0)
    nits: List[str] = Field(..., min_length=1, description="Lista de NITs a agregar")
    creado_por: Optional[str] = Field(None, min_length=1, max_length=100)

    @field_validator('nits')
    @classmethod
    def validate_nits_list(cls, v: List[str]) -> List[str]:
        """Valida lista de NITs"""
        cleaned_nits = []
        for nit in v:
            nit_clean = nit.strip()
            if not nit_clean.isdigit():
                raise ValueError(f"NIT inválido '{nit}': debe contener solo números")
            if len(nit_clean) < 5 or len(nit_clean) > 20:
                raise ValueError(f"NIT inválido '{nit}': debe tener entre 5 y 20 dígitos")
            cleaned_nits.append(nit_clean)

        # Verificar duplicados
        if len(cleaned_nits) != len(set(cleaned_nits)):
            raise ValueError("Hay NITs duplicados en la lista")

        return cleaned_nits


class BulkNitsResponse(BaseModel):
    """Respuesta de operación bulk"""
    cuenta_correo_id: int
    nits_agregados: int
    nits_duplicados: int
    nits_fallidos: int
    detalles: List[dict]


# ==================== Estadísticas ====================

class EstadisticasExtraccion(BaseModel):
    """Estadísticas de extracción por cuenta"""
    cuenta_correo_id: int
    email: str
    total_ejecuciones: int
    ultima_ejecucion: Optional[datetime]
    total_facturas_encontradas: int
    total_facturas_creadas: int
    tasa_exito: float = Field(..., ge=0.0, le=100.0, description="Porcentaje de éxito")
    promedio_tiempo_ms: Optional[float]


# ==================== Validación de NIT ====================

class NitValidationRequest(BaseModel):
    """Request para validar un NIT"""
    nit: str = Field(..., min_length=5, max_length=20, description="NIT a validar (con o sin DV)")


class NitValidationResponse(BaseModel):
    """Response de validación de NIT"""
    is_valid: bool = Field(..., description="True si el NIT es válido")
    nit_normalizado: Optional[str] = Field(None, description="NIT normalizado (XXXXXXXXX-D) si es válido")
    error: Optional[str] = Field(None, description="Mensaje de error si no es válido")
