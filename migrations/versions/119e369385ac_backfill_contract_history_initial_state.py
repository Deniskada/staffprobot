"""backfill_contract_history_initial_state

Revision ID: 119e369385ac
Revises: 7d8bbe751a44
Create Date: 2026-01-15 15:13:05.392593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '119e369385ac'
down_revision: Union[str, Sequence[str], None] = '7d8bbe751a44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Заполняем начальную историю для всех существующих договоров
    # Создаем записи с текущим состоянием всех отслеживаемых полей
    op.execute("""
        INSERT INTO contract_history (
            contract_id,
            changed_at,
            changed_by,
            change_type,
            field_name,
            old_value,
            new_value,
            change_reason,
            effective_from,
            change_metadata
        )
        SELECT 
            c.id AS contract_id,
            COALESCE(c.created_at, NOW()) AS changed_at,
            c.owner_id AS changed_by,
            'created' AS change_type,
            field_name,
            NULL AS old_value,
            CASE 
                WHEN field_name = 'hourly_rate' THEN to_jsonb(c.hourly_rate)
                WHEN field_name = 'use_contract_rate' THEN to_jsonb(c.use_contract_rate)
                WHEN field_name = 'payment_schedule_id' THEN to_jsonb(c.payment_schedule_id)
                WHEN field_name = 'inherit_payment_schedule' THEN to_jsonb(COALESCE(c.inherit_payment_schedule, true))
                WHEN field_name = 'payment_system_id' THEN to_jsonb(c.payment_system_id)
                WHEN field_name = 'use_contract_payment_system' THEN to_jsonb(c.use_contract_payment_system)
                WHEN field_name = 'status' THEN to_jsonb(c.status)
                WHEN field_name = 'allowed_objects' THEN to_jsonb(c.allowed_objects)
                WHEN field_name = 'title' THEN to_jsonb(c.title)
                WHEN field_name = 'template_id' THEN to_jsonb(c.template_id)
                ELSE NULL
            END AS new_value,
            NULL AS change_reason,
            NULL AS effective_from,
            NULL AS change_metadata
        FROM contracts c
        CROSS JOIN (
            SELECT 'hourly_rate' AS field_name
            UNION ALL SELECT 'use_contract_rate'
            UNION ALL SELECT 'payment_schedule_id'
            UNION ALL SELECT 'inherit_payment_schedule'
            UNION ALL SELECT 'payment_system_id'
            UNION ALL SELECT 'use_contract_payment_system'
            UNION ALL SELECT 'status'
            UNION ALL SELECT 'allowed_objects'
            UNION ALL SELECT 'title'
            UNION ALL SELECT 'template_id'
        ) AS fields
        WHERE NOT EXISTS (
            SELECT 1 FROM contract_history ch 
            WHERE ch.contract_id = c.id 
            AND ch.field_name = fields.field_name
            AND ch.change_type = 'created'
        )
        AND (
            (fields.field_name = 'hourly_rate' AND c.hourly_rate IS NOT NULL)
            OR (fields.field_name = 'use_contract_rate')
            OR (fields.field_name = 'payment_schedule_id' AND c.payment_schedule_id IS NOT NULL)
            OR (fields.field_name = 'inherit_payment_schedule')
            OR (fields.field_name = 'payment_system_id' AND c.payment_system_id IS NOT NULL)
            OR (fields.field_name = 'use_contract_payment_system')
            OR (fields.field_name = 'status')
            OR (fields.field_name = 'allowed_objects' AND c.allowed_objects IS NOT NULL)
            OR (fields.field_name = 'title' AND c.title IS NOT NULL)
            OR (fields.field_name = 'template_id' AND c.template_id IS NOT NULL)
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем начальные записи истории (с change_type='created')
    op.execute("""
        DELETE FROM contract_history 
        WHERE change_type = 'created'
        AND changed_at < (SELECT MIN(changed_at) FROM contract_history WHERE change_type = 'updated' OR change_type = 'status_changed');
    """)
