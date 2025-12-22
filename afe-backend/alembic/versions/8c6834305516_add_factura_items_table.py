"""add_factura_items_table

Revision ID: 8c6834305516
Revises: 959d4f1f1475
Create Date: 2025-10-09 16:07:17.706743

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c6834305516'
down_revision: Union[str, Sequence[str], None] = '959d4f1f1475'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crea la tabla factura_items para almacenar líneas individuales de facturas.

    Esta tabla permite:
    - Comparaciones granulares item por item
    - Análisis de precios unitarios históricos
    - Detección de cambios en composición de servicios/productos
    """
    # Crear tabla factura_items
    op.create_table(
        'factura_items',

        # Columnas de identificación
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('factura_id', sa.BigInteger(), nullable=False),
        sa.Column('numero_linea', sa.Integer(), nullable=False),

        # Descripción y códigos
        sa.Column('descripcion', sa.String(2000), nullable=False),
        sa.Column('codigo_producto', sa.String(100), nullable=True),
        sa.Column('codigo_estandar', sa.String(100), nullable=True),

        # Cantidades
        sa.Column('cantidad', sa.Numeric(15, 4), nullable=False, server_default='1'),
        sa.Column('unidad_medida', sa.String(50), nullable=True, server_default='unidad'),

        # Precios
        sa.Column('precio_unitario', sa.Numeric(15, 4), nullable=False),
        sa.Column('subtotal', sa.Numeric(15, 2), nullable=False),
        sa.Column('total_impuestos', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('total', sa.Numeric(15, 2), nullable=False),

        # Descuentos
        sa.Column('descuento_porcentaje', sa.Numeric(5, 2), nullable=True),
        sa.Column('descuento_valor', sa.Numeric(15, 2), nullable=True),

        # Normalización para matching
        sa.Column('descripcion_normalizada', sa.String(500), nullable=True),
        sa.Column('item_hash', sa.String(32), nullable=True),

        # Clasificación
        sa.Column('categoria', sa.String(100), nullable=True),
        sa.Column('es_recurrente', sa.Numeric(1, 0), nullable=True, server_default='0'),

        # Metadata
        sa.Column('notas', sa.String(1000), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        # Primary Key
        sa.PrimaryKeyConstraint('id', name='pk_factura_items'),

        # Foreign Key con CASCADE DELETE
        sa.ForeignKeyConstraint(
            ['factura_id'],
            ['facturas.id'],
            name='fk_factura_items_factura_id',
            ondelete='CASCADE'
        ),

        # Configuración MySQL
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_engine='InnoDB'
    )

    # Índices para performance
    op.create_index(
        'idx_factura_id',
        'factura_items',
        ['factura_id']
    )

    op.create_index(
        'idx_factura_item_linea',
        'factura_items',
        ['factura_id', 'numero_linea'],
        unique=True  # No puede haber líneas duplicadas en una factura
    )

    op.create_index(
        'idx_item_hash_factura',
        'factura_items',
        ['item_hash', 'factura_id']
    )

    op.create_index(
        'idx_item_descripcion_norm',
        'factura_items',
        ['descripcion_normalizada']
    )

    op.create_index(
        'idx_item_codigo_producto',
        'factura_items',
        ['codigo_producto']
    )

    op.create_index(
        'idx_item_recurrente_categoria',
        'factura_items',
        ['es_recurrente', 'categoria']
    )


def downgrade() -> None:
    """Elimina la tabla factura_items y sus índices."""
    # Eliminar índices primero
    op.drop_index('idx_item_recurrente_categoria', table_name='factura_items')
    op.drop_index('idx_item_codigo_producto', table_name='factura_items')
    op.drop_index('idx_item_descripcion_norm', table_name='factura_items')
    op.drop_index('idx_item_hash_factura', table_name='factura_items')
    op.drop_index('idx_factura_item_linea', table_name='factura_items')
    op.drop_index('idx_factura_id', table_name='factura_items')

    # Eliminar tabla
    op.drop_table('factura_items')
