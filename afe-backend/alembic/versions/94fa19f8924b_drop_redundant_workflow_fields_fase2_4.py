"""drop_redundant_workflow_fields_fase2_4

Elimina campos redundantes de aprobación/rechazo de tabla facturas.

Estos datos ahora viven exclusivamente en workflow_aprobacion_facturas.
Acceso a través de helpers _workflow en el modelo Factura.

IMPORTANTE:
- Ejecutar script migrar_datos_workflow_fase2_4.py ANTES de esta migración
- Asegurarse que todos los datos fueron migrados a workflow
- Esta migración es REVERSIBLE (downgrade restaura columnas)

Revision ID: 94fa19f8924b
Revises: a05adc423964
Create Date: 2025-10-19 20:06:05.271968

Nivel: Fortune 500 Data Normalization
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '94fa19f8924b'
down_revision: Union[str, Sequence[str], None] = 'a05adc423964'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Eliminar campos redundantes de facturas.

    Campos eliminados:
    - aprobado_por: Ahora en workflow_aprobacion_facturas.aprobada_por
    - fecha_aprobacion: Ahora en workflow_aprobacion_facturas.fecha_aprobacion
    - rechazado_por: Ahora en workflow_aprobacion_facturas.rechazada_por
    - fecha_rechazo: Ahora en workflow_aprobacion_facturas.fecha_rechazo
    - motivo_rechazo: Ahora en workflow_aprobacion_facturas.detalle_rechazo

    Acceso: factura.aprobado_por_workflow, factura.rechazado_por_workflow, etc.
    """
    print("\n" + "="*80)
    print("[INFO] Eliminando campos redundantes de tabla facturas...")
    print("="*80)

    # PASO 1: Eliminar constraints que dependen de estos campos
    print("\n[1/7] Eliminando constraint chk_facturas_aprobada_con_aprobador...")
    op.drop_constraint('chk_facturas_aprobada_con_aprobador', 'facturas', type_='check')

    print("[2/7] Eliminando constraint chk_facturas_rechazada_con_motivo...")
    op.drop_constraint('chk_facturas_rechazada_con_motivo', 'facturas', type_='check')

    # PASO 2: Eliminar campos de aprobación
    print("\n[3/7] Eliminando campo aprobado_por...")
    op.drop_column('facturas', 'aprobado_por')

    print("[4/7] Eliminando campo fecha_aprobacion...")
    op.drop_column('facturas', 'fecha_aprobacion')

    # PASO 3: Eliminar campos de rechazo
    print("[5/7] Eliminando campo rechazado_por...")
    op.drop_column('facturas', 'rechazado_por')

    print("[6/7] Eliminando campo fecha_rechazo...")
    op.drop_column('facturas', 'fecha_rechazo')

    print("[7/7] Eliminando campo motivo_rechazo...")
    op.drop_column('facturas', 'motivo_rechazo')

    print("\n[OK] Campos redundantes eliminados exitosamente")
    print("="*80)
    print("\nAcceso a datos:")
    print("  - factura.aprobado_por_workflow")
    print("  - factura.fecha_aprobacion_workflow")
    print("  - factura.rechazado_por_workflow")
    print("  - factura.fecha_rechazo_workflow")
    print("  - factura.motivo_rechazo_workflow")
    print("\nDatos almacenados en: workflow_aprobacion_facturas")
    print("="*80 + "\n")


def downgrade() -> None:
    """
    Restaurar campos redundantes (rollback).

    NOTA: Los datos NO se restauran automáticamente.
    Es necesario ejecutar script de reversión si se necesitan los datos.
    """
    print("\n" + "="*80)
    print("[INFO] Restaurando campos redundantes en tabla facturas...")
    print("="*80)

    # Restaurar campos de aprobación
    print("\n[1/5] Restaurando campo aprobado_por...")
    op.add_column('facturas',
        sa.Column('aprobado_por', mysql.VARCHAR(length=100), nullable=True,
                  comment="Usuario que aprobó la factura manualmente")
    )

    print("[2/5] Restaurando campo fecha_aprobacion...")
    op.add_column('facturas',
        sa.Column('fecha_aprobacion', mysql.DATETIME(timezone=True), nullable=True,
                  comment="Fecha y hora de aprobación")
    )

    # Restaurar campos de rechazo
    print("[3/5] Restaurando campo rechazado_por...")
    op.add_column('facturas',
        sa.Column('rechazado_por', mysql.VARCHAR(length=100), nullable=True,
                  comment="Usuario que rechazó la factura")
    )

    print("[4/5] Restaurando campo fecha_rechazo...")
    op.add_column('facturas',
        sa.Column('fecha_rechazo', mysql.DATETIME(timezone=True), nullable=True,
                  comment="Fecha y hora de rechazo")
    )

    print("[5/5] Restaurando campo motivo_rechazo...")
    op.add_column('facturas',
        sa.Column('motivo_rechazo', mysql.VARCHAR(length=1000), nullable=True,
                  comment="Motivo del rechazo de la factura")
    )

    # Restaurar constraints
    print("\n[6/7] Restaurando constraint chk_facturas_aprobada_con_aprobador...")
    op.create_check_constraint(
        'chk_facturas_aprobada_con_aprobador',
        'facturas',
        "(estado NOT IN ('aprobada', 'aprobada_auto')) OR "
        "(aprobado_por IS NOT NULL AND fecha_aprobacion IS NOT NULL)"
    )

    print("[7/7] Restaurando constraint chk_facturas_rechazada_con_motivo...")
    op.create_check_constraint(
        'chk_facturas_rechazada_con_motivo',
        'facturas',
        "estado != 'rechazada' OR "
        "(rechazado_por IS NOT NULL AND motivo_rechazo IS NOT NULL)"
    )

    print("\n[OK] Campos y constraints restaurados")
    print("="*80)
    print("\nADVERTENCIA: Columnas restauradas pero SIN datos")
    print("Ejecutar script de reversión para poblar datos desde workflow")
    print("="*80 + "\n")
