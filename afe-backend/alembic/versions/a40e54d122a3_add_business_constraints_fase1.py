"""add_business_constraints_fase1

Agregar constraints de negocio nivel enterprise para validación de datos.

FASE 1: Quick Wins - Mejoras de bajo riesgo, alto impacto
Objetivo: Llevar DB a nivel 100% profesional Fortune 500

Constraints agregados:
- Validación de montos positivos (facturas, items)
- Validación de porcentajes válidos (descuentos)
- Validación de estado consistente (aprobado/rechazado)
- Validación de cantidades positivas

Revision ID: a40e54d122a3
Revises: 2025_10_19_drop_rp
Create Date: 2025-10-19 19:05:10.563857

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a40e54d122a3'
down_revision: Union[str, Sequence[str], None] = '2025_10_19_drop_rp'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agregar constraints de negocio a nivel de base de datos."""

    # Obtener conexión para limpiar constraints duplicados si existen
    connection = op.get_bind()

    # ============================================================================
    # LIMPIEZA: Eliminar constraints duplicados si existen
    # ============================================================================
    print("[INFO] Limpiando constraints duplicados si existen...")

    constraints_to_clean = [
        ('facturas', 'chk_facturas_subtotal_positivo'),
        ('facturas', 'chk_facturas_iva_positivo'),
        ('facturas', 'chk_facturas_aprobada_con_aprobador'),
        ('facturas', 'chk_facturas_rechazada_con_motivo'),
        ('factura_items', 'chk_items_cantidad_positiva'),
        ('factura_items', 'chk_items_precio_positivo'),
        ('factura_items', 'chk_items_subtotal_positivo'),
        ('factura_items', 'chk_items_total_positivo'),
        ('factura_items', 'chk_items_descuento_valido'),
        ('proveedores', 'chk_proveedores_nit_no_vacio'),
    ]

    for table, constraint in constraints_to_clean:
        try:
            connection.execute(sa.text(f'ALTER TABLE {table} DROP CHECK {constraint}'))
        except Exception:
            pass  # Constraint no existe, continuar

    # ============================================================================
    # FACTURAS: Validación de montos
    # ============================================================================
    print("[INFO] Agregando constraints de montos en facturas...")

    op.create_check_constraint(
        'chk_facturas_subtotal_positivo',
        'facturas',
        'subtotal >= 0'
    )

    op.create_check_constraint(
        'chk_facturas_iva_positivo',
        'facturas',
        'iva >= 0'
    )

    # ============================================================================
    # FACTURAS: Validación de estados consistentes
    # ============================================================================
    print("[INFO] Agregando constraints de estados en facturas...")

    # PASO 1: Corregir datos existentes que violan los constraints
    print("[INFO] Corrigiendo datos existentes que violan constraints...")

    # Corregir facturas aprobadas sin aprobador (usar usuario sistema)
    connection.execute(sa.text("""
        UPDATE facturas
        SET
            aprobado_por = 'sistema',
            fecha_aprobacion = COALESCE(fecha_aprobacion, creado_en, NOW())
        WHERE estado IN ('aprobada', 'aprobada_auto')
        AND (aprobado_por IS NULL OR fecha_aprobacion IS NULL)
    """))

    # Corregir facturas rechazadas sin motivo
    connection.execute(sa.text("""
        UPDATE facturas
        SET
            rechazado_por = 'sistema',
            motivo_rechazo = COALESCE(motivo_rechazo, 'Migración: motivo no especificado')
        WHERE estado = 'rechazada'
        AND (rechazado_por IS NULL OR motivo_rechazo IS NULL)
    """))

    print("[OK] Datos corregidos exitosamente")

    # PASO 2: Agregar constraints
    # Factura aprobada DEBE tener aprobado_por y fecha_aprobacion
    op.create_check_constraint(
        'chk_facturas_aprobada_con_aprobador',
        'facturas',
        "(estado NOT IN ('aprobada', 'aprobada_auto')) OR "
        "(aprobado_por IS NOT NULL AND fecha_aprobacion IS NOT NULL)"
    )

    # Factura rechazada DEBE tener rechazado_por y motivo_rechazo
    op.create_check_constraint(
        'chk_facturas_rechazada_con_motivo',
        'facturas',
        "estado != 'rechazada' OR "
        "(rechazado_por IS NOT NULL AND motivo_rechazo IS NOT NULL)"
    )

    # ============================================================================
    # FACTURA_ITEMS: Validación de cantidades y precios
    # ============================================================================
    print("[INFO] Agregando constraints en factura_items...")

    op.create_check_constraint(
        'chk_items_cantidad_positiva',
        'factura_items',
        'cantidad > 0'
    )

    op.create_check_constraint(
        'chk_items_precio_positivo',
        'factura_items',
        'precio_unitario >= 0'
    )

    op.create_check_constraint(
        'chk_items_subtotal_positivo',
        'factura_items',
        'subtotal >= 0'
    )

    op.create_check_constraint(
        'chk_items_total_positivo',
        'factura_items',
        'total >= 0'
    )

    # ============================================================================
    # FACTURA_ITEMS: Validación de porcentaje de descuento
    # ============================================================================
    op.create_check_constraint(
        'chk_items_descuento_valido',
        'factura_items',
        'descuento_porcentaje IS NULL OR '
        '(descuento_porcentaje >= 0 AND descuento_porcentaje <= 100)'
    )

    # ============================================================================
    # PROVEEDORES: Validación de NIT no vacío
    # ============================================================================
    print("[INFO] Agregando constraints en proveedores...")

    op.create_check_constraint(
        'chk_proveedores_nit_no_vacio',
        'proveedores',
        "nit != '' AND LENGTH(TRIM(nit)) > 0"
    )

    print("[OK] Constraints de negocio agregados exitosamente")


def downgrade() -> None:
    """Eliminar constraints de negocio."""

    print("[INFO] Eliminando constraints de facturas...")
    op.drop_constraint('chk_facturas_subtotal_positivo', 'facturas', type_='check')
    op.drop_constraint('chk_facturas_iva_positivo', 'facturas', type_='check')
    op.drop_constraint('chk_facturas_aprobada_con_aprobador', 'facturas', type_='check')
    op.drop_constraint('chk_facturas_rechazada_con_motivo', 'facturas', type_='check')

    print("[INFO] Eliminando constraints de factura_items...")
    op.drop_constraint('chk_items_cantidad_positiva', 'factura_items', type_='check')
    op.drop_constraint('chk_items_precio_positivo', 'factura_items', type_='check')
    op.drop_constraint('chk_items_subtotal_positivo', 'factura_items', type_='check')
    op.drop_constraint('chk_items_total_positivo', 'factura_items', type_='check')
    op.drop_constraint('chk_items_descuento_valido', 'factura_items', type_='check')

    print("[INFO] Eliminando constraints de proveedores...")
    op.drop_constraint('chk_proveedores_nit_no_vacio', 'proveedores', type_='check')

    print("[OK] Constraints eliminados exitosamente")
