# app/models/email_config.py
"""
Modelos para configuración de extracción de correos corporativos con Microsoft Graph.

Soporta múltiples cuentas de correo con configuraciones independientes de:
- NITs a filtrar
- Límites de extracción
- Días de búsqueda retroactiva
- Estado activo/inactivo
"""
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, CheckConstraint, event
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
from app.db.base import Base


class CuentaCorreo(Base):
    """
    Cuenta de correo corporativo configurada para extracción de facturas.

    Ejemplo: facturacion.electronica@angiografiadecolombia.com
    """
    __tablename__ = "cuentas_correo"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True, comment="Email corporativo (Microsoft Graph)")
    nombre_descriptivo = Column(String(255), nullable=True, comment="Nombre amigable: 'Angiografía de Colombia'")

    # Configuración de extracción incremental
    max_correos_por_ejecucion = Column(Integer, nullable=False, default=10000, comment="Límite de seguridad por ejecución (no arbitrario)")
    ventana_inicial_dias = Column(Integer, nullable=False, default=30, comment="Días hacia atrás en primera ejecución")

    # Tracking de extracción incremental
    ultima_ejecucion_exitosa = Column(DateTime(timezone=True), nullable=True, comment="Última ejecución exitosa (para extracción incremental)")
    fecha_ultimo_correo_procesado = Column(DateTime(timezone=True), nullable=True, comment="Timestamp del último correo procesado")

    # Estado y metadata
    activa = Column(Boolean, nullable=False, default=True, index=True, comment="Si está activa para extracción")
    organizacion = Column(String(100), nullable=True, index=True, comment="Organización: 'ANGIOGRAFIA', 'AVIDANTI', etc.")

    # FASE 2: MULTI-TENANT - Grupo empresarial
    grupo_id = Column(
        BigInteger,
        ForeignKey("grupos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Grupo empresarial al que pertenece esta cuenta de correo"
    )

    # Auditoría
    creada_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizada_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    creada_por = Column(String(100), nullable=False, comment="Usuario que creó la configuración")
    actualizada_por = Column(String(100), nullable=True, comment="Último usuario que modificó")

    # Relaciones
    nits = relationship("NitConfiguracion", back_populates="cuenta_correo", cascade="all, delete-orphan")
    historial_extracciones = relationship("HistorialExtraccion", back_populates="cuenta_correo", cascade="all, delete-orphan")
    grupo = relationship("Grupo", back_populates="cuentas_correo", lazy="joined")

    # Constraints
    __table_args__ = (
        CheckConstraint('max_correos_por_ejecucion > 0 AND max_correos_por_ejecucion <= 100000', name='check_max_correos_range'),
        CheckConstraint('ventana_inicial_dias > 0 AND ventana_inicial_dias <= 365', name='check_ventana_inicial_range'),
        Index('idx_cuenta_correo_activa_org', 'activa', 'organizacion'),
    )

    def __repr__(self):
        return f"<CuentaCorreo(id={self.id}, email='{self.email}', activa={self.activa})>"


class NitConfiguracion(Base):
    """
    NITs configurados para filtrado de facturas por cuenta de correo.

    Relación N:1 con CuentaCorreo (una cuenta puede tener múltiples NITs).
    """
    __tablename__ = "nit_configuracion"

    id = Column(Integer, primary_key=True, index=True)
    cuenta_correo_id = Column(Integer, ForeignKey("cuentas_correo.id", ondelete="CASCADE"), nullable=False, index=True)
    nit = Column(String(20), nullable=False, index=True, comment="NIT del proveedor/emisor a filtrar")

    # Metadata opcional
    nombre_proveedor = Column(String(255), nullable=True, comment="Nombre del proveedor (opcional)")
    activo = Column(Boolean, nullable=False, default=True, comment="Si este NIT está activo para filtrado")
    notas = Column(String(500), nullable=True, comment="Notas adicionales sobre este NIT")

    # Auditoría
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    creado_por = Column(String(100), nullable=False)
    actualizado_por = Column(String(100), nullable=True)

    # Relaciones
    cuenta_correo = relationship("CuentaCorreo", back_populates="nits")

    # Constraints: Un NIT no puede estar duplicado en la misma cuenta
    __table_args__ = (
        UniqueConstraint('cuenta_correo_id', 'nit', name='uq_cuenta_nit'),
        Index('idx_nit_activo', 'nit', 'activo'),
    )

    def __repr__(self):
        return f"<NitConfiguracion(id={self.id}, cuenta_id={self.cuenta_correo_id}, nit='{self.nit}')>"


class HistorialExtraccion(Base):
    """
    Historial de ejecuciones de extracción de correos por cuenta.

    Registra cada vez que se ejecuta el proceso de extracción para auditoría y métricas.
    """
    __tablename__ = "historial_extracciones"

    id = Column(Integer, primary_key=True, index=True)
    cuenta_correo_id = Column(Integer, ForeignKey("cuentas_correo.id", ondelete="CASCADE"), nullable=False, index=True)

    # Información de la extracción
    fecha_ejecucion = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    correos_procesados = Column(Integer, nullable=False, default=0, comment="Total de correos analizados")
    facturas_encontradas = Column(Integer, nullable=False, default=0, comment="Facturas XML encontradas")
    facturas_creadas = Column(Integer, nullable=False, default=0, comment="Nuevas facturas creadas")
    facturas_actualizadas = Column(Integer, nullable=False, default=0, comment="Facturas actualizadas")
    facturas_ignoradas = Column(Integer, nullable=False, default=0, comment="Facturas duplicadas/ignoradas")

    # Resultado
    exito = Column(Boolean, nullable=False, default=True)
    mensaje_error = Column(String(1000), nullable=True, comment="Mensaje de error si falla")
    tiempo_ejecucion_ms = Column(Integer, nullable=True, comment="Tiempo de ejecución en milisegundos")

    # Configuración usada en la extracción
    fetch_limit_usado = Column(Integer, nullable=True)
    fetch_days_usado = Column(Integer, nullable=True)
    nits_usados = Column(Integer, nullable=True, comment="Cantidad de NITs activos en la extracción")

    # Tracking de extracción incremental
    fecha_desde = Column(DateTime(timezone=True), nullable=True, comment="Fecha desde la cual se extrajeron correos")
    fecha_hasta = Column(DateTime(timezone=True), nullable=True, comment="Fecha hasta la cual se extrajeron correos")
    es_primera_ejecucion = Column(Boolean, nullable=False, default=False, comment="Si fue la primera ejecución de esta cuenta")

    # Relaciones
    cuenta_correo = relationship("CuentaCorreo", back_populates="historial_extracciones")

    # Índices
    __table_args__ = (
        Index('idx_historial_fecha_exito', 'fecha_ejecucion', 'exito'),
        Index('idx_historial_cuenta_fecha', 'cuenta_correo_id', 'fecha_ejecucion'),
    )

    def __repr__(self):
        return f"<HistorialExtraccion(id={self.id}, cuenta_id={self.cuenta_correo_id}, facturas={self.facturas_encontradas})>"


# ==================== LISTENERS DE SINCRONIZACIÓN ====================

@event.listens_for(NitConfiguracion, 'before_insert')
@event.listens_for(NitConfiguracion, 'before_update')
def sincronizar_nombre_proveedor(mapper, connection, target):
    """
    SINCRONIZACIÓN AUTOMÁTICA: NITs → Proveedores (Single Source of Truth).

    ARQUITECTURA PROFESIONAL:
    - SIEMPRE sincroniza desde tabla proveedores (fuente de verdad)
    - No permite overrides manuales
    - Garantiza consistencia de datos en todo momento

    Se ejecuta ANTES de INSERT/UPDATE en nit_configuracion.
    """
    if target.nit:
        from app.models.proveedor import Proveedor
        session = Session.object_session(target)
        if session:
            proveedor = session.query(Proveedor).filter(
                Proveedor.nit == target.nit
            ).first()

            if proveedor and proveedor.razon_social:
                # SIEMPRE sobrescribir con la fuente de verdad
                target.nombre_proveedor = proveedor.razon_social
            else:
                # Si no existe proveedor, marcar como NULL
                target.nombre_proveedor = None
