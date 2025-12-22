"""Fix accion_por para TODAS las facturas aprobadas automáticamente (todas las variantes)

Revision ID: 2025_12_15_fix_completo
Revises: 2025_12_15_accion_por_auto
Create Date: 2025-12-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_12_15_fix_completo'
down_revision = '2025_12_15_accion_por_auto'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Actualiza accion_por para TODAS las facturas aprobadas automáticamente.

    CASOS CUBIERTOS:
    1. estado = 'aprobada_auto'
    2. estado = 'aprobado_auto' (variante)
    3. estado = 'Aprobado Automático' (con mayúsculas)
    4. aprobada_automaticamente = 1 (independiente del estado)
    """

    print("\n" + "=" * 80)
    print("MIGRACION: Fix completo de accion_por en TODAS las aprobaciones automaticas")
    print("=" * 80 + "\n")

    connection = op.get_bind()

    # 1. Diagnóstico inicial - ver todas las variantes de estado
    print("[1/5] Diagnosticando estados de aprobacion automatica...")

    variantes = connection.execute(sa.text("""
        SELECT DISTINCT estado, COUNT(*) as total
        FROM facturas
        WHERE estado LIKE '%aproba%auto%'
        GROUP BY estado
        ORDER BY total DESC
    """)).fetchall()

    print("  Estados encontrados:")
    for estado, total in variantes:
        print(f"    - '{estado}': {total} facturas")
    print()

    # 2. Contar facturas que necesitan corrección
    print("[2/5] Contando facturas que necesitan correccion...")

    result_antes = connection.execute(sa.text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN accion_por = 'Sistema Automático' THEN 1 ELSE 0 END) as correctas,
            SUM(CASE WHEN accion_por IS NULL OR accion_por != 'Sistema Automático' THEN 1 ELSE 0 END) as incorrectas
        FROM facturas
        WHERE estado IN ('aprobada_auto', 'aprobado_auto', 'Aprobado Automático', 'aprobada automaticamente')
    """)).fetchone()

    print(f"  Total facturas con aprobacion automatica: {result_antes[0]}")
    print(f"  Con accion_por correcto: {result_antes[1]}")
    print(f"  Que necesitan correccion: {result_antes[2]}")
    print()

    if result_antes[2] == 0:
        print("[OK] No hay facturas que corregir.")
        return

    # 3. Mostrar ejemplos
    print("[3/5] Ejemplos de facturas que se corregiran (primeras 10):")

    ejemplos = connection.execute(sa.text("""
        SELECT id, numero_factura, estado, accion_por
        FROM facturas
        WHERE estado IN ('aprobada_auto', 'aprobado_auto', 'Aprobado Automático', 'aprobada automaticamente')
        AND (accion_por IS NULL OR accion_por != 'Sistema Automático')
        LIMIT 10
    """)).fetchall()

    for ejemplo in ejemplos:
        accion = ejemplo[3] if ejemplo[3] else 'NULL'
        print(f"  - ID: {ejemplo[0]} | {ejemplo[1]} | estado: '{ejemplo[2]}' | accion_por: '{accion}'")

    if result_antes[2] > 10:
        print(f"  ... y {result_antes[2] - 10} mas")
    print()

    # 4. Actualizar TODAS las facturas
    print("[4/5] Actualizando facturas...")

    result = connection.execute(sa.text("""
        UPDATE facturas
        SET accion_por = 'Sistema Automático',
            actualizado_en = NOW()
        WHERE estado IN ('aprobada_auto', 'aprobado_auto', 'Aprobado Automático', 'aprobada automaticamente')
        AND (accion_por IS NULL OR accion_por != 'Sistema Automático')
    """))

    print(f"  Total actualizado: {result.rowcount}")
    print()

    # 5. Verificación final
    print("[5/5] Verificacion final...")

    result_despues = connection.execute(sa.text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN accion_por = 'Sistema Automático' THEN 1 ELSE 0 END) as correctas,
            SUM(CASE WHEN accion_por IS NULL OR accion_por != 'Sistema Automático' THEN 1 ELSE 0 END) as incorrectas
        FROM facturas
        WHERE estado IN ('aprobada_auto', 'aprobado_auto', 'Aprobado Automático', 'aprobada automaticamente')
    """)).fetchone()

    print(f"  Total facturas: {result_despues[0]}")
    print(f"  Con accion_por correcto: {result_despues[1]}")
    print(f"  Pendientes: {result_despues[2]}")
    print()

    if result_despues[2] == 0:
        print("[OK] EXITO: TODAS las facturas con aprobacion automatica tienen accion_por correcto")
    else:
        print(f"[!] ADVERTENCIA: Todavia hay {result_despues[2]} facturas pendientes")

        # Mostrar las que quedan pendientes
        pendientes = connection.execute(sa.text("""
            SELECT id, numero_factura, estado, accion_por
            FROM facturas
            WHERE estado IN ('aprobada_auto', 'aprobado_auto', 'Aprobado Automático', 'aprobada automaticamente')
            AND (accion_por IS NULL OR accion_por != 'Sistema Automático')
            LIMIT 5
        """)).fetchall()

        print("  Facturas pendientes:")
        for p in pendientes:
            accion = p[3] if p[3] else 'NULL'
            print(f"    - ID: {p[0]} | {p[1]} | estado: '{p[2]}' | accion_por: '{accion}'")

    print("\n" + "=" * 80)
    print("MIGRACION COMPLETADA")
    print("=" * 80 + "\n")


def downgrade() -> None:
    """No reversible."""
    print("[INFO] Esta migracion no es reversible.")
