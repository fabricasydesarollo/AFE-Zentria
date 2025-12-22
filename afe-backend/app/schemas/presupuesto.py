"""
Schemas Pydantic para sistema de importación y comparación presupuestal.

Fecha: 2025-10-04
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Dict, Optional, Any
from decimal import Decimal
from datetime import datetime, date
from enum import Enum


class TipoArchivo(str, Enum):
    """Tipos de archivo soportados para importación."""
    CSV = "csv"
    EXCEL = "xlsx"
    EXCEL_XLS = "xls"


class EstadoImportacion(str, Enum):
    """Estados del proceso de importación."""
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    COMPLETADO = "completado"
    ERROR = "error"


class PresupuestoMensual(BaseModel):
    """Modelo de presupuesto mensual por línea."""
    model_config = ConfigDict(from_attributes=True)

    mes: str = Field(..., description="Nombre del mes (ene, feb, mar...)")
    valor_presupuestado: Decimal = Field(..., description="Valor presupuestado")
    valor_ejecutado: Decimal = Field(default=Decimal('0'), description="Valor ejecutado")
    desviacion: Decimal = Field(default=Decimal('0'), description="Desviación (ejecutado - presupuestado)")
    porcentaje_ejecucion: float = Field(default=0.0, description="% de ejecución")

    @field_validator('mes')
    @classmethod
    def validate_mes(cls, v: str) -> str:
        """Valida que el mes sea válido."""
        meses_validos = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
                        'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
        if v.lower() not in meses_validos:
            raise ValueError(f'Mes inválido: {v}. Debe ser uno de {meses_validos}')
        return v.lower()


class LineaPresupuestal(BaseModel):
    """Línea presupuestal con detalles completos."""
    model_config = ConfigDict(from_attributes=True)

    id_linea: int = Field(..., description="ID único de la línea presupuestal")
    nombre_cuenta: str = Field(..., min_length=1, max_length=500, description="Nombre de la cuenta")
    responsable: Optional[str] = Field(None, max_length=100, description="Usuario de la línea")
    area: Optional[str] = Field(None, max_length=100, description="Área responsable")

    # Datos mensuales
    presupuesto_mensual: List[PresupuestoMensual] = Field(
        default_factory=list,
        description="Presupuesto y ejecución por mes"
    )

    # Facturas asociadas
    facturas: List[str] = Field(default_factory=list, description="Números de factura asociados")

    # Totales anuales
    total_presupuesto_anual: Decimal = Field(..., description="Total presupuestado anual")
    total_ejecucion_anual: Decimal = Field(default=Decimal('0'), description="Total ejecutado anual")
    desviacion_anual: Decimal = Field(default=Decimal('0'), description="Desviación anual")
    porcentaje_ejecucion_anual: float = Field(default=0.0, description="% ejecución anual")


class FacturaComparacion(BaseModel):
    """Factura para comparación con presupuesto."""
    model_config = ConfigDict(from_attributes=True)

    numero_factura: str = Field(..., description="Número de factura")
    total: Decimal = Field(..., description="Monto total de la factura")
    fecha_emision: datetime = Field(..., description="Fecha de emisión")
    periodo_factura: str = Field(..., description="Período (YYYY-MM)")
    proveedor: Optional[str] = Field(None, description="Nombre del proveedor")
    estado: Optional[str] = Field(None, description="Estado de la factura")


class DesviacionPresupuestal(BaseModel):
    """Desviación presupuestal detectada."""
    model_config = ConfigDict(from_attributes=True)

    linea: str = Field(..., description="Línea presupuestal")
    mes: str = Field(..., description="Mes de la desviación")
    presupuesto: Decimal = Field(..., description="Valor presupuestado")
    ejecucion: Decimal = Field(..., description="Valor ejecutado")
    desviacion: Decimal = Field(..., description="Diferencia (ejecución - presupuesto)")
    porcentaje: float = Field(..., description="Porcentaje de desviación")
    criticidad: str = Field(default="media", description="Nivel de criticidad (baja|media|alta|critica)")

    @field_validator('criticidad')
    @classmethod
    def asignar_criticidad(cls, v: str, info) -> str:
        """Asigna criticidad automáticamente basado en porcentaje."""
        porcentaje = abs(info.data.get('porcentaje', 0))

        if porcentaje > 50:
            return "critica"
        elif porcentaje > 25:
            return "alta"
        elif porcentaje > 10:
            return "media"
        else:
            return "baja"


class ReporteComparacion(BaseModel):
    """Reporte completo de comparación presupuesto vs ejecución."""
    model_config = ConfigDict(from_attributes=True)

    # Metadata
    fecha_generacion: datetime = Field(default_factory=datetime.now, description="Fecha de generación del reporte")
    archivo_origen: str = Field(..., description="Nombre del archivo Excel/CSV")
    usuario_generador: Optional[str] = Field(None, description="Usuario que generó el reporte")

    # Resumen ejecutivo
    total_lineas_excel: int = Field(..., description="Total de líneas presupuestales")
    total_facturas_db: int = Field(..., description="Total de facturas en BD")
    facturas_encontradas_count: int = Field(default=0, description="Facturas encontradas")
    facturas_faltantes_count: int = Field(default=0, description="Facturas faltantes")
    desviaciones_count: int = Field(default=0, description="Desviaciones detectadas")

    # Resumen financiero
    presupuesto_total_anual: Decimal = Field(..., description="Presupuesto total anual")
    ejecucion_total_anual: Decimal = Field(..., description="Ejecución total anual")
    desviacion_global: Decimal = Field(..., description="Desviación global")
    porcentaje_ejecucion_global: float = Field(..., description="% de ejecución global")

    # Detalles
    lineas_presupuestales: List[LineaPresupuestal] = Field(
        default_factory=list,
        description="Detalle de líneas presupuestales"
    )
    facturas_encontradas: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Facturas que coinciden"
    )
    facturas_faltantes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Facturas que faltan en BD"
    )
    desviaciones: List[DesviacionPresupuestal] = Field(
        default_factory=list,
        description="Desviaciones presupuestales"
    )

    # Alertas y recomendaciones
    alertas: List[str] = Field(default_factory=list, description="Alertas generadas")
    recomendaciones: List[str] = Field(default_factory=list, description="Recomendaciones")


class ImportacionRequest(BaseModel):
    """Request para importar archivo de presupuesto."""
    model_config = ConfigDict(from_attributes=True)

    año: int = Field(..., ge=2020, le=2030, description="Año del presupuesto")
    descripcion: Optional[str] = Field(None, max_length=500, description="Descripción de la importación")
    generar_reporte_pdf: bool = Field(default=False, description="Generar reporte en PDF")
    enviar_email: bool = Field(default=False, description="Enviar reporte por email")
    email_destino: Optional[str] = Field(None, description="Email para enviar reporte")


class ImportacionResponse(BaseModel):
    """Response de importación de presupuesto."""
    model_config = ConfigDict(from_attributes=True)

    id_importacion: int = Field(..., description="ID de la importación")
    estado: EstadoImportacion = Field(..., description="Estado de la importación")
    mensaje: str = Field(..., description="Mensaje descriptivo")
    reporte: Optional[ReporteComparacion] = Field(None, description="Reporte generado")
    archivo_pdf_url: Optional[str] = Field(None, description="URL del PDF generado")
    errores: List[str] = Field(default_factory=list, description="Errores encontrados")
    advertencias: List[str] = Field(default_factory=list, description="Advertencias")


class HistorialImportacion(BaseModel):
    """Historial de importaciones realizadas."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    archivo_origen: str
    año: int
    fecha_importacion: datetime
    usuario: str
    estado: EstadoImportacion
    total_lineas: int
    total_desviaciones: int
    desviacion_global: Decimal


class EstadisticasPresupuesto(BaseModel):
    """Estadísticas agregadas de presupuesto."""
    model_config = ConfigDict(from_attributes=True)

    periodo: str = Field(..., description="Período (YYYY o YYYY-MM)")
    total_lineas: int = Field(..., description="Total de líneas presupuestales")
    presupuesto_total: Decimal = Field(..., description="Presupuesto total")
    ejecucion_total: Decimal = Field(..., description="Ejecución total")
    desviacion_total: Decimal = Field(..., description="Desviación total")
    porcentaje_ejecucion: float = Field(..., description="% de ejecución")

    # Por área
    por_area: List[Dict[str, Any]] = Field(default_factory=list, description="Desglose por área")

    # Por responsable
    por_responsable: List[Dict[str, Any]] = Field(default_factory=list, description="Desglose por responsable")

    # Top desviaciones
    top_sobreejecutadas: List[Dict[str, Any]] = Field(default_factory=list, description="Top líneas sobre-ejecutadas")
    top_subejectudas: List[Dict[str, Any]] = Field(default_factory=list, description="Top líneas sub-ejecutadas")


# ========================================
# Schemas para API de Presupuesto Enterprise
# ========================================

class LineaPresupuestalCreate(BaseModel):
    """Schema para crear línea presupuestal."""
    model_config = ConfigDict(from_attributes=True)

    codigo: str = Field(..., min_length=1, max_length=50)
    nombre: str = Field(..., min_length=1, max_length=255)
    descripcion: Optional[str] = None
    responsable_id: int
    año_fiscal: int
    presupuestos_mensuales: Dict[str, Decimal] = Field(
        ...,
        description="Dict con claves: ene, feb, mar, abr, may, jun, jul, ago, sep, oct, nov, dic"
    )
    centro_costo: Optional[str] = None
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    proveedor_preferido: Optional[str] = None
    umbral_alerta: Optional[int] = 80
    nivel_aprobacion: Optional[str] = "RESPONSABLE_LINEA"
    creado_por: Optional[str] = None


class LineaPresupuestalUpdate(BaseModel):
    """Schema para actualizar línea presupuestal."""
    model_config = ConfigDict(from_attributes=True)

    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    presupuesto_ene: Optional[Decimal] = None
    presupuesto_feb: Optional[Decimal] = None
    presupuesto_mar: Optional[Decimal] = None
    presupuesto_abr: Optional[Decimal] = None
    presupuesto_may: Optional[Decimal] = None
    presupuesto_jun: Optional[Decimal] = None
    presupuesto_jul: Optional[Decimal] = None
    presupuesto_ago: Optional[Decimal] = None
    presupuesto_sep: Optional[Decimal] = None
    presupuesto_oct: Optional[Decimal] = None
    presupuesto_nov: Optional[Decimal] = None
    presupuesto_dic: Optional[Decimal] = None
    centro_costo: Optional[str] = None
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    proveedor_preferido: Optional[str] = None
    umbral_alerta: Optional[int] = None
    actualizado_por: str


class LineaPresupuestalResponse(BaseModel):
    """Schema de respuesta para línea presupuestal."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str]
    responsable_id: int
    año_fiscal: int

    presupuesto_ene: Optional[Decimal]
    presupuesto_feb: Optional[Decimal]
    presupuesto_mar: Optional[Decimal]
    presupuesto_abr: Optional[Decimal]
    presupuesto_may: Optional[Decimal]
    presupuesto_jun: Optional[Decimal]
    presupuesto_jul: Optional[Decimal]
    presupuesto_ago: Optional[Decimal]
    presupuesto_sep: Optional[Decimal]
    presupuesto_oct: Optional[Decimal]
    presupuesto_nov: Optional[Decimal]
    presupuesto_dic: Optional[Decimal]

    presupuesto_anual: Decimal
    ejecutado_acumulado: Decimal
    saldo_disponible: Decimal
    porcentaje_ejecucion: Decimal

    estado: str
    centro_costo: Optional[str]
    categoria: Optional[str]
    subcategoria: Optional[str]
    proveedor_preferido: Optional[str]

    umbral_alerta_porcentaje: int
    nivel_aprobacion_requerido: str

    aprobado_por: Optional[str]
    fecha_aprobacion: Optional[datetime]
    observaciones_aprobacion: Optional[str]

    fecha_inicio_vigencia: Optional[datetime]
    fecha_fin_vigencia: Optional[datetime]

    version: int
    creado_por: Optional[str]
    creado_en: datetime
    actualizado_por: Optional[str]
    actualizado_en: Optional[datetime]


class EjecucionPresupuestalCreate(BaseModel):
    """Schema para crear ejecución presupuestal."""
    model_config = ConfigDict(from_attributes=True)

    linea_presupuesto_id: int
    factura_id: int
    monto_ejecutado: Decimal
    periodo_ejecucion: date = Field(..., description="Fecha de la ejecución (se extrae mes/año)")
    descripcion: Optional[str] = None
    vinculacion_automatica: Optional[bool] = False
    confianza_vinculacion: Optional[int] = None
    criterios_matching: Optional[Dict[str, Any]] = None
    creado_por: Optional[str] = None


class EjecucionPresupuestalResponse(BaseModel):
    """Schema de respuesta para ejecución presupuestal."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    linea_presupuesto_id: int
    factura_id: int
    monto_ejecutado: Decimal
    periodo_ejecucion: date
    mes_ejecucion: int
    año_ejecucion: int

    presupuesto_mes_correspondiente: Decimal
    desviacion: Decimal
    desviacion_porcentaje: Decimal
    tipo_desviacion: str

    descripcion: Optional[str]
    estado: str

    vinculacion_automatica: bool
    tipo_vinculacion: str
    confianza_vinculacion: Optional[int]
    criterios_matching: Optional[Dict[str, Any]]

    aprobado_nivel1: bool
    aprobador_nivel1: Optional[str]
    fecha_aprobacion_nivel1: Optional[datetime]
    observaciones_nivel1: Optional[str]

    aprobado_nivel2: bool
    aprobador_nivel2: Optional[str]
    fecha_aprobacion_nivel2: Optional[datetime]
    observaciones_nivel2: Optional[str]

    aprobado_nivel3: bool
    aprobador_nivel3: Optional[str]
    fecha_aprobacion_nivel3: Optional[datetime]
    observaciones_nivel3: Optional[str]

    requiere_aprobacion_nivel2: bool
    requiere_aprobacion_nivel3: bool

    fecha_aprobacion_final: Optional[datetime]
    motivo_rechazo: Optional[str]

    alerta_generada: bool
    tipo_alerta: Optional[str]
    notificacion_enviada: bool
    destinatarios_notificacion: Optional[Dict[str, Any]]

    creado_por: Optional[str]
    creado_en: datetime
    actualizado_por: Optional[str]
    actualizado_en: Optional[datetime]


class AprobacionRequest(BaseModel):
    """Schema para aprobar una ejecución o línea."""
    model_config = ConfigDict(from_attributes=True)

    aprobador: str
    observaciones: Optional[str] = None


class RechazoRequest(BaseModel):
    """Schema para rechazar una ejecución."""
    model_config = ConfigDict(from_attributes=True)

    rechazado_por: str
    motivo_rechazo: str


class DashboardPresupuesto(BaseModel):
    """Schema para dashboard de presupuesto."""
    model_config = ConfigDict(from_attributes=True)

    año_fiscal: int
    total_lineas: int
    presupuesto_total: float
    ejecutado_total: float
    saldo_total: float
    porcentaje_ejecucion_global: float
    lineas_por_estado: Dict[str, int]
    lineas_en_riesgo: List[Dict[str, Any]]
    total_lineas_en_riesgo: int
