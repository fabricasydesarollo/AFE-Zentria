"""
Normalizar accion_por para eliminar inconsistencias

Revision ID: 2025_11_10_normalize_accion_por
Revises: 2025_11_06_add_provider_auto_creation_fields
Create Date: 2025-11-10

Problema:
- Facturas recientes tienen accion_por = 'Sistema Automático'
- Facturas históricas tienen accion_por = NULL con estado = 'aprobada_auto'
- El schema hace fallback a 'SISTEMA DE AUTOMATIZACIÓN' para datos históricos
- Esto causa que en el dashboard aparezcan DOS valores diferentes

Solución:
- Normalizar TODAS las facturas con estado 'aprobada_auto' y accion_por NULL a 'Sistema Automático'
- Elimina la necesidad del fallback temporal en el schema
- Garantiza que el valor sea consistente: solo 'Sistema Automático'
"""
from alembic import op
import sqlalchemy as sa


revision = '2025_11_10_normalize_accion_por'
down_revision = 'provider_auto_create_2025'
branch_labels = None
depends_on = None


def upgrade():
    """Normalizar accion_por a 'Sistema Automático' para todas las aprobadas_auto sin accion_por"""
    connection = op.get_bind()

    # Contar facturas a actualizar
    count_result = connection.execute(
        sa.text("""
            SELECT COUNT(*) as count FROM facturas
            WHERE estado = 'aprobada_auto' AND accion_por IS NULL
        """)
    )
    count = count_result.scalar()
    print(f"\n[NORMALIZACION] Actualizando {count} facturas historicas...")

    # Actualizar todas las facturas históricas con estado aprobada_auto y accion_por NULL
    connection.execute(
        sa.text("""
            UPDATE facturas
            SET accion_por = 'Sistema Automatico',
                actualizado_en = NOW()
            WHERE estado = 'aprobada_auto' AND accion_por IS NULL
        """)
    )
    connection.commit()
    print(f"[NORMALIZACION] [OK] {count} facturas actualizadas a 'Sistema Automatico'")

    # Verificación de sanidad
    remaining = connection.execute(
        sa.text("""
            SELECT COUNT(*) as count FROM facturas
            WHERE estado = 'aprobada_auto' AND accion_por IS NULL
        """)
    ).scalar()

    if remaining > 0:
        print(f"[ADVERTENCIA] Todavia hay {remaining} facturas sin normalizar")
    else:
        print("[VALIDACION] [OK] Todas las facturas aprobadas_auto tienen accion_por")


def downgrade():
    """Revertir normalización - no es recomendado usar downgrade"""
    print("\n[ADVERTENCIA] Downgrade no soportado - esta migracion normaliza datos")
    print("Para revertir, use SQL manual o crear una nueva migracion")
