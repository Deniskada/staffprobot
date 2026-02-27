"""Convert notifications.type from ENUM to VARCHAR(50).

Revision ID: 20260227_notification_type_varchar
Revises: incident_types_260207
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

revision = '20260227_notif_type_varchar'
down_revision = 'incident_types_260207'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE notifications
        ALTER COLUMN type TYPE VARCHAR(50)
        USING type::text
    """)
    op.execute("""
        ALTER TABLE notification_templates
        ALTER COLUMN type TYPE VARCHAR(50)
        USING type::text
    """)
    op.execute("""
        ALTER TABLE payment_notifications
        ALTER COLUMN notification_type TYPE VARCHAR(50)
        USING notification_type::text
    """)
    op.execute("DROP TYPE IF EXISTS notificationtype")


def downgrade():
    op.execute("""
        CREATE TYPE notificationtype AS ENUM (
            'shift_reminder', 'shift_confirmed', 'shift_cancelled',
            'shift_started', 'shift_completed', 'shift_did_not_start',
            'object_opened', 'object_closed', 'object_late_opening',
            'object_no_shifts_today', 'object_early_closing',
            'contract_signed', 'contract_terminated', 'contract_expiring', 'contract_updated',
            'offer_sent', 'offer_accepted', 'offer_rejected', 'offer_terms_changed',
            'kyc_required', 'kyc_verified', 'kyc_failed',
            'review_received', 'review_moderated', 'appeal_submitted', 'appeal_decision',
            'payment_due', 'payment_success', 'payment_failed',
            'subscription_expiring', 'subscription_expired',
            'usage_limit_warning', 'usage_limit_exceeded',
            'task_assigned', 'task_completed', 'task_overdue',
            'incident_created', 'incident_resolved', 'incident_rejected', 'incident_cancelled',
            'welcome', 'password_reset', 'account_suspended', 'account_activated',
            'system_maintenance', 'feature_announcement'
        )
    """)
    op.execute("""
        ALTER TABLE notifications
        ALTER COLUMN type TYPE notificationtype
        USING type::notificationtype
    """)
