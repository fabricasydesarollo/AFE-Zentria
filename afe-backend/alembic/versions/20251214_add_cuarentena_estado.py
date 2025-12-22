"""add_cuarentena_estado

Revision ID: 20251214_cuarentena
Revises: f81c62d7acc9
Create Date: 2025-12-14

MULTI-TENANT 2025-12-14:
Agrega estado "en_cuarentena" para facturas sin grupo_id asignado.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251214_cuarentena'
down_revision = '2025_12_04_responsables'
branch_labels = None
depends_on = None


def upgrade():
    """
    Agrega estado "en_cuarentena" al enum EstadoFactura.

    IMPORTANTE: En MySQL, alterar enums requiere recrear la columna.
    """
    # MySQL: Alterar enum agregando nuevo valor
    op.execute("""
        ALTER TABLE facturas
        MODIFY COLUMN estado
        ENUM(
            'en_cuarentena',
            'en_revision',
            'aprobada',
            'aprobada_auto',
            'rechazada',
            'validada_contabilidad',
            'devuelta_contabilidad'
        )
        NOT NULL
        DEFAULT 'en_revision'
    """)


def downgrade():
    """
    Remueve estado "en_cuarentena" del enum.

    ADVERTENCIA: Si existen facturas con estado "en_cuarentena",
    esta migración fallará o cambiará su estado.
    """
    # Primero, cambiar facturas en cuarentena a en_revision
    op.execute("""
        UPDATE facturas
        SET estado = 'en_revision'
        WHERE estado = 'en_cuarentena'
    """)

    # Luego, remover valor del enum
    op.execute("""
        ALTER TABLE facturas
        MODIFY COLUMN estado
        ENUM(
            'en_revision',
            'aprobada',
            'aprobada_auto',
            'rechazada',
            'validada_contabilidad',
            'devuelta_contabilidad'
        )
        NOT NULL
        DEFAULT 'en_revision'
    """)
