"""Add OAuth support to responsables table - Clean version

Revision ID: oauth_support_clean
Revises: eliminar_pendiente_2025
Create Date: 2025-10-28 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'oauth_support_clean'
down_revision: Union[str, Sequence[str], None] = 'eliminar_pendiente_2025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agregar campos OAuth a tabla responsables."""

    # 1. Agregar columna auth_provider
    op.add_column('responsables',
        sa.Column('auth_provider', sa.String(length=50),
                  server_default=sa.text("'local'"),
                  nullable=False)
    )

    # 2. Agregar columna oauth_id
    op.add_column('responsables',
        sa.Column('oauth_id', sa.String(length=255),
                  nullable=True)
    )

    # 3. Agregar columna oauth_picture
    op.add_column('responsables',
        sa.Column('oauth_picture', sa.String(length=500),
                  nullable=True)
    )

    # 4. Hacer hashed_password nullable (para usuarios OAuth)
    op.alter_column('responsables', 'hashed_password',
                    existing_type=sa.String(length=255),
                    nullable=True)

    # 5. Crear índice único en oauth_id
    op.create_index(op.f('ix_responsables_oauth_id'),
                    'responsables', ['oauth_id'],
                    unique=True)


def downgrade() -> None:
    """Revertir cambios OAuth."""

    # Eliminar índice
    op.drop_index(op.f('ix_responsables_oauth_id'), table_name='responsables')

    # Hacer hashed_password NOT NULL nuevamente
    op.alter_column('responsables', 'hashed_password',
                    existing_type=sa.String(length=255),
                    nullable=False)

    # Eliminar columnas
    op.drop_column('responsables', 'oauth_picture')
    op.drop_column('responsables', 'oauth_id')
    op.drop_column('responsables', 'auth_provider')
