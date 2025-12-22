"""Eliminar estado pendiente y migrar a en_revision

Revision ID: 2025_10_23_eliminar_estado_pendiente
Revises: 2025_10_22_phase3_add_estado_asignacion_field
Create Date: 2025-10-23

REFACTORIZACIÓN ENTERPRISE:
- Elimina el estado 'pendiente' del enum EstadoFactura
- Migra todas las facturas con estado 'pendiente' → 'en_revision'
- Actualiza el enum en MySQL para eliminar el valor 'pendiente'

Justificación:
- Simplifica UX: Un solo estado de "espera" en lugar de dos confusos
- Mejora claridad: 'en_revision' es más descriptivo que 'pendiente'
- Optimiza workflow: Transición inmediata a 'en_revision' o 'aprobada_auto'
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eliminar_pendiente_2025'
down_revision = 'add_retenciones_2025_10_23'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Migración UPGRADE: Elimina 'pendiente' y migra a 'en_revision'
    """
    # Paso 1: Migrar todas las facturas con estado 'pendiente' → 'en_revision'
    op.execute("""
        UPDATE facturas
        SET estado = 'en_revision'
        WHERE estado = 'pendiente'
    """)

    # Paso 2: Actualizar el enum para eliminar 'pendiente'
    # MySQL no soporta ALTER TYPE directamente, debemos recrear la columna
    op.execute("""
        ALTER TABLE facturas
        MODIFY COLUMN estado ENUM('en_revision', 'aprobada', 'rechazada', 'aprobada_auto', 'pagada')
        NOT NULL DEFAULT 'en_revision'
    """)

    print("[OK] Migracion completada:")
    print("   - Facturas migradas: pendiente -> en_revision")
    print("   - Enum actualizado: eliminado 'pendiente'")
    print("   - Nuevo default: 'en_revision'")


def downgrade() -> None:
    """
    Migración DOWNGRADE: Restaura el estado 'pendiente'
    """
    # Paso 1: Recrear el enum con 'pendiente'
    op.execute("""
        ALTER TABLE facturas
        MODIFY COLUMN estado ENUM('pendiente', 'en_revision', 'aprobada', 'rechazada', 'aprobada_auto', 'pagada')
        NOT NULL DEFAULT 'pendiente'
    """)

    # Paso 2: Opcionalmente, migrar algunas facturas de vuelta a 'pendiente'
    # (esto es opcional, puedes dejarlo comentado si prefieres mantener todo en 'en_revision')
    # op.execute("""
    #     UPDATE facturas
    #     SET estado = 'pendiente'
    #     WHERE estado = 'en_revision' AND fecha_procesamiento_auto IS NULL
    # """)

    print("[WARNING] Downgrade completado: Estado 'pendiente' restaurado")
