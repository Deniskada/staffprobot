"""cancel_specific_shifts

Revision ID: f3b3bb8c9a1f
Revises: e1196d40bbd1
Create Date: 2025-11-13 12:20:00.000000
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f3b3bb8c9a1f'
down_revision: Union[str, Sequence[str], None] = 'e1196d40bbd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Mark problematic shifts as cancelled."""
    op.execute(
        """
        UPDATE shifts
        SET status = 'cancelled'
        WHERE id IN (608, 816)
           OR schedule_id IN (608, 816);
        """
    )

    op.execute(
        """
        UPDATE shift_schedules
        SET status = 'cancelled'
        WHERE id IN (608, 816);
        """
    )


def downgrade() -> None:
    """Manual rollback required."""
    raise NotImplementedError('Downgrade is not supported for data-fix migration f3b3bb8c9a1f.')
