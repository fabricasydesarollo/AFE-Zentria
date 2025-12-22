"""Create database triggers for assignment-invoice integrity

Revision ID: trigger_integrity_2025
Revises:
Create Date: 2025-10-21

ENTERPRISE LEVEL: Database-level guarantees for data consistency
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'trigger_integrity_2025'
down_revision = '8cac6c86089d'  # Performance index for activo in asignacion
branch_labels = None
depends_on = None


def upgrade():
    """
    Create triggers to guarantee invoice-assignment synchronization at database level.

    IMPLEMENTACIÓN PROFESIONAL ENTERPRISE:
    Los triggers se crean por separado en lugar de usar DELIMITER.
    DELIMITER no es soportado en SQLAlchemy op.execute().

    Triggers creados:
    1. after_asignacion_soft_delete: Desasigna facturas cuando se marca como inactiva
    2. after_asignacion_activate: Asigna facturas cuando se crea/restaura asignación
    3. after_asignacion_restore: Reasigna facturas cuando se restaura asignación

    Benefits:
    - Works even if Python code has bugs
    - Works with manual SQL operations
    - Works with any future framework/language
    - Cannot be bypassed or forgotten
    - Atomic with the transaction
    - Idempotent: puede ejecutarse múltiples veces sin fallar
    """

    # Trigger 1: Desasignar facturas cuando se marca como inactiva
    op.execute("""
        DROP TRIGGER IF EXISTS after_asignacion_soft_delete
    """)

    op.execute("""
        CREATE TRIGGER after_asignacion_soft_delete
        AFTER UPDATE ON asignacion_nit_responsable
        FOR EACH ROW
        BEGIN
            IF OLD.activo = TRUE AND NEW.activo = FALSE THEN
                UPDATE facturas
                SET responsable_id = NULL,
                    actualizado_en = NOW()
                WHERE responsable_id = OLD.responsable_id;
            END IF;
        END
    """)

    # Trigger 2: Asignar facturas cuando se crea asignación
    op.execute("""
        DROP TRIGGER IF EXISTS after_asignacion_activate
    """)

    op.execute("""
        CREATE TRIGGER after_asignacion_activate
        AFTER INSERT ON asignacion_nit_responsable
        FOR EACH ROW
        BEGIN
            IF NEW.activo = TRUE THEN
                UPDATE facturas f
                INNER JOIN proveedores p ON f.proveedor_id = p.id
                SET f.responsable_id = NEW.responsable_id,
                    f.actualizado_en = NOW()
                WHERE p.nit LIKE CONCAT(NEW.nit, '%')
                  AND f.responsable_id IS NULL;
            END IF;
        END
    """)

    # Trigger 3: Reasignar facturas cuando se restaura asignación
    op.execute("""
        DROP TRIGGER IF EXISTS after_asignacion_restore
    """)

    op.execute("""
        CREATE TRIGGER after_asignacion_restore
        AFTER UPDATE ON asignacion_nit_responsable
        FOR EACH ROW
        BEGIN
            IF OLD.activo = FALSE AND NEW.activo = TRUE THEN
                UPDATE facturas f
                INNER JOIN proveedores p ON f.proveedor_id = p.id
                SET f.responsable_id = NEW.responsable_id,
                    f.actualizado_en = NOW()
                WHERE p.nit LIKE CONCAT(NEW.nit, '%')
                  AND f.responsable_id IS NULL;
            END IF;
        END
    """)


def downgrade():
    """Remove triggers."""

    op.execute("DROP TRIGGER IF EXISTS after_asignacion_soft_delete")
    op.execute("DROP TRIGGER IF EXISTS after_asignacion_activate")
    op.execute("DROP TRIGGER IF EXISTS after_asignacion_restore")

    print(" Triggers de integridad eliminados")
