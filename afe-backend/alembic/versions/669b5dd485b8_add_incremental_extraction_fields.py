"""add_incremental_extraction_fields

Revision ID: 669b5dd485b8
Revises: a7fc9998a49f
Create Date: 2025-10-13 19:58:44.150144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '669b5dd485b8'
down_revision: Union[str, Sequence[str], None] = 'a7fc9998a49f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migración a extracción incremental profesional.

    Cambios:
    1. Agrega campos para extracción incremental (ultima_ejecucion_exitosa, etc.)
    2. Renombra fetch_limit → max_correos_por_ejecucion (más claro)
    3. Renombra fetch_days → ventana_inicial_dias (más claro)
    4. Actualiza valores por defecto (500→10000, 90→30)
    5. Agrega campos de rastreo en historial_extracciones
    """

    # ============================================================================
    # TABLA: cuentas_correo
    # ============================================================================

    # 1. Agregar nuevos campos de extracción incremental
    op.add_column('cuentas_correo',
        sa.Column('ultima_ejecucion_exitosa', sa.DateTime(timezone=True), nullable=True,
                  comment='Última ejecución exitosa (para extracción incremental)'))

    op.add_column('cuentas_correo',
        sa.Column('fecha_ultimo_correo_procesado', sa.DateTime(timezone=True), nullable=True,
                  comment='Timestamp del último correo procesado'))

    # 2. Eliminar constraints PRIMERO (MySQL requiere esto antes de renombrar)
    op.drop_constraint('check_fetch_limit_range', 'cuentas_correo', type_='check')
    op.drop_constraint('check_fetch_days_range', 'cuentas_correo', type_='check')

    # 3. Renombrar campos existentes para mayor claridad
    # MySQL no soporta ALTER COLUMN RENAME directamente, usamos CHANGE COLUMN
    op.execute("""
        ALTER TABLE cuentas_correo
        CHANGE COLUMN fetch_limit max_correos_por_ejecucion INT NOT NULL DEFAULT 10000
        COMMENT 'Límite de seguridad por ejecución (no arbitrario)'
    """)

    op.execute("""
        ALTER TABLE cuentas_correo
        CHANGE COLUMN fetch_days ventana_inicial_dias INT NOT NULL DEFAULT 30
        COMMENT 'Días hacia atrás en primera ejecución'
    """)

    # 4. Actualizar valores existentes a los nuevos por defecto
    op.execute("""
        UPDATE cuentas_correo
        SET max_correos_por_ejecucion = 10000
        WHERE max_correos_por_ejecucion = 500
    """)

    op.execute("""
        UPDATE cuentas_correo
        SET ventana_inicial_dias = 30
        WHERE ventana_inicial_dias = 90
    """)

    # 5. Agregar nuevos constraints
    op.create_check_constraint(
        'check_max_correos_range',
        'cuentas_correo',
        'max_correos_por_ejecucion > 0 AND max_correos_por_ejecucion <= 100000'
    )

    op.create_check_constraint(
        'check_ventana_inicial_range',
        'cuentas_correo',
        'ventana_inicial_dias > 0 AND ventana_inicial_dias <= 365'
    )

    # ============================================================================
    # TABLA: historial_extracciones
    # ============================================================================

    # Agregar campos de rastreo incremental
    op.add_column('historial_extracciones',
        sa.Column('fecha_desde', sa.DateTime(timezone=True), nullable=True,
                  comment='Fecha desde la cual se extrajeron correos'))

    op.add_column('historial_extracciones',
        sa.Column('fecha_hasta', sa.DateTime(timezone=True), nullable=True,
                  comment='Fecha hasta la cual se extrajeron correos'))

    op.add_column('historial_extracciones',
        sa.Column('es_primera_ejecucion', sa.Boolean(), nullable=False, server_default='0',
                  comment='Si fue la primera ejecución de esta cuenta'))

    # Agregar índice para búsquedas por cuenta y fecha
    op.create_index('idx_historial_cuenta_fecha', 'historial_extracciones',
                   ['cuenta_correo_id', 'fecha_ejecucion'])


def downgrade() -> None:
    """
    Rollback a la versión anterior.
    """

    # ============================================================================
    # TABLA: historial_extracciones - Revertir
    # ============================================================================

    op.drop_index('idx_historial_cuenta_fecha', 'historial_extracciones')
    op.drop_column('historial_extracciones', 'es_primera_ejecucion')
    op.drop_column('historial_extracciones', 'fecha_hasta')
    op.drop_column('historial_extracciones', 'fecha_desde')

    # ============================================================================
    # TABLA: cuentas_correo - Revertir
    # ============================================================================

    # Eliminar constraints nuevos
    op.drop_constraint('check_ventana_inicial_range', 'cuentas_correo', type_='check')
    op.drop_constraint('check_max_correos_range', 'cuentas_correo', type_='check')

    # Revertir valores a los antiguos
    op.execute("""
        UPDATE cuentas_correo
        SET max_correos_por_ejecucion = 500
        WHERE max_correos_por_ejecucion = 10000
    """)

    op.execute("""
        UPDATE cuentas_correo
        SET ventana_inicial_dias = 90
        WHERE ventana_inicial_dias = 30
    """)

    # Renombrar columnas de vuelta
    op.execute("""
        ALTER TABLE cuentas_correo
        CHANGE COLUMN max_correos_por_ejecucion fetch_limit INT NOT NULL DEFAULT 500
        COMMENT 'Límite de correos a extraer por ejecución'
    """)

    op.execute("""
        ALTER TABLE cuentas_correo
        CHANGE COLUMN ventana_inicial_dias fetch_days INT NOT NULL DEFAULT 90
        COMMENT 'Días hacia atrás para buscar correos'
    """)

    # Restaurar constraints antiguos
    op.create_check_constraint(
        'check_fetch_limit_range',
        'cuentas_correo',
        'fetch_limit > 0 AND fetch_limit <= 1000'
    )

    op.create_check_constraint(
        'check_fetch_days_range',
        'cuentas_correo',
        'fetch_days > 0 AND fetch_days <= 365'
    )

    # Eliminar campos de extracción incremental
    op.drop_column('cuentas_correo', 'fecha_ultimo_correo_procesado')
    op.drop_column('cuentas_correo', 'ultima_ejecucion_exitosa')
