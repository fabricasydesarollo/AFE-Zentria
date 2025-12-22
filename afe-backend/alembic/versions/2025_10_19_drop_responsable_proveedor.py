"""drop_responsable_proveedor_table

Revision ID: 2025_10_19_drop_rp
Revises: f6feb264b552
Create Date: 2025-10-19 20:00:00.000000

Elimina la tabla responsable_proveedor que fue reemplazada por asignacion_nit_responsable.

  UNIFICACIÓN ARQUITECTÓNICA COMPLETADA
- Todos los datos migrados a asignacion_nit_responsable
- CRUD actualizado para usar solo asignacion_nit_responsable
- Nuevos endpoints: /api/v1/asignacion-nit
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '2025_10_19_drop_rp'
down_revision = ('f6feb264b552', '4ad923b70f74')  # Merge de ambos heads
branch_labels = None
depends_on = None


def upgrade():
    """
    Elimina la tabla responsable_proveedor.

    IMPORTANTE: Antes de ejecutar esta migración, asegúrate de:
    1. Haber ejecutado el script de migración de datos
    2. Haber validado que todos los datos están en asignacion_nit_responsable
    3. Haber actualizado todos los endpoints del frontend
    """
    # Eliminar tabla responsable_proveedor
    op.drop_table('responsable_proveedor')

    print("[OK] Tabla responsable_proveedor eliminada exitosamente")
    print("[OK] Sistema ahora usa SOLO asignacion_nit_responsable")


def downgrade():
    """
    Recrea la tabla responsable_proveedor en caso de rollback.

    ADVERTENCIA: Los datos NO se restaurarán automáticamente.
    """
    op.create_table(
        'responsable_proveedor',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('responsable_id', sa.BigInteger(), nullable=False),
        sa.Column('proveedor_id', sa.BigInteger(), nullable=False),
        sa.Column('activo', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['proveedor_id'], ['proveedores.id'], ),
        sa.ForeignKeyConstraint(['responsable_id'], ['responsables.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('responsable_id', 'proveedor_id', name='uix_resp_prov')
    )

    print("[WARN] Tabla responsable_proveedor recreada")
    print("[WARN] ADVERTENCIA: Los datos NO fueron restaurados")
