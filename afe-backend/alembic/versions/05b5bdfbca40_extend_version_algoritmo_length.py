"""Extend version_algoritmo field length

Revision ID: 05b5bdfbca40
Revises: ab8f4888b5b5
Create Date: 2025-10-08 09:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05b5bdfbca40'
down_revision: Union[str, Sequence[str], None] = 'ab8f4888b5b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Extend version_algoritmo from VARCHAR(20) to VARCHAR(50)."""
    op.alter_column('facturas', 'version_algoritmo',
                   existing_type=sa.String(20),
                   type_=sa.String(50),
                   existing_nullable=True)


def downgrade() -> None:
    """Revert version_algoritmo back to VARCHAR(20)."""
    op.alter_column('facturas', 'version_algoritmo',
                   existing_type=sa.String(50),
                   type_=sa.String(20),
                   existing_nullable=True)
