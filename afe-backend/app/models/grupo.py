"""
Modelo de Grupo (Sede/Empresa) para clasificación de facturas por grupos.

Arquitectura Multi-Tenant con Jerarquía:
- Cada grupo es una sede u empresa
- Soporta jerarquía de grupos (padre-hijo)
- Un responsable puede estar en múltiples grupos
- Un NIT puede estar en múltiples grupos con diferentes usuarios
- Las facturas pertenecen a un grupo específico

Jerarquía:
- grupo_padre_id: FK al grupo padre (NULL si es raíz)
- nivel: Nivel en jerarquía (1=raíz, 2=hijo, 3=nieto...)
- ruta_jerarquica: Path completo "1/5/12" para navegación eficiente

Nivel: Enterprise Multi-Tenant Architecture
"""

from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Text, JSON, Index, UniqueConstraint, ForeignKey, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime
from typing import Optional, List


class Grupo(Base):
    """
    Grupo o Sede empresarial con soporte jerárquico.

    Representa una unidad de negocio con estructura jerárquica:
    - Grupos raíz (nivel 1): AVIDANTI, ADC, DSZF, CAA
    - Grupos hijos (nivel 2+): CAM, CAI, CASM (hijos de AVIDANTI)

    Campos principales:
    - id: Identificador único
    - codigo_corto: Código único (CAM, CAI, AVID, etc.)
    - nombre: Nombre completo del grupo
    - grupo_padre_id: FK al grupo padre (NULL si es raíz)
    - nivel: Nivel en jerarquía (1=raíz, 2=hijo...)
    - ruta_jerarquica: Path completo "1/5/12"
    - correos_corporativos: JSON array de correos
    - permite_subsedes: ¿Puede tener hijos?
    - max_nivel_subsedes: Profundidad máxima permitida
    """

    __tablename__ = "grupos"

    # ==================== PRIMARY KEY ====================
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Identificador único del grupo"
    )

    # ==================== IDENTIFICACIÓN ====================
    nombre = Column(
        String(150),
        nullable=False,
        index=True,
        comment="Nombre del grupo/sede"
    )

    codigo_corto = Column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        comment="Código único (CAM, CAI, AVID, etc.)"
    )

    descripcion = Column(
        Text,
        nullable=True,
        comment="Descripción detallada del grupo"
    )

    # ==================== JERARQUÍA ====================
    grupo_padre_id = Column(
        BigInteger,
        ForeignKey("grupos.id", name="fk_grupo_padre"),
        nullable=True,
        index=True,
        comment="FK al grupo padre (NULL si es raíz)"
    )

    nivel = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Nivel en jerarquía (1=raíz, 2=hijo, etc.)"
    )

    ruta_jerarquica = Column(
        String(500),
        nullable=True,
        index=True,
        comment="Ruta completa: '1/5/12' para navegación"
    )

    # ==================== CONFIGURACIÓN ====================
    correos_corporativos = Column(
        JSON,
        nullable=True,
        default=list,
        comment="Array de correos corporativos del grupo"
    )

    permite_subsedes = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="¿Puede tener hijos?"
    )

    max_nivel_subsedes = Column(
        Integer,
        nullable=False,
        default=3,
        comment="Profundidad máxima permitida"
    )

    # ==================== ESTADO ====================
    activo = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
        comment="Estado activo/inactivo"
    )

    eliminado = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True,
        comment="Soft delete"
    )

    fecha_eliminacion = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Cuándo se eliminó"
    )

    eliminado_por = Column(
        String(255),
        nullable=True,
        comment="Usuario que eliminó"
    )

    # ==================== AUDITORÍA ====================
    creado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp de creación"
    )

    creado_por = Column(
        String(255),
        nullable=False,
        default="SYSTEM",
        comment="Usuario que creó"
    )

    actualizado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp de última actualización"
    )

    actualizado_por = Column(
        String(255),
        nullable=True,
        comment="Usuario que actualizó"
    )

    # ==================== RELACIONES ====================
    # Auto-referencia para jerarquía
    grupo_padre = relationship(
        "Grupo",
        remote_side=[id],
        backref="hijos",
        foreign_keys=[grupo_padre_id]
    )

    # Relación M:N con Usuario
    usuarios = relationship(
        "ResponsableGrupo",
        back_populates="grupo",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # Relación con facturas
    facturas = relationship(
        "Factura",
        back_populates="grupo",
        lazy="select"
    )

    # Relación con asignaciones NIT
    asignaciones_nit = relationship(
        "AsignacionNitResponsable",
        back_populates="grupo",
        lazy="select"
    )

    # Relación con cuentas de correo
    cuentas_correo = relationship(
        "CuentaCorreo",
        back_populates="grupo",
        lazy="select"
    )

    # ==================== ÍNDICES ====================
    __table_args__ = (
        Index('idx_grupo_padre', 'grupo_padre_id'),
        Index('idx_grupo_activo_eliminado', 'activo', 'eliminado'),
        Index('idx_grupo_ruta', 'ruta_jerarquica'),
        Index('idx_grupo_codigo', 'codigo_corto'),
    )

    def __repr__(self) -> str:
        return f"<Grupo(id={self.id}, codigo={self.codigo_corto}, nombre={self.nombre}, nivel={self.nivel})>"

    # ==================== MÉTODOS HELPER ====================
    def es_raiz(self) -> bool:
        """Verifica si el grupo es raíz (no tiene padre)."""
        return self.grupo_padre_id is None

    def puede_tener_hijos(self) -> bool:
        """Verifica si el grupo puede tener subsedes."""
        return self.permite_subsedes and self.nivel < self.max_nivel_subsedes

    def soft_delete(self, usuario: str) -> None:
        """Realiza soft delete del grupo."""
        self.eliminado = True
        self.activo = False
        self.fecha_eliminacion = datetime.utcnow()
        self.eliminado_por = usuario


class ResponsableGrupo(Base):
    """
    Tabla relacional M:N entre Usuario y Grupo con Auditoría Completa.

    Define la relación entre usuarios y grupos:
    - Un responsable puede estar en múltiples grupos
    - Un grupo puede tener múltiples usuarios
    - Cada responsable tiene un rol específico en cada grupo

    Campos principales:
    - responsable_id: FK a usuarios
    - grupo_id: FK a grupos
    - activo: Flag de estado (soft delete)

    Auditoría (Enterprise-grade):
    - asignado_en: Cuándo se creó la asignación
    - asignado_por: Quién creó la asignación (username/email)
    - actualizado_en: Última modificación
    - actualizado_por: Quién modificó (username/email)
    - creado_en: Deprecado (mantener por compatibilidad)
    """

    __tablename__ = "responsable_grupo"

    # ==================== PRIMARY KEY ====================
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Identificador único"
    )

    # ==================== FOREIGN KEYS ====================
    responsable_id = Column(
        BigInteger,
        ForeignKey("usuarios.id", name="fk_responsable_grupo_usuario"),
        nullable=False,
        index=True,
        comment="FK a usuarios"
    )

    grupo_id = Column(
        BigInteger,
        ForeignKey("grupos.id", name="fk_responsable_grupo_grupo"),
        nullable=False,
        index=True,
        comment="FK a grupos"
    )

    # ==================== ESTADO ====================
    activo = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="Flag de pertenencia activa"
    )

    # ==================== AUDITORÍA ====================
    asignado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Cuándo se asignó el responsable al grupo"
    )

    asignado_por = Column(
        String(100),
        nullable=True,
        comment="Usuario que asignó (username/email)"
    )

    actualizado_en = Column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
        comment="Última actualización"
    )

    actualizado_por = Column(
        String(100),
        nullable=True,
        comment="Usuario que actualizó (username/email)"
    )

    # Mantener creado_en por compatibilidad (deprecado)
    creado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp de creación (deprecado - usar asignado_en)"
    )

    # ==================== RELACIONES ====================
    grupo = relationship("Grupo", back_populates="usuarios", foreign_keys=[grupo_id])
    usuario = relationship("Usuario", back_populates="grupos", foreign_keys=[responsable_id])

    # ==================== CONSTRAINTS ====================
    __table_args__ = (
        UniqueConstraint('responsable_id', 'grupo_id', name='uq_responsable_grupo'),
        Index('idx_responsable_grupo_grupo', 'grupo_id'),
        Index('idx_responsable_grupo_responsable', 'responsable_id'),
    )

    def __repr__(self) -> str:
        return f"<ResponsableGrupo(responsable_id={self.responsable_id}, grupo_id={self.grupo_id}, activo={self.activo})>"
