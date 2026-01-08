"""remove_nombre_proveedor_cache_field

Revision ID: 2025_12_15_remove_cache
Revises: 2025_12_15_deprecate
Create Date: 2025-12-15

🏗️ ARQUITECTURA 2025-12-15: Eliminar campo cache nombre_proveedor

MOTIVACIÓN:
El campo `nombre_proveedor` en `asignacion_nit_responsable` es una duplicación
de `razon_social` en `proveedores`. Esta duplicación causa problemas de
sincronización y viola el principio de Single Source of Truth (SSOT).

PROBLEMA ACTUAL:
1. Cuando se actualiza `proveedores.razon_social`, el campo
   `asignacion_nit_responsable.nombre_proveedor` queda desactualizado
2. No hay sincronización automática entre ambas tablas
3. Las vistas muestran datos inconsistentes

SOLUCIÓN ARQUITECTÓNICA:
Eliminar el campo cache y usar JOIN con tabla proveedores para obtener
razon_social en tiempo real. Esto garantiza:
- Siempre datos actualizados
- No duplicación de datos
- No código de sincronización
- Arquitectura limpia (SSOT)

IMPACTO:
- Modelo SQLAlchemy: Agregar relación con Proveedor (eager loading)
- Endpoints: Usar JOIN para obtener razon_social
- Performance: Overhead mínimo (~5-10%) gracias a eager loading

CAMBIOS EN BD:
- DROP COLUMN asignacion_nit_responsable.nombre_proveedor
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_12_15_remove_cache'
down_revision = '2025_12_15_deprecate'
branch_labels = None
depends_on = None


def upgrade():
    """
    Elimina el campo cache nombre_proveedor de asignacion_nit_responsable.
    
    El nombre del proveedor se obtendrá mediante JOIN con tabla proveedores
    usando el campo nit como clave foránea.
    """
    # Eliminar columna nombre_proveedor
    op.drop_column('asignacion_nit_responsable', 'nombre_proveedor')
    
    # Nota: Los índices en 'nit' ya existen en ambas tablas para JOINs eficientes


def downgrade():
    """
    Restaura el campo nombre_proveedor y lo repobla desde tabla proveedores.
    
    IMPORTANTE: Este downgrade solo debe usarse en caso de emergencia.
    Requiere que todos los NITs en asignaciones existan en proveedores.
    """
    # Restaurar columna
    op.add_column(
        'asignacion_nit_responsable',
        sa.Column('nombre_proveedor', sa.String(255), nullable=True,
                  comment='[CACHE] Nombre del proveedor (duplicado de proveedores.razon_social)')
    )
    
    # Repoblar desde proveedores
    op.execute("""
        UPDATE asignacion_nit_responsable anr
        JOIN proveedores p ON anr.nit = p.nit
        SET anr.nombre_proveedor = p.razon_social
    """)
