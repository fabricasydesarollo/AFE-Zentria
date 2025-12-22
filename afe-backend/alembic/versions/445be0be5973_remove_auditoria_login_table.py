"""remove_auditoria_login_table

Revision ID: 445be0be5973
Revises: f81c62d7acc9
Create Date: 2025-11-26 07:50:32.903872

Elimina tabla auditoria_login que fue creada para rastrear logins por empresa/sede.
No tiene valor en sistema single-empresa.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '445be0be5973'
down_revision: Union[str, Sequence[str], None] = 'f81c62d7acc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Elimina tabla auditoria_login."""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    if 'auditoria_login' not in inspector.get_table_names():
        print("Tabla auditoria_login no existe, saltando eliminacion")
        return

    # Eliminar tabla (elimina automáticamente índices y constraints)
    op.drop_table('auditoria_login')
    print("Tabla auditoria_login eliminada exitosamente")


def downgrade() -> None:
    """Restaura tabla auditoria_login (solo estructura, sin datos)."""
    op.create_table(
        'auditoria_login',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('responsable_id', sa.BigInteger(), nullable=False),
        sa.Column('empresa_id', sa.BigInteger(), nullable=True),
        sa.Column('sede_id', sa.BigInteger(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('login_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('logout_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['responsable_id'], ['responsables.id'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
