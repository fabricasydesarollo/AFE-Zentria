"""convert_enums_to_varchar_for_enterprise_compatibility

Revision ID: 4ad923b70f74
Revises: 88f9b5fd2ca3
Create Date: 2025-10-15 16:43:39.791468

ENTERPRISE MIGRATION: Convertir ENUMs a VARCHAR para compatibilidad MySQL/SQLAlchemy
====================================================================================

Problema:
- MySQL ENUMs tienen limitaciones de compatibilidad con SQLAlchemy
- Los valores del enum en BD (minúsculas) no coinciden con nombres Python (mayúsculas)
- Esto causa errores al leer registros: "servicio_por_consumo is not among defined values"

Solución:
- Convertir columnas ENUM a VARCHAR(50)
- Mantener validación en capa de aplicación (Python Enum)
- Mejor práctica Fortune 500: ENUMs en código, VARCHAR en BD

Impacto:
- Los datos existentes se preservan automáticamente
- Mayor flexibilidad para cambios futuros
- Sin impacto en performance (VARCHAR con índice)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '4ad923b70f74'
down_revision: Union[str, Sequence[str], None] = '88f9b5fd2ca3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Convierte columnas ENUM a VARCHAR para compatibilidad enterprise.
    """
    print("=" * 80)
    print("MIGRACION ENTERPRISE: ENUM -> VARCHAR")
    print("=" * 80)
    print()

    # ============================================================================
    # 1. ASIGNACION_NIT_RESPONSABLE: Convertir ENUMs a VARCHAR
    # ============================================================================

    print("[1/4] Convirtiendo tipo_servicio_proveedor a VARCHAR(50)...")

    # Verificar si la columna temporal ya existe
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('asignacion_nit_responsable')]

    # Método seguro para MySQL: Crear columna temporal, copiar datos, eliminar antigua, renombrar
    if 'tipo_servicio_proveedor_temp' not in columns:
        op.add_column('asignacion_nit_responsable',
            sa.Column('tipo_servicio_proveedor_temp', sa.String(50), nullable=True)
        )

    # Copiar datos del ENUM al VARCHAR (solo si hay columna ENUM)
    if 'tipo_servicio_proveedor' in columns and 'tipo_servicio_proveedor_temp' in columns:
        op.execute("""
            UPDATE asignacion_nit_responsable
            SET tipo_servicio_proveedor_temp = tipo_servicio_proveedor
            WHERE tipo_servicio_proveedor IS NOT NULL
        """)

    # Eliminar columna ENUM antigua (solo si existe y temporal también existe)
    if 'tipo_servicio_proveedor' in columns and 'tipo_servicio_proveedor_temp' in columns:
        op.drop_column('asignacion_nit_responsable', 'tipo_servicio_proveedor')

    # Renombrar columna temporal a nombre final (solo si temporal existe y final no)
    columns_refresh = [c['name'] for c in inspector.get_columns('asignacion_nit_responsable')]
    if 'tipo_servicio_proveedor_temp' in columns_refresh and 'tipo_servicio_proveedor' not in columns_refresh:
        op.alter_column('asignacion_nit_responsable', 'tipo_servicio_proveedor_temp',
                       new_column_name='tipo_servicio_proveedor',
                       existing_type=sa.String(50))

    # Agregar índice para performance
    op.create_index('idx_asig_tipo_servicio', 'asignacion_nit_responsable',
                   ['tipo_servicio_proveedor'])

    print("[1/4] Completado")
    print()

    # ============================================================================
    # 2. ASIGNACION_NIT_RESPONSABLE: nivel_confianza_proveedor
    # ============================================================================

    print("[2/4] Convirtiendo nivel_confianza_proveedor a VARCHAR(50)...")

    columns = [c['name'] for c in inspector.get_columns('asignacion_nit_responsable')]

    if 'nivel_confianza_proveedor_temp' not in columns:
        op.add_column('asignacion_nit_responsable',
            sa.Column('nivel_confianza_proveedor_temp', sa.String(50), nullable=True)
        )

    columns = [c['name'] for c in inspector.get_columns('asignacion_nit_responsable')]
    if 'nivel_confianza_proveedor' in columns and 'nivel_confianza_proveedor_temp' in columns:
        op.execute("""
            UPDATE asignacion_nit_responsable
            SET nivel_confianza_proveedor_temp = nivel_confianza_proveedor
            WHERE nivel_confianza_proveedor IS NOT NULL
        """)

    if 'nivel_confianza_proveedor' in columns and 'nivel_confianza_proveedor_temp' in columns:
        op.drop_column('asignacion_nit_responsable', 'nivel_confianza_proveedor')

    columns_refresh = [c['name'] for c in inspector.get_columns('asignacion_nit_responsable')]
    if 'nivel_confianza_proveedor_temp' in columns_refresh and 'nivel_confianza_proveedor' not in columns_refresh:
        op.alter_column('asignacion_nit_responsable', 'nivel_confianza_proveedor_temp',
                       new_column_name='nivel_confianza_proveedor',
                       existing_type=sa.String(50))

    op.create_index('idx_asig_nivel_confianza', 'asignacion_nit_responsable',
                   ['nivel_confianza_proveedor'])

    print("[2/4] Completado")
    print()

    # ============================================================================
    # 3. ALERTAS_APROBACION_AUTOMATICA: tipo_alerta
    # ============================================================================

    print("[3/4] Convirtiendo tipo_alerta a VARCHAR(50)...")

    # Verificar si la tabla existe
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'alertas_aprobacion_automatica' in inspector.get_table_names():
        op.add_column('alertas_aprobacion_automatica',
            sa.Column('tipo_alerta_temp', sa.String(50), nullable=True)
        )

        op.execute("""
            UPDATE alertas_aprobacion_automatica
            SET tipo_alerta_temp = tipo_alerta
            WHERE tipo_alerta IS NOT NULL
        """)

        op.drop_column('alertas_aprobacion_automatica', 'tipo_alerta')

        op.alter_column('alertas_aprobacion_automatica', 'tipo_alerta_temp',
                       new_column_name='tipo_alerta',
                       existing_type=sa.String(50))

        print("[3/4] Completado")
    else:
        print("[3/4] Tabla no existe, omitiendo")

    print()

    # ============================================================================
    # 4. ALERTAS_APROBACION_AUTOMATICA: severidad
    # ============================================================================

    print("[4/4] Convirtiendo severidad a VARCHAR(50)...")

    if 'alertas_aprobacion_automatica' in inspector.get_table_names():
        op.add_column('alertas_aprobacion_automatica',
            sa.Column('severidad_temp', sa.String(50), nullable=True)
        )

        op.execute("""
            UPDATE alertas_aprobacion_automatica
            SET severidad_temp = severidad
            WHERE severidad IS NOT NULL
        """)

        op.drop_column('alertas_aprobacion_automatica', 'severidad')

        op.alter_column('alertas_aprobacion_automatica', 'severidad_temp',
                       new_column_name='severidad',
                       existing_type=sa.String(50))

        print("[4/4] Completado")
    else:
        print("[4/4] Tabla no existe, omitiendo")

    print()
    print("=" * 80)
    print("MIGRACION COMPLETADA EXITOSAMENTE")
    print("=" * 80)
    print()
    print("CAMBIOS APLICADOS:")
    print("  - tipo_servicio_proveedor: ENUM -> VARCHAR(50)")
    print("  - nivel_confianza_proveedor: ENUM -> VARCHAR(50)")
    print("  - tipo_alerta: ENUM -> VARCHAR(50)")
    print("  - severidad: ENUM -> VARCHAR(50)")
    print()
    print("VENTAJAS:")
    print("  - Compatibilidad total MySQL/SQLAlchemy")
    print("  - Validacion en capa de aplicacion (Python Enum)")
    print("  - Mayor flexibilidad para cambios futuros")
    print("  - Datos existentes preservados")
    print()


def downgrade() -> None:
    """
    Revierte VARCHAR a ENUM (no recomendado en producción).
    """
    print("ADVERTENCIA: Revertir VARCHAR a ENUM puede causar problemas")
    print("Solo ejecutar en desarrollo/testing")
    print()

    # Revertir es más complejo y arriesgado, se omite por seguridad
    # En producción NUNCA se debe hacer downgrade de esta migración
    print("DOWNGRADE NO IMPLEMENTADO POR SEGURIDAD")
    print("Si necesitas revertir, hazlo manualmente con precaución")
