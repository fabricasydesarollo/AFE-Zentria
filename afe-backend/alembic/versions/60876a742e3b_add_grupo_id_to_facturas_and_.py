"""add_grupo_id_to_facturas_and_asignaciones

Revision ID: 60876a742e3b
Revises: 0328a1c7e9a2
Create Date: 2025-12-02 16:29:31.894053

FASE 1: Integración Multi-Tenant con Grupos

Agrega campo grupo_id a:
1. facturas - Para segregación por grupo empresarial
2. asignacion_nit_responsable - Para soportar multi-tenant

Características:
- NULLABLE: Backward compatible (datos existentes quedan NULL)
- FK con ON DELETE SET NULL (facturas) / CASCADE (asignaciones)
- Índices para queries por grupo
- Nueva constraint UNIQUE en asignaciones

Nivel: Fortune 500 Enterprise Migration
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60876a742e3b'
down_revision: Union[str, Sequence[str], None] = '0328a1c7e9a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    UPGRADE: Agregar grupo_id a facturas y asignaciones.

    Estrategia IDEMPOTENTE:
    - Detecta qué ya existe en BD
    - Solo ejecuta lo que falta
    - Puede ejecutarse múltiples veces sin errores
    - CERO PÉRDIDA DE DATOS

    Nivel: Fortune 500 Safe Migration
    """
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    # ==================== FACTURAS ====================
    print("[INFO] Procesando tabla facturas...")

    # Verificar columnas existentes
    facturas_cols = {col['name'] for col in inspector.get_columns('facturas')}
    facturas_fks = {fk['name'] for fk in inspector.get_foreign_keys('facturas')}
    facturas_indexes = {idx['name'] for idx in inspector.get_indexes('facturas')}

    # 1. Agregar columna grupo_id (si no existe)
    if 'grupo_id' not in facturas_cols:
        op.add_column(
            'facturas',
            sa.Column(
                'grupo_id',
                sa.BigInteger(),
                nullable=True,
                comment='Grupo empresarial al que pertenece la factura'
            )
        )
        print("   [+] facturas.grupo_id agregado")
    else:
        print("   [SKIP] facturas.grupo_id ya existe")

    # 2. Agregar Foreign Key (si no existe)
    if 'fk_factura_grupo' not in facturas_fks:
        op.create_foreign_key(
            'fk_factura_grupo',
            'facturas',
            'grupos',
            ['grupo_id'],
            ['id'],
            ondelete='SET NULL'
        )
        print("   [+] fk_factura_grupo creada")
    else:
        print("   [SKIP] fk_factura_grupo ya existe")

    # 3. Agregar índice (si no existe)
    if 'idx_factura_grupo' not in facturas_indexes:
        op.create_index(
            'idx_factura_grupo',
            'facturas',
            ['grupo_id']
        )
        print("   [+] idx_factura_grupo creado")
    else:
        print("   [SKIP] idx_factura_grupo ya existe")

    # ==================== ASIGNACIONES NIT ====================
    print("[INFO] Procesando tabla asignacion_nit_responsable...")

    asig_cols = {col['name'] for col in inspector.get_columns('asignacion_nit_responsable')}
    asig_fks = {fk['name'] for fk in inspector.get_foreign_keys('asignacion_nit_responsable')}
    asig_indexes = {idx['name'] for idx in inspector.get_indexes('asignacion_nit_responsable')}
    asig_constraints = {uc['name'] for uc in inspector.get_unique_constraints('asignacion_nit_responsable')}

    # 1. Agregar columna grupo_id (si no existe)
    if 'grupo_id' not in asig_cols:
        op.add_column(
            'asignacion_nit_responsable',
            sa.Column(
                'grupo_id',
                sa.BigInteger(),
                nullable=True,
                comment='Grupo específico (NULL = aplica a todos los grupos)'
            )
        )
        print("   [+] asignacion_nit_responsable.grupo_id agregado")
    else:
        print("   [SKIP] asignacion_nit_responsable.grupo_id ya existe")

    # 2. Agregar Foreign Key (si no existe)
    if 'fk_asignacion_grupo' not in asig_fks:
        op.create_foreign_key(
            'fk_asignacion_grupo',
            'asignacion_nit_responsable',
            'grupos',
            ['grupo_id'],
            ['id'],
            ondelete='CASCADE'
        )
        print("   [+] fk_asignacion_grupo creada")
    else:
        print("   [SKIP] fk_asignacion_grupo ya existe")

    # 3. Agregar índice (si no existe)
    if 'idx_asignacion_grupo' not in asig_indexes:
        op.create_index(
            'idx_asignacion_grupo',
            'asignacion_nit_responsable',
            ['grupo_id']
        )
        print("   [+] idx_asignacion_grupo creado")
    else:
        print("   [SKIP] idx_asignacion_grupo ya existe")

    # 4. Actualizar constraint UNIQUE
    # DROP old constraint (si existe)
    if 'uq_nit_responsable' in asig_constraints:
        op.drop_constraint('uq_nit_responsable', 'asignacion_nit_responsable', type_='unique')
        print("   [-] uq_nit_responsable eliminada")
    else:
        print("   [SKIP] uq_nit_responsable no existe (ya fue eliminada)")

    # ADD new constraint (si no existe)
    if 'uq_nit_responsable_grupo' not in asig_constraints:
        op.create_unique_constraint(
            'uq_nit_responsable_grupo',
            'asignacion_nit_responsable',
            ['nit', 'responsable_id', 'grupo_id']
        )
        print("   [+] uq_nit_responsable_grupo creada")
    else:
        print("   [SKIP] uq_nit_responsable_grupo ya existe")

    print("[OK] Migracion completada exitosamente (idempotente)")


def downgrade() -> None:
    """
    DOWNGRADE: Revertir cambios (rollback strategy).

    IMPORTANTE: Esta operación es segura ya que grupo_id es NULLABLE.
    No se pierden datos críticos.
    """

    # ==================== ASIGNACIONES (reverse order) ====================

    # 1. Restaurar constraint antigua
    op.drop_constraint('uq_nit_responsable_grupo', 'asignacion_nit_responsable', type_='unique')
    op.create_unique_constraint(
        'uq_nit_responsable',
        'asignacion_nit_responsable',
        ['nit', 'responsable_id']
    )

    # 2. Eliminar índice
    op.drop_index('idx_asignacion_grupo', table_name='asignacion_nit_responsable')

    # 3. Eliminar Foreign Key
    op.drop_constraint('fk_asignacion_grupo', 'asignacion_nit_responsable', type_='foreignkey')

    # 4. Eliminar columna
    op.drop_column('asignacion_nit_responsable', 'grupo_id')

    # ==================== FACTURAS ====================

    # 1. Eliminar índice
    op.drop_index('idx_factura_grupo', table_name='facturas')

    # 2. Eliminar Foreign Key
    op.drop_constraint('fk_factura_grupo', 'facturas', type_='foreignkey')

    # 3. Eliminar columna
    op.drop_column('facturas', 'grupo_id')

    print("[OK] Rollback completado:")
    print("   - facturas.grupo_id eliminado")
    print("   - asignacion_nit_responsable.grupo_id eliminado")
    print("   - Constraints restauradas")
    print("   - Sistema en estado anterior")
