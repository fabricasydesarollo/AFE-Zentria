"""add_importaciones_presupuesto_table

Revision ID: 757c660b2207
Revises: 6a652d604685
Create Date: 2025-10-04 16:09:08.760483

IMPORTANTE: Revision corregida a 6a652d604685 (sin particionamiento fallido)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '757c660b2207'
down_revision: Union[str, Sequence[str], None] = '129ab8035fa8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crea tabla de auditoría para importaciones presupuestales.

    Esta tabla registra cada importación de archivo Excel/CSV para
    comparación presupuestal, incluyendo métricas y resultados.
    """
    op.create_table(
        'importaciones_presupuesto',

        # Identificación
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('archivo_nombre', sa.String(500), nullable=False),
        sa.Column('archivo_hash', sa.String(64), nullable=True),
        sa.Column('archivo_tamaño', sa.BigInteger(), nullable=True),

        # Período
        sa.Column('año', sa.BigInteger(), nullable=False),
        sa.Column('mes_inicio', sa.BigInteger(), nullable=True),
        sa.Column('mes_fin', sa.BigInteger(), nullable=True),

        # Estado
        sa.Column('estado', sa.Enum('PENDIENTE', 'PROCESANDO', 'COMPLETADO', 'ERROR', name='estadoimportacion'),
                  nullable=False, server_default='PENDIENTE'),
        sa.Column('fecha_inicio', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('fecha_fin', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tiempo_procesamiento_segundos', sa.Numeric(10, 2), nullable=True),

        # Usuario
        sa.Column('usuario_importador', sa.String(100), nullable=False),
        sa.Column('descripcion', sa.String(1000), nullable=True),

        # Resultados numéricos
        sa.Column('total_lineas_presupuesto', sa.BigInteger(), server_default='0'),
        sa.Column('total_facturas_comparadas', sa.BigInteger(), server_default='0'),
        sa.Column('total_facturas_encontradas', sa.BigInteger(), server_default='0'),
        sa.Column('total_facturas_faltantes', sa.BigInteger(), server_default='0'),
        sa.Column('total_desviaciones', sa.BigInteger(), server_default='0'),

        # Resultados financieros
        sa.Column('presupuesto_total', sa.Numeric(20, 2), server_default='0'),
        sa.Column('ejecucion_total', sa.Numeric(20, 2), server_default='0'),
        sa.Column('desviacion_global', sa.Numeric(20, 2), server_default='0'),
        sa.Column('porcentaje_ejecucion', sa.Numeric(5, 2), server_default='0'),

        # JSON data
        sa.Column('reporte_completo', mysql.JSON(), nullable=True),
        sa.Column('errores', mysql.JSON(), nullable=True),
        sa.Column('advertencias', mysql.JSON(), nullable=True),
        sa.Column('config_importacion', mysql.JSON(), nullable=True),

        # Archivos generados
        sa.Column('pdf_generado', sa.Boolean(), server_default='0'),
        sa.Column('pdf_ruta', sa.String(500), nullable=True),
        sa.Column('excel_resultado_ruta', sa.String(500), nullable=True),

        # Email
        sa.Column('email_enviado', sa.Boolean(), server_default='0'),
        sa.Column('email_destino', sa.String(500), nullable=True),
        sa.Column('email_fecha_envio', sa.DateTime(timezone=True), nullable=True),

        # Metadata
        sa.Column('notas', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.PrimaryKeyConstraint('id')
    )

    # Índices para búsquedas eficientes
    op.create_index('idx_importaciones_año', 'importaciones_presupuesto', ['año'])
    op.create_index('idx_importaciones_estado', 'importaciones_presupuesto', ['estado'])
    op.create_index('idx_importaciones_usuario', 'importaciones_presupuesto', ['usuario_importador'])
    op.create_index('idx_importaciones_fecha', 'importaciones_presupuesto', ['creado_en'])


def downgrade() -> None:
    """Revierte la creación de la tabla."""
    op.drop_index('idx_importaciones_fecha', table_name='importaciones_presupuesto')
    op.drop_index('idx_importaciones_usuario', table_name='importaciones_presupuesto')
    op.drop_index('idx_importaciones_estado', table_name='importaciones_presupuesto')
    op.drop_index('idx_importaciones_año', table_name='importaciones_presupuesto')
    op.drop_table('importaciones_presupuesto')
