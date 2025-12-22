"""add_periodo_fields_to_facturas

Revision ID: 129ab8035fa8
Revises: e4b2063b3d6e
Create Date: 2025-10-03 17:01:37.184333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '129ab8035fa8'
down_revision: Union[str, Sequence[str], None] = 'e4b2063b3d6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Agregar columnas de período
    op.add_column('facturas', sa.Column('año_factura', sa.Integer(), nullable=True))
    op.add_column('facturas', sa.Column('mes_factura', sa.Integer(), nullable=True))
    op.add_column('facturas', sa.Column('periodo_factura', sa.String(length=7), nullable=True))

    # Crear índices para optimizar consultas
    op.create_index('idx_facturas_año', 'facturas', ['año_factura'], unique=False)
    op.create_index('idx_facturas_mes', 'facturas', ['mes_factura'], unique=False)
    op.create_index('idx_facturas_periodo', 'facturas', ['periodo_factura'], unique=False)
    op.create_index('idx_facturas_periodo_estado', 'facturas', ['periodo_factura', 'estado'], unique=False)
    op.create_index('idx_facturas_periodo_proveedor', 'facturas', ['periodo_factura', 'proveedor_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Eliminar índices
    op.drop_index('idx_facturas_periodo_proveedor', table_name='facturas')
    op.drop_index('idx_facturas_periodo_estado', table_name='facturas')
    op.drop_index('idx_facturas_periodo', table_name='facturas')
    op.drop_index('idx_facturas_mes', table_name='facturas')
    op.drop_index('idx_facturas_año', table_name='facturas')

    # Eliminar columnas
    op.drop_column('facturas', 'periodo_factura')
    op.drop_column('facturas', 'mes_factura')
    op.drop_column('facturas', 'año_factura')
