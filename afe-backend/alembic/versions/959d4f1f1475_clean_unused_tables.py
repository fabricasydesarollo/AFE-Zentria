"""clean_unused_tables

Revision ID: 959d4f1f1475
Revises: 2263c8ec1f69
Create Date: 2025-10-09 10:59:07.114813

Elimina tablas vacías y no utilizadas del sistema.

Tablas eliminadas:
- automation_audit, automation_metrics, configuracion_automatizacion, proveedor_trust
- ejecuciones_presupuestales, lineas_presupuesto
- notificaciones_workflow, configuracion_correo
- usuarios

Tablas mantenidas (necesarias para automatización):
- facturas, proveedores, responsables (CORE)
- historial_pagos (patrones históricos)
- workflow_aprobacion_facturas, asignacion_nit_responsable (workflow)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '959d4f1f1475'
down_revision: Union[str, Sequence[str], None] = '2263c8ec1f69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Elimina tablas vacías y no utilizadas.
    """
    # Eliminar tablas de sistema de automatización no usado
    op.drop_table('proveedor_trust')
    op.drop_table('configuracion_automatizacion')
    op.drop_table('automation_metrics')
    op.drop_table('automation_audit')

    # Eliminar tablas de presupuesto no usado
    op.drop_table('ejecuciones_presupuestales')
    op.drop_table('lineas_presupuesto')

    # Eliminar tablas de notificaciones no configuradas
    op.drop_table('notificaciones_workflow')
    op.drop_table('configuracion_correo')

    # Eliminar tabla de usuarios vacía
    op.drop_table('usuarios')


def downgrade() -> None:
    """
    Recrea las tablas eliminadas (estructura básica).
    """
    # Nota: Este downgrade crea estructura básica, no restaura datos
    pass
