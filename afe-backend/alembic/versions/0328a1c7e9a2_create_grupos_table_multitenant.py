"""create_grupos_table_multitenant

Revision ID: 0328a1c7e9a2
Revises: 9611a5a6b002
Create Date: 2025-12-02 15:14:29.691553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0328a1c7e9a2'
down_revision: Union[str, Sequence[str], None] = '9611a5a6b002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
