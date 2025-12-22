"""PHASE 3: Complete assignment status tracking implementation

Revision ID: phase3_estado_asignacion_2025
Revises: trigger_integrity_2025
Create Date: 2025-10-22

ENTERPRISE LEVEL: Assignment lifecycle tracking for professional invoice management.

CONTEXTO:
El modelo Factura ya tiene el campo estado_asignacion (agregado en el último update).
Esta migración se encarga de:
1. Inicializar valores históricos del campo
2. Crear índice para optimizar queries del dashboard
3. Crear triggers para mantener sincronizado automáticamente

ARQUITECTURA:
- sin_asignar: Factura sin responsable (responsable_id = NULL, accion_por = NULL)
- asignado: Factura con responsable activo (responsable_id != NULL)
- huerfano: Factura procesada pero sin responsable (responsable_id=NULL, accion_por!=NULL)
- inconsistente: Estados anómalos para auditoría futura

JUSTIFICACIÓN PROFESIONAL:
- Previene datos huérfanos confusos en el dashboard
- Proporciona trazabilidad completa del ciclo de vida
- Permite detección automática de asignaciones rotas
- Facilita limpieza de datos y housekeeping
- Compatible con auditoría y reporting futuro
"""
from alembic import op
import sqlalchemy as sa


revision = 'phase3_estado_asignacion_2025'
down_revision = 'trigger_integrity_2025'
branch_labels = None
depends_on = None


def upgrade():
    """
    PHASE 3 Upgrade: Initialize and secure assignment status tracking.

    PASOS:
    0A. Crear columna accion_por si no existe (idempotente)
    0B. Crear columna estado_asignacion si no existe (idempotente)
    1. Inicializar valores basados SOLO en responsable_id
    2. Crear índices para optimizar queries
    3. Crear triggers para mantener sincronizado automáticamente

    IDEMPOTENCIA: Seguro ejecutar múltiples veces sin errores
    """

    connection = op.get_bind()

    # PASO 0A: Crear columna accion_por si no existe
    result_accion = connection.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'facturas'
          AND COLUMN_NAME = 'accion_por'
    """))

    if result_accion.scalar() == 0:
        op.add_column('facturas',
            sa.Column(
                'accion_por',
                sa.String(255),
                nullable=True,
                comment='Who approved/rejected - synced from workflow'
            )
        )
        # Índice para accion_por
        op.create_index(
            'ix_facturas_accion_por',
            'facturas',
            ['accion_por']
        )

    # PASO 0B: Crear columna estado_asignacion si no existe
    result = connection.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'facturas'
          AND COLUMN_NAME = 'estado_asignacion'
    """))

    if result.scalar() == 0:
        op.add_column('facturas',
            sa.Column(
                'estado_asignacion',
                sa.String(20),
                nullable=False,
                server_default='sin_asignar',
                comment='Estado del ciclo de vida de asignación'
            )
        )

    # PASO 1: Inicializar valores basados SOLO en responsable_id
    # accion_por será sincronizado después por el workflow
    op.execute("""
        UPDATE facturas
        SET estado_asignacion = CASE
            WHEN responsable_id IS NOT NULL THEN 'asignado'
            ELSE 'sin_asignar'
        END
    """)

    # PASO 2: Crear índice para optimizar queries del dashboard
    # Este índice es crítico para performance de filtros en el dashboard
    # Verificación idempotente
    result_index = connection.execute(sa.text("""
        SELECT COUNT(*) as idx_exists
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'facturas'
          AND INDEX_NAME = 'ix_facturas_estado_asignacion'
    """))

    index_exists = result_index.scalar() > 0

    if not index_exists:
        op.create_index(
            'ix_facturas_estado_asignacion',
            'facturas',
            ['estado_asignacion']
        )

    # PASO 3: Crear triggers para sincronización automática

    # Trigger 3A: BEFORE UPDATE
    # Recalcula estado_asignacion cuando cambian responsable_id o accion_por
    op.execute("""
        DROP TRIGGER IF EXISTS before_facturas_update_estado_asignacion
    """)

    op.execute("""
        CREATE TRIGGER before_facturas_update_estado_asignacion
        BEFORE UPDATE ON facturas
        FOR EACH ROW
        BEGIN
            -- Recalcular estado_asignacion basado en nuevos valores
            -- Esto se ejecuta automáticamente en cada UPDATE
            IF NEW.responsable_id IS NOT NULL THEN
                SET NEW.estado_asignacion = 'asignado';
            ELSEIF NEW.responsable_id IS NULL AND NEW.accion_por IS NOT NULL THEN
                SET NEW.estado_asignacion = 'huerfano';
            ELSE
                SET NEW.estado_asignacion = 'sin_asignar';
            END IF;
        END
    """)

    # Trigger 3B: BEFORE INSERT
    # Calcula estado_asignacion al crear nueva factura
    op.execute("""
        DROP TRIGGER IF EXISTS before_facturas_insert_estado_asignacion
    """)

    op.execute("""
        CREATE TRIGGER before_facturas_insert_estado_asignacion
        BEFORE INSERT ON facturas
        FOR EACH ROW
        BEGIN
            -- Calcular estado_asignacion si no se especifica
            IF NEW.estado_asignacion IS NULL OR NEW.estado_asignacion = 'sin_asignar' THEN
                IF NEW.responsable_id IS NOT NULL THEN
                    SET NEW.estado_asignacion = 'asignado';
                ELSEIF NEW.accion_por IS NOT NULL THEN
                    SET NEW.estado_asignacion = 'huerfano';
                ELSE
                    SET NEW.estado_asignacion = 'sin_asignar';
                END IF;
            END IF;
        END
    """)


def downgrade():
    """
    PHASE 3 Downgrade: Remove assignment status tracking infrastructure.

    PASOS:
    1. Eliminar triggers automáticos
    2. Eliminar índices (idempotente)
    3. Eliminar columnas accion_por y estado_asignacion

    NOTA: Este downgrade es completo y elimina ambas columnas
    """

    connection = op.get_bind()

    # PASO 1: Eliminar triggers
    op.execute("DROP TRIGGER IF EXISTS before_facturas_update_estado_asignacion")
    op.execute("DROP TRIGGER IF EXISTS before_facturas_insert_estado_asignacion")

    # PASO 2: Eliminar índice estado_asignacion
    result_idx = connection.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'facturas'
          AND INDEX_NAME = 'ix_facturas_estado_asignacion'
    """))
    if result_idx.scalar() > 0:
        op.drop_index('ix_facturas_estado_asignacion', table_name='facturas')

    # PASO 3: Eliminar índice accion_por
    result_idx2 = connection.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'facturas'
          AND INDEX_NAME = 'ix_facturas_accion_por'
    """))
    if result_idx2.scalar() > 0:
        op.drop_index('ix_facturas_accion_por', table_name='facturas')

    # PASO 4: Eliminar columna estado_asignacion
    result_col = connection.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'facturas'
          AND COLUMN_NAME = 'estado_asignacion'
    """))
    if result_col.scalar() > 0:
        op.drop_column('facturas', 'estado_asignacion')

    # PASO 5: Eliminar columna accion_por
    result_col2 = connection.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'facturas'
          AND COLUMN_NAME = 'accion_por'
    """))
    if result_col2.scalar() > 0:
        op.drop_column('facturas', 'accion_por')
