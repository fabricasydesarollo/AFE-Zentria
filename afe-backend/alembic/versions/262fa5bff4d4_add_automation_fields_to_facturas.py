"""add_automation_fields_to_facturas

Revision ID: 262fa5bff4d4
Revises: 1e507fe2fa12
Create Date: 2025-10-14 09:15:17.158315

Agrega campos necesarios para el sistema de automatizacion empresarial:
- concepto_principal: Descripcion/concepto de la factura (generado desde items)
- concepto_hash: Hash MD5 para comparaciones rapidas entre facturas
- concepto_normalizado: Concepto normalizado (sin stopwords, lowercase)
- orden_compra_numero: Numero de orden de compra asociada (si aplica)
- patron_recurrencia: Si la factura tiene patron de recurrencia (FIJO/VARIABLE/UNICO)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '262fa5bff4d4'
down_revision: Union[str, Sequence[str], None] = '1e507fe2fa12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agrega campos para automatizacion empresarial de facturas.
    """
    # 1. Campo principal: concepto de la factura
    op.add_column('facturas',
        sa.Column('concepto_principal', sa.String(500), nullable=True,
                  comment='Descripcion/concepto principal de la factura'))

    # 2. Hash MD5 del concepto para comparaciones rapidas
    op.add_column('facturas',
        sa.Column('concepto_hash', sa.String(32), nullable=True, index=True,
                  comment='Hash MD5 del concepto normalizado para matching rapido'))

    # 3. Concepto normalizado (sin stopwords, lowercase)
    op.add_column('facturas',
        sa.Column('concepto_normalizado', sa.String(500), nullable=True,
                  comment='Concepto sin stopwords y normalizado'))

    # 4. Numero de orden de compra (si aplica)
    op.add_column('facturas',
        sa.Column('orden_compra_numero', sa.String(50), nullable=True, index=True,
                  comment='Numero de orden de compra asociada'))

    # 5. Patron de recurrencia detectado
    op.add_column('facturas',
        sa.Column('patron_recurrencia', sa.String(20), nullable=True,
                  comment='Patron: FIJO, VARIABLE, UNICO, DESCONOCIDO'))

    # 6. Crear indice compuesto para busquedas de automatizacion
    op.create_index('idx_facturas_automation',
                   'facturas',
                   ['proveedor_id', 'concepto_hash', 'estado'],
                   unique=False)

    print("Campos de automatizacion agregados exitosamente")


def downgrade() -> None:
    """
    Revierte los cambios (elimina campos de automatizacion).
    """
    # Eliminar indice
    op.drop_index('idx_facturas_automation', 'facturas')

    # Eliminar columnas
    op.drop_column('facturas', 'patron_recurrencia')
    op.drop_column('facturas', 'orden_compra_numero')
    op.drop_column('facturas', 'concepto_normalizado')
    op.drop_column('facturas', 'concepto_hash')
    op.drop_column('facturas', 'concepto_principal')
