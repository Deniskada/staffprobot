"""add profile_documents table and contract.rejection_reason

Revision ID: 20260228_profile_docs
Revises: 20260227_holiday_greeting
Create Date: 2026-02-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '20260228_profile_docs'
down_revision: Union[str, Sequence[str], None] = '20260227_holiday_greeting'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'profile_documents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('profile_id', sa.Integer(), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('document_type', sa.String(50), nullable=False, index=True),
        sa.Column('file_key', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.add_column('contracts', sa.Column('rejection_reason', sa.String(1000), nullable=True))


def downgrade() -> None:
    op.drop_column('contracts', 'rejection_reason')
    op.drop_table('profile_documents')
