"""remove_unused_fields_from_factura_items

Revision ID: 2d665e89c06b
Revises: e81dd7999fd0
Create Date: 2025-11-25 16:30:53.762373

Elimina 3 campos BASURA sin uso confirmado:
- codigo_estandar (0 referencias en código)
- descuento_porcentaje (0 referencias en código)
- notas (confundido con nit_configuracion.notas)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d665e89c06b'
down_revision: Union[str, Sequence[str], None] = 'e81dd7999fd0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Elimina campos sin uso de factura_items."""
    op.drop_column('factura_items', 'codigo_estandar')
    op.drop_column('factura_items', 'descuento_porcentaje')
    op.drop_column('factura_items', 'notas')


def downgrade() -> None:
    """Restaura campos eliminados (solo estructura, sin datos)."""
    op.add_column('factura_items', sa.Column('codigo_estandar', sa.String(length=100), nullable=True))
    op.add_column('factura_items', sa.Column('descuento_porcentaje', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('factura_items', sa.Column('notas', sa.String(length=1000), nullable=True))
