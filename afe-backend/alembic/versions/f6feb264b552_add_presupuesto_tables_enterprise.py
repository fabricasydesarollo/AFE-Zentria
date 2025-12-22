"""add_presupuesto_tables_enterprise

Revision ID: f6feb264b552
Revises: 757c660b2207
Create Date: 2025-10-04 17:20:03.383680

Crea sistema empresarial de control presupuestal con:
- Tabla lineas_presupuesto: Presupuesto planeado
- Tabla ejecuciones_presupuestales: Vinculación con facturas reales
- Workflow de aprobaciones multinivel
- Sistema de alertas y desviaciones

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'f6feb264b552'
down_revision: Union[str, Sequence[str], None] = '6a652d604685'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crea tablas del sistema de control presupuestal empresarial.
    """

    # ========== TABLA 1: LÍNEAS PRESUPUESTO ==========
    op.create_table(
        'lineas_presupuesto',

        # Identificación
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('año', sa.BigInteger(), nullable=False),
        sa.Column('codigo_linea', sa.String(50), nullable=False),
        sa.Column('nombre_cuenta', sa.String(500), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),

        # Clasificación
        sa.Column('tipo_linea', sa.Enum('OPEX', 'CAPEX', 'SERVICIOS', 'LICENCIAS', 'MANTENIMIENTO', 'CONSULTORIA',
                                        name='tipolineapresupuesto'), nullable=False, server_default='OPEX'),
        sa.Column('area', sa.String(100), nullable=True),
        sa.Column('centro_costo', sa.String(50), nullable=True),

        # Responsables
        sa.Column('responsable_id', sa.BigInteger(), nullable=True),
        sa.Column('responsable_backup_id', sa.BigInteger(), nullable=True),

        # Proveedor
        sa.Column('proveedor_id', sa.BigInteger(), nullable=True),

        # Presupuesto mensual (12 meses)
        sa.Column('presupuesto_ene', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('presupuesto_feb', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('presupuesto_mar', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('presupuesto_abr', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('presupuesto_may', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('presupuesto_jun', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('presupuesto_jul', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('presupuesto_ago', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('presupuesto_sep', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('presupuesto_oct', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('presupuesto_nov', sa.Numeric(15, 2), nullable=False, server_default='0'),
        sa.Column('presupuesto_dic', sa.Numeric(15, 2), nullable=False, server_default='0'),

        # Totales calculados
        sa.Column('presupuesto_anual', sa.Numeric(20, 2), nullable=False),
        sa.Column('ejecutado_acumulado', sa.Numeric(20, 2), nullable=False, server_default='0'),
        sa.Column('saldo_disponible', sa.Numeric(20, 2), nullable=False),
        sa.Column('porcentaje_ejecucion', sa.Numeric(5, 2), nullable=False, server_default='0'),

        # Estado
        sa.Column('estado', sa.Enum('BORRADOR', 'APROBADO', 'ACTIVO', 'SUSPENDIDO', 'CERRADO', 'CANCELADO',
                                    name='estadolineapresupuesto'), nullable=False, server_default='BORRADOR'),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='1'),

        # Aprobaciones
        sa.Column('fecha_aprobacion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('aprobado_por', sa.String(100), nullable=True),
        sa.Column('observaciones_aprobacion', sa.Text(), nullable=True),

        # Alertas
        sa.Column('umbral_alerta_porcentaje', sa.Numeric(5, 2), nullable=False, server_default='90.0'),
        sa.Column('requiere_aprobacion_sobre_ejecucion', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('nivel_aprobacion_requerido',
                  sa.Enum('RESPONSABLE_LINEA', 'JEFE_AREA', 'GERENCIA_FINANCIERA', 'GERENCIA_GENERAL', 'CFO', 'CEO',
                          name='nivelaprobacion'), nullable=False, server_default='RESPONSABLE_LINEA'),

        # Metadata importación
        sa.Column('importacion_id', sa.BigInteger(), nullable=True),
        sa.Column('fila_excel_origen', sa.BigInteger(), nullable=True),

        # Versionamiento
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('version_anterior_id', sa.BigInteger(), nullable=True),

        # Timestamps
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('creado_por', sa.String(100), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('actualizado_por', sa.String(100), nullable=True),

        # Primary Key
        sa.PrimaryKeyConstraint('id'),

        # Foreign Keys
        sa.ForeignKeyConstraint(['responsable_id'], ['responsables.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['responsable_backup_id'], ['responsables.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['proveedor_id'], ['proveedores.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['importacion_id'], ['importaciones_presupuesto.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['version_anterior_id'], ['lineas_presupuesto.id'], ondelete='SET NULL'),

        # Unique Constraints
        sa.UniqueConstraint('año', 'codigo_linea', name='uix_año_codigo_linea'),

        # Check Constraints
        sa.CheckConstraint('presupuesto_anual >= 0', name='chk_presupuesto_positivo'),
        sa.CheckConstraint('ejecutado_acumulado >= 0', name='chk_ejecutado_positivo'),
        sa.CheckConstraint('porcentaje_ejecucion >= 0 AND porcentaje_ejecucion <= 999', name='chk_porcentaje_rango'),
    )

    # Índices para lineas_presupuesto
    op.create_index('idx_lineas_año', 'lineas_presupuesto', ['año'])
    op.create_index('idx_lineas_estado', 'lineas_presupuesto', ['estado'])
    op.create_index('idx_lineas_area', 'lineas_presupuesto', ['area'])
    op.create_index('idx_lineas_responsable', 'lineas_presupuesto', ['responsable_id'])
    op.create_index('idx_lineas_codigo', 'lineas_presupuesto', ['codigo_linea'])


    # ========== TABLA 2: EJECUCIONES PRESUPUESTALES ==========
    op.create_table(
        'ejecuciones_presupuestales',

        # Identificación
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),

        # Vinculación
        sa.Column('linea_presupuesto_id', sa.BigInteger(), nullable=False),
        sa.Column('factura_id', sa.BigInteger(), nullable=False),

        # Período
        sa.Column('año', sa.BigInteger(), nullable=False),
        sa.Column('mes', sa.BigInteger(), nullable=False),
        sa.Column('periodo', sa.String(7), nullable=False),

        # Valores
        sa.Column('valor_presupuestado', sa.Numeric(15, 2), nullable=False),
        sa.Column('valor_factura', sa.Numeric(15, 2), nullable=False),
        sa.Column('valor_imputado', sa.Numeric(15, 2), nullable=False),

        # Desviación
        sa.Column('desviacion', sa.Numeric(15, 2), nullable=False),
        sa.Column('desviacion_porcentaje', sa.Numeric(8, 4), nullable=False),
        sa.Column('tipo_desviacion',
                  sa.Enum('DENTRO_RANGO', 'BAJO_PRESUPUESTO', 'SOBRE_PRESUPUESTO_LEVE',
                          'SOBRE_PRESUPUESTO_MODERADO', 'SOBRE_PRESUPUESTO_CRITICO',
                          name='tipodesviacion'), nullable=False),

        # Estado
        sa.Column('estado',
                  sa.Enum('PENDIENTE_VINCULACION', 'VINCULADO', 'PENDIENTE_APROBACION',
                          'APROBADO', 'RECHAZADO', 'OBSERVADO',
                          name='estadoejecucion'), nullable=False, server_default='PENDIENTE_VINCULACION'),

        # Vinculación automática
        sa.Column('vinculacion_automatica', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('confianza_vinculacion', sa.Numeric(3, 2), nullable=True),
        sa.Column('criterios_matching', mysql.JSON(), nullable=True),

        # Aprobaciones
        sa.Column('requiere_aprobacion', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('nivel_aprobacion_requerido',
                  sa.Enum('RESPONSABLE_LINEA', 'JEFE_AREA', 'GERENCIA_FINANCIERA', 'GERENCIA_GENERAL', 'CFO', 'CEO',
                          name='nivelaprobacion'), nullable=True),

        # Aprobación Nivel 1
        sa.Column('aprobado_nivel1', sa.Boolean(), server_default='0'),
        sa.Column('aprobador_nivel1', sa.String(100), nullable=True),
        sa.Column('fecha_aprobacion_nivel1', sa.DateTime(timezone=True), nullable=True),
        sa.Column('observaciones_nivel1', sa.Text(), nullable=True),

        # Aprobación Nivel 2
        sa.Column('aprobado_nivel2', sa.Boolean(), server_default='0'),
        sa.Column('aprobador_nivel2', sa.String(100), nullable=True),
        sa.Column('fecha_aprobacion_nivel2', sa.DateTime(timezone=True), nullable=True),
        sa.Column('observaciones_nivel2', sa.Text(), nullable=True),

        # Aprobación Nivel 3
        sa.Column('aprobado_nivel3', sa.Boolean(), server_default='0'),
        sa.Column('aprobador_nivel3', sa.String(100), nullable=True),
        sa.Column('fecha_aprobacion_nivel3', sa.DateTime(timezone=True), nullable=True),
        sa.Column('observaciones_nivel3', sa.Text(), nullable=True),

        # Rechazo
        sa.Column('motivo_rechazo', sa.Text(), nullable=True),
        sa.Column('rechazado_por', sa.String(100), nullable=True),
        sa.Column('fecha_rechazo', sa.DateTime(timezone=True), nullable=True),

        # Observaciones
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('justificacion_desviacion', sa.Text(), nullable=True),

        # Alertas
        sa.Column('alerta_generada', sa.Boolean(), server_default='0'),
        sa.Column('tipo_alerta', sa.String(50), nullable=True),
        sa.Column('notificacion_enviada', sa.Boolean(), server_default='0'),
        sa.Column('destinatarios_notificacion', mysql.JSON(), nullable=True),

        # Timestamps
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('creado_por', sa.String(100), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('actualizado_por', sa.String(100), nullable=True),

        # Primary Key
        sa.PrimaryKeyConstraint('id'),

        # Foreign Keys
        sa.ForeignKeyConstraint(['linea_presupuesto_id'], ['lineas_presupuesto.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['factura_id'], ['facturas.id'], ondelete='RESTRICT'),

        # Unique Constraints
        sa.UniqueConstraint('linea_presupuesto_id', 'factura_id', name='uix_linea_factura'),

        # Check Constraints
        sa.CheckConstraint('valor_imputado > 0', name='chk_valor_imputado_positivo'),
        sa.CheckConstraint('mes >= 1 AND mes <= 12', name='chk_mes_valido'),
    )

    # Índices para ejecuciones_presupuestales
    op.create_index('idx_ejecuciones_linea', 'ejecuciones_presupuestales', ['linea_presupuesto_id'])
    op.create_index('idx_ejecuciones_factura', 'ejecuciones_presupuestales', ['factura_id'])
    op.create_index('idx_ejecuciones_periodo', 'ejecuciones_presupuestales', ['periodo'])
    op.create_index('idx_ejecuciones_año', 'ejecuciones_presupuestales', ['año'])
    op.create_index('idx_ejecuciones_estado', 'ejecuciones_presupuestales', ['estado'])
    op.create_index('idx_ejecuciones_desviacion', 'ejecuciones_presupuestales', ['tipo_desviacion'])


def downgrade() -> None:
    """
    Revierte la creación de las tablas de presupuesto.
    """
    # Eliminar índices de ejecuciones
    op.drop_index('idx_ejecuciones_desviacion', table_name='ejecuciones_presupuestales')
    op.drop_index('idx_ejecuciones_estado', table_name='ejecuciones_presupuestales')
    op.drop_index('idx_ejecuciones_año', table_name='ejecuciones_presupuestales')
    op.drop_index('idx_ejecuciones_periodo', table_name='ejecuciones_presupuestales')
    op.drop_index('idx_ejecuciones_factura', table_name='ejecuciones_presupuestales')
    op.drop_index('idx_ejecuciones_linea', table_name='ejecuciones_presupuestales')

    # Eliminar tabla ejecuciones
    op.drop_table('ejecuciones_presupuestales')

    # Eliminar índices de líneas
    op.drop_index('idx_lineas_codigo', table_name='lineas_presupuesto')
    op.drop_index('idx_lineas_responsable', table_name='lineas_presupuesto')
    op.drop_index('idx_lineas_area', table_name='lineas_presupuesto')
    op.drop_index('idx_lineas_estado', table_name='lineas_presupuesto')
    op.drop_index('idx_lineas_año', table_name='lineas_presupuesto')

    # Eliminar tabla líneas
    op.drop_table('lineas_presupuesto')
