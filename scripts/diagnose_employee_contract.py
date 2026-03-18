#!/usr/bin/env python3
"""
Диагностика: почему сотрудник с ТГ ID 5577223137 числится уволенным при активном договоре 007-2025-000024.
Запуск на проде: docker compose exec web python scripts/diagnose_employee_contract.py
Или: DATABASE_URL=... python scripts/diagnose_employee_contract.py (из корня проекта)
"""

import asyncio
import sys
from pathlib import Path
from datetime import date

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, text
from core.database.session import get_async_session
from domain.entities.user import User


TELEGRAM_ID = 5577223137
CONTRACT_NUMBER = "007-2025-000024"


def _active_for_work(status: str, is_active: bool, termination_date) -> bool:
    if status != "active" or not is_active:
        return False
    if termination_date is None:
        return True
    return termination_date > date.today()


def _terminated_for_payroll(status: str, termination_date) -> bool:
    if status == "terminated":
        return True
    if status == "active" and termination_date is not None:
        return True
    return False


async def main():
    print(f"Проверка: пользователь telegram_id={TELEGRAM_ID}, договор №{CONTRACT_NUMBER}\n")
    async with get_async_session() as session:
        # Пользователь
        user_result = await session.execute(select(User).where(User.telegram_id == TELEGRAM_ID))
        user = user_result.scalar_one_or_none()
        if not user:
            print(f"❌ Пользователь с telegram_id={TELEGRAM_ID} не найден в БД.")
            return
        print(f"Пользователь: id={user.id}, telegram_id={user.telegram_id}, role={user.role}, roles={getattr(user, 'roles', None)}")

        # Договор по номеру (только нужные колонки — совместимость со старыми миграциями)
        row = await session.execute(
            text("""
                SELECT id, contract_number, owner_id, employee_id, status, is_active,
                       termination_date, terminated_at, allowed_objects
                FROM contracts WHERE contract_number = :num
            """),
            {"num": CONTRACT_NUMBER},
        )
        contract_row = row.mappings().first()
        if not contract_row:
            print(f"❌ Договор с номером {CONTRACT_NUMBER} не найден в БД.")
            return
        c = contract_row
        print(f"\nДоговор №{c['contract_number']}: id={c['id']}")
        print(f"  owner_id={c['owner_id']}, employee_id={c['employee_id']}")
        print(f"  status={c['status']!r}, is_active={c['is_active']}")
        print(f"  termination_date={c['termination_date']}, terminated_at={c['terminated_at']}")
        print(f"  allowed_objects={c['allowed_objects']}")

        if c["employee_id"] != user.id:
            print(f"\n⚠️  Договор привязан к другому сотруднику: employee_id={c['employee_id']} != user.id={user.id}")
            print("   Возможны два аккаунта с разными user.id для одного ТГ — проверьте дубликаты по telegram_id.")
        else:
            print(f"\n✓ employee_id договора совпадает с user.id ({user.id}).")

        active_for_work = _active_for_work(c["status"], c["is_active"], c["termination_date"])
        terminated_for_payroll = _terminated_for_payroll(c["status"], c["termination_date"])
        print(f"\nЛогика системы:")
        print(f"  is_contract_active_for_work (бот/смены): {active_for_work}")
        print(f"  is_contract_terminated_for_payroll (расчётные): {terminated_for_payroll}")

        if c["status"] != "active":
            print(f"\n→ Причина «уволенный»: у договора status={c['status']!r}, а не 'active'.")
        elif c["termination_date"] is not None:
            print(f"\n→ Причина: у договора задана дата увольнения termination_date={c['termination_date']}.")
            print("  Для работы контракт активен только если termination_date > сегодня.")
        elif not c["is_active"]:
            print(f"\n→ Причина: is_active=False.")
        else:
            print("\n→ По данным БД договор активен. Если в ЛК показывается «уволенный», проверьте:")
            print("  - для списка по объекту: у сотрудника может быть второй договор (старый, terminated) с тем же объектом — в карточке подставляется один из них.")

        # Все договоры этого сотрудника с этим владельцем
        all_rows = await session.execute(
            text("""
                SELECT id, contract_number, status, termination_date
                FROM contracts
                WHERE employee_id = :eid AND owner_id = :oid
                ORDER BY id
            """),
            {"eid": user.id, "oid": c["owner_id"]},
        )
        all_contracts = all_rows.mappings().all()
        if len(all_contracts) > 1:
            print(f"\nВсего договоров у этого сотрудника с владельцем owner_id={c['owner_id']}: {len(all_contracts)}")
            for r in all_contracts:
                print(f"  - id={r['id']}, №{r['contract_number']}, status={r['status']}, termination_date={r['termination_date']}")


if __name__ == "__main__":
    asyncio.run(main())
