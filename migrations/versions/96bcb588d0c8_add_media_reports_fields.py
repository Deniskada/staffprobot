"""add_media_reports_fields

Revision ID: 96bcb588d0c8
Revises: e6381c327d9e
Create Date: 2025-10-11 12:58:56.263558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96bcb588d0c8'
down_revision: Union[str, Sequence[str], None] = 'e6381c327d9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Object: добавляем поля для Telegram группы отчетов
    op.add_column('objects', sa.Column('telegram_report_chat_id', sa.String(100), nullable=True))
    op.add_column('objects', sa.Column('inherit_telegram_chat', sa.Boolean(), server_default='true', nullable=False))
    
    # OrgStructureUnit: добавляем поле для Telegram группы отчетов
    op.add_column('org_structure_units', sa.Column('telegram_report_chat_id', sa.String(100), nullable=True))
    
    # TimeslotTaskTemplate: добавляем поля для фото/видео отчетов
    op.add_column('timeslot_task_templates', sa.Column('requires_media', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('timeslot_task_templates', sa.Column('media_types', sa.Text(), server_default='photo,video', nullable=True))
    
    # Создаем индексы для быстрого поиска объектов и подразделений с настроенными группами
    op.create_index('ix_objects_telegram_report_chat_id', 'objects', ['telegram_report_chat_id'])
    op.create_index('ix_org_structure_units_telegram_report_chat_id', 'org_structure_units', ['telegram_report_chat_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индексы
    op.drop_index('ix_org_structure_units_telegram_report_chat_id', table_name='org_structure_units')
    op.drop_index('ix_objects_telegram_report_chat_id', table_name='objects')
    
    # Удаляем столбцы из TimeslotTaskTemplate
    op.drop_column('timeslot_task_templates', 'media_types')
    op.drop_column('timeslot_task_templates', 'requires_media')
    
    # Удаляем столбец из OrgStructureUnit
    op.drop_column('org_structure_units', 'telegram_report_chat_id')
    
    # Удаляем столбцы из Object
    op.drop_column('objects', 'inherit_telegram_chat')
    op.drop_column('objects', 'telegram_report_chat_id')
