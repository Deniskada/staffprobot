from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251023_001'
down_revision = '20251022_001_add_cancellation_reasons'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('scope', sa.String(length=50), nullable=False),
        sa.Column('condition_json', sa.Text(), nullable=False),
        sa.Column('action_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    )
    op.create_index('ix_rules_owner_id', 'rules', ['owner_id'])
    op.create_index('ix_rules_code', 'rules', ['code'])
    op.create_index('ix_rules_scope', 'rules', ['scope'])

    op.create_table(
        'task_templates_v2',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('org_unit_id', sa.Integer(), nullable=True),
        sa.Column('object_id', sa.Integer(), nullable=True),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('requires_media', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('default_bonus_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    )
    op.create_index('ix_task_templates_v2_owner_id', 'task_templates_v2', ['owner_id'])
    op.create_index('ix_task_templates_v2_org_unit_id', 'task_templates_v2', ['org_unit_id'])
    op.create_index('ix_task_templates_v2_object_id', 'task_templates_v2', ['object_id'])
    op.create_index('ix_task_templates_v2_code', 'task_templates_v2', ['code'])

    op.create_table(
        'task_plans_v2',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('object_id', sa.Integer(), nullable=True),
        sa.Column('time_slot_id', sa.Integer(), nullable=True),
        sa.Column('planned_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    )
    op.create_index('ix_task_plans_v2_template_id', 'task_plans_v2', ['template_id'])
    op.create_index('ix_task_plans_v2_owner_id', 'task_plans_v2', ['owner_id'])
    op.create_index('ix_task_plans_v2_object_id', 'task_plans_v2', ['object_id'])
    op.create_index('ix_task_plans_v2_time_slot_id', 'task_plans_v2', ['time_slot_id'])

    op.create_table(
        'task_entries_v2',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('plan_id', sa.Integer(), nullable=True),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('shift_schedule_id', sa.Integer(), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('requires_media', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    )
    op.create_index('ix_task_entries_v2_plan_id', 'task_entries_v2', ['plan_id'])
    op.create_index('ix_task_entries_v2_template_id', 'task_entries_v2', ['template_id'])
    op.create_index('ix_task_entries_v2_shift_schedule_id', 'task_entries_v2', ['shift_schedule_id'])
    op.create_index('ix_task_entries_v2_employee_id', 'task_entries_v2', ['employee_id'])

    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('object_id', sa.Integer(), nullable=True),
        sa.Column('shift_schedule_id', sa.Integer(), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='new'),
        sa.Column('reason_code', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('evidence_media_ids', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    )
    op.create_index('ix_incidents_owner_id', 'incidents', ['owner_id'])
    op.create_index('ix_incidents_object_id', 'incidents', ['object_id'])
    op.create_index('ix_incidents_shift_schedule_id', 'incidents', ['shift_schedule_id'])
    op.create_index('ix_incidents_employee_id', 'incidents', ['employee_id'])


def downgrade() -> None:
    op.drop_index('ix_incidents_employee_id', table_name='incidents')
    op.drop_index('ix_incidents_shift_schedule_id', table_name='incidents')
    op.drop_index('ix_incidents_object_id', table_name='incidents')
    op.drop_index('ix_incidents_owner_id', table_name='incidents')
    op.drop_table('incidents')

    op.drop_index('ix_task_entries_v2_employee_id', table_name='task_entries_v2')
    op.drop_index('ix_task_entries_v2_shift_schedule_id', table_name='task_entries_v2')
    op.drop_index('ix_task_entries_v2_template_id', table_name='task_entries_v2')
    op.drop_index('ix_task_entries_v2_plan_id', table_name='task_entries_v2')
    op.drop_table('task_entries_v2')

    op.drop_index('ix_task_plans_v2_time_slot_id', table_name='task_plans_v2')
    op.drop_index('ix_task_plans_v2_object_id', table_name='task_plans_v2')
    op.drop_index('ix_task_plans_v2_owner_id', table_name='task_plans_v2')
    op.drop_index('ix_task_plans_v2_template_id', table_name='task_plans_v2')
    op.drop_table('task_plans_v2')

    op.drop_index('ix_task_templates_v2_code', table_name='task_templates_v2')
    op.drop_index('ix_task_templates_v2_object_id', table_name='task_templates_v2')
    op.drop_index('ix_task_templates_v2_org_unit_id', table_name='task_templates_v2')
    op.drop_index('ix_task_templates_v2_owner_id', table_name='task_templates_v2')
    op.drop_table('task_templates_v2')

    op.drop_index('ix_rules_scope', table_name='rules')
    op.drop_index('ix_rules_code', table_name='rules')
    op.drop_index('ix_rules_owner_id', table_name='rules')
    op.drop_table('rules')


