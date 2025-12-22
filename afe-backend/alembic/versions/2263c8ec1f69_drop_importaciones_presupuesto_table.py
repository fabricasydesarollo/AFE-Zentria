"""drop_importaciones_presupuesto_table

Revision ID: 2263c8ec1f69
Revises: 187d4c86be43
Create Date: 2025-10-09 10:49:41.506077

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '2263c8ec1f69'
down_revision: Union[str, Sequence[str], None] = '187d4c86be43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Elimina tabla importaciones_presupuesto y su foreign key en lineas_presupuesto.

    Razón: Se eliminó el modelo ImportacionPresupuesto y todas sus referencias.
    """
    # Primero eliminar la foreign key constraint en lineas_presupuesto
    # El nombre exacto puede variar (ibfk_1, ibfk_4, etc)
    op.drop_constraint('lineas_presupuesto_ibfk_4', 'lineas_presupuesto', type_='foreignkey')

    # Eliminar la columna importacion_id de lineas_presupuesto
    op.drop_column('lineas_presupuesto', 'importacion_id')

    # Eliminar índices de importaciones_presupuesto
    op.drop_index('idx_importaciones_fecha', table_name='importaciones_presupuesto')
    op.drop_index('idx_importaciones_usuario', table_name='importaciones_presupuesto')
    op.drop_index('idx_importaciones_estado', table_name='importaciones_presupuesto')
    op.drop_index('idx_importaciones_año', table_name='importaciones_presupuesto')

    # Eliminar tabla importaciones_presupuesto
    op.drop_table('importaciones_presupuesto')


def downgrade() -> None:
    """
    Recrea tabla importaciones_presupuesto y restaura foreign key.
    """
    # Recrear tabla importaciones_presupuesto
    op.create_table(
        'importaciones_presupuesto',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('archivo_nombre', sa.String(500), nullable=False),
        sa.Column('archivo_hash', sa.String(64), nullable=True),
        sa.Column('archivo_tamaño', sa.BigInteger(), nullable=True),
        sa.Column('año', sa.BigInteger(), nullable=False),
        sa.Column('mes_inicio', sa.BigInteger(), nullable=True),
        sa.Column('mes_fin', sa.BigInteger(), nullable=True),
        sa.Column('estado', sa.Enum('PENDIENTE', 'PROCESANDO', 'COMPLETADO', 'ERROR', name='estadoimportacion'),
                  nullable=False, server_default='PENDIENTE'),
        sa.Column('fecha_inicio', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('fecha_fin', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tiempo_procesamiento_segundos', sa.Numeric(10, 2), nullable=True),
        sa.Column('usuario_importador', sa.String(100), nullable=False),
        sa.Column('descripcion', sa.String(1000), nullable=True),
        sa.Column('total_lineas_presupuesto', sa.BigInteger(), server_default='0'),
        sa.Column('total_facturas_comparadas', sa.BigInteger(), server_default='0'),
        sa.Column('total_facturas_encontradas', sa.BigInteger(), server_default='0'),
        sa.Column('total_facturas_faltantes', sa.BigInteger(), server_default='0'),
        sa.Column('total_desviaciones', sa.BigInteger(), server_default='0'),
        sa.Column('presupuesto_total', sa.Numeric(20, 2), server_default='0'),
        sa.Column('ejecucion_total', sa.Numeric(20, 2), server_default='0'),
        sa.Column('desviacion_global', sa.Numeric(20, 2), server_default='0'),
        sa.Column('porcentaje_ejecucion', sa.Numeric(5, 2), server_default='0'),
        sa.Column('reporte_completo', mysql.JSON(), nullable=True),
        sa.Column('errores', mysql.JSON(), nullable=True),
        sa.Column('advertencias', mysql.JSON(), nullable=True),
        sa.Column('config_importacion', mysql.JSON(), nullable=True),
        sa.Column('pdf_generado', sa.Boolean(), server_default='0'),
        sa.Column('pdf_ruta', sa.String(500), nullable=True),
        sa.Column('excel_resultado_ruta', sa.String(500), nullable=True),
        sa.Column('email_enviado', sa.Boolean(), server_default='0'),
        sa.Column('email_destino', sa.String(500), nullable=True),
        sa.Column('email_fecha_envio', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Recrear índices
    op.create_index('idx_importaciones_año', 'importaciones_presupuesto', ['año'])
    op.create_index('idx_importaciones_estado', 'importaciones_presupuesto', ['estado'])
    op.create_index('idx_importaciones_usuario', 'importaciones_presupuesto', ['usuario_importador'])
    op.create_index('idx_importaciones_fecha', 'importaciones_presupuesto', ['creado_en'])

    # Recrear columna importacion_id en lineas_presupuesto
    op.add_column('lineas_presupuesto',
        sa.Column('importacion_id', sa.BigInteger(), nullable=True)
    )

    # Recrear foreign key
    op.create_foreign_key(
        'lineas_presupuesto_ibfk_1',
        'lineas_presupuesto', 'importaciones_presupuesto',
        ['importacion_id'], ['id'],
        ondelete='SET NULL'
    )
