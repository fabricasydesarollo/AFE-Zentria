"""drop_obsolete_historial_pagos_table

Revision ID: 11588de714fd
Revises: 13e7a720374c
Create Date: 2025-10-10 10:05:21.824049

Elimina tabla historial_pagos (datos de versión anterior obsoleta).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11588de714fd'
down_revision: Union[str, Sequence[str], None] = '13e7a720374c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Elimina tabla obsoleta historial_pagos."""
    op.drop_table('historial_pagos')


def downgrade() -> None:
    """No se puede restaurar - datos obsoletos."""
    pass
