"""add_workflow_tables

Revision ID: abc123
Revises: f6feb264b552
Create Date: 2025-10-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'abc123'
down_revision: Union[str, None] = 'f6feb264b552'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabla: workflow_aprobacion_facturas
    op.create_table(
        'workflow_aprobacion_facturas',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('factura_id', sa.BigInteger(), nullable=False),

        # Información del correo
        sa.Column('email_id', sa.String(255), nullable=True, comment='ID del correo en el servidor'),
        sa.Column('email_asunto', sa.String(500), nullable=True, comment='Asunto del correo'),
        sa.Column('email_remitente', sa.String(255), nullable=True, comment='Email del remitente'),
        sa.Column('email_fecha_recepcion', sa.DateTime(), nullable=True, comment='Fecha de recepción del correo'),
        sa.Column('email_body_preview', sa.Text(), nullable=True, comment='Preview del cuerpo del correo'),

        # Estado del workflow
        sa.Column('estado', sa.Enum('RECIBIDA', 'EN_ANALISIS', 'APROBADA_AUTO', 'PENDIENTE_REVISION', 'EN_REVISION', 'APROBADA_MANUAL', 'RECHAZADA', 'OBSERVADA', 'ENVIADA_CONTABILIDAD', 'PROCESADA', name='estadofacturaworkflow'), nullable=False),
        sa.Column('estado_anterior', sa.Enum('RECIBIDA', 'EN_ANALISIS', 'APROBADA_AUTO', 'PENDIENTE_REVISION', 'EN_REVISION', 'APROBADA_MANUAL', 'RECHAZADA', 'OBSERVADA', 'ENVIADA_CONTABILIDAD', 'PROCESADA', name='estadofacturaworkflow'), nullable=True),
        sa.Column('fecha_cambio_estado', sa.DateTime(), nullable=True),

        # Asignación automática
        sa.Column('nit_proveedor', sa.String(20), nullable=True, comment='NIT identificado automáticamente'),
        sa.Column('responsable_id', sa.BigInteger(), nullable=True),
        sa.Column('area_responsable', sa.String(100), nullable=True, comment='Área del responsable'),
        sa.Column('fecha_asignacion', sa.DateTime(), nullable=True),

        # Análisis de identidad
        sa.Column('factura_mes_anterior_id', sa.BigInteger(), nullable=True),
        sa.Column('es_identica_mes_anterior', sa.Boolean(), default=False),
        sa.Column('porcentaje_similitud', sa.Numeric(5, 2), nullable=True),
        sa.Column('diferencias_detectadas', sa.JSON(), nullable=True),
        sa.Column('criterios_comparacion', sa.JSON(), nullable=True),

        # Aprobación
        sa.Column('tipo_aprobacion', sa.Enum('AUTOMATICA', 'MANUAL', 'MASIVA', 'FORZADA', name='tipoaprobacion'), nullable=True),
        sa.Column('aprobada', sa.Boolean(), default=False),
        sa.Column('aprobada_por', sa.String(255), nullable=True),
        sa.Column('fecha_aprobacion', sa.DateTime(), nullable=True),
        sa.Column('observaciones_aprobacion', sa.Text(), nullable=True),

        # Rechazo
        sa.Column('rechazada', sa.Boolean(), default=False),
        sa.Column('rechazada_por', sa.String(255), nullable=True),
        sa.Column('fecha_rechazo', sa.DateTime(), nullable=True),
        sa.Column('motivo_rechazo', sa.Enum('MONTO_INCORRECTO', 'SERVICIO_NO_PRESTADO', 'PROVEEDOR_INCORRECTO', 'DUPLICADA', 'SIN_PRESUPUESTO', 'OTRO', name='motivorechazo'), nullable=True),
        sa.Column('detalle_rechazo', sa.Text(), nullable=True),

        # Tiempos
        sa.Column('tiempo_en_analisis', sa.BigInteger(), nullable=True),
        sa.Column('tiempo_en_revision', sa.BigInteger(), nullable=True),
        sa.Column('tiempo_total_aprobacion', sa.BigInteger(), nullable=True),

        # Notificaciones
        sa.Column('notificaciones_enviadas', sa.JSON(), nullable=True),
        sa.Column('recordatorios_enviados', sa.BigInteger(), default=0),

        # Metadata
        sa.Column('metadata_workflow', sa.JSON(), nullable=True),

        # Auditoría
        sa.Column('creado_en', sa.DateTime(), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(), nullable=True),
        sa.Column('creado_por', sa.String(255), nullable=True, default='SISTEMA_AUTO'),
        sa.Column('actualizado_por', sa.String(255), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['factura_id'], ['facturas.id'], ),
        sa.ForeignKeyConstraint(['factura_mes_anterior_id'], ['facturas.id'], ),
        sa.ForeignKeyConstraint(['responsable_id'], ['responsables.id'], )
    )

    # Índices para workflow
    op.create_index('idx_workflow_factura', 'workflow_aprobacion_facturas', ['factura_id'])
    op.create_index('idx_workflow_estado', 'workflow_aprobacion_facturas', ['estado'])
    op.create_index('idx_workflow_nit', 'workflow_aprobacion_facturas', ['nit_proveedor'])
    op.create_index('idx_workflow_responsable', 'workflow_aprobacion_facturas', ['responsable_id'])
    op.create_index('idx_workflow_estado_responsable', 'workflow_aprobacion_facturas', ['estado', 'responsable_id'])
    op.create_index('idx_workflow_nit_fecha', 'workflow_aprobacion_facturas', ['nit_proveedor', 'email_fecha_recepcion'])
    op.create_index('idx_workflow_estado_fecha', 'workflow_aprobacion_facturas', ['estado', 'fecha_cambio_estado'])

    # Tabla: asignacion_nit_responsable
    op.create_table(
        'asignacion_nit_responsable',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('nit', sa.String(20), nullable=False),
        sa.Column('nombre_proveedor', sa.String(255), nullable=True),
        sa.Column('responsable_id', sa.BigInteger(), nullable=False),
        sa.Column('area', sa.String(100), nullable=True),
        sa.Column('permitir_aprobacion_automatica', sa.Boolean(), default=True),
        sa.Column('requiere_revision_siempre', sa.Boolean(), default=False),
        sa.Column('monto_maximo_auto_aprobacion', sa.Numeric(15, 2), nullable=True),
        sa.Column('porcentaje_variacion_permitido', sa.Numeric(5, 2), default=5.0),
        sa.Column('emails_notificacion', sa.JSON(), nullable=True),
        sa.Column('activo', sa.Boolean(), default=True),
        sa.Column('creado_en', sa.DateTime(), nullable=True),
        sa.Column('actualizado_en', sa.DateTime(), nullable=True),
        sa.Column('creado_por', sa.String(255), nullable=True),
        sa.Column('actualizado_por', sa.String(255), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nit'),
        sa.ForeignKeyConstraint(['responsable_id'], ['responsables.id'], )
    )

    op.create_index('idx_asignacion_nit', 'asignacion_nit_responsable', ['nit'])
    op.create_index('idx_asignacion_responsable', 'asignacion_nit_responsable', ['responsable_id'])
    op.create_index('idx_asignacion_activo', 'asignacion_nit_responsable', ['activo'])

    # Tabla: notificaciones_workflow
    op.create_table(
        'notificaciones_workflow',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('workflow_id', sa.BigInteger(), nullable=False),
        sa.Column('tipo', sa.Enum('FACTURA_RECIBIDA', 'PENDIENTE_REVISION', 'FACTURA_APROBADA', 'FACTURA_RECHAZADA', 'RECORDATORIO', 'ALERTA', name='tiponotificacion'), nullable=False),
        sa.Column('destinatarios', sa.JSON(), nullable=False),
        sa.Column('asunto', sa.String(500), nullable=True),
        sa.Column('cuerpo', sa.Text(), nullable=True),
        sa.Column('enviada', sa.Boolean(), default=False),
        sa.Column('fecha_envio', sa.DateTime(), nullable=True),
        sa.Column('proveedor_email', sa.String(100), nullable=True),
        sa.Column('abierta', sa.Boolean(), default=False),
        sa.Column('fecha_apertura', sa.DateTime(), nullable=True),
        sa.Column('respondida', sa.Boolean(), default=False),
        sa.Column('fecha_respuesta', sa.DateTime(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('intentos_envio', sa.BigInteger(), default=0),
        sa.Column('creado_en', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow_aprobacion_facturas.id'], )
    )

    op.create_index('idx_notif_workflow', 'notificaciones_workflow', ['workflow_id'])
    op.create_index('idx_notif_tipo', 'notificaciones_workflow', ['tipo'])
    op.create_index('idx_notif_enviada', 'notificaciones_workflow', ['enviada'])
    op.create_index('idx_notif_workflow_tipo', 'notificaciones_workflow', ['workflow_id', 'tipo'])

    # Tabla: configuracion_correo
    op.create_table(
        'configuracion_correo',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('servidor_imap', sa.String(255), nullable=False),
        sa.Column('puerto_imap', sa.BigInteger(), default=993),
        sa.Column('usa_ssl', sa.Boolean(), default=True),
        sa.Column('password', sa.String(500), nullable=True),
        sa.Column('oauth_token', sa.Text(), nullable=True),
        sa.Column('carpeta_inbox', sa.String(100), default='INBOX'),
        sa.Column('carpeta_procesados', sa.String(100), default='Procesados'),
        sa.Column('carpeta_errores', sa.String(100), default='Errores'),
        sa.Column('filtro_asunto', sa.JSON(), nullable=True),
        sa.Column('filtro_remitente', sa.JSON(), nullable=True),
        sa.Column('activo', sa.Boolean(), default=True),
        sa.Column('ultima_lectura', sa.DateTime(), nullable=True),
        sa.Column('total_correos_procesados', sa.BigInteger(), default=0),
        sa.Column('creado_en', sa.DateTime(), nullable=True),
        sa.Column('actualizado_en', sa.DateTime(), nullable=True),
        sa.Column('creado_por', sa.String(255), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    op.create_index('idx_config_email', 'configuracion_correo', ['email'])
    op.create_index('idx_config_activo', 'configuracion_correo', ['activo'])
    op.create_index('idx_config_activo_email', 'configuracion_correo', ['activo', 'email'])


def downgrade() -> None:
    op.drop_index('idx_config_activo_email', table_name='configuracion_correo')
    op.drop_index('idx_config_activo', table_name='configuracion_correo')
    op.drop_index('idx_config_email', table_name='configuracion_correo')
    op.drop_table('configuracion_correo')

    op.drop_index('idx_notif_workflow_tipo', table_name='notificaciones_workflow')
    op.drop_index('idx_notif_enviada', table_name='notificaciones_workflow')
    op.drop_index('idx_notif_tipo', table_name='notificaciones_workflow')
    op.drop_index('idx_notif_workflow', table_name='notificaciones_workflow')
    op.drop_table('notificaciones_workflow')

    op.drop_index('idx_asignacion_activo', table_name='asignacion_nit_responsable')
    op.drop_index('idx_asignacion_responsable', table_name='asignacion_nit_responsable')
    op.drop_index('idx_asignacion_nit', table_name='asignacion_nit_responsable')
    op.drop_table('asignacion_nit_responsable')

    op.drop_index('idx_workflow_estado_fecha', table_name='workflow_aprobacion_facturas')
    op.drop_index('idx_workflow_nit_fecha', table_name='workflow_aprobacion_facturas')
    op.drop_index('idx_workflow_estado_responsable', table_name='workflow_aprobacion_facturas')
    op.drop_index('idx_workflow_responsable', table_name='workflow_aprobacion_facturas')
    op.drop_index('idx_workflow_nit', table_name='workflow_aprobacion_facturas')
    op.drop_index('idx_workflow_estado', table_name='workflow_aprobacion_facturas')
    op.drop_index('idx_workflow_factura', table_name='workflow_aprobacion_facturas')
    op.drop_table('workflow_aprobacion_facturas')
