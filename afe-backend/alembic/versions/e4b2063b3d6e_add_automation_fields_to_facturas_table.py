"""Add automation fields to facturas table

Revision ID: e4b2063b3d6e
Revises: da7367e01cd7
Create Date: 2025-09-24 10:29:26.918551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4b2063b3d6e'
down_revision: Union[str, Sequence[str], None] = 'da7367e01cd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agregar campos para automatización de facturas recurrentes."""
    
    # Campos de concepto y clasificación
    op.add_column('facturas', sa.Column('concepto_principal', sa.String(1000), nullable=True,
                                       comment="Concepto principal extraído del XML"))
    
    op.add_column('facturas', sa.Column('concepto_normalizado', sa.String(200), nullable=True,
                                       comment="Concepto normalizado para matching de recurrencia"))
    
    op.add_column('facturas', sa.Column('concepto_hash', sa.String(32), nullable=True,
                                       comment="Hash MD5 del concepto normalizado"))
    
    op.add_column('facturas', sa.Column('tipo_factura', sa.String(50), nullable=True,
                                       comment="Clasificación del tipo de factura"))
    
    # Campos de items y orden de compra
    op.add_column('facturas', sa.Column('items_resumen', sa.JSON(), nullable=True,
                                       comment="Array JSON con los 5 items principales"))
    
    op.add_column('facturas', sa.Column('orden_compra_numero', sa.String(50), nullable=True,
                                       comment="Número de orden de compra del XML"))
    
    op.add_column('facturas', sa.Column('orden_compra_sap', sa.String(50), nullable=True,
                                       comment="Número SAP de la orden de compra"))
    
    # Campos de automatización inteligente
    op.add_column('facturas', sa.Column('patron_recurrencia', sa.String(50), nullable=True,
                                       comment="Patrón detectado: mensual, quincenal, semanal"))
    
    op.add_column('facturas', sa.Column('confianza_automatica', sa.Numeric(3, 2), nullable=True,
                                       comment="Confianza (0.00-1.00) para aprobación automática"))
    
    op.add_column('facturas', sa.Column('factura_referencia_id', sa.BigInteger(), nullable=True,
                                       comment="ID de factura del mes anterior usada como referencia"))
    
    op.add_column('facturas', sa.Column('motivo_decision', sa.String(500), nullable=True,
                                       comment="Razón de la decisión automática"))
    
    # Campos de metadata y auditoría
    op.add_column('facturas', sa.Column('procesamiento_info', sa.JSON(), nullable=True,
                                       comment="Información técnica del procesamiento"))
    
    op.add_column('facturas', sa.Column('notas_adicionales', sa.JSON(), nullable=True,
                                       comment="Notas adicionales extraídas del XML"))
    
    op.add_column('facturas', sa.Column('fecha_procesamiento_auto', sa.DateTime(timezone=True), nullable=True,
                                       comment="Cuándo se ejecutó el procesamiento automático"))
    
    op.add_column('facturas', sa.Column('version_algoritmo', sa.String(20), nullable=True,
                                       server_default='1.0', comment="Versión del algoritmo"))
    
    # Crear foreign key para factura_referencia_id
    op.create_foreign_key('fk_factura_referencia', 'facturas', 'facturas', 
                         ['factura_referencia_id'], ['id'])
    
    # Crear índices para optimizar consultas de automatización
    op.create_index('idx_concepto_hash', 'facturas', ['concepto_hash'])
    op.create_index('idx_concepto_normalizado', 'facturas', ['concepto_normalizado'])
    op.create_index('idx_orden_compra_numero', 'facturas', ['orden_compra_numero'])
    op.create_index('idx_proveedor_concepto', 'facturas', ['proveedor_id', 'concepto_normalizado'])
    op.create_index('idx_patron_recurrencia', 'facturas', ['patron_recurrencia'])
    op.create_index('idx_fecha_procesamiento', 'facturas', ['fecha_procesamiento_auto'])


def downgrade() -> None:
    """Eliminar campos de automatización."""
    
    # Eliminar índices
    op.drop_index('idx_fecha_procesamiento', 'facturas')
    op.drop_index('idx_patron_recurrencia', 'facturas')
    op.drop_index('idx_proveedor_concepto', 'facturas')
    op.drop_index('idx_orden_compra_numero', 'facturas')
    op.drop_index('idx_concepto_normalizado', 'facturas')
    op.drop_index('idx_concepto_hash', 'facturas')
    
    # Eliminar foreign key
    op.drop_constraint('fk_factura_referencia', 'facturas', type_='foreignkey')
    
    # Eliminar columnas en orden inverso
    op.drop_column('facturas', 'version_algoritmo')
    op.drop_column('facturas', 'fecha_procesamiento_auto')
    op.drop_column('facturas', 'notas_adicionales')
    op.drop_column('facturas', 'procesamiento_info')
    op.drop_column('facturas', 'motivo_decision')
    op.drop_column('facturas', 'factura_referencia_id')
    op.drop_column('facturas', 'confianza_automatica')
    op.drop_column('facturas', 'patron_recurrencia')
    op.drop_column('facturas', 'orden_compra_sap')
    op.drop_column('facturas', 'orden_compra_numero')
    op.drop_column('facturas', 'items_resumen')
    op.drop_column('facturas', 'tipo_factura')
    op.drop_column('facturas', 'concepto_hash')
    op.drop_column('facturas', 'concepto_normalizado')
    op.drop_column('facturas', 'concepto_principal')
