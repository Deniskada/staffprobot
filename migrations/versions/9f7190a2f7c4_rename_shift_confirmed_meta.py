"""Rename shift_confirmed notification meta title."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "9f7190a2f7c4"
down_revision = "f3b3bb8c9a1f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE notification_types_meta
        SET title = 'Уведомление о планировании смены сотрудником',
            description = 'Сообщает владельцу, что сотрудник запланировал смену через веб-интерфейс или бота'
        WHERE type_code = 'shift_confirmed'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE notification_types_meta
        SET title = 'Смена подтверждена',
            description = 'Уведомляет о подтверждении смены сотрудником'
        WHERE type_code = 'shift_confirmed'
        """
    )

