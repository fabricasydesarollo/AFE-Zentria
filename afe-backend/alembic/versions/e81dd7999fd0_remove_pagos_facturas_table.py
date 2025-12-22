"""remove_pagos_facturas_table

Revision ID: e81dd7999fd0
Revises: 2025_11_20_add_payment_system
Create Date: 2025-11-25 16:29:57.478492

Elimina tabla pagos_facturas (código creado hace menos de una semana).
Responsabilidad de pagos es externa (tesorería).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e81dd7999fd0'
down_revision: Union[str, Sequence[str], None] = '2025_11_11_cleanup_accion_por'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Elimina tabla pagos_facturas con todas sus constraints e índices."""
    from sqlalchemy import inspect

    # Verificar si la tabla existe
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'pagos_facturas' not in inspector.get_table_names():
        print("Tabla pagos_facturas no existe, saltando eliminacion")
        return

    # Eliminar tabla (esto elimina automáticamente todos los índices y constraints)
    op.drop_table('pagos_facturas')
    print("Tabla pagos_facturas eliminada exitosamente")


def downgrade() -> None:
    """Restaura tabla pagos_facturas (solo estructura, sin datos)."""
    # Recrear tabla
    op.create_table(
        'pagos_facturas',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('factura_id', sa.BigInteger(), nullable=False),
        sa.Column('monto_pagado', sa.Numeric(precision=15, scale=2, asdecimal=True), nullable=False),
        sa.Column('referencia_pago', sa.String(length=100), nullable=False),
        sa.Column('metodo_pago', sa.String(length=50), nullable=True),
        sa.Column('estado_pago', sa.Enum('completado', 'fallido', 'cancelado', name='estadopago'), nullable=False, server_default='completado'),
        sa.Column('procesado_por', sa.String(length=255), nullable=False),
        sa.Column('fecha_pago', sa.DateTime(timezone=True), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['factura_id'], ['facturas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('referencia_pago', name='referencia_pago'),
    )

    # Recrear índices
    op.create_index('ix_pagos_facturas_factura_id', 'pagos_facturas', ['factura_id'])
    op.create_index('ix_pagos_facturas_factura_id_estado', 'pagos_facturas', ['factura_id', 'estado_pago'])
    op.create_index('ix_pagos_facturas_fecha_pago', 'pagos_facturas', ['fecha_pago'])
    op.create_index('ix_pagos_facturas_estado_pago', 'pagos_facturas', ['estado_pago'])
    op.create_index('ix_pagos_facturas_procesado_por', 'pagos_facturas', ['procesado_por'])
    op.create_index('ix_pagos_facturas_referencia_pago', 'pagos_facturas', ['referencia_pago'])
    op.create_index('ix_pagos_facturas_creado_en', 'pagos_facturas', ['creado_en'])
