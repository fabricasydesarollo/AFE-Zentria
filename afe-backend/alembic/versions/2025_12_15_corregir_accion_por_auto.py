"""Corregir accion_por en facturas aprobadas automáticamente

Revision ID: 2025_12_15_accion_por_auto
Revises: c99cb6884535_merge_heads_remove_cache
Create Date: 2025-12-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_12_15_accion_por_auto'
down_revision = 'c99cb6884535'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Corrige el campo accion_por en facturas aprobadas automáticamente.

    PROBLEMA:
    - Facturas con estado 'aprobada_auto' no tienen accion_por asignado
    - El flujo de automatización no estaba sincronizando este campo

    SOLUCIÓN:
    - Actualizar TODAS las facturas con estado 'aprobada_auto' a accion_por = 'Sistema Automático'
    """

    print("\n" + "=" * 80)
    print("MIGRACIÓN: Corregir accion_por en facturas aprobadas automáticamente")
    print("=" * 80 + "\n")

    connection = op.get_bind()

    # 1. Verificar cuántas facturas necesitan corrección
    result_antes = connection.execute(sa.text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN accion_por = 'Sistema Automático' THEN 1 ELSE 0 END) as correctas,
            SUM(CASE WHEN accion_por IS NULL OR accion_por != 'Sistema Automático' THEN 1 ELSE 0 END) as incorrectas
        FROM facturas
        WHERE estado = 'aprobada_auto'
    """)).fetchone()

    print(f"[ANTES DE LA CORRECCIÓN]")
    print(f"  Total facturas aprobadas_auto: {result_antes[0]}")
    print(f"  Facturas con accion_por correcto: {result_antes[1]}")
    print(f"  Facturas que necesitan corrección: {result_antes[2]}")
    print()

    if result_antes[2] == 0:
        print("[OK] No hay facturas que corregir.")
        return

    # 2. Mostrar algunas facturas que se van a corregir
    print("[MUESTRAS] Facturas que se corregirán (primeras 5):")
    muestras = connection.execute(sa.text("""
        SELECT id, numero_factura, estado, accion_por, fecha_emision
        FROM facturas
        WHERE estado = 'aprobada_auto'
        AND (accion_por IS NULL OR accion_por != 'Sistema Automático')
        LIMIT 5
    """)).fetchall()

    for muestra in muestras:
        print(f"  - ID: {muestra[0]} | {muestra[1]} | accion_por: '{muestra[3]}' -> 'Sistema Automático'")

    if result_antes[2] > 5:
        print(f"  ... y {result_antes[2] - 5} más")
    print()

    # 3. Realizar la corrección
    print("[CORRIGIENDO] Actualizando facturas...")

    result_update = connection.execute(sa.text("""
        UPDATE facturas
        SET accion_por = 'Sistema Automático',
            actualizado_en = NOW()
        WHERE estado = 'aprobada_auto'
        AND (accion_por IS NULL OR accion_por != 'Sistema Automático')
    """))

    print(f"[OK] Se actualizaron {result_update.rowcount} facturas.")
    print()

    # 4. Verificar la corrección
    print("[VERIFICACIÓN] Revisando correcciones...")

    result_despues = connection.execute(sa.text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN accion_por = 'Sistema Automático' THEN 1 ELSE 0 END) as correctas,
            SUM(CASE WHEN accion_por IS NULL OR accion_por != 'Sistema Automático' THEN 1 ELSE 0 END) as incorrectas
        FROM facturas
        WHERE estado = 'aprobada_auto'
    """)).fetchone()

    print(f"[DESPUÉS DE LA CORRECCIÓN]")
    print(f"  Total facturas aprobadas_auto: {result_despues[0]}")
    print(f"  Facturas con accion_por correcto: {result_despues[1]}")
    print(f"  Facturas pendientes de corrección: {result_despues[2]}")
    print()

    if result_despues[2] == 0:
        print("[OK] EXITO: TODAS las facturas aprobadas automaticamente tienen accion_por = 'Sistema Automatico'")
    else:
        print(f"[!] ADVERTENCIA: Todavia hay {result_despues[2]} facturas sin corregir.")

    print("\n" + "=" * 80)
    print("MIGRACIÓN COMPLETADA")
    print("=" * 80 + "\n")


def downgrade() -> None:
    """
    No se puede revertir esta migración de datos.
    """
    print("[INFO] Esta migración de datos no es reversible.")
    print("[INFO] Para revertir, ejecute manualmente:")
    print("  UPDATE facturas SET accion_por = NULL WHERE estado = 'aprobada_auto'")
