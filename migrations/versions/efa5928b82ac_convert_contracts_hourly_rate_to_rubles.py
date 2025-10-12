"""convert_contracts_hourly_rate_to_rubles

Преобразование contracts.hourly_rate из копеек (Integer) в рубли (Numeric).

Revision ID: efa5928b82ac
Revises: abcd1234
Create Date: 2025-10-09 12:50:44.060422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'efa5928b82ac'
down_revision: Union[str, Sequence[str], None] = 'abcd1234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Преобразование hourly_rate: копейки (Integer) → рубли (Numeric)."""
    
    # Шаг 1: Создать временный столбец
    op.add_column('contracts', 
        sa.Column('hourly_rate_temp', sa.Numeric(10, 2), nullable=True)
    )
    
    # Шаг 2: Преобразовать данные (копейки → рубли)
    op.execute("""
        UPDATE contracts 
        SET hourly_rate_temp = CAST(hourly_rate AS NUMERIC) / 100.0
        WHERE hourly_rate IS NOT NULL
    """)
    
    # Шаг 3: Удалить старый столбец
    op.drop_column('contracts', 'hourly_rate')
    
    # Шаг 4: Переименовать временный столбец
    op.alter_column('contracts', 'hourly_rate_temp', new_column_name='hourly_rate')
    
    # Шаг 5: Добавить комментарий
    op.execute("COMMENT ON COLUMN contracts.hourly_rate IS 'Почасовая ставка в рублях'")


def downgrade() -> None:
    """Обратное преобразование: рубли (Numeric) → копейки (Integer)."""
    
    # Шаг 1: Создать временный столбец
    op.add_column('contracts', 
        sa.Column('hourly_rate_temp', sa.Integer, nullable=True)
    )
    
    # Шаг 2: Обратное преобразование (рубли → копейки)
    op.execute("""
        UPDATE contracts 
        SET hourly_rate_temp = CAST(hourly_rate * 100 AS INTEGER)
        WHERE hourly_rate IS NOT NULL
    """)
    
    # Шаг 3: Удалить текущий столбец
    op.drop_column('contracts', 'hourly_rate')
    
    # Шаг 4: Переименовать временный столбец
    op.alter_column('contracts', 'hourly_rate_temp', new_column_name='hourly_rate')
    
    # Шаг 5: Вернуть комментарий
    op.execute("COMMENT ON COLUMN contracts.hourly_rate IS 'Почасовая ставка в копейках'")
