"""add automation tables

Revision ID: 7bad075511e9
Revises: 05b5bdfbca40
Create Date: 2025-10-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '7bad075511e9'
down_revision = '05b5bdfbca40'
branch_labels = None
depends_on = None


def upgrade():
    """
    Crea las tablas necesarias para el sistema de automatización inteligente.
    """

    # Tabla: automation_audit
    op.create_table(
        'automation_audit',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('factura_id', sa.BigInteger(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('confianza', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('motivo', sa.Text(), nullable=False),
        sa.Column('patron_detectado', sa.String(length=50), nullable=True),
        sa.Column('factura_referencia_id', sa.BigInteger(), nullable=True),
        sa.Column('criterios_evaluados', mysql.JSON(), nullable=True),
        sa.Column('configuracion_utilizada', mysql.JSON(), nullable=True),
        sa.Column('metadata', mysql.JSON(), nullable=True),
        sa.Column('version_algoritmo', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('proveedor_nit', sa.String(length=20), nullable=True),
        sa.Column('proveedor_nombre', sa.String(length=500), nullable=True),
        sa.Column('monto_factura', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('requirio_accion_manual', sa.Boolean(), server_default='0'),
        sa.Column('override_manual', sa.Boolean(), server_default='0'),
        sa.Column('override_por', sa.String(length=100), nullable=True),
        sa.Column('override_razon', sa.String(length=1000), nullable=True),
        sa.Column('override_fecha', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resultado_final', sa.String(length=50), nullable=True),
        sa.Column('tiempo_procesamiento_ms', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['factura_id'], ['facturas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['factura_referencia_id'], ['facturas.id'], ondelete='SET NULL')
    )

    # Índices para automation_audit
    op.create_index('ix_automation_audit_factura_id', 'automation_audit', ['factura_id'])
    op.create_index('ix_automation_audit_timestamp', 'automation_audit', ['timestamp'])
    op.create_index('ix_automation_audit_decision', 'automation_audit', ['decision'])
    op.create_index('ix_automation_audit_proveedor_nit', 'automation_audit', ['proveedor_nit'])
    op.create_index('ix_automation_audit_requirio_accion', 'automation_audit', ['requirio_accion_manual'])
    op.create_index('ix_automation_audit_resultado_final', 'automation_audit', ['resultado_final'])


    # Tabla: automation_metrics
    op.create_table(
        'automation_metrics',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('periodo', sa.String(length=20), nullable=False),
        sa.Column('fecha_calculo', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('total_facturas_procesadas', sa.BigInteger(), server_default='0'),
        sa.Column('total_aprobadas_automaticamente', sa.BigInteger(), server_default='0'),
        sa.Column('total_enviadas_revision', sa.BigInteger(), server_default='0'),
        sa.Column('total_rechazadas', sa.BigInteger(), server_default='0'),
        sa.Column('tasa_automatizacion', sa.Numeric(precision=5, scale=2), server_default='0.0'),
        sa.Column('tasa_precision', sa.Numeric(precision=5, scale=2), server_default='0.0'),
        sa.Column('tiempo_promedio_procesamiento_ms', sa.BigInteger(), nullable=True),
        sa.Column('tiempo_minimo_procesamiento_ms', sa.BigInteger(), nullable=True),
        sa.Column('tiempo_maximo_procesamiento_ms', sa.BigInteger(), nullable=True),
        sa.Column('confianza_promedio', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('patrones_detectados', mysql.JSON(), nullable=True),
        sa.Column('total_proveedores_procesados', sa.BigInteger(), server_default='0'),
        sa.Column('top_proveedores', mysql.JSON(), nullable=True),
        sa.Column('monto_total_procesado', sa.Numeric(precision=20, scale=2), server_default='0.0'),
        sa.Column('monto_total_aprobado_auto', sa.Numeric(precision=20, scale=2), server_default='0.0'),
        sa.Column('total_errores', sa.BigInteger(), server_default='0'),
        sa.Column('errores_detalle', mysql.JSON(), nullable=True),
        sa.Column('metadata', mysql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Índices para automation_metrics
    op.create_index('ix_automation_metrics_periodo', 'automation_metrics', ['periodo'])


    # Tabla: configuracion_automatizacion
    op.create_table(
        'configuracion_automatizacion',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('clave', sa.String(length=100), nullable=False),
        sa.Column('valor', mysql.JSON(), nullable=False),
        sa.Column('tipo_dato', sa.String(length=50), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('valor_minimo', mysql.JSON(), nullable=True),
        sa.Column('valor_maximo', mysql.JSON(), nullable=True),
        sa.Column('valores_permitidos', mysql.JSON(), nullable=True),
        sa.Column('categoria', sa.String(length=100), nullable=True),
        sa.Column('activa', sa.Boolean(), server_default='1'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actualizado_por', sa.String(length=100), nullable=True),
        sa.Column('version', sa.BigInteger(), server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('clave')
    )

    # Índices para configuracion_automatizacion
    op.create_index('ix_configuracion_automatizacion_clave', 'configuracion_automatizacion', ['clave'])
    op.create_index('ix_configuracion_automatizacion_categoria', 'configuracion_automatizacion', ['categoria'])


    # Tabla: proveedor_trust
    op.create_table(
        'proveedor_trust',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('proveedor_id', sa.BigInteger(), nullable=False),
        sa.Column('trust_score', sa.Numeric(precision=5, scale=4), nullable=False, server_default='0.5000'),
        sa.Column('nivel_confianza', sa.String(length=20), nullable=False, server_default='medio'),
        sa.Column('total_facturas', sa.BigInteger(), server_default='0'),
        sa.Column('facturas_aprobadas', sa.BigInteger(), server_default='0'),
        sa.Column('facturas_rechazadas', sa.BigInteger(), server_default='0'),
        sa.Column('facturas_aprobadas_auto', sa.BigInteger(), server_default='0'),
        sa.Column('tasa_aprobacion', sa.Numeric(precision=5, scale=2), server_default='0.0'),
        sa.Column('tasa_automatizacion_exitosa', sa.Numeric(precision=5, scale=2), server_default='0.0'),
        sa.Column('historial_confianza', mysql.JSON(), nullable=True),
        sa.Column('patrones_recurrentes', mysql.JSON(), nullable=True),
        sa.Column('bloqueado', sa.Boolean(), server_default='0'),
        sa.Column('motivo_bloqueo', sa.Text(), nullable=True),
        sa.Column('bloqueado_por', sa.String(length=100), nullable=True),
        sa.Column('bloqueado_en', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requiere_revision_siempre', sa.Boolean(), server_default='0'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['proveedor_id'], ['proveedores.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('proveedor_id')
    )

    # Índices para proveedor_trust
    op.create_index('ix_proveedor_trust_proveedor_id', 'proveedor_trust', ['proveedor_id'])


    # Insertar configuraciones por defecto
    op.execute("""
        INSERT INTO configuracion_automatizacion (clave, valor, tipo_dato, descripcion, categoria)
        VALUES
        ('confianza_minima_aprobacion', '0.85', 'float', 'Score mínimo para aprobación automática (0.0-1.0)', 'decision_engine'),
        ('confianza_minima_revision', '0.40', 'float', 'Score mínimo para enviar a revisión (0.0-1.0)', 'decision_engine'),
        ('dias_historico_patron', '90', 'int', 'Días de historial para detección de patrones', 'pattern_detector'),
        ('variacion_monto_permitida', '0.20', 'float', 'Variación de monto permitida (0.0-1.0 = 0%-100%)', 'pattern_detector'),
        ('max_monto_aprobacion_automatica', '50000000', 'int', 'Monto máximo para aprobación automática (COP)', 'decision_engine'),
        ('procesamiento_automatico_activo', 'true', 'bool', 'Si el procesamiento automático está activo', 'general'),
        ('notificaciones_activas', 'true', 'bool', 'Si las notificaciones están activas', 'notificaciones')
    """)


def downgrade():
    """
    Elimina las tablas del sistema de automatización.
    """
    op.drop_table('proveedor_trust')
    op.drop_table('configuracion_automatizacion')
    op.drop_table('automation_metrics')
    op.drop_table('automation_audit')
