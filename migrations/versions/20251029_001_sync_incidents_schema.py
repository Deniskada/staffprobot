"""
Sync incidents schema with dev: add suggested_adjustments, indexes, and FKs

Revision ID: 20251029_001
Revises: 78851600b877
Create Date: 2025-10-29 20:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251029_001'
down_revision = '78851600b877'
branch_labels = None
depends_on = None


def upgrade():
    # Add suggested_adjustments column if missing (idempotent)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('incidents')]
    if 'suggested_adjustments' not in columns:
        with op.batch_alter_table('incidents') as batch_op:
            batch_op.add_column(sa.Column('suggested_adjustments', sa.Text(), nullable=True))

    # Create index on id only if not exists
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('incidents')}
    if 'ix_incidents_id' not in existing_indexes:
        op.create_index('ix_incidents_id', 'incidents', ['id'])

    # Create foreign keys only if not exists
    existing_fks = {fk['name'] for fk in inspector.get_foreign_keys('incidents') if fk.get('name')}

    if 'incidents_created_by_fkey' not in existing_fks:
        op.create_foreign_key('incidents_created_by_fkey', 'incidents', 'users', ['created_by'], ['id'])
    if 'incidents_employee_id_fkey' not in existing_fks:
        op.create_foreign_key('incidents_employee_id_fkey', 'incidents', 'users', ['employee_id'], ['id'])
    if 'incidents_object_id_fkey' not in existing_fks:
        op.create_foreign_key('incidents_object_id_fkey', 'incidents', 'objects', ['object_id'], ['id'])
    if 'incidents_owner_id_fkey' not in existing_fks:
        op.create_foreign_key('incidents_owner_id_fkey', 'incidents', 'users', ['owner_id'], ['id'])
    if 'incidents_shift_schedule_id_fkey' not in existing_fks:
        op.create_foreign_key('incidents_shift_schedule_id_fkey', 'incidents', 'shift_schedules', ['shift_schedule_id'], ['id'])


def downgrade():
    # Drop foreign keys (safe if exist)
    for fk in [
        'incidents_shift_schedule_id_fkey',
        'incidents_owner_id_fkey',
        'incidents_object_id_fkey',
        'incidents_employee_id_fkey',
        'incidents_created_by_fkey',
    ]:
        try:
            op.drop_constraint(fk, 'incidents', type_='foreignkey')
        except Exception:
            pass

    # Drop index
    try:
        op.drop_index('ix_incidents_id', table_name='incidents')
    except Exception:
        pass

    # Drop column
    with op.batch_alter_table('incidents') as batch_op:
        try:
            batch_op.drop_column('suggested_adjustments')
        except Exception:
            pass


