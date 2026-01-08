"""
Migración: Agregar campos de auditoría para auto-creación de proveedores

Objetivo:
- Extender tabla 'proveedores' con campos para rastrear proveedores auto-creados
- Soportar auditoría completa de creaciones automáticas desde facturas
- Permitir identificar proveedores que requieren validación manual posterior

Cambios:
- es_auto_creado: Flag booleano (default=false) para marcar proveedores auto-creados
- creado_automaticamente_en: DATETIME con timestamp de creación automática
- ambos campos son NULLABLE y con índice para queries rápidas

Fecha: 2025-11-06
: 
Nivel: Enterprise
Reversión: Supported (DOWN migration implementada)
"""

from alembic import op
import sqlalchemy as sa

# Metadata
revision = 'provider_auto_create_2025'
down_revision = 'd9608252aff1'  # add_viewer_role (current DB state)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade: Agregar campos para auto-creación de proveedores.

    IDEMPOTENTE: Esta migración puede ejecutarse múltiples veces sin error.

    Estrategia:
    1. Agregar columna es_auto_creado (BOOLEAN, DEFAULT FALSE)
       - Permite distinguir proveedores creados manualmente vs automáticamente
       - Facilita reporting y auditoría

    2. Agregar columna creado_automaticamente_en (DATETIME)
       - Timestamp exacto de cuándo se creó automáticamente
       - NULL si no fue auto-creado (proveedor manual)
       - Facilita auditoría y debugging

    3. Agregar índices para queries optimizadas
       - Queries rápidas filtrando proveedores auto-creados
       - Importante para dashboards de auditoría
    """

    # Obtener conexión para ejecutar SQL nativo
    conn = op.get_bind()

    # Paso 1: Agregar columna es_auto_creado (IDEMPOTENTE)
    # Verificar si la columna existe antes de agregarla
    result = conn.execute(sa.text("""
        SELECT COUNT(*) as count
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'proveedores'
        AND COLUMN_NAME = 'es_auto_creado'
    """))

    column_exists = result.scalar() > 0

    if not column_exists:
        op.add_column(
            'proveedores',
            sa.Column(
                'es_auto_creado',
                sa.Boolean,
                nullable=False,
                default=False,
                server_default='0',
                comment='Flag para rastrear proveedores auto-creados desde facturas'
            )
        )

    # Paso 2: Agregar columna creado_automaticamente_en (IDEMPOTENTE)
    result = conn.execute(sa.text("""
        SELECT COUNT(*) as count
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'proveedores'
        AND COLUMN_NAME = 'creado_automaticamente_en'
    """))

    column_exists = result.scalar() > 0

    if not column_exists:
        op.add_column(
            'proveedores',
            sa.Column(
                'creado_automaticamente_en',
                sa.DateTime(timezone=True),
                nullable=True,
                comment='Timestamp de creación automática (NULL si fue creación manual)'
            )
        )

    # Paso 3: Crear índices (IDEMPOTENTE con verificación)
    # Índice 1: Para queries que filtren proveedores auto-creados
    result = conn.execute(sa.text("""
        SELECT COUNT(*) as count
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'proveedores'
        AND INDEX_NAME = 'idx_proveedores_es_auto_creado'
    """))

    if result.scalar() == 0:
        op.create_index(
            'idx_proveedores_es_auto_creado',
            'proveedores',
            ['es_auto_creado'],
            unique=False
        )

    # Índice 2: Para ordenamiento por fecha de creación automática
    result = conn.execute(sa.text("""
        SELECT COUNT(*) as count
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'proveedores'
        AND INDEX_NAME = 'idx_proveedores_creado_automaticamente_en'
    """))

    if result.scalar() == 0:
        op.create_index(
            'idx_proveedores_creado_automaticamente_en',
            'proveedores',
            ['creado_automaticamente_en'],
            unique=False
        )

    # Índice 3: Combinado para queries más complejas
    result = conn.execute(sa.text("""
        SELECT COUNT(*) as count
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'proveedores'
        AND INDEX_NAME = 'idx_proveedores_auto_creado_fecha'
    """))

    if result.scalar() == 0:
        op.create_index(
            'idx_proveedores_auto_creado_fecha',
            'proveedores',
            ['es_auto_creado', 'creado_automaticamente_en'],
            unique=False
        )


def downgrade() -> None:
    """
    Downgrade: Revertir cambios (remover campos e índices).

    Nota: Esta operación es destructiva. En producción, considerar
    mantener los datos por auditoría y solo deshabilitar la funcionalidad.
    """

    # Paso 1: Eliminar índices (en orden inverso)
    op.drop_index(
        'idx_proveedores_auto_creado_fecha',
        table_name='proveedores'
    )

    op.drop_index(
        'idx_proveedores_creado_automaticamente_en',
        table_name='proveedores'
    )

    op.drop_index(
        'idx_proveedores_es_auto_creado',
        table_name='proveedores'
    )

    # Paso 2: Eliminar columnas
    op.drop_column('proveedores', 'creado_automaticamente_en')
    op.drop_column('proveedores', 'es_auto_creado')
