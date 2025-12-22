# app/models/patrones_facturas.py
"""
Modelo para análisis estadístico de patrones de facturas por proveedor y concepto.

Este modelo almacena el análisis histórico (últimos 12 meses) de facturas
para generar recomendaciones inteligentes en el workflow de aprobación automática.

NO realiza pagos ni tracking de transacciones - es puramente análisis estadístico.
"""
from sqlalchemy import Column, BigInteger, String, Numeric, Integer, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum


class TipoPatron(enum.Enum):
    """
    Clasificación de patrones según el PDF del proyecto:
    - TIPO_A: Valores fijos predecibles (misma cantidad mensual)
    - TIPO_B: Valores fluctuantes predecibles (dentro de rangos conocidos)
    - TIPO_C: Valores excepcionales (nuevos proveedores, montos atípicos)
    """
    TIPO_A = "TIPO_A"  # Fijo - CV < 5%
    TIPO_B = "TIPO_B"  # Fluctuante predecible - CV < 30%
    TIPO_C = "TIPO_C"  # Excepcional - CV > 30% o sin historial


class PatronesFacturas(Base):
    """
    Modelo para análisis estadístico de patrones de facturas por proveedor y concepto.

    Propósito:
    - Analiza facturas históricas (últimos 12 meses) agrupadas por proveedor + concepto
    - Calcula estadísticas: promedio, desviación, coeficiente de variación
    - Clasifica patrones como TIPO_A (fijo), TIPO_B (fluctuante), TIPO_C (excepcional)
    - Genera recomendaciones de aprobación automática para el workflow

    NO es un sistema de pagos - no realiza transacciones ni reconciliación.
    Es puramente análisis estadístico para inteligencia de aprobación.

    Relación: Proveedor (1) -> PatronesFacturas (N)
    """
    __tablename__ = "patrones_facturas"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # ============================================================================
    # IDENTIFICACIÓN DEL PATRÓN
    # ============================================================================
    proveedor_id = Column(
        BigInteger,
        ForeignKey("proveedores.id"),
        nullable=False,
        index=True,
        comment="FK a proveedor"
    )

    concepto_normalizado = Column(
        String(200),
        nullable=False,
        index=True,
        comment="Concepto normalizado para matching"
    )

    concepto_hash = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Hash MD5 del concepto para búsqueda rápida"
    )

    # ============================================================================
    # CLASIFICACIÓN DEL PATRÓN
    # ============================================================================
    tipo_patron = Column(
        Enum(TipoPatron),
        nullable=False,
        index=True,
        comment="Clasificación: TIPO_A (fijo), TIPO_B (fluctuante), TIPO_C (excepcional)"
    )

    # ============================================================================
    # ESTADÍSTICAS DE ANÁLISIS (últimos 12 meses)
    # ============================================================================
    pagos_analizados = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Cantidad de facturas analizadas"
    )

    meses_con_pagos = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Cantidad de meses diferentes con facturas"
    )

    # ============================================================================
    # ANÁLISIS ESTADÍSTICO
    # ============================================================================
    monto_promedio = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Promedio de montos de facturas"
    )

    monto_minimo = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Monto mínimo histórico"
    )

    monto_maximo = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Monto máximo histórico"
    )

    desviacion_estandar = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Desviación estándar de los montos"
    )

    coeficiente_variacion = Column(
        Numeric(5, 2),
        nullable=False,
        comment="CV = (desv_std / promedio) * 100, métrica de estabilidad"
    )

    # ============================================================================
    # RANGO ESPERADO (Para TIPO_B)
    # ============================================================================
    rango_inferior = Column(
        Numeric(15, 2),
        nullable=True,
        comment="Límite inferior esperado (promedio - 2*desv)"
    )

    rango_superior = Column(
        Numeric(15, 2),
        nullable=True,
        comment="Límite superior esperado (promedio + 2*desv)"
    )

    # ============================================================================
    # PATRÓN DE RECURRENCIA
    # ============================================================================
    frecuencia_detectada = Column(
        String(50),
        nullable=True,
        comment="Frecuencia detectada: mensual, quincenal, trimestral, etc."
    )

    ultimo_pago_fecha = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de la última factura registrada"
    )

    ultimo_pago_monto = Column(
        Numeric(15, 2),
        nullable=True,
        comment="Monto de la última factura"
    )

    # ============================================================================
    # DATOS HISTÓRICOS DETALLADOS
    # ============================================================================
    pagos_detalle = Column(
        JSON,
        nullable=True,
        comment="Array con últimos 12 meses: [{periodo, monto, factura_id}]"
    )

    # ============================================================================
    # METADATA DEL ANÁLISIS
    # ============================================================================
    fecha_analisis = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Cuándo se realizó este análisis"
    )

    version_algoritmo = Column(
        String(20),
        nullable=False,
        server_default="1.0",
        comment="Versión del algoritmo de análisis"
    )

    # ============================================================================
    # RECOMENDACIÓN AUTOMÁTICA
    # ============================================================================
    puede_aprobar_auto = Column(
        Integer,
        nullable=False,
        default=0,
        comment="1 si cumple criterios para aprobación automática, 0 si no"
    )

    umbral_alerta = Column(
        Numeric(5, 2),
        nullable=True,
        comment="Porcentaje de desviación para generar alerta"
    )

    # ============================================================================
    # AUDITORÍA
    # ============================================================================
    creado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp de creación"
    )

    actualizado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp de última actualización"
    )

    # ============================================================================
    # RELATIONSHIPS
    # ============================================================================
    proveedor = relationship(
        "Proveedor",
        backref="patrones_facturas",
        lazy="joined"
    )

    def __repr__(self):
        return (
            f"<PatronesFacturas("
            f"id={self.id}, "
            f"proveedor_id={self.proveedor_id}, "
            f"concepto='{self.concepto_normalizado[:20]}...', "
            f"tipo={self.tipo_patron.value}, "
            f"promedio={self.monto_promedio}"
            f")>"
        )
