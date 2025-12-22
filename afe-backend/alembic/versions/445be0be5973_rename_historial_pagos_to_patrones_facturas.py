"""rename_historial_pagos_to_patrones_facturas

Revision ID: 445be0be5974
Revises: 445be0be5973
Create Date: 2025-11-26 10:00:00.000000

Renombra tabla historial_pagos a patrones_facturas para claridad semántica.

RAZÓN DEL CAMBIO:
- El nombre historial_pagos implica tracking de transacciones de pago
- En realidad es análisis estadístico de patrones de facturas
- No realiza pagos, solo análisis para recomendaciones de aprobación automática
- El nuevo nombre patrones_facturas es semanticamente correcto y evita confusión
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '445be0be5974'
down_revision: Union[str, Sequence[str], None] = '445be0be5973'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Renombra tabla historial_pagos a patrones_facturas."""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    # Verificar que la tabla existe antes de renombrar
    if 'historial_pagos' not in inspector.get_table_names():
        print("Tabla historial_pagos no existe, saltando renombrado")
        return

    # Renombrar tabla
    op.rename_table('historial_pagos', 'patrones_facturas')
    print("Tabla historial_pagos renombrada a patrones_facturas exitosamente")


def downgrade() -> None:
    """Revierte el renombrado de patrones_facturas a historial_pagos."""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    # Verificar que la tabla existe antes de renombrar
    if 'patrones_facturas' not in inspector.get_table_names():
        print("Tabla patrones_facturas no existe, saltando downgrade")
        return

    # Renombrar tabla de vuelta
    op.rename_table('patrones_facturas', 'historial_pagos')
    print("Tabla patrones_facturas renombrada a historial_pagos exitosamente")
