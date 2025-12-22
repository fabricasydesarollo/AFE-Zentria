"""remove_obsolete_tables_configuracion_correo_and_clientes

Revision ID: 1e507fe2fa12
Revises: 669b5dd485b8
Create Date: 2025-10-14 08:45:56.500971

Elimina tablas obsoletas:
1. configuracion_correo - Duplicada (ya existe cuentas_correo para Microsoft Graph)
2. clientes - No se usa en el sistema actual (solo gestionamos proveedores)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '1e507fe2fa12'
down_revision: Union[str, Sequence[str], None] = '669b5dd485b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Elimina tablas obsoletas del sistema.

    NOTA: Antes de ejecutar esta migración, asegúrate de que no haya datos
    importantes en estas tablas. Si hay datos, haz un backup primero.
    """
    # Eliminar tabla configuracion_correo (obsoleta, usamos cuentas_correo ahora)
    op.drop_table('configuracion_correo')

    # Eliminar tabla clientes (no se usa en el flujo actual)
    op.drop_table('clientes')


def downgrade() -> None:
    """
    Restaura las tablas eliminadas (solo estructura, sin datos).
    """
    # Restaurar tabla clientes
    op.create_table(
        'clientes',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('nit', sa.String(64), nullable=False),
        sa.Column('razon_social', sa.String(255), nullable=False),
        sa.Column('contacto_email', sa.String(255), nullable=True),
        sa.Column('telefono', sa.String(50), nullable=True),
        sa.Column('direccion', sa.String(255), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nit')
    )

    # Restaurar tabla configuracion_correo
    op.create_table(
        'configuracion_correo',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('servidor_imap', sa.String(255), nullable=False),
        sa.Column('puerto_imap', sa.BigInteger(), nullable=True),
        sa.Column('usa_ssl', sa.Boolean(), nullable=True),
        sa.Column('password', sa.String(500), nullable=True),
        sa.Column('oauth_token', sa.Text(), nullable=True),
        sa.Column('carpeta_inbox', sa.String(100), nullable=True),
        sa.Column('carpeta_procesados', sa.String(100), nullable=True),
        sa.Column('carpeta_errores', sa.String(100), nullable=True),
        sa.Column('filtro_asunto', sa.JSON(), nullable=True),
        sa.Column('filtro_remitente', sa.JSON(), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=True),
        sa.Column('ultima_lectura', sa.DateTime(), nullable=True),
        sa.Column('total_correos_procesados', sa.BigInteger(), nullable=True),
        sa.Column('creado_en', sa.DateTime(), nullable=True),
        sa.Column('actualizado_en', sa.DateTime(), nullable=True),
        sa.Column('creado_por', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_config_correo_activo', 'configuracion_correo', ['activo', 'email'])
