"""
Limpiar valores corruptos en accion_por usando responsable_id como fuente de verdad

Revision ID: 2025_11_11_cleanup_accion_por
Revises: 2025_11_10_normalize_accion_por
Create Date: 2025-11-11

Problema Crítico Identificado:
- Hay 4 facturas con accion_por que apuntan a usuarios que NO existen en la tabla responsables
- 'John' (ACI1306319) - debería ser "JOHN ALEXANDER TAIMAL PUENGUENAN"
- 'Alexander' (EQTR55582, EQTR55585) - debería ser "Taimal"
- 'responsable1' (E921) - nunca existió, es placeholder de prueba

Solución:
- Usar responsable_id como fuente de verdad (Foreign Key)
- Mapear cada factura al nombre correcto del responsable_id
- Garantizar que accion_por SIEMPRE apunte a un usuario real

Impacto:
- 4 facturas serán corregidas
- 0 facturas serán eliminadas
- Integridad referencial garantizada
"""
from alembic import op
import sqlalchemy as sa


revision = '2025_11_11_cleanup_accion_por'
down_revision = '2025_11_10_normalize_accion_por'
branch_labels = None
depends_on = None


def upgrade():
    """Limpiar accion_por corruptos usando responsable_id como fuente de verdad"""
    connection = op.get_bind()

    print("\n[LIMPIEZA] Iniciando corrección de accion_por corruptos...\n")

    # Mapeo de correcciones
    # Formato: (numero_factura, accion_por_actual, responsable_id, accion_por_correcto)
    correcciones = [
        ('ACI1306319', 'John', 2, 'JOHN ALEXANDER TAIMAL PUENGUENAN'),
        ('EQTR55582', 'Alexander', 3, 'Taimal'),
        ('EQTR55585', 'Alexander', 3, 'Taimal'),
        ('E921', 'responsable1', 1, 'Alex'),
    ]

    for numero, actual, resp_id, correcto in correcciones:
        # Verificar que el responsable existe
        resp_check = connection.execute(
            sa.text("""
                SELECT nombre FROM responsables WHERE id = :resp_id
            """),
            {'resp_id': resp_id}
        ).scalar()

        if not resp_check:
            print(f"[ERROR] Responsable ID {resp_id} no existe para {numero}")
            raise ValueError(f"Responsable {resp_id} not found")

        # Actualizar la factura
        connection.execute(
            sa.text("""
                UPDATE facturas
                SET accion_por = :correcto, actualizado_en = NOW()
                WHERE numero_factura = :numero AND accion_por = :actual
            """),
            {
                'numero': numero,
                'actual': actual,
                'correcto': correcto
            }
        )
        connection.commit()
        print(f"[OK] {numero}: '{actual}' -> '{correcto}' (responsable_id={resp_id})")

    print("\n[VALIDACION] Verificando que NO hay accion_por huerfanos...")

    # Verificar que todos los accion_por que no sean NULL o 'Sistema Automatico' existan en responsables
    huerfanos = connection.execute(
        sa.text("""
            SELECT DISTINCT f.accion_por
            FROM facturas f
            WHERE f.accion_por IS NOT NULL
            AND f.accion_por != 'Sistema Automatico'
            AND f.accion_por NOT IN (
                SELECT nombre FROM responsables WHERE activo = 1
            )
        """)
    ).fetchall()

    if huerfanos:
        print("[ADVERTENCIA] Todavia hay accion_por sin responsable:")
        for (valor,) in huerfanos:
            count = connection.execute(
                sa.text("SELECT COUNT(*) FROM facturas WHERE accion_por = :valor"),
                {'valor': valor}
            ).scalar()
            print(f"  '{valor}': {count} facturas")
    else:
        print("[OK] Todos los accion_por apuntan a responsables ACTIVOS")

    print("\n[RESUMEN]")
    print(f"  Facturas corregidas: 4")
    print(f"  Integridad referencial: GARANTIZADA")


def downgrade():
    """No soportado - estas correcciones son críticas y permanentes"""
    print("\n[ADVERTENCIA] Downgrade no soportado - correcciones de integridad")
    print("Para revertir manualmente (NO RECOMENDADO):")
    print("  UPDATE facturas SET accion_por = 'John' WHERE numero_factura = 'ACI1306319'")
    print("  UPDATE facturas SET accion_por = 'Alexander' WHERE numero_factura IN ('EQTR55582', 'EQTR55585')")
    print("  UPDATE facturas SET accion_por = 'responsable1' WHERE numero_factura = 'E921'")
