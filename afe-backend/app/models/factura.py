# app/models/factura.py
from sqlalchemy import Column, BigInteger, String, Date, Numeric, Enum, Boolean, ForeignKey, DateTime, UniqueConstraint, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class EstadoFactura(enum.Enum):
    """
    Estados de factura - FLUJO CONTADOR SIMPLIFICADO (sin Tesorería).

    FASE 0: PRE-PROCESAMIENTO (2025-12-14)
    - en_cuarentena: Factura sin grupo_id asignado (requiere configuración manual)

    FASE 1: APROBACIÓN (Responsable revisa)
    - en_revision: Factura requiere revisión manual
    - aprobada: Factura aprobada manualmente por usuario
    - aprobada_auto: Factura aprobada automáticamente por el sistema
    - rechazada: Factura rechazada por usuario

    FASE 2: VALIDACIÓN (Contador revisa - SIN PAGO)
    - validada_contabilidad: Contador validó - OK para que Tesorería la procese
    - devuelta_contabilidad: Contador devolvió - requiere corrección

    NOTA: Tesorería es sistema aparte. Solo enviamos facturas validadas por Contador.
    """
    # FASE 0: PRE-PROCESAMIENTO
    en_cuarentena = "en_cuarentena"

    # FASE 1: APROBACIÓN
    en_revision = "en_revision"
    aprobada = "aprobada"
    aprobada_auto = "aprobada_auto"
    rechazada = "rechazada"

    # FASE 2: VALIDACIÓN CONTABLE
    validada_contabilidad = "validada_contabilidad"
    devuelta_contabilidad = "devuelta_contabilidad"

class EstadoAsignacion(enum.Enum):
    """
    PHASE 3: Estados de asignación de usuarios (enterprise tracking).

    Estados posibles:
    - sin_asignar: Factura sin responsable (responsable_id = NULL)
    - asignado: Factura con responsable activo (responsable_id != NULL)
    - huerfano: Factura que perdió su responsable (responsable_id=NULL pero accion_por!=NULL)
    - inconsistente: Estado anómalo que requiere investigación (futura auditoría)
    """
    sin_asignar = "sin_asignar"
    asignado = "asignado"
    huerfano = "huerfano"
    inconsistente = "inconsistente"

class Factura(Base):
    __tablename__ = "facturas"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    numero_factura = Column(String(50), nullable=False)
    fecha_emision = Column(Date, nullable=False)
    proveedor_id = Column(BigInteger, ForeignKey("proveedores.id"), nullable=True)
    subtotal = Column(Numeric(15, 2, asdecimal=True))
    iva = Column(Numeric(15, 2, asdecimal=True))
    estado = Column(Enum(EstadoFactura), default=EstadoFactura.en_revision, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)
    cufe = Column(String(100), unique=True, nullable=False)
    total_a_pagar = Column(Numeric(15, 2, asdecimal=True))
    responsable_id = Column(BigInteger, ForeignKey("usuarios.id"), nullable=True)

    # FASE 1: MULTI-TENANT - Grupo empresarial
    grupo_id = Column(
        BigInteger,
        ForeignKey("grupos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Grupo empresarial al que pertenece la factura"
    )

    # ACCION_POR: Single source of truth for "who changed the status"
    # Automatically synchronized from workflow_aprobacion_facturas.aprobada_por/rechazada_por
    # This is the ONLY place this information should be read from in the dashboard
    accion_por = Column(String(255), nullable=True, index=True,
                       comment="Who approved/rejected the factura - synchronized from workflow")

    # PHASE 3: ESTADO_ASIGNACION: Track assignment lifecycle
    # Automatically computed field: sin_asignar, asignado, huerfano, inconsistente
    # Used by dashboard to display accurate assignment status and identify orphaned facturas
    estado_asignacion = Column(
        Enum(EstadoAsignacion),
        default=EstadoAsignacion.sin_asignar,
        nullable=False,
        index=True,
        comment="PHASE 3: Assignment status - sin_asignar/asignado/huerfano/inconsistente"
    )

    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # CAMPOS PARA AUTOMATIZACIÓN DE FACTURAS RECURRENTES ✨
    # NOTA: Campos de aprobación/rechazo eliminados en Fase 2.4
    # Ahora viven en workflow_aprobacion_facturas
    # Acceso vía propiedades: aprobado_por_workflow, fecha_aprobacion_workflow, etc.

    # Automatización inteligente
    confianza_automatica = Column(Numeric(3, 2), nullable=True,
                                 comment="Confianza (0.00-1.00) para aprobación automática")
    factura_referencia_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=True,
                                  comment="ID de factura del mes anterior usada como referencia")
    motivo_decision = Column(String(500), nullable=True,
                           comment="Razón de la decisión automática")

    # Metadata y auditoría
    fecha_procesamiento_auto = Column(DateTime(timezone=True), nullable=True,
                                     comment="Cuándo se ejecutó el procesamiento automático")

    # CAMPOS PARA MATCHING Y COMPARACIÓN EMPRESARIAL ✨

    # Concepto y descripción
    concepto_principal = Column(String(500), nullable=True,
                               comment="Descripción/concepto principal de la factura")
    concepto_hash = Column(String(32), nullable=True, index=True,
                          comment="Hash MD5 del concepto normalizado para matching rápido")
    concepto_normalizado = Column(String(500), nullable=True,
                                 comment="Concepto sin stopwords y normalizado")

    # Orden de compra
    orden_compra_numero = Column(String(50), nullable=True, index=True,
                                comment="Número de orden de compra asociada")

    # Patrón de recurrencia
    patron_recurrencia = Column(String(20), nullable=True,
                               comment="Patrón: FIJO, VARIABLE, UNICO, DESCONOCIDO")

    # Tipo de factura (clasificación empresarial)
    tipo_factura = Column(String(20), nullable=False, server_default='COMPRA',
                         comment="Tipo: COMPRA, VENTA, NOTA_CREDITO, NOTA_DEBITO")

    proveedor = relationship("Proveedor", back_populates="facturas", lazy="joined")
    usuario = relationship("Usuario", back_populates="facturas", lazy="joined")
    grupo = relationship("Grupo", back_populates="facturas", lazy="joined")

    # Relationship para factura de referencia (para automatización)
    factura_referencia = relationship("Factura", remote_side=[id], backref="facturas_relacionadas")

    # NUEVA RELACIÓN: Items de la factura (líneas individuales)
    items = relationship(
        "FacturaItem",
        back_populates="factura",
        lazy="selectin",  # Carga eficiente de items
        cascade="all, delete-orphan",  # Si se borra factura, se borran items
        order_by="FacturaItem.numero_linea"  # Ordenados por línea
    )

    # FASE 2: Relación a Workflow (para normalización de datos)
    # NOTA: uselist=True porque con multi-responsable, una factura puede tener múltiples workflows
    workflow_history = relationship(
        "WorkflowAprobacionFactura",
        foreign_keys="[WorkflowAprobacionFactura.factura_id]",
        uselist=True,   # Múltiples workflows por factura (multi-responsable)
        lazy="select",  # Lazy loading con explicit selectinload en CRUD
        viewonly=True   # No modifica desde Factura
    )


    __table_args__ = (UniqueConstraint("numero_factura", "proveedor_id", name="uix_num_prov"),)

    # ==================== COMPUTED PROPERTIES (FASE 1 - PROFESIONAL) ====================

    @property
    def total_calculado(self):
        """
        Total calculado dinámicamente desde subtotal + IVA.

        FALLBACK: Si subtotal e iva están nulos (datos legacy), usa total_a_pagar
        como fuente de verdad.

        Nivel: Fortune 500 Data Integrity
        """
        from decimal import Decimal
        subtotal = self.subtotal or Decimal('0.00')
        iva = self.iva or Decimal('0.00')
        calculado = subtotal + iva

        # Fallback: Si está vacío y tenemos total_a_pagar, usarlo
        if calculado == Decimal('0.00') and self.total_a_pagar:
            return self.total_a_pagar

        return calculado

    @property
    def total_desde_items(self):
        """
        Total calculado desde la suma de items individuales.

        Útil para validación y detección de inconsistencias.
        Si total_calculado != total_desde_items, hay un problema de integridad.

        Returns:
            Decimal: Suma de total de todos los items
        """
        from decimal import Decimal
        if not self.items:
            return Decimal('0.00')
        return sum((item.total or Decimal('0.00')) for item in self.items)

    @property
    def tiene_inconsistencia_total(self):
        """
        Detecta si hay inconsistencia entre total almacenado vs calculado.

        Returns:
            bool: True si hay inconsistencia que requiere corrección
        """
        from decimal import Decimal
        if self.total_a_pagar is None:
            return False

        diferencia = abs(self.total_a_pagar - self.total_calculado)
        # Tolerancia de 1 centavo por redondeo
        return diferencia > Decimal('0.01')

    # ==================== HELPERS DE WORKFLOW (FASE 2 - NORMALIZACIÓN) ====================

    @property
    def aprobado_por_workflow(self):
        """
        Usuario que aprobó la factura (desde workflow).

          FASE 2.4 COMPLETADA:
        Los campos de aprobación/rechazo ahora viven exclusivamente en workflow.
        Datos 100% normalizados (3NF perfecto).

        Nivel: Fortune 500 Data Normalization
        """
        if self.workflow_history:
            # Buscar el workflow con aprobación (puede haber múltiples por multi-responsable)
            for wf in self.workflow_history:
                if wf.aprobada_por:
                    return wf.aprobada_por
        return None

    @property
    def fecha_aprobacion_workflow(self):
        """Fecha de aprobación (desde workflow)."""
        if self.workflow_history:
            for wf in self.workflow_history:
                if wf.fecha_aprobacion:
                    return wf.fecha_aprobacion
        return None

    @property
    def rechazado_por_workflow(self):
        """Usuario que rechazó (desde workflow)."""
        if self.workflow_history:
            for wf in self.workflow_history:
                if wf.rechazada_por:
                    return wf.rechazada_por
        return None

    @property
    def fecha_rechazo_workflow(self):
        """Fecha de rechazo (desde workflow)."""
        if self.workflow_history:
            for wf in self.workflow_history:
                if wf.fecha_rechazo:
                    return wf.fecha_rechazo
        return None

    @property
    def motivo_rechazo_workflow(self):
        """Motivo de rechazo (desde workflow)."""
        if self.workflow_history:
            for wf in self.workflow_history:
                if wf.detalle_rechazo:
                    return wf.detalle_rechazo
        return None

    @property
    def tipo_aprobacion_workflow(self):
        """
        Tipo de aprobación (solo disponible en workflow).

        Returns:
            str: 'automatica', 'manual', 'masiva', 'forzada' o None
        """
        if self.workflow_history:
            for wf in self.workflow_history:
                if wf.tipo_aprobacion:
                    return wf.tipo_aprobacion.value
        return None

    # ==================== PHASE 3: ASSIGNMENT STATUS TRACKING ====================

    def calcular_estado_asignacion(self):
        """
        Calcula automáticamente el estado de asignación de la factura.

        PHASE 3: Enterprise-grade assignment tracking.

        Lógica:
        - sin_asignar: responsable_id = NULL AND accion_por = NULL
        - asignado: responsable_id != NULL (independiente de accion_por)
        - huerfano: responsable_id = NULL AND accion_por != NULL
                    (la factura fue procesada pero perdió su responsable)
        - inconsistente: Otros estados anómalos (reservado para auditoría)

        Returns:
            EstadoAsignacion: El estado calculado
        """
        has_responsable = self.responsable_id is not None
        has_accion_por = self.accion_por is not None

        if has_responsable:
            # Factura asignada a responsable
            return EstadoAsignacion.asignado
        elif has_accion_por:
            # Factura sin responsable pero fue procesada (huérfana)
            return EstadoAsignacion.huerfano
        else:
            # Factura sin asignar y sin procesar
            return EstadoAsignacion.sin_asignar

    def validar_y_actualizar_estado_asignacion(self):
        """
        Valida y actualiza el estado de asignación si es necesario.

        Se ejecuta automáticamente en hooks de SQLAlchemy (before_update, before_insert).

        Returns:
            bool: True si se actualizó, False si no fue necesario
        """
        nuevo_estado = self.calcular_estado_asignacion()
        if self.estado_asignacion != nuevo_estado:
            self.estado_asignacion = nuevo_estado
            return True
        return False

