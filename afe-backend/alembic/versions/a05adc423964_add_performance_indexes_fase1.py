"""add_performance_indexes_fase1

Agregar índices adicionales para mejorar performance de queries frecuentes.

FASE 1: Quick Wins - Optimización de performance
Objetivo: Mejorar velocidad de queries comunes en dashboard y reportes

Índices agregados:
- facturas: (fecha_emision DESC, estado) para dashboard
- facturas: (proveedor_id, fecha_emision DESC) para reportes por proveedor
- facturas: (responsable_id, estado) para workflow
- workflow: (responsable_id, estado, fecha_cambio_estado) para pendientes
- factura_items: (codigo_producto) para búsqueda de productos

Revision ID: a05adc423964
Revises: a40e54d122a3
Create Date: 2025-10-19 19:05:58.590882

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a05adc423964'
down_revision: Union[str, Sequence[str], None] = 'a40e54d122a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agregar índices para mejorar performance."""

    print("[INFO] Agregando índices de performance en facturas...")

    # Dashboard: búsqueda por fecha y estado (query más común)
    op.create_index(
        'idx_facturas_fecha_estado',
        'facturas',
        ['fecha_emision', 'estado'],
        unique=False
    )

    # Reportes: búsqueda por proveedor y fecha
    op.create_index(
        'idx_facturas_proveedor_fecha',
        'facturas',
        ['proveedor_id', 'fecha_emision'],
        unique=False
    )

    # Workflow: búsqueda por responsable y estado
    op.create_index(
        'idx_facturas_responsable_estado',
        'facturas',
        ['responsable_id', 'estado'],
        unique=False
    )

    print("[INFO] Agregando índices de performance en workflow...")

    # Workflow pendientes: query crítico para dashboard de responsables
    op.create_index(
        'idx_workflow_responsable_estado_fecha',
        'workflow_aprobacion_facturas',
        ['responsable_id', 'estado', 'fecha_cambio_estado'],
        unique=False
    )

    print("[INFO] Agregando índices de performance en factura_items...")

    # Búsqueda de items por código de producto
    op.create_index(
        'idx_items_codigo',
        'factura_items',
        ['codigo_producto'],
        unique=False
    )

    print("[OK] Índices de performance agregados exitosamente")
    print("[INFO] Recomendación: Ejecutar ANALYZE TABLE para actualizar estadísticas")


def downgrade() -> None:
    """Eliminar índices de performance."""

    print("[INFO] Eliminando índices de facturas...")
    op.drop_index('idx_facturas_fecha_estado', table_name='facturas')
    op.drop_index('idx_facturas_proveedor_fecha', table_name='facturas')
    op.drop_index('idx_facturas_responsable_estado', table_name='facturas')

    print("[INFO] Eliminando índices de workflow...")
    op.drop_index('idx_workflow_responsable_estado_fecha', table_name='workflow_aprobacion_facturas')

    print("[INFO] Eliminando índices de factura_items...")
    op.drop_index('idx_items_codigo', table_name='factura_items')

    print("[OK] Índices eliminados exitosamente")
