"""Resetear workflows de facturas devueltas históricas

Revision ID: 2025_12_04_workflows_devueltas
Revises: 2025_12_04_responsables
Create Date: 2025-12-04 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_12_04_workflows_devueltas'
down_revision = '2025_12_04_responsables'
branch_labels = None
depends_on = None


def upgrade():
    """
    Resetea workflows de facturas históricas que están en estado 'devuelta_contabilidad'.

    Esta migración corrige facturas devueltas anteriormente para que:
    1. Aparezcan en la vista "Por Revisar" del responsable
    2. Los responsables puedan aprobar o rechazar nuevamente
    3. El workflow tenga el estado correcto (PENDIENTE_REVISION)

    Se ejecuta UNA SOLA VEZ para corregir datos históricos.
    """
    bind = op.get_bind()

    # SQL para resetear workflows de facturas devueltas
    resetear_sql = """
    UPDATE workflow_aprobacion_facturas w
    INNER JOIN facturas f ON w.factura_id = f.id
    SET
        w.aprobada = false,
        w.aprobada_por = NULL,
        w.fecha_aprobacion = NULL,
        w.tipo_aprobacion = NULL,
        w.rechazada = false,
        w.rechazada_por = NULL,
        w.fecha_rechazo = NULL,
        w.detalle_rechazo = NULL,
        w.estado = 'pendiente_revision'
    WHERE f.estado = 'devuelta_contabilidad'
    AND (
        w.aprobada = true
        OR w.rechazada = true
        OR w.estado != 'pendiente_revision'
    );
    """

    # Ejecutar reseteo
    result = bind.execute(sa.text(resetear_sql))
    workflows_actualizados = result.rowcount

    # Contar facturas devueltas
    stats = bind.execute(sa.text("""
        SELECT
            COUNT(DISTINCT f.id) as total_devueltas,
            COUNT(w.id) as total_workflows
        FROM facturas f
        LEFT JOIN workflow_aprobacion_facturas w ON w.factura_id = f.id
        WHERE f.estado = 'devuelta_contabilidad';
    """)).fetchone()

    print("\n" + "=" * 80)
    print("MIGRACION: Reseteo de workflows devueltas completado")
    print("=" * 80)
    print(f"[OK] Workflows reseteados: {workflows_actualizados}")
    print(f"[INFO] Total facturas devueltas: {stats[0]}")
    print(f"[INFO] Total workflows asociados: {stats[1]}")
    print("")
    print("Las facturas devueltas ahora apareceran en 'Por Revisar'")
    print("de los responsables con estado PENDIENTE_REVISION")
    print("=" * 80)


def downgrade():
    """
    No hay downgrade para esta migración.

    Es una corrección de datos que permite que el flujo de trabajo
    funcione correctamente. No se debe revertir.
    """
    pass
