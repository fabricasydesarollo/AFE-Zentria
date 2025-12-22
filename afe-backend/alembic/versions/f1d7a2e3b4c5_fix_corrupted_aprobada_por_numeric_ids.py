"""
Fix corrupted aprobada_por field - convert numeric IDs to actual names.

Revision ID: f1d7a2e3b4c5
Revises: a40e54d122a3
Create Date: 2025-10-22 21:30:00.000000

This migration fixes workflows where aprobada_por was stored as a numeric ID
instead of the user's actual name (e.g., '5' instead of 'Alex').

The issue occurred due to a bug in earlier versions where responsable IDs
were being saved directly instead of the responsable's nombre field.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'f1d7a2e3b4c5'
down_revision = 'a40e54d122a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Find workflows where aprobada_por or rechazada_por are pure numbers and convert to actual names.
    """
    bind = op.get_bind()
    session = Session(bind=bind)

    try:
        # Fix aprobada_por (MySQL syntax)
        query_aprobada = text("""
            UPDATE workflow_aprobacion_facturas waf
            INNER JOIN responsables r ON CAST(waf.aprobada_por AS UNSIGNED) = r.id
            SET waf.aprobada_por = r.nombre
            WHERE waf.aprobada_por REGEXP '^[0-9]+$'
            AND waf.aprobada = true
        """)
        session.execute(query_aprobada)

        # Fix rechazada_por (MySQL syntax)
        query_rechazada = text("""
            UPDATE workflow_aprobacion_facturas waf
            INNER JOIN responsables r ON CAST(waf.rechazada_por AS UNSIGNED) = r.id
            SET waf.rechazada_por = r.nombre
            WHERE waf.rechazada_por REGEXP '^[0-9]+$'
            AND waf.rechazada = true
        """)
        session.execute(query_rechazada)

        session.commit()

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def downgrade() -> None:
    """
    Rollback would require storing the original numeric ID mapping, which is not feasible.
    This migration is one-way due to data loss potential.
    """
    pass
