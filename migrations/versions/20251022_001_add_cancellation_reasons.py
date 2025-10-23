"""add cancellation_reasons table

Revision ID: 20251022_001
Revises: 
Create Date: 2025-10-22 21:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251022_001'
down_revision = 'f7b35e4d704c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'cancellation_reasons',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('requires_document', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('treated_as_valid', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_employee_visible', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    # Индекс по owner_id уже создается благодаря index=True в определении столбца
    op.create_unique_constraint('uq_cancellation_reasons_owner_code', 'cancellation_reasons', ['owner_id', 'code'])

    # Seed global default reasons (owner_id = NULL)
    from sqlalchemy.sql import table, column
    from sqlalchemy import Integer, String, Boolean, DateTime

    reasons_table = table(
        'cancellation_reasons',
        column('owner_id', Integer),
        column('code', String),
        column('title', String),
        column('requires_document', Boolean),
        column('treated_as_valid', Boolean),
        column('is_active', Boolean),
        column('is_employee_visible', Boolean),
        column('order_index', Integer),
    )

    op.bulk_insert(
        reasons_table,
        [
            {
                'owner_id': None,
                'code': 'medical_cert',
                'title': 'Медицинская справка',
                'requires_document': True,
                'treated_as_valid': True,
                'is_active': True,
                'is_employee_visible': True,
                'order_index': 10,
            },
            {
                'owner_id': None,
                'code': 'emergency_cert',
                'title': 'Справка от МЧС',
                'requires_document': True,
                'treated_as_valid': True,
                'is_active': True,
                'is_employee_visible': True,
                'order_index': 11,
            },
            {
                'owner_id': None,
                'code': 'police_cert',
                'title': 'Справка от полиции',
                'requires_document': True,
                'treated_as_valid': True,
                'is_active': True,
                'is_employee_visible': True,
                'order_index': 12,
            },
            {
                'owner_id': None,
                'code': 'illness',
                'title': 'Болезнь',
                'requires_document': False,
                'treated_as_valid': False,
                'is_active': True,
                'is_employee_visible': True,
                'order_index': 1,
            },
            {
                'owner_id': None,
                'code': 'family',
                'title': 'Семейные обстоятельства',
                'requires_document': False,
                'treated_as_valid': False,
                'is_active': True,
                'is_employee_visible': True,
                'order_index': 2,
            },
            {
                'owner_id': None,
                'code': 'transport',
                'title': 'Проблемы с транспортом',
                'requires_document': False,
                'treated_as_valid': False,
                'is_active': True,
                'is_employee_visible': True,
                'order_index': 3,
            },
            {
                'owner_id': None,
                'code': 'other',
                'title': 'Другая причина',
                'requires_document': False,
                'treated_as_valid': False,
                'is_active': True,
                'is_employee_visible': True,
                'order_index': 4,
            },
            # System/internal reasons (not visible to employee)
            {
                'owner_id': None,
                'code': 'short_notice',
                'title': 'Отмена в короткий срок',
                'requires_document': False,
                'treated_as_valid': False,
                'is_active': True,
                'is_employee_visible': False,
                'order_index': 90,
            },
            {
                'owner_id': None,
                'code': 'no_reason',
                'title': 'Без указания причины',
                'requires_document': False,
                'treated_as_valid': False,
                'is_active': True,
                'is_employee_visible': False,
                'order_index': 91,
            },
            {
                'owner_id': None,
                'code': 'owner_decision',
                'title': 'Решение владельца',
                'requires_document': False,
                'treated_as_valid': False,
                'is_active': True,
                'is_employee_visible': False,
                'order_index': 92,
            },
            {
                'owner_id': None,
                'code': 'contract_termination',
                'title': 'Расторжение договора',
                'requires_document': False,
                'treated_as_valid': False,
                'is_active': True,
                'is_employee_visible': False,
                'order_index': 93,
            },
        ]
    )


def downgrade() -> None:
    op.drop_constraint('uq_cancellation_reasons_owner_code', 'cancellation_reasons', type_='unique')
    op.drop_index('ix_cancellation_reasons_owner_id', table_name='cancellation_reasons')
    op.drop_table('cancellation_reasons')


