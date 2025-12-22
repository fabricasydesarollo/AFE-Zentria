"""remove_redundant_total_field

Revision ID: 13e7a720374c
Revises: 6b569b88b197
Create Date: 2025-10-10 09:51:25.806457

Elimina campo 'total' redundante.
Se mantiene 'total_a_pagar' (más claro y profesional).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '13e7a720374c'
down_revision: Union[str, Sequence[str], None] = '6b569b88b197'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Elimina campo 'total' redundante."""
    op.drop_column('facturas', 'total')


def downgrade() -> None:
    """Restaura campo 'total'."""
    op.add_column('facturas', sa.Column('total', sa.Numeric(15, 2), nullable=True))
