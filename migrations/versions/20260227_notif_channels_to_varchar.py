"""Convert notifications channel/status/priority from ENUM to VARCHAR.

Revision ID: 20260227_notif_ch_varchar
Revises: 20260227_notif_type_varchar
Create Date: 2026-02-27
"""
from alembic import op

revision = '20260227_notif_ch_varchar'
down_revision = '20260227_notif_type_varchar'
branch_labels = None
depends_on = None


def upgrade():
    for col, enum_type in [
        ('channel', 'notificationchannel'),
        ('status', 'notificationstatus'),
        ('priority', 'notificationpriority'),
    ]:
        op.execute(f"""
            ALTER TABLE notifications
            ALTER COLUMN {col} TYPE VARCHAR(50)
            USING {col}::text
        """)
        op.execute(f"DROP TYPE IF EXISTS {enum_type} CASCADE")


def downgrade():
    pass  # Необратимо — восстановление ENUM нецелесообразно
