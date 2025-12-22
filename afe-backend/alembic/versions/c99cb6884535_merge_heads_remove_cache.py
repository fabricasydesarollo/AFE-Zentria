"""merge_heads_remove_cache

Revision ID: c99cb6884535
Revises: 2025_12_04_workflows_devueltas, 2025_12_15_remove_cache
Create Date: 2025-12-15 10:06:16.341244

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c99cb6884535'
down_revision: Union[str, Sequence[str], None] = ('2025_12_04_workflows_devueltas', '2025_12_15_remove_cache')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
