"""add_estado_pagada_to_facturas

Revision ID: 187d4c86be43
Revises: 7bad075511e9
Create Date: 2025-10-09 10:00:49.082680

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '187d4c86be43'
down_revision: Union[str, Sequence[str], None] = '7bad075511e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agrega el valor 'pagada' al enum EstadoFactura en MySQL.

    En MySQL, para agregar un valor al ENUM se debe usar ALTER TABLE MODIFY COLUMN.
    """
    # Modificar la columna estado de la tabla facturas para agregar 'pagada' al ENUM
    op.execute("""
        ALTER TABLE facturas
        MODIFY COLUMN estado ENUM(
            'pendiente',
            'aprobada_auto',
            'en_revision',
            'aprobada',
            'rechazada',
            'pagada'
        ) NOT NULL DEFAULT 'pendiente'
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # No se puede eliminar valores de un enum en PostgreSQL fácilmente
    # Se requeriría recrear el enum, lo cual es complejo
    pass
