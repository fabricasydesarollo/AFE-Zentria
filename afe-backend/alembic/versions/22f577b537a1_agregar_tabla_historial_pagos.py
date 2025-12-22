"""agregar_tabla_historial_pagos

Revision ID: 22f577b537a1
Revises: abc123
Create Date: 2025-10-06 14:17:21.212422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22f577b537a1'
down_revision: Union[str, Sequence[str], None] = 'abc123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agregar tabla historial_pagos para análisis de patrones históricos."""

    # Crear tabla historial_pagos
    op.create_table(
        'historial_pagos',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),

        # Identificación del patrón
        sa.Column('proveedor_id', sa.BigInteger(), nullable=False),
        sa.Column('concepto_normalizado', sa.String(200), nullable=False),
        sa.Column('concepto_hash', sa.String(32), nullable=False),

        # Clasificación del patrón
        sa.Column('tipo_patron', sa.Enum('TIPO_A', 'TIPO_B', 'TIPO_C', name='tipopatron'), nullable=False),

        # Estadísticas
        sa.Column('pagos_analizados', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('meses_con_pagos', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('monto_promedio', sa.Numeric(15, 2), nullable=False),
        sa.Column('monto_minimo', sa.Numeric(15, 2), nullable=False),
        sa.Column('monto_maximo', sa.Numeric(15, 2), nullable=False),
        sa.Column('desviacion_estandar', sa.Numeric(15, 2), nullable=False),
        sa.Column('coeficiente_variacion', sa.Numeric(5, 2), nullable=False),

        # Rango esperado
        sa.Column('rango_inferior', sa.Numeric(15, 2), nullable=True),
        sa.Column('rango_superior', sa.Numeric(15, 2), nullable=True),

        # Patrón de recurrencia
        sa.Column('frecuencia_detectada', sa.String(50), nullable=True),
        sa.Column('ultimo_pago_fecha', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ultimo_pago_monto', sa.Numeric(15, 2), nullable=True),

        # Datos históricos detallados
        sa.Column('pagos_detalle', sa.JSON(), nullable=True),

        # Metadata del análisis
        sa.Column('fecha_analisis', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('version_algoritmo', sa.String(20), nullable=False, server_default='1.0'),

        # Recomendación automática
        sa.Column('puede_aprobar_auto', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('umbral_alerta', sa.Numeric(5, 2), nullable=True),

        # Auditoría
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['proveedor_id'], ['proveedores.id'], ),
    )

    # Crear índices
    op.create_index('ix_historial_pagos_proveedor_id', 'historial_pagos', ['proveedor_id'])
    op.create_index('ix_historial_pagos_concepto_normalizado', 'historial_pagos', ['concepto_normalizado'])
    op.create_index('ix_historial_pagos_concepto_hash', 'historial_pagos', ['concepto_hash'])
    op.create_index('ix_historial_pagos_tipo_patron', 'historial_pagos', ['tipo_patron'])

    # Índice compuesto para búsquedas rápidas
    op.create_index(
        'ix_historial_proveedor_concepto',
        'historial_pagos',
        ['proveedor_id', 'concepto_hash'],
        unique=False
    )


def downgrade() -> None:
    """Eliminar tabla historial_pagos."""
    op.drop_index('ix_historial_proveedor_concepto', table_name='historial_pagos')
    op.drop_index('ix_historial_pagos_tipo_patron', table_name='historial_pagos')
    op.drop_index('ix_historial_pagos_concepto_hash', table_name='historial_pagos')
    op.drop_index('ix_historial_pagos_concepto_normalizado', table_name='historial_pagos')
    op.drop_index('ix_historial_pagos_proveedor_id', table_name='historial_pagos')
    op.drop_table('historial_pagos')
