"""Sincronizar accion_por en facturas históricas

Revision ID: 2025_12_04_accion_por
Revises:
Create Date: 2025-12-04 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_12_04_accion_por'
down_revision = '1cb2fe74559e'  # Última migración actual
branch_labels = None
depends_on = None


def upgrade():
    """
    Sincroniza accion_por para TODAS las facturas históricas.

    Esta migración garantiza que:
    1. Facturas aprobadas automáticamente → accion_por = 'Sistema Automático'
    2. Facturas aprobadas manualmente → accion_por = nombre del usuario
    3. Facturas rechazadas → accion_por = nombre del usuario que rechazó
    4. Facturas en revisión → accion_por = NULL

    Se ejecuta UNA SOLA VEZ y corrige todos los datos históricos.
    """
    bind = op.get_bind()

    # SQL para sincronizar TODAS las facturas
    # ENFOQUE: Usar el ESTADO de la factura como fuente de verdad primaria
    sincronizar_sql = """
    UPDATE facturas f
    SET accion_por = CASE
        -- CASO 1: Factura RECHAZADA - buscar quien rechazó
        WHEN f.estado = 'rechazada' THEN (
            SELECT COALESCE(w.rechazada_por, 'Usuario Desconocido')
            FROM workflow_aprobacion_facturas w
            WHERE w.factura_id = f.id AND w.rechazada = true
            ORDER BY w.fecha_rechazo ASC
            LIMIT 1
        )

        -- CASO 2: Factura APROBADA_AUTO - siempre "Sistema Automático"
        WHEN f.estado = 'aprobada_auto' THEN 'Sistema Automático'

        -- CASO 3: Factura APROBADA manualmente - buscar quien aprobó
        WHEN f.estado = 'aprobada' THEN (
            SELECT COALESCE(w.aprobada_por, 'Usuario Desconocido')
            FROM workflow_aprobacion_facturas w
            WHERE w.factura_id = f.id AND w.aprobada = true
            ORDER BY w.fecha_aprobacion ASC
            LIMIT 1
        )

        -- CASO 4: Factura en revisión o pendiente - NULL
        ELSE NULL
    END
    WHERE f.estado IN ('aprobada', 'aprobada_auto', 'rechazada')
    AND (
        -- Solo actualizar si accion_por está vacío o incorrecto
        f.accion_por IS NULL
        OR (f.estado = 'aprobada_auto' AND f.accion_por != 'Sistema Automático')
        OR (f.estado = 'rechazada' AND f.accion_por IS NULL)
        OR (f.estado = 'aprobada' AND f.accion_por IS NULL)
    );
    """

    # Ejecutar sincronización
    bind.execute(sa.text(sincronizar_sql))

    # Contar resultados (sintaxis MySQL - evitar palabras reservadas)
    result = bind.execute(sa.text("""
        SELECT
            SUM(CASE WHEN accion_por = 'Sistema Automático' THEN 1 ELSE 0 END) as automaticas,
            SUM(CASE WHEN accion_por IS NOT NULL AND accion_por != 'Sistema Automático' THEN 1 ELSE 0 END) as manuales,
            SUM(CASE WHEN accion_por IS NULL THEN 1 ELSE 0 END) as sin_accion
        FROM facturas
        WHERE EXISTS (
            SELECT 1 FROM workflow_aprobacion_facturas w
            WHERE w.factura_id = facturas.id
        );
    """)).fetchone()

    print("\n" + "=" * 80)
    print("MIGRACION: Sincronizacion de accion_por completada")
    print("=" * 80)
    print(f"[OK] Facturas con 'Sistema Automatico': {result[0]}")
    print(f"[OK] Facturas con usuario manual: {result[1]}")
    print(f"[PENDING] Facturas en revision (sin accion_por): {result[2]}")
    print("=" * 80)


def downgrade():
    """
    No hay downgrade para esta migración.

    Es una corrección de datos que no modifica la estructura de la BD.
    Los datos corregidos deben permanecer correctos.
    """
    pass
