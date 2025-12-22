"""Merge data quality fixes with assignment tracking (PHASE 3 + aprobada_por cleanup)

Revision ID: b24d5353830d
Revises: phase3_estado_asignacion_2025, f1d7a2e3b4c5
Create Date: 2025-10-22 23:20:56.681135

ENTERPRISE MERGE: Unifies two independent data quality improvements
================================================================

CONTEXT:
Two parallel improvements were developed on separate branches from revision a40e54d122a3:

Branch 1 - PHASE 3 Assignment Tracking (phase3_estado_asignacion_2025):
  - Implements complete assignment lifecycle tracking
  - Adds estado_asignacion field to facturas table
  - Creates automated triggers for data consistency
  - Enables dashboard filtering and audit trails

Branch 2 - Data Quality Fix (f1d7a2e3b4c5):
  - Fixes corrupted aprobada_por/rechazada_por fields in workflow_aprobacion_facturas
  - Converts numeric IDs to actual user names
  - Resolves historical data quality issues

COMPATIBILITY ANALYSIS:
✓ No schema conflicts - different tables (facturas vs workflow_aprobacion_facturas)
✓ No data conflicts - independent operations
✓ Safe to merge without additional migration code

CORPORATE RATIONALE:
This merge maintains clean migration history while preserving both improvements.
Both features are production-ready and complement the overall data integrity strategy.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b24d5353830d'
down_revision: Union[str, Sequence[str], None] = ('phase3_estado_asignacion_2025', 'f1d7a2e3b4c5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
