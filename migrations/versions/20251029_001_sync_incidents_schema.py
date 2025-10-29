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
    # Add suggested_adjustments column if missing
    with op.batch_alter_table('incidents') as batch_op:
        batch_op.add_column(sa.Column('suggested_adjustments', sa.Text(), nullable=True))

    # Create index on id to match dev (redundant but for parity)
    try:
        op.create_index('ix_incidents_id', 'incidents', ['id'])
    except Exception:
        # Index may already exist
        pass

    # Create foreign keys if missing
    # Note: use explicit names to match dev
    try:
        op.create_foreign_key('incidents_created_by_fkey', 'incidents', 'users', ['created_by'], ['id'])
    except Exception:
        pass
    try:
        op.create_foreign_key('incidents_employee_id_fkey', 'incidents', 'users', ['employee_id'], ['id'])
    except Exception:
        pass
    try:
        op.create_foreign_key('incidents_object_id_fkey', 'incidents', 'objects', ['object_id'], ['id'])
    except Exception:
        pass
    try:
        op.create_foreign_key('incidents_owner_id_fkey', 'incidents', 'users', ['owner_id'], ['id'])
    except Exception:
        pass
    try:
        op.create_foreign_key('incidents_shift_schedule_id_fkey', 'incidents', 'shift_schedules', ['shift_schedule_id'], ['id'])
    except Exception:
        pass


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


