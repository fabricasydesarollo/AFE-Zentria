"""Add approval fields to facturas

Revision ID: ab8f4888b5b5
Revises: 22f577b537a1
Create Date: 2025-10-07 12:58:05.727664

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab8f4888b5b5'
down_revision: Union[str, Sequence[str], None] = '22f577b537a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add approval and rejection fields to facturas table."""
    # Add approval fields
    op.add_column('facturas', sa.Column('aprobado_por', sa.String(100), nullable=True, comment='Usuario que aprobó la factura manualmente'))
    op.add_column('facturas', sa.Column('fecha_aprobacion', sa.DateTime(timezone=True), nullable=True, comment='Fecha y hora de aprobación'))

    # Add rejection fields
    op.add_column('facturas', sa.Column('rechazado_por', sa.String(100), nullable=True, comment='Usuario que rechazó la factura'))
    op.add_column('facturas', sa.Column('fecha_rechazo', sa.DateTime(timezone=True), nullable=True, comment='Fecha y hora de rechazo'))
    op.add_column('facturas', sa.Column('motivo_rechazo', sa.String(1000), nullable=True, comment='Motivo del rechazo de la factura'))


def downgrade() -> None:
    """Remove approval and rejection fields from facturas table."""
    # Remove rejection fields
    op.drop_column('facturas', 'motivo_rechazo')
    op.drop_column('facturas', 'fecha_rechazo')
    op.drop_column('facturas', 'rechazado_por')

    # Remove approval fields
    op.drop_column('facturas', 'fecha_aprobacion')
    op.drop_column('facturas', 'aprobado_por')
