"""Asignar responsables a facturas existentes

Revision ID: 2025_12_04_responsables
Revises: 2025_12_04_accion_por
Create Date: 2025-12-04 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_12_04_responsables'
down_revision = '2025_12_04_accion_por'
branch_labels = None
depends_on = None


def upgrade():
    """
    Asigna responsables a facturas existentes que no los tienen.

    Esta migración corrige facturas históricas que fueron creadas antes
    de que existieran asignaciones NIT-Responsable.

    Se ejecuta automáticamente cada vez que se crea una nueva asignación.
    """
    bind = op.get_bind()

    # SQL para asignar responsables basándose en asignaciones existentes
    asignar_sql = """
    UPDATE facturas f
    INNER JOIN proveedores p ON f.proveedor_id = p.id
    INNER JOIN asignacion_nit_responsable anr ON anr.nit = p.nit
    SET f.responsable_id = anr.responsable_id
    WHERE f.responsable_id IS NULL
      AND anr.activo = true
      AND f.estado IN ('en_revision', 'pendiente', 'aprobada', 'aprobada_auto')
    """

    # Ejecutar asignación
    result = bind.execute(sa.text(asignar_sql))
    affected = result.rowcount

    # Contar resultados
    stats = bind.execute(sa.text("""
        SELECT
            COUNT(CASE WHEN f.responsable_id IS NOT NULL THEN 1 END) as con_responsable,
            COUNT(CASE WHEN f.responsable_id IS NULL THEN 1 END) as sin_responsable
        FROM facturas f
        WHERE f.estado IN ('en_revision', 'pendiente', 'aprobada', 'aprobada_auto');
    """)).fetchone()

    print("\n" + "=" * 80)
    print("MIGRACION: Asignacion de responsables completada")
    print("=" * 80)
    print(f"[OK] Facturas actualizadas: {affected}")
    print(f"[OK] Total con responsable: {stats[0]}")
    print(f"[WARNING] Facturas sin responsable: {stats[1]}")
    if stats[1] > 0:
        print("         (Requieren crear asignaciones NIT-Responsable)")
    print("=" * 80)


def downgrade():
    """
    No hay downgrade para esta migración.

    Los responsables asignados deben permanecer.
    """
    pass
