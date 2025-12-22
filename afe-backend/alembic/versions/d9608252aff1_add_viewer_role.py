"""add_viewer_role

Revision ID: d9608252aff1
Revises: oauth_support_clean
Create Date: 2025-10-29 16:33:34.047659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9608252aff1'
down_revision: Union[str, Sequence[str], None] = 'oauth_support_clean'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agregar rol 'viewer' (visualizador) a la tabla roles."""
    # Insertar el nuevo rol 'viewer' solo si no existe
    op.execute("""
        INSERT INTO roles (nombre)
        SELECT 'viewer'
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE nombre = 'viewer');
    """)


def downgrade() -> None:
    """Eliminar rol 'viewer'."""
    # Primero verificar que no haya usuarios con este rol
    # Si los hay, la migración fallará (protección)
    op.execute("""
        DELETE FROM roles WHERE nombre = 'viewer';
    """)
