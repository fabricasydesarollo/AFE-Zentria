"""add_grupo_id_to_cuentas_correo

Revision ID: a8b9c0d1e2f3
Revises: 60876a742e3b
Create Date: 2025-12-03 14:40:00.000000

FASE 2: Integración Multi-Tenant - Cuentas de Correo

Agrega campo grupo_id a cuentas_correo para:
1. Asignación automática de grupo cuando Invoice_Extractor procesa facturas
2. Permite que cada cuenta de correo pertenezca a un grupo específico
3. Simplifica el flujo: correo recibe factura → grupo_id del correo

Características:
- NULLABLE: Backward compatible
- FK con ON DELETE SET NULL (si se elimina grupo, correo queda sin grupo)
- Índice para queries por grupo
- Migración idempotente (detecta qué existe)

Nivel: Fortune 500 Enterprise Migration
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, Sequence[str], None] = '60876a742e3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    UPGRADE: Agregar grupo_id a cuentas_correo.

    Estrategia IDEMPOTENTE:
    - Detecta qué ya existe en BD
    - Solo ejecuta lo que falta
    - Puede ejecutarse múltiples veces sin errores
    - CERO PÉRDIDA DE DATOS
    """
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    print("[INFO] Procesando tabla cuentas_correo...")

    # Verificar columnas, FKs e índices existentes
    cols = {col['name'] for col in inspector.get_columns('cuentas_correo')}
    fks = {fk['name'] for fk in inspector.get_foreign_keys('cuentas_correo')}
    indexes = {idx['name'] for idx in inspector.get_indexes('cuentas_correo')}

    # 1. Agregar columna grupo_id (si no existe)
    if 'grupo_id' not in cols:
        op.add_column(
            'cuentas_correo',
            sa.Column(
                'grupo_id',
                sa.BigInteger(),
                nullable=True,
                comment='Grupo empresarial al que pertenece esta cuenta de correo'
            )
        )
        print("   [+] cuentas_correo.grupo_id agregado")
    else:
        print("   [SKIP] cuentas_correo.grupo_id ya existe")

    # 2. Agregar Foreign Key (si no existe)
    if 'fk_cuenta_correo_grupo' not in fks:
        op.create_foreign_key(
            'fk_cuenta_correo_grupo',
            'cuentas_correo',
            'grupos',
            ['grupo_id'],
            ['id'],
            ondelete='SET NULL'
        )
        print("   [+] fk_cuenta_correo_grupo creada")
    else:
        print("   [SKIP] fk_cuenta_correo_grupo ya existe")

    # 3. Agregar índice (si no existe)
    if 'idx_cuenta_correo_grupo' not in indexes:
        op.create_index(
            'idx_cuenta_correo_grupo',
            'cuentas_correo',
            ['grupo_id']
        )
        print("   [+] idx_cuenta_correo_grupo creado")
    else:
        print("   [SKIP] idx_cuenta_correo_grupo ya existe")

    print("[OK] Migracion completada exitosamente (idempotente)")


def downgrade() -> None:
    """
    DOWNGRADE: Revertir cambios (rollback strategy).

    IMPORTANTE: Esta operación es segura ya que grupo_id es NULLABLE.
    No se pierden datos críticos.
    """

    # 1. Eliminar índice
    op.drop_index('idx_cuenta_correo_grupo', table_name='cuentas_correo')

    # 2. Eliminar Foreign Key
    op.drop_constraint('fk_cuenta_correo_grupo', 'cuentas_correo', type_='foreignkey')

    # 3. Eliminar columna
    op.drop_column('cuentas_correo', 'grupo_id')

    print("[OK] Rollback completado:")
    print("   - cuentas_correo.grupo_id eliminado")
    print("   - Sistema en estado anterior")
