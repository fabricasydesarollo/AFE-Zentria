"""add enterprise risk controls

Revision ID: 88f9b5fd2ca3
Revises:
Create Date: 2025-10-15 00:00:00.000000

ENTERPRISE MIGRATION: Sistema de Control de Riesgos Multinivel
===============================================================

Este migration añade campos críticos para control de riesgos empresarial:

1. TipoServicioProveedor: Clasificación de servicios (Fijo, Variable, Por Consumo)
2. NivelConfianzaProveedor: Nivel de confianza (1-5) con umbrales dinámicos
3. FechaInicioRelacion: Para calcular antigüedad y ajustar criterios
4. Sistema de Alertas: Tabla para early warning system

Nivel: Fortune 500 Compliant
Impacto: CRÍTICO - Afecta decisiones de aprobación automática
Testing: Requiere validación en staging antes de producción
Rollback: Disponible (down() completo)

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '88f9b5fd2ca3'
down_revision = '9e297d20deaa'
branch_labels = None
depends_on = None


def upgrade():
    """
    Upgrade: Añade campos de control de riesgos empresarial.
    """

    # ============================================================================
    # 1. ASIGNACION_NIT_RESPONSABLE: Campos de clasificación de riesgos
    # ============================================================================

    print("[1/4] Añadiendo campos de clasificación de riesgos a asignacion_nit_responsable...")

    # Tipo de servicio del proveedor
    op.add_column('asignacion_nit_responsable',
        sa.Column('tipo_servicio_proveedor',
                  sa.Enum('servicio_fijo_mensual',
                         'servicio_variable_predecible',
                         'servicio_por_consumo',
                         'servicio_eventual',
                         name='tiposervicioproveedor'),
                  nullable=True,
                  comment='Clasificación del tipo de servicio para ajustar criterios de aprobación')
    )

    # Nivel de confianza del proveedor (1=Crítico, 5=Nuevo)
    op.add_column('asignacion_nit_responsable',
        sa.Column('nivel_confianza_proveedor',
                  sa.Enum('nivel_1_critico',
                         'nivel_2_alto',
                         'nivel_3_medio',
                         'nivel_4_bajo',
                         'nivel_5_nuevo',
                         name='nivelconfianzaproveedor'),
                  nullable=True,
                  server_default='nivel_5_nuevo',
                  comment='Nivel de confianza: 1=Crítico(95%), 2=Alto(92%), 3=Medio(88%), 4=Bajo(85%), 5=Nuevo(100%)')
    )

    # Fecha de inicio de relación con proveedor
    op.add_column('asignacion_nit_responsable',
        sa.Column('fecha_inicio_relacion',
                  sa.Date(),
                  nullable=True,
                  comment='Fecha de inicio de relación con proveedor (para calcular antigüedad)')
    )

    # Coeficiente de variación histórico (calculado)
    op.add_column('asignacion_nit_responsable',
        sa.Column('coeficiente_variacion_historico',
                  sa.Numeric(5, 2),
                  nullable=True,
                  comment='CV% histórico de montos (calculado automáticamente)')
    )

    # Requiere orden de compra obligatoria
    op.add_column('asignacion_nit_responsable',
        sa.Column('requiere_orden_compra_obligatoria',
                  sa.Boolean(),
                  nullable=False,
                  server_default='0',
                  comment='Si TRUE, facturas sin OC nunca se auto-aprueban')
    )

    # Metadata de análisis de riesgos
    op.add_column('asignacion_nit_responsable',
        sa.Column('metadata_riesgos',
                  sa.JSON(),
                  nullable=True,
                  comment='Metadata de análisis de riesgos: última evaluación, incidentes, etc.')
    )

    print("[1/4] Campos añadidos exitosamente a asignacion_nit_responsable")

    # ============================================================================
    # 2. WORKFLOW_APROBACION_FACTURAS: Campos de auditoría mejorada
    # ============================================================================

    print("[2/4] Añadiendo campos de auditoría mejorada a workflow_aprobacion_facturas...")

    # Nivel de riesgo calculado (0-100)
    op.add_column('workflow_aprobacion_facturas',
        sa.Column('nivel_riesgo_calculado',
                  sa.Integer(),
                  nullable=True,
                  comment='Nivel de riesgo 0-100 (0=Sin riesgo, 100=Alto riesgo)')
    )

    # Umbral de confianza utilizado en la decisión
    op.add_column('workflow_aprobacion_facturas',
        sa.Column('umbral_confianza_utilizado',
                  sa.Numeric(5, 2),
                  nullable=True,
                  comment='Umbral de confianza usado en esta decisión (varía según tipo de proveedor)')
    )

    # Tipo de validación aplicada
    op.add_column('workflow_aprobacion_facturas',
        sa.Column('tipo_validacion_aplicada',
                  sa.String(50),
                  nullable=True,
                  comment='Tipo de validación: rango_historico, orden_compra, patron_fijo, etc.')
    )

    # Resultado de validación de rango
    op.add_column('workflow_aprobacion_facturas',
        sa.Column('validacion_rango_resultado',
                  sa.JSON(),
                  nullable=True,
                  comment='Resultado de validación de rango histórico')
    )

    print("[2/4] Campos añadidos exitosamente a workflow_aprobacion_facturas")

    # ============================================================================
    # 3. NUEVA TABLA: ALERTAS_APROBACION_AUTOMATICA
    # ============================================================================

    print("[3/4] Creando tabla alertas_aprobacion_automatica (Early Warning System)...")

    # Verificar si la tabla ya existe
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'alertas_aprobacion_automatica' in inspector.get_table_names():
        print("[3/4] Tabla alertas_aprobacion_automatica ya existe, omitiendo creación...")
    else:
        op.create_table('alertas_aprobacion_automatica',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('workflow_id', sa.BigInteger(), nullable=True),
            sa.Column('factura_id', sa.BigInteger(), nullable=False),

            # Tipo y severidad de alerta
            sa.Column('tipo_alerta',
                      sa.Enum('confianza_borde',
                             'variacion_precio_moderada',
                             'item_nuevo_bajo_valor',
                             'patron_inusual',
                             'proveedor_nuevo',
                             'monto_cerca_limite',
                             'cambio_frecuencia',
                             name='tipoalerta'),
                      nullable=False,
                      comment='Tipo de alerta detectada'),

            sa.Column('severidad',
                      sa.Enum('baja', 'media', 'alta', 'critica', name='severidadalerta'),
                      nullable=False,
                      comment='Severidad de la alerta'),

            # Datos de la alerta
            sa.Column('confianza_calculada', sa.Numeric(5, 2), nullable=True),
            sa.Column('umbral_requerido', sa.Numeric(5, 2), nullable=True),
            sa.Column('diferencia', sa.Numeric(5, 2), nullable=True),
            sa.Column('valor_detectado', sa.String(255), nullable=True),
            sa.Column('valor_esperado', sa.String(255), nullable=True),

            # Flags de gestión
            sa.Column('requiere_revision_urgente', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('revisada', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('revisada_por', sa.String(255), nullable=True),
            sa.Column('fecha_revision', sa.DateTime(), nullable=True),
            sa.Column('accion_tomada', sa.Text(), nullable=True),

            # Metadata y auditoría
            sa.Column('metadata_alerta', sa.JSON(), nullable=True),
            sa.Column('creado_en', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('actualizado_en', sa.DateTime(), nullable=True, onupdate=sa.text('CURRENT_TIMESTAMP')),

            # Constraints
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['workflow_id'], ['workflow_aprobacion_facturas.id'],
                                   name='fk_alertas_workflow_id'),
            sa.ForeignKeyConstraint(['factura_id'], ['facturas.id'],
                                   name='fk_alertas_factura_id'),

            comment='Sistema de alertas tempranas para auditoría continua de aprobaciones automáticas'
        )

        # Índices para queries frecuentes
        op.create_index('idx_alertas_revisada', 'alertas_aprobacion_automatica', ['revisada'])
        op.create_index('idx_alertas_severidad', 'alertas_aprobacion_automatica', ['severidad'])
        op.create_index('idx_alertas_tipo', 'alertas_aprobacion_automatica', ['tipo_alerta'])
        op.create_index('idx_alertas_factura', 'alertas_aprobacion_automatica', ['factura_id'])
        op.create_index('idx_alertas_workflow', 'alertas_aprobacion_automatica', ['workflow_id'])

        print("[3/4] Tabla alertas_aprobacion_automatica creada exitosamente")

    # ============================================================================
    # 4. ÍNDICES PARA PERFORMANCE
    # ============================================================================

    print("[4/4] Creando índices de performance...")

    # Índice compuesto para clasificación de proveedores
    op.create_index('idx_asig_tipo_nivel', 'asignacion_nit_responsable',
                   ['tipo_servicio_proveedor', 'nivel_confianza_proveedor'])

    # Índice para búsqueda por CV
    op.create_index('idx_asig_cv', 'asignacion_nit_responsable',
                   ['coeficiente_variacion_historico'])

    print("[4/4] Índices creados exitosamente")

    print("=" * 80)
    print("MIGRACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 80)
    print()
    print("SIGUIENTE PASO:")
    print("  1. Ejecutar script de clasificación de proveedores")
    print("  2. Revisar configuración de tipos de servicio")
    print("  3. Validar en staging antes de producción")
    print()


def downgrade():
    """
    Downgrade: Rollback completo de cambios (seguridad empresarial).
    """

    print("INICIANDO ROLLBACK DE MIGRACIÓN...")
    print()

    # Eliminar tabla de alertas
    print("[1/3] Eliminando tabla alertas_aprobacion_automatica...")
    op.drop_index('idx_alertas_workflow', table_name='alertas_aprobacion_automatica')
    op.drop_index('idx_alertas_factura', table_name='alertas_aprobacion_automatica')
    op.drop_index('idx_alertas_tipo', table_name='alertas_aprobacion_automatica')
    op.drop_index('idx_alertas_severidad', table_name='alertas_aprobacion_automatica')
    op.drop_index('idx_alertas_revisada', table_name='alertas_aprobacion_automatica')
    op.drop_table('alertas_aprobacion_automatica')

    # Eliminar columnas de workflow
    print("[2/3] Eliminando campos de workflow_aprobacion_facturas...")
    op.drop_column('workflow_aprobacion_facturas', 'validacion_rango_resultado')
    op.drop_column('workflow_aprobacion_facturas', 'tipo_validacion_aplicada')
    op.drop_column('workflow_aprobacion_facturas', 'umbral_confianza_utilizado')
    op.drop_column('workflow_aprobacion_facturas', 'nivel_riesgo_calculado')

    # Eliminar columnas de asignacion
    print("[3/3] Eliminando campos de asignacion_nit_responsable...")
    op.drop_index('idx_asig_cv', table_name='asignacion_nit_responsable')
    op.drop_index('idx_asig_tipo_nivel', table_name='asignacion_nit_responsable')

    op.drop_column('asignacion_nit_responsable', 'metadata_riesgos')
    op.drop_column('asignacion_nit_responsable', 'requiere_orden_compra_obligatoria')
    op.drop_column('asignacion_nit_responsable', 'coeficiente_variacion_historico')
    op.drop_column('asignacion_nit_responsable', 'fecha_inicio_relacion')
    op.drop_column('asignacion_nit_responsable', 'nivel_confianza_proveedor')
    op.drop_column('asignacion_nit_responsable', 'tipo_servicio_proveedor')

    print("ROLLBACK COMPLETADO")
