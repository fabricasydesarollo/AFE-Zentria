"""add_audit_fields_to_responsable_grupo

Agrega campos de auditoría enterprise-grade a la tabla responsable_grupo
para cumplir con estándares de compliance, seguridad y trazabilidad.

Campos agregados:
- asignado_en: DateTime - Cuándo se asignó el responsable al grupo
- asignado_por: String(100) - Quién asignó (username/email)
- actualizado_en: DateTime - Última actualización
- actualizado_por: String(100) - Quién actualizó (username/email)

Beneficios:
- Trazabilidad completa de asignaciones
- Compliance (ISO 27001, SOC 2, GDPR)
- Debugging y soporte mejorado
- Auditoría de seguridad

Revision ID: 1cb2fe74559e
Revises: a8b9c0d1e2f3
Create Date: 2025-12-03 18:08:35.367630

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1cb2fe74559e'
down_revision: Union[str, Sequence[str], None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agrega campos de auditoría a responsable_grupo.

    - asignado_en: NOT NULL con default NOW() para registros nuevos
    - asignado_por: NULL (registros históricos sin info)
    - actualizado_en: NULL (solo se llena en updates)
    - actualizado_por: NULL (solo se llena en updates)
    """
    # Agregar asignado_en (NOT NULL con default)
    op.add_column(
        'responsable_grupo',
        sa.Column(
            'asignado_en',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Cuándo se asignó el responsable al grupo'
        )
    )

    # Agregar asignado_por (NULL permitido)
    op.add_column(
        'responsable_grupo',
        sa.Column(
            'asignado_por',
            sa.String(100),
            nullable=True,
            comment='Usuario que asignó (username/email)'
        )
    )

    # Agregar actualizado_en (NULL permitido, se llena en updates)
    op.add_column(
        'responsable_grupo',
        sa.Column(
            'actualizado_en',
            sa.DateTime(timezone=True),
            nullable=True,
            onupdate=sa.func.now(),
            comment='Última actualización'
        )
    )

    # Agregar actualizado_por (NULL permitido)
    op.add_column(
        'responsable_grupo',
        sa.Column(
            'actualizado_por',
            sa.String(100),
            nullable=True,
            comment='Usuario que actualizó (username/email)'
        )
    )

    # Crear índice para queries de auditoría por fecha
    op.create_index(
        'ix_responsable_grupo_asignado_en',
        'responsable_grupo',
        ['asignado_en'],
        unique=False
    )

    print("[OK] Campos de auditoria agregados exitosamente a responsable_grupo")
    print("   - asignado_en: Registros existentes tendran timestamp actual")
    print("   - asignado_por: NULL para registros historicos")
    print("   - actualizado_en/por: NULL hasta que se modifiquen")


def downgrade() -> None:
    """
    Revierte los cambios de auditoría.

    ⚠️  ADVERTENCIA: Esto eliminará datos de auditoría permanentemente.
    Solo usar en desarrollo o con backup completo.
    """
    # Eliminar índice
    op.drop_index('ix_responsable_grupo_asignado_en', table_name='responsable_grupo')

    # Eliminar columnas en orden inverso
    op.drop_column('responsable_grupo', 'actualizado_por')
    op.drop_column('responsable_grupo', 'actualizado_en')
    op.drop_column('responsable_grupo', 'asignado_por')
    op.drop_column('responsable_grupo', 'asignado_en')

    print("[WARNING] Campos de auditoria eliminados de responsable_grupo")
    print("   Datos de auditoria perdidos permanentemente")
