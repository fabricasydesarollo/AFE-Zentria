"""remove_unnecessary_fields_from_facturas

Revision ID: 4ca79fbcd3d4
Revises: d721faa20fc3
Create Date: 2025-10-10 09:22:28.449988

Limpieza profesional de campos innecesarios y redundantes.

Campos eliminados (13):
REDUNDANTES:
- aprobada_automaticamente (redundante con estado='aprobada_auto')
- periodo_factura (derivable de mes_factura + año_factura)

INNECESARIOS:
- cliente_id (no se usa en automatización)
- moneda (siempre COP en Colombia)
- observaciones (usar motivo_rechazo)
- creado_por (sistema siempre crea)
- tipo_factura (no está documentado/usado)
- año_factura (derivable de fecha_emision.year)
- mes_factura (derivable de fecha_emision.month)
- orden_compra_numero (mover a factura_items si es necesario)
- orden_compra_sap (mover a factura_items si es necesario)
- procesamiento_info (JSON catch-all = anti-patrón)
- version_algoritmo (no aporta valor)

Resultado: 36 -> 23 campos (estructura profesional)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '4ca79fbcd3d4'
down_revision: Union[str, Sequence[str], None] = 'd721faa20fc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Elimina campos innecesarios y redundantes."""
    # INNECESARIOS (cliente_id mantenerlo por ahora por FK)
    op.drop_column('facturas', 'moneda')
    op.drop_column('facturas', 'observaciones')
    op.drop_column('facturas', 'creado_por')
    op.drop_column('facturas', 'tipo_factura')
    op.drop_column('facturas', 'año_factura')
    op.drop_column('facturas', 'mes_factura')
    op.drop_column('facturas', 'orden_compra_numero')
    op.drop_column('facturas', 'orden_compra_sap')
    op.drop_column('facturas', 'procesamiento_info')
    op.drop_column('facturas', 'version_algoritmo')


def downgrade() -> None:
    """Restaura campos eliminados."""
    # REDUNDANTES
    op.add_column('facturas', sa.Column('aprobada_automaticamente', sa.Boolean(), nullable=True))
    op.add_column('facturas', sa.Column('periodo_factura', sa.String(7), nullable=True))

    # INNECESARIOS
    op.add_column('facturas', sa.Column('cliente_id', sa.BigInteger(), nullable=True))
    op.add_column('facturas', sa.Column('moneda', sa.String(10), nullable=False, server_default='COP'))
    op.add_column('facturas', sa.Column('observaciones', sa.String(2048), nullable=True))
    op.add_column('facturas', sa.Column('creado_por', sa.String(100), nullable=True))
    op.add_column('facturas', sa.Column('tipo_factura', sa.String(50), nullable=True))
    op.add_column('facturas', sa.Column('año_factura', sa.BigInteger(), nullable=True))
    op.add_column('facturas', sa.Column('mes_factura', sa.Integer(), nullable=True))
    op.add_column('facturas', sa.Column('orden_compra_numero', sa.String(50), nullable=True))
    op.add_column('facturas', sa.Column('orden_compra_sap', sa.String(50), nullable=True))
    op.add_column('facturas', sa.Column('procesamiento_info', mysql.JSON(), nullable=True))
    op.add_column('facturas', sa.Column('version_algoritmo', sa.String(50), nullable=True))

    # Restaurar foreign key constraint
    op.create_foreign_key('facturas_ibfk_1', 'facturas', 'clientes', ['cliente_id'], ['id'])
