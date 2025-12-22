"""add_performance_indexes_and_constraints

Revision ID: 6b569b88b197
Revises: 4cf72d1df18f
Create Date: 2025-10-10 09:39:32.365350

NOTA: Todos los índices de rendimiento YA EXISTEN en la base de datos.
La base de datos ya está correctamente optimizada.
Esta migración se ejecuta sin hacer cambios (no-op).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b569b88b197'
down_revision: Union[str, Sequence[str], None] = '4cf72d1df18f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: todos los índices ya existen."""
    pass


def downgrade() -> None:
    """No-op."""
    pass
