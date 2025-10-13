"""Сервис аналитики и отчетов."""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from core.database.connection import get_sync_session
from domain.entities.shift import Shift
from domain.entities.object import Object
from domain.entities.user import User
from core.logging.logger import logger


class AnalyticsService:
    """Сервис для формирования отчетов и аналитики."""
    
    def __init__(self):
        """Инициализация сервиса."""
        logger.info("AnalyticsService initialized")
    
    def get_object_report(
        self,
        object_id: Optional[int],
        start_date: date,
        end_date: date,
        owner_id: int
    ) -> Dict[str, Any]:
        """
        Формирует отчет по объекту за период.
        
        Args:
            object_id: ID объекта (None для всех объектов владельца)
            start_date: Начальная дата
            end_date: Конечная дата
            owner_id: ID владельца (для проверки прав)
            
        Returns:
            Словарь с данными отчета
        """
        try:
            with get_sync_session() as db:
                # Получаем объекты владельца
                if object_id is None:
                    # Все объекты владельца
                    objects = db.query(Object).filter(Object.owner_id == owner_id).all()
                    if not objects:
                        return {"error": "У вас нет объектов для анализа"}
                    object_ids = [obj.id for obj in objects]
                    obj = None  # Нет конкретного объекта
                else:
                    # Конкретный объект
                    obj = db.query(Object).filter(
                        and_(Object.id == object_id, Object.owner_id == owner_id)
                    ).first()
                    
                    if not obj:
                        return {"error": "Объект не найден или нет прав доступа"}
                    object_ids = [object_id]
                
                # Получаем смены за период
                shifts = db.query(Shift).join(User).filter(
                    and_(
                        Shift.object_id.in_(object_ids),
                        func.date(Shift.start_time) >= start_date,
                        func.date(Shift.start_time) <= end_date,
                        Shift.status.in_(["completed", "active"])
                    )
                ).all()
                
                # Базовая статистика
                total_shifts = len(shifts)
                completed_shifts = len([s for s in shifts if s.status == "completed"])
                active_shifts = len([s for s in shifts if s.status == "active"])
                
                # Расчет времени и оплаты
                total_hours = sum([s.total_hours or 0 for s in shifts])
                total_payment = sum([s.total_payment or 0 for s in shifts])
                
                # Статистика по сотрудникам
                employee_stats = self._calculate_employee_stats(shifts, db)
                
                # Статистика по дням
                daily_stats = self._calculate_daily_stats(shifts, start_date, end_date)
                
                # Средние показатели
                avg_shift_duration = total_hours / completed_shifts if completed_shifts > 0 else 0
                avg_daily_hours = total_hours / ((end_date - start_date).days + 1)
                
                # Формируем данные об объекте(ах)
                if obj:
                    # Один объект
                    object_info = {
                        "id": obj.id,
                        "name": obj.name,
                        "address": obj.address,
                        "working_hours": obj.working_hours,
                        "hourly_rate": float(obj.hourly_rate)
                    }
                else:
                    # Все объекты
                    object_info = {
                        "id": None,
                        "name": "Все объекты",
                        "address": f"Всего объектов: {len(objects)}",
                        "working_hours": "Различные",
                        "hourly_rate": "Различные"
                    }
                
                return {
                    "object": object_info,
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "days": (end_date - start_date).days + 1
                    },
                    "summary": {
                        "total_shifts": total_shifts,
                        "completed_shifts": completed_shifts,
                        "active_shifts": active_shifts,
                        "total_hours": float(total_hours),
                        "total_payment": float(total_payment),
                        "avg_shift_duration": round(avg_shift_duration, 2),
                        "avg_daily_hours": round(avg_daily_hours, 2)
                    },
                    "employees": employee_stats,
                    "daily_breakdown": daily_stats
                }
                
        except Exception as e:
            logger.error(f"Error generating object report for object {object_id}: {e}")
            return {"error": f"Ошибка формирования отчета: {str(e)}"}
    
    def get_personal_report(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        object_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Формирует персональный отчет сотрудника.
        
        Args:
            user_id: ID пользователя в базе данных (не telegram_id!)
            start_date: Начальная дата
            end_date: Конечная дата
            object_id: Опциональный фильтр по объекту
            
        Returns:
            Словарь с данными отчета
        """
        try:
            with get_sync_session() as db:
                # Находим пользователя по database ID
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"error": "Пользователь не найден"}
                
                # Формируем фильтры
                filters = [
                    Shift.user_id == user.id,
                    func.date(Shift.start_time) >= start_date,
                    func.date(Shift.start_time) <= end_date,
                    Shift.status.in_(["completed", "active"])
                ]
                
                if object_id:
                    filters.append(Shift.object_id == object_id)
                
                # Получаем смены
                shifts = db.query(Shift).join(Object).filter(
                    and_(*filters)
                ).order_by(desc(Shift.start_time)).all()
                
                # Базовая статистика
                total_shifts = len(shifts)
                completed_shifts = len([s for s in shifts if s.status == "completed"])
                active_shifts = len([s for s in shifts if s.status == "active"])
                
                # Расчет времени и заработка
                total_hours = sum([s.total_hours or 0 for s in shifts])
                total_earnings = sum([s.total_payment or 0 for s in shifts])
                
                # Статистика по объектам
                object_stats = self._calculate_object_stats_for_user(shifts, db)
                
                # Детальная разбивка по сменам
                shift_details = []
                for shift in shifts[:20]:  # Последние 20 смен
                    shift_details.append({
                        "id": shift.id,
                        "object_name": shift.object.name,
                        "date": shift.start_time.date().isoformat(),
                        "start_time": shift.start_time.strftime("%H:%M"),
                        "end_time": shift.end_time.strftime("%H:%M") if shift.end_time else "Активна",
                        "duration_hours": float(shift.total_hours or 0),
                        "payment": float(shift.total_payment or 0),
                        "status": shift.status
                    })
                
                # Средние показатели
                avg_shift_duration = total_hours / completed_shifts if completed_shifts > 0 else 0
                avg_daily_earnings = total_earnings / ((end_date - start_date).days + 1)
                
                return {
                    "user": {
                        "id": user.id,
                        "telegram_id": user.telegram_id,
                        "name": user.full_name,
                        "username": user.username
                    },
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "days": (end_date - start_date).days + 1
                    },
                    "summary": {
                        "total_shifts": total_shifts,
                        "completed_shifts": completed_shifts,
                        "active_shifts": active_shifts,
                        "total_hours": float(total_hours),
                        "total_earnings": float(total_earnings),
                        "avg_shift_duration": round(avg_shift_duration, 2),
                        "avg_daily_earnings": round(avg_daily_earnings, 2)
                    },
                    "objects": object_stats,
                    "recent_shifts": shift_details
                }
                
        except Exception as e:
            logger.error(f"Error generating personal report for user {user_id}: {e}")
            return {"error": f"Ошибка формирования отчета: {str(e)}"}
    
    def get_dashboard_metrics(self, owner_id: int) -> Dict[str, Any]:
        """
        Получает ключевые метрики для дашборда владельца.
        
        Args:
            owner_id: ID владельца в базе данных (не telegram_id!)
            
        Returns:
            Словарь с метриками
        """
        try:
            with get_sync_session() as db:
                # Находим пользователя по database ID
                owner = db.query(User).filter(User.id == owner_id).first()
                if not owner:
                    return {"error": "Пользователь не найден"}
                
                # Получаем объекты владельца
                objects = db.query(Object).filter(Object.owner_id == owner.id).all()
                object_ids = [obj.id for obj in objects]
                
                if not object_ids:
                    return {
                        "objects_count": 0,
                        "active_shifts": 0,
                        "today_stats": {"shifts": 0, "hours": 0, "payments": 0},
                        "week_stats": {"shifts": 0, "hours": 0, "payments": 0},
                        "month_stats": {"shifts": 0, "hours": 0, "payments": 0}
                    }
                
                # Текущие активные смены
                active_shifts_count = db.query(Shift).filter(
                    and_(
                        Shift.object_id.in_(object_ids),
                        Shift.status == "active"
                    )
                ).count()
                
                # Статистика за сегодня
                today = date.today()
                today_stats = self._get_period_stats(db, object_ids, today, today)
                
                # Статистика за неделю
                week_start = today - timedelta(days=6)
                week_stats = self._get_period_stats(db, object_ids, week_start, today)
                
                # Статистика за месяц
                month_start = today - timedelta(days=29)
                month_stats = self._get_period_stats(db, object_ids, month_start, today)
                
                # Топ объекты по активности
                top_objects = self._get_top_objects(db, object_ids, month_start, today)
                
                return {
                    "objects_count": len(objects),
                    "active_shifts": active_shifts_count,
                    "today_stats": today_stats,
                    "week_stats": week_stats,
                    "month_stats": month_stats,
                    "top_objects": top_objects
                }
                
        except Exception as e:
            logger.error(f"Error generating dashboard metrics for owner {owner_id}: {e}")
            return {"error": f"Ошибка получения метрик: {str(e)}"}
    
    def get_owner_dashboard(self, owner_id: int) -> Dict[str, Any]:
        """
        Получает данные для дашборда владельца.
        
        Args:
            owner_id: ID владельца в базе данных
            
        Returns:
            Словарь с данными дашборда
        """
        try:
            with get_sync_session() as db:
                # Получаем объекты владельца
                objects = db.query(Object).filter(Object.owner_id == owner_id).all()
                object_ids = [obj.id for obj in objects]
                
                if not object_ids:
                    return {
                        "total_payments": 0,
                        "total_shifts": 0,
                        "active_shifts": 0,
                        "top_objects": []
                    }
                
                # Общая сумма к выплате
                total_payments = db.query(func.sum(Shift.total_payment)).filter(
                    and_(
                        Shift.object_id.in_(object_ids),
                        Shift.status == "completed"
                    )
                ).scalar() or 0
                
                # Общее количество смен
                total_shifts = db.query(func.count(Shift.id)).filter(
                    Shift.object_id.in_(object_ids)
                ).scalar() or 0
                
                # Активные смены
                active_shifts = db.query(func.count(Shift.id)).filter(
                    and_(
                        Shift.object_id.in_(object_ids),
                        Shift.status == "active"
                    )
                ).scalar() or 0
                
                # Топ объекты по активности
                top_objects = db.query(
                    Object.name,
                    func.count(Shift.id).label('shifts_count')
                ).join(Shift).filter(
                    Shift.object_id.in_(object_ids)
                ).group_by(Object.id, Object.name).order_by(
                    func.count(Shift.id).desc()
                ).limit(3).all()
                
                top_objects_list = [
                    {
                        "name": obj.name,
                        "shifts_count": obj.shifts_count
                    }
                    for obj in top_objects
                ]
                
                return {
                    "total_payments": float(total_payments),
                    "total_shifts": total_shifts,
                    "active_shifts": active_shifts,
                    "top_objects": top_objects_list
                }
                
        except Exception as e:
            logger.error(f"Error getting owner dashboard for owner {owner_id}: {e}")
            return {"error": f"Ошибка получения дашборда: {str(e)}"}
    
    def _calculate_employee_stats(self, shifts: List[Shift], db: Session) -> List[Dict[str, Any]]:
        """Рассчитывает статистику по сотрудникам."""
        employee_data = {}
        
        for shift in shifts:
            user_id = shift.user_id
            if user_id not in employee_data:
                user = db.query(User).filter(User.id == user_id).first()
                employee_data[user_id] = {
                    "name": user.full_name if user else "Неизвестно",
                    "shifts": 0,
                    "hours": 0,
                    "payment": 0
                }
            
            employee_data[user_id]["shifts"] += 1
            employee_data[user_id]["hours"] += float(shift.total_hours or 0)
            employee_data[user_id]["payment"] += float(shift.total_payment or 0)
        
        # Сортируем по количеству смен (по убыванию)
        sorted_employees = sorted(
            employee_data.values(),
            key=lambda x: x["shifts"],
            reverse=True
        )
        
        return [
            {
                "name": data["name"],
                "shifts": data["shifts"],
                "hours": round(data["hours"], 2),
                "payment": round(data["payment"], 2)
            }
            for data in sorted_employees
        ]
    
    def _calculate_daily_stats(self, shifts: List[Shift], start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Рассчитывает статистику по дням."""
        daily_data = {}
        
        # Инициализируем все дни периода
        current_date = start_date
        while current_date <= end_date:
            daily_data[current_date] = {"shifts": 0, "hours": 0, "payment": 0}
            current_date += timedelta(days=1)
        
        # Заполняем данными из смен
        for shift in shifts:
            shift_date = shift.start_time.date()
            if shift_date in daily_data:
                daily_data[shift_date]["shifts"] += 1
                daily_data[shift_date]["hours"] += float(shift.total_hours or 0)
                daily_data[shift_date]["payment"] += float(shift.total_payment or 0)
        
        return [
            {
                "date": date_key.isoformat(),
                "shifts": data["shifts"],
                "hours": round(data["hours"], 2),
                "payment": round(data["payment"], 2)
            }
            for date_key, data in sorted(daily_data.items())
        ]
    
    def _calculate_object_stats_for_user(self, shifts: List[Shift], db: Session) -> List[Dict[str, Any]]:
        """Рассчитывает статистику по объектам для пользователя."""
        object_data = {}
        
        for shift in shifts:
            object_id = shift.object_id
            if object_id not in object_data:
                object_data[object_id] = {
                    "name": shift.object.name,
                    "shifts": 0,
                    "hours": 0,
                    "earnings": 0
                }
            
            object_data[object_id]["shifts"] += 1
            object_data[object_id]["hours"] += float(shift.total_hours or 0)
            object_data[object_id]["earnings"] += float(shift.total_payment or 0)
        
        return [
            {
                "name": data["name"],
                "shifts": data["shifts"],
                "hours": round(data["hours"], 2),
                "earnings": round(data["earnings"], 2)
            }
            for data in object_data.values()
        ]
    
    def _get_period_stats(self, db: Session, object_ids: List[int], start_date: date, end_date: date) -> Dict[str, Any]:
        """Получает статистику за период."""
        shifts = db.query(Shift).filter(
            and_(
                Shift.object_id.in_(object_ids),
                func.date(Shift.start_time) >= start_date,
                func.date(Shift.start_time) <= end_date,
                Shift.status.in_(["completed", "active"])
            )
        ).all()
        
        total_hours = sum([s.total_hours or 0 for s in shifts])
        # Для владельца это расходы (payments), а не доход
        total_payments = sum([s.total_payment or 0 for s in shifts])
        
        return {
            "shifts": len(shifts),
            "hours": round(float(total_hours), 2),
            "payments": round(float(total_payments), 2),
            "earnings": round(float(total_payments), 2)  # Для совместимости с тестами
        }
    
    def _get_top_objects(self, db: Session, object_ids: List[int], start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Получает топ объекты по активности."""
        result = db.query(
            Object.name,
            func.count(Shift.id).label('shift_count'),
            func.sum(Shift.total_hours).label('total_hours'),
            func.sum(Shift.total_payment).label('total_payment')
        ).join(Shift).filter(
            and_(
                Object.id.in_(object_ids),
                func.date(Shift.start_time) >= start_date,
                func.date(Shift.start_time) <= end_date,
                Shift.status.in_(["completed", "active"])
            )
        ).group_by(Object.id, Object.name).order_by(desc('shift_count')).limit(5).all()
        
        return [
            {
                "name": row.name,
                "shifts": row.shift_count,
                "hours": round(float(row.total_hours or 0), 2),
                "payments": round(float(row.total_payment or 0), 2)
            }
            for row in result
        ]
    
    def get_cancellation_statistics(
        self,
        owner_id: int,
        start_date: date,
        end_date: date,
        object_id: Optional[int] = None,
        employee_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Формирует статистику по отменам смен за период.
        
        Args:
            owner_id: ID владельца
            start_date: Начальная дата
            end_date: Конечная дата
            object_id: ID объекта (опционально)
            employee_id: ID сотрудника (опционально)
            
        Returns:
            Словарь со статистикой отмен
        """
        from domain.entities.shift_cancellation import ShiftCancellation
        from domain.entities.shift_schedule import ShiftSchedule
        
        try:
            with get_sync_session() as db:
                # Базовый запрос: только отмены объектов владельца
                query = (
                    db.query(ShiftCancellation)
                    .join(Object, ShiftCancellation.object_id == Object.id)
                    .join(ShiftSchedule, ShiftCancellation.shift_schedule_id == ShiftSchedule.id)
                    .filter(
                        Object.owner_id == owner_id,
                        func.date(ShiftCancellation.created_at) >= start_date,
                        func.date(ShiftCancellation.created_at) <= end_date
                    )
                )
                
                # Фильтры
                if object_id:
                    query = query.filter(ShiftCancellation.object_id == object_id)
                if employee_id:
                    query = query.filter(ShiftCancellation.employee_id == employee_id)
                
                cancellations = query.all()
                
                # Подсчет статистики
                total_cancellations = len(cancellations)
                
                # По типам отменивших
                by_type = {}
                for c in cancellations:
                    by_type[c.cancelled_by_type] = by_type.get(c.cancelled_by_type, 0) + 1
                
                # По причинам
                by_reason = {}
                for c in cancellations:
                    by_reason[c.cancellation_reason] = by_reason.get(c.cancellation_reason, 0) + 1
                
                # По сотрудникам (топ 10)
                by_employee = {}
                for c in cancellations:
                    if c.employee_id not in by_employee:
                        by_employee[c.employee_id] = {
                            'count': 0,
                            'total_fine': Decimal('0'),
                            'name': ''
                        }
                    by_employee[c.employee_id]['count'] += 1
                    if c.fine_amount:
                        by_employee[c.employee_id]['total_fine'] += c.fine_amount
                
                # Получаем имена сотрудников
                for emp_id in by_employee.keys():
                    user = db.query(User).filter(User.id == emp_id).first()
                    if user:
                        by_employee[emp_id]['name'] = f"{user.first_name} {user.last_name or ''}".strip()
                
                # Топ отменяющих
                top_employees = sorted(
                    [{'id': k, **v} for k, v in by_employee.items()],
                    key=lambda x: x['count'],
                    reverse=True
                )[:10]
                
                # Суммы штрафов
                total_fines = sum(float(c.fine_amount or 0) for c in cancellations)
                applied_fines = sum(float(c.fine_amount or 0) for c in cancellations if c.fine_applied)
                
                # Уважительные причины
                valid_reasons_count = sum(1 for c in cancellations if c.is_valid_reason)
                valid_reasons_verified = sum(1 for c in cancellations if c.is_valid_reason and c.document_verified)
                
                return {
                    'success': True,
                    'total_cancellations': total_cancellations,
                    'by_type': by_type,
                    'by_reason': by_reason,
                    'top_employees': top_employees,
                    'total_fines': round(total_fines, 2),
                    'applied_fines': round(applied_fines, 2),
                    'valid_reasons_count': valid_reasons_count,
                    'valid_reasons_verified': valid_reasons_verified,
                    'valid_reasons_percent': round(valid_reasons_count / total_cancellations * 100, 1) if total_cancellations > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting cancellation statistics: {e}")
            return {
                'success': False,
                'error': str(e)
            }