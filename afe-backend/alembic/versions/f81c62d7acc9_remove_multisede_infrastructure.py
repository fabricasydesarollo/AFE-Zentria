"""remove_multisede_infrastructure

Revision ID: f81c62d7acc9
Revises: 2d665e89c06b
Create Date: 2025-11-26 07:44:09.147422

Elimina toda la infraestructura de multi-sede (empresas, sedes, responsables_empresa).
No se usa actualmente - la gestion es de una sola empresa.
Se eliminan tambien los campos FK en otras tablas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f81c62d7acc9'
down_revision: Union[str, Sequence[str], None] = '2d665e89c06b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Elimina infraestructura de multi-sede y campos FK relacionados."""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    # Paso 1: Eliminar tablas que dependen de empresas/sedes

    # 1.1: Eliminar responsables_empresa si existe
    if 'responsables_empresa' in existing_tables:
        op.drop_table('responsables_empresa')

    # 1.2: Eliminar mapeo_correos_empresas si existe
    if 'mapeo_correos_empresas' in existing_tables:
        op.drop_table('mapeo_correos_empresas')

    # Paso 2: Eliminar columnas FK de tablas existentes

    # 2.1: Eliminar FK de facturas si existen
    if 'facturas' in existing_tables:
        fk_constraints = inspector.get_foreign_keys('facturas')
        fk_names = [fk['name'] for fk in fk_constraints]
        if 'fk_facturas_empresa' in fk_names:
            op.drop_constraint('fk_facturas_empresa', 'facturas', type_='foreignkey')
        if 'fk_facturas_sede' in fk_names:
            op.drop_constraint('fk_facturas_sede', 'facturas', type_='foreignkey')

        columns = [col['name'] for col in inspector.get_columns('facturas')]
        if 'empresa_id' in columns:
            op.drop_column('facturas', 'empresa_id')
        if 'sede_id' in columns:
            op.drop_column('facturas', 'sede_id')

    # 2.2: Eliminar FK de auditoria_login si existen
    if 'auditoria_login' in existing_tables:
        fk_constraints = inspector.get_foreign_keys('auditoria_login')
        fk_names = [fk['name'] for fk in fk_constraints]
        if 'auditoria_login_ibfk_2' in fk_names:
            op.drop_constraint('auditoria_login_ibfk_2', 'auditoria_login', type_='foreignkey')
        if 'auditoria_login_ibfk_3' in fk_names:
            op.drop_constraint('auditoria_login_ibfk_3', 'auditoria_login', type_='foreignkey')

        columns = [col['name'] for col in inspector.get_columns('auditoria_login')]
        if 'empresa_id' in columns:
            op.drop_column('auditoria_login', 'empresa_id')
        if 'sede_id' in columns:
            op.drop_column('auditoria_login', 'sede_id')

    # 2.3: Eliminar FK de cuentas_correo si existen
    if 'cuentas_correo' in existing_tables:
        fk_constraints = inspector.get_foreign_keys('cuentas_correo')
        fk_names = [fk['name'] for fk in fk_constraints]
        if 'fk_cuentas_correo_empresa' in fk_names:
            op.drop_constraint('fk_cuentas_correo_empresa', 'cuentas_correo', type_='foreignkey')

        columns = [col['name'] for col in inspector.get_columns('cuentas_correo')]
        if 'empresa_id' in columns:
            op.drop_column('cuentas_correo', 'empresa_id')

    # Paso 3: Eliminar tablas base (sedes, luego empresas)

    # 3.1: Eliminar sedes si existe
    if 'sedes' in existing_tables:
        op.drop_table('sedes')

    # 3.2: Eliminar empresas si existe
    if 'empresas' in existing_tables:
        op.drop_table('empresas')


def downgrade() -> None:
    """Restaura infraestructura de multi-sede (solo estructura, sin datos)."""

    # Recrear empresas
    op.create_table(
        'empresas',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('nit', sa.String(length=20), nullable=False, unique=True),
        sa.Column('activo', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Recrear sedes
    op.create_table(
        'sedes',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('empresa_id', sa.BigInteger(), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('ciudad', sa.String(length=100), nullable=True),
        sa.Column('activo', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Recrear mapeo_correos_empresas
    op.create_table(
        'mapeo_correos_empresas',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('empresa_id', sa.BigInteger(), nullable=False),
        sa.Column('sede_id', sa.BigInteger(), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('activo', sa.Boolean(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], onupdate='CASCADE', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Recrear responsables_empresa
    op.create_table(
        'responsables_empresa',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('responsable_id', sa.BigInteger(), nullable=False),
        sa.Column('empresa_id', sa.BigInteger(), nullable=False),
        sa.Column('sede_id', sa.BigInteger(), nullable=True),
        sa.Column('pude_ver', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('pude_crear', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('pude_editar', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('pude_anular', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('pude_rechazar', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('aprueba_hasta', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('activo', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['responsable_id'], ['responsables.id'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], onupdate='CASCADE', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Recrear columnas en facturas
    op.add_column('facturas', sa.Column('empresa_id', sa.BigInteger(), nullable=True))
    op.add_column('facturas', sa.Column('sede_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('fk_facturas_empresa', 'facturas', 'empresas', ['empresa_id'], ['id'], onupdate='CASCADE', ondelete='SET NULL')
    op.create_foreign_key('fk_facturas_sede', 'facturas', 'sedes', ['sede_id'], ['id'], onupdate='CASCADE', ondelete='SET NULL')

    # Recrear columnas en auditoria_login
    op.add_column('auditoria_login', sa.Column('empresa_id', sa.BigInteger(), nullable=True))
    op.add_column('auditoria_login', sa.Column('sede_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('auditoria_login_ibfk_2', 'auditoria_login', 'empresas', ['empresa_id'], ['id'], onupdate='CASCADE', ondelete='SET NULL')
    op.create_foreign_key('auditoria_login_ibfk_3', 'auditoria_login', 'sedes', ['sede_id'], ['id'], onupdate='CASCADE', ondelete='SET NULL')

    # Recrear columnas en cuentas_correo
    op.add_column('cuentas_correo', sa.Column('empresa_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('fk_cuentas_correo_empresa', 'cuentas_correo', 'empresas', ['empresa_id'], ['id'], onupdate='CASCADE', ondelete='SET NULL')
