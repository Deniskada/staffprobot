"""merge offer_edo and profile_docs heads

Revision ID: 20260301_merge
Revises: offer_edo_260215, 20260228_profile_docs
Create Date: 2026-03-01
"""
from typing import Sequence, Union

revision: str = '20260301_merge'
down_revision: tuple = ('offer_edo_260215', '20260228_profile_docs')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
