"""fix_multiple_responsables_per_nit

Revision ID: c9b4479ff345
Revises: 6060d9a9969f
Create Date: 2025-10-19 23:05:54.082983

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9b4479ff345'
down_revision: Union[str, Sequence[str], None] = '6060d9a9969f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Permite que un mismo NIT pueda ser asignado a múltiples responsables.

    Cambios:
    1. Elimina UNIQUE constraint en columna 'nit'
    2. Agrega UNIQUE constraint compuesto (nit, responsable_id)

    Esto permite:
    - Un NIT puede tener múltiples responsables
    - Pero NO puede haber duplicados de la misma combinación
    """
    # 1. Eliminar el constraint UNIQUE de la columna 'nit'
    op.drop_constraint('nit', 'asignacion_nit_responsable', type_='unique')

    # 2. Crear constraint UNIQUE compuesto (nit, responsable_id)
    op.create_unique_constraint(
        'uq_nit_responsable',
        'asignacion_nit_responsable',
        ['nit', 'responsable_id']
    )


def downgrade() -> None:
    """Revertir cambios: volver a constraint UNIQUE en 'nit'."""
    # 1. Eliminar constraint compuesto
    op.drop_constraint('uq_nit_responsable', 'asignacion_nit_responsable', type_='unique')

    # 2. Recrear constraint UNIQUE en columna 'nit'
    op.create_unique_constraint('nit', 'asignacion_nit_responsable', ['nit'])
