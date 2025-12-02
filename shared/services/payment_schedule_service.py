"""Утилиты для работы с графиками выплат."""

from datetime import date, timedelta
from typing import Optional, Dict

from domain.entities.payment_schedule import PaymentSchedule


async def get_payment_period_for_date(
    schedule: PaymentSchedule,
    target_date: date,
) -> Optional[Dict[str, date]]:
    """
    Определяет период выплаты для заданной даты по графику.

    Args:
        schedule: График выплат
        target_date: Дата, для которой проверяем

    Returns:
        dict: {'period_start': date, 'period_end': date} или None, если день не является датой выплаты
    """

    if not schedule.payment_period:
        return None

    # Еженедельные графики
    if schedule.frequency == "weekly":
        target_weekday = target_date.weekday() + 1  # 1=Пн ... 7=Вс

        if target_weekday != schedule.payment_day:
            return None

        period_config = schedule.payment_period
        start_offset = period_config.get("start_offset", -22)
        end_offset = period_config.get("end_offset", -16)

        period_start = target_date + timedelta(days=start_offset)
        period_end = target_date + timedelta(days=end_offset)

        return {"period_start": period_start, "period_end": period_end}

    # Двухнедельные графики
    if schedule.frequency == "biweekly":
        target_weekday = target_date.weekday() + 1

        if target_weekday != schedule.payment_day:
            return None

        period_config = schedule.payment_period
        start_offset = period_config.get("start_offset", -28)
        end_offset = period_config.get("end_offset", -14)

        period_start = target_date + timedelta(days=start_offset)
        period_end = target_date + timedelta(days=end_offset)

        return {"period_start": period_start, "period_end": period_end}

    # Месячные графики
    if schedule.frequency == "monthly":
        period_config = schedule.payment_period
        payments = period_config.get("payments", [])

        if payments:
            matching_payment = None
            for payment in payments:
                # Определить день выплаты для этого payment
                if payment.get("is_start_of_month", False):
                    # Первая выплата - используем payment_day из графика
                    payment_day_of_month = schedule.payment_day
                else:
                    # Остальные выплаты - извлекаем день из next_payment_date
                    next_payment_str = payment.get("next_payment_date")
                    if next_payment_str:
                        try:
                            next_payment = date.fromisoformat(next_payment_str)
                            payment_day_of_month = next_payment.day
                        except (ValueError, TypeError):
                            continue
                    else:
                        continue
                
                # Проверяем день месяца вместо точной даты
                if target_date.day == payment_day_of_month:
                    matching_payment = payment
                    break

            if not matching_payment:
                return None

            start_offset = matching_payment.get("start_offset", 0)
            end_offset = matching_payment.get("end_offset", 0)
            is_end_of_month = matching_payment.get("is_end_of_month", False)

            if is_end_of_month:
                # Для is_end_of_month период охватывает вторую половину предыдущего месяца
                # Нужно найти день окончания первой выплаты из первого payment
                
                # Находим предыдущий месяц относительно target_date
                if target_date.month == 1:
                    prev_month = 12
                    prev_year = target_date.year - 1
                else:
                    prev_month = target_date.month - 1
                    prev_year = target_date.year
                
                # Последний день предыдущего месяца
                if prev_month == 12:
                    next_month_start = date(prev_year + 1, 1, 1)
                else:
                    next_month_start = date(prev_year, prev_month + 1, 1)
                period_end = next_month_start - timedelta(days=1)
                
                # Найти первую выплату чтобы определить день окончания первого периода
                first_payment_end_day = None
                for p in payments:
                    if p.get("is_start_of_month", False):
                        # Первая выплата: payment_day + end_offset = день окончания
                        # Например: 25 + (-10) = 15
                        first_payment_end_day = schedule.payment_day + p.get("end_offset", 0)
                        break
                
                if first_payment_end_day:
                    # period_start = день после окончания первого периода
                    period_start = date(prev_year, prev_month, first_payment_end_day + 1)
                else:
                    # Fallback: используем стандартный расчёт
                    period_start = target_date + timedelta(days=start_offset)
            else:
                period_start = target_date + timedelta(days=start_offset)
                period_end = target_date + timedelta(days=end_offset)

            return {"period_start": period_start, "period_end": period_end}

        # Старый формат (без payments)
        if target_date.day != schedule.payment_day:
            return None

        start_offset = period_config.get("start_offset", -60)
        end_offset = period_config.get("end_offset", -30)

        period_start = target_date + timedelta(days=start_offset)
        period_end = target_date + timedelta(days=end_offset)

        calc_rules = period_config.get("calc_rules", {})
        if calc_rules.get("period") == "previous_month":
            prev_month = target_date.month - 1
            prev_year = target_date.year
            if prev_month < 1:
                prev_month = 12
                prev_year -= 1

            period_start = date(prev_year, prev_month, 1)
            first_day_current = date(target_date.year, target_date.month, 1)
            period_end = first_day_current - timedelta(days=1)

        return {"period_start": period_start, "period_end": period_end}

    # Ежедневные графики
    if schedule.frequency == "daily":
        period_config = schedule.payment_period
        start_offset = period_config.get("start_offset", -1)
        end_offset = period_config.get("end_offset", -1)

        period_start = target_date + timedelta(days=start_offset)
        period_end = target_date + timedelta(days=end_offset)

        return {"period_start": period_start, "period_end": period_end}

    return None

