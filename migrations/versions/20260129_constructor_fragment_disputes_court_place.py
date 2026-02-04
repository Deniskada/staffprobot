"""Фрагмент «Разрешение споров»: подсудность через court_place (label), не _option.

Revision ID: frag_disputes_260129
Revises: cond_steps_260129
Create Date: 2026-01-29
"""
from typing import Sequence, Union
from alembic import op

revision: str = "frag_disputes_260129"
down_revision: Union[str, Sequence[str], None] = "cond_steps_260129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import text
    conn = op.get_bind()
    new_content = (
        "<p><strong>11. Разрешение споров</strong></p>"
        "<p>Претензия {{ claim_required }} {{ claim_days }} дн. Подсудность: {{ court_place }}.</p>"
    )
    conn.execute(
        text("UPDATE constructor_fragments SET fragment_content = :c WHERE id = 19"),
        {"c": new_content},
    )


def downgrade() -> None:
    from sqlalchemy import text
    conn = op.get_bind()
    old_content = (
        "<p><strong>11. Разрешение споров</strong></p>"
        "<p>Претензия {{ claim_required }} {{ claim_days }} дн. Подсудность: {{ _option }}.</p>"
    )
    conn.execute(
        text("UPDATE constructor_fragments SET fragment_content = :c WHERE id = 19"),
        {"c": old_content},
    )
