"""add_email_config_tables_for_invoice_extraction

Revision ID: a7fc9998a49f
Revises: 11588de714fd
Create Date: 2025-10-11 15:14:29.561935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7fc9998a49f'
down_revision: Union[str, Sequence[str], None] = '11588de714fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add tables for email configuration and invoice extraction."""

    # Create cuentas_correo table
    op.create_table(
        'cuentas_correo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, comment='Email corporativo (Microsoft Graph)'),
        sa.Column('nombre_descriptivo', sa.String(length=255), nullable=True, comment="Nombre amigable: 'Angiografía de Colombia'"),
        sa.Column('fetch_limit', sa.Integer(), nullable=False, server_default='500', comment='Límite de correos a extraer por ejecución'),
        sa.Column('fetch_days', sa.Integer(), nullable=False, server_default='90', comment='Días hacia atrás para buscar correos'),
        sa.Column('activa', sa.Boolean(), nullable=False, server_default='1', comment='Si está activa para extracción'),
        sa.Column('organizacion', sa.String(length=100), nullable=True, comment="Organización: 'ANGIOGRAFIA', 'AVIDANTI', etc."),
        sa.Column('creada_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('actualizada_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('creada_por', sa.String(length=100), nullable=False, comment='Usuario que creó la configuración'),
        sa.Column('actualizada_por', sa.String(length=100), nullable=True, comment='Último usuario que modificó'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('fetch_limit > 0 AND fetch_limit <= 1000', name='check_fetch_limit_range'),
        sa.CheckConstraint('fetch_days > 0 AND fetch_days <= 365', name='check_fetch_days_range'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    op.create_index('ix_cuentas_correo_email', 'cuentas_correo', ['email'], unique=True)
    op.create_index('ix_cuentas_correo_activa', 'cuentas_correo', ['activa'])
    op.create_index('ix_cuentas_correo_organizacion', 'cuentas_correo', ['organizacion'])
    op.create_index('idx_cuenta_correo_activa_org', 'cuentas_correo', ['activa', 'organizacion'])

    # Create nit_configuracion table
    op.create_table(
        'nit_configuracion',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cuenta_correo_id', sa.Integer(), nullable=False),
        sa.Column('nit', sa.String(length=20), nullable=False, comment='NIT del proveedor/emisor a filtrar'),
        sa.Column('nombre_proveedor', sa.String(length=255), nullable=True, comment='Nombre del proveedor (opcional)'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='1', comment='Si este NIT está activo para filtrado'),
        sa.Column('notas', sa.String(length=500), nullable=True, comment='Notas adicionales sobre este NIT'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('creado_por', sa.String(length=100), nullable=False),
        sa.Column('actualizado_por', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['cuenta_correo_id'], ['cuentas_correo.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cuenta_correo_id', 'nit', name='uq_cuenta_nit'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    op.create_index('ix_nit_configuracion_cuenta_correo_id', 'nit_configuracion', ['cuenta_correo_id'])
    op.create_index('ix_nit_configuracion_nit', 'nit_configuracion', ['nit'])
    op.create_index('idx_nit_activo', 'nit_configuracion', ['nit', 'activo'])

    # Create historial_extracciones table
    op.create_table(
        'historial_extracciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cuenta_correo_id', sa.Integer(), nullable=False),
        sa.Column('fecha_ejecucion', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('correos_procesados', sa.Integer(), nullable=False, server_default='0', comment='Total de correos analizados'),
        sa.Column('facturas_encontradas', sa.Integer(), nullable=False, server_default='0', comment='Facturas XML encontradas'),
        sa.Column('facturas_creadas', sa.Integer(), nullable=False, server_default='0', comment='Nuevas facturas creadas'),
        sa.Column('facturas_actualizadas', sa.Integer(), nullable=False, server_default='0', comment='Facturas actualizadas'),
        sa.Column('facturas_ignoradas', sa.Integer(), nullable=False, server_default='0', comment='Facturas duplicadas/ignoradas'),
        sa.Column('exito', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('mensaje_error', sa.String(length=1000), nullable=True, comment='Mensaje de error si falla'),
        sa.Column('tiempo_ejecucion_ms', sa.Integer(), nullable=True, comment='Tiempo de ejecución en milisegundos'),
        sa.Column('fetch_limit_usado', sa.Integer(), nullable=True),
        sa.Column('fetch_days_usado', sa.Integer(), nullable=True),
        sa.Column('nits_usados', sa.Integer(), nullable=True, comment='Cantidad de NITs activos en la extracción'),
        sa.ForeignKeyConstraint(['cuenta_correo_id'], ['cuentas_correo.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    op.create_index('ix_historial_extracciones_cuenta_correo_id', 'historial_extracciones', ['cuenta_correo_id'])
    op.create_index('ix_historial_extracciones_fecha_ejecucion', 'historial_extracciones', ['fecha_ejecucion'])
    op.create_index('idx_historial_fecha_exito', 'historial_extracciones', ['fecha_ejecucion', 'exito'])
    op.create_index('idx_historial_cuenta_fecha', 'historial_extracciones', ['cuenta_correo_id', 'fecha_ejecucion'])


def downgrade() -> None:
    """Downgrade schema - Drop email configuration tables."""
    op.drop_table('historial_extracciones')
    op.drop_table('nit_configuracion')
    op.drop_table('cuentas_correo')
