"""remove_redundant_fields_from_facturas

Revision ID: d721faa20fc3
Revises: 8c6834305516
Create Date: 2025-10-10 09:09:11.407159

Elimina campos redundantes de la tabla facturas ahora que existe factura_items.

Campos eliminados:
- concepto_principal → movido a factura_items.descripcion
- concepto_normalizado → movido a factura_items.descripcion_normalizada
- concepto_hash → movido a factura_items.item_hash
- items_resumen → redundante, items en tabla dedicada
- patron_recurrencia → movido a factura_items.es_recurrente
- notas_adicionales → redundante con observaciones
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'd721faa20fc3'
down_revision: Union[str, Sequence[str], None] = '8c6834305516'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Elimina campos redundantes de facturas."""
    # Eliminar campos relacionados con conceptos (ahora en factura_items)
    op.drop_column('facturas', 'concepto_principal')
    op.drop_column('facturas', 'concepto_normalizado')
    op.drop_column('facturas', 'concepto_hash')

    # Eliminar resumen de items (redundante)
    op.drop_column('facturas', 'items_resumen')

    # Eliminar patron de recurrencia (ahora en factura_items)
    op.drop_column('facturas', 'patron_recurrencia')

    # Eliminar notas adicionales (redundante con observaciones)
    op.drop_column('facturas', 'notas_adicionales')


def downgrade() -> None:
    """Restaura campos eliminados."""
    # Restaurar campos relacionados con conceptos
    op.add_column('facturas', sa.Column('concepto_principal', sa.String(1000), nullable=True))
    op.add_column('facturas', sa.Column('concepto_normalizado', sa.String(200), nullable=True))
    op.add_column('facturas', sa.Column('concepto_hash', sa.String(32), nullable=True))

    # Restaurar resumen de items
    op.add_column('facturas', sa.Column('items_resumen', mysql.JSON(), nullable=True))

    # Restaurar patron de recurrencia
    op.add_column('facturas', sa.Column('patron_recurrencia', sa.String(50), nullable=True))

    # Restaurar notas adicionales
    op.add_column('facturas', sa.Column('notas_adicionales', mysql.JSON(), nullable=True))
