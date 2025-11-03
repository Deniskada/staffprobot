"""create_devops_tables

Revision ID: 26f081e4388f
Revises: 0827df3c36e3
Create Date: 2025-11-03 01:10:04.011340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26f081e4388f'
down_revision: Union[str, Sequence[str], None] = '0827df3c36e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Таблица для отчетов о багах
    op.create_table(
        'bug_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('what_doing', sa.Text(), nullable=False),
        sa.Column('expected', sa.Text(), nullable=False),
        sa.Column('actual', sa.Text(), nullable=False),
        sa.Column('screenshot_url', sa.String(length=500), nullable=True),
        sa.Column('priority', sa.String(length=20), server_default='medium', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='open', nullable=False),
        sa.Column('github_issue_number', sa.Integer(), nullable=True),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_bug_logs_user', 'bug_logs', ['user_id'])
    op.create_index('idx_bug_logs_status', 'bug_logs', ['status'])
    op.create_index('idx_bug_logs_priority', 'bug_logs', ['priority'])
    
    # Таблица для журнала изменений/улучшений
    op.create_table(
        'changelog_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=False),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('commit_sha', sa.String(length=40), nullable=True),
        sa.Column('github_issue', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('impact_score', sa.Float(), nullable=True),
        sa.Column('indexed_in_brain', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_changelog_component', 'changelog_entries', ['component'])
    op.create_index('idx_changelog_status', 'changelog_entries', ['status'])
    op.create_index('idx_changelog_type', 'changelog_entries', ['change_type'])
    
    # Таблица для деплоев (DORA метрики)
    op.create_table(
        'deployments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('commit_sha', sa.String(length=40), nullable=False),
        sa.Column('commit_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('triggered_by', sa.String(length=100), nullable=True),
        sa.Column('tests_passed', sa.Integer(), nullable=True),
        sa.Column('tests_failed', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_deployments_sha', 'deployments', ['commit_sha'])
    op.create_index('idx_deployments_status', 'deployments', ['status'])
    op.create_index('idx_deployments_date', 'deployments', ['started_at'])
    
    # Таблица incidents уже существует, пропускаем создание
    # Но добавим недостающие индексы если их нет
    try:
        op.create_index('idx_incidents_severity', 'incidents', ['severity'], if_not_exists=True)
    except:
        pass
    try:
        op.create_index('idx_incidents_date', 'incidents', ['detected_at'], if_not_exists=True)
    except:
        pass
    
    # Таблица для FAQ
    op.create_table(
        'faq_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), server_default='0', nullable=False),
        sa.Column('views_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('helpful_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_faq_category', 'faq_entries', ['category'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_faq_category', table_name='faq_entries')
    op.drop_table('faq_entries')
    
    # Таблица incidents не удаляется, т.к. существовала до этой миграции
    
    op.drop_index('idx_deployments_date', table_name='deployments')
    op.drop_index('idx_deployments_status', table_name='deployments')
    op.drop_index('idx_deployments_sha', table_name='deployments')
    op.drop_table('deployments')
    
    op.drop_index('idx_changelog_type', table_name='changelog_entries')
    op.drop_index('idx_changelog_status', table_name='changelog_entries')
    op.drop_index('idx_changelog_component', table_name='changelog_entries')
    op.drop_table('changelog_entries')
    
    op.drop_index('idx_bug_logs_priority', table_name='bug_logs')
    op.drop_index('idx_bug_logs_status', table_name='bug_logs')
    op.drop_index('idx_bug_logs_user', table_name='bug_logs')
    op.drop_table('bug_logs')
