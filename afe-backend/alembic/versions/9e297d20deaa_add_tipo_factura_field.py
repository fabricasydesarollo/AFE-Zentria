"""add_tipo_factura_field

Revision ID: 9e297d20deaa
Revises: 262fa5bff4d4
Create Date: 2025-10-14 09:20:14.904628

Agrega campo tipo_factura para clasificacion empresarial:
- COMPRA: Factura de compra/proveedor (default)
- VENTA: Factura de venta (si aplica en el futuro)
- NOTA_CREDITO: Nota de credito
- NOTA_DEBITO: Nota de debito
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e297d20deaa'
down_revision: Union[str, Sequence[str], None] = '262fa5bff4d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agrega campo tipo_factura para clasificacion empresarial.
    """
    op.add_column('facturas',
        sa.Column('tipo_factura', sa.String(20), nullable=False,
                  server_default='COMPRA',
                  comment='Tipo: COMPRA, VENTA, NOTA_CREDITO, NOTA_DEBITO'))

    # Crear indice para consultas por tipo
    op.create_index('idx_facturas_tipo', 'facturas', ['tipo_factura'], unique=False)


def downgrade() -> None:
    """
    Revierte los cambios.
    """
    op.drop_index('idx_facturas_tipo', 'facturas')
    op.drop_column('facturas', 'tipo_factura')
