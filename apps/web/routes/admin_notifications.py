"""Роуты для управления уведомлениями в админ-панели (только для суперадмина)."""

import json
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_db_session
from apps.web.middleware.auth_middleware import require_superadmin
from apps.web.services.admin_notification_service import AdminNotificationService
from apps.web.services.notification_template_service import NotificationTemplateService
from apps.web.services.notification_channel_service import NotificationChannelService
from apps.web.services.notification_bulk_service import NotificationBulkService
from domain.entities.notification import NotificationType, NotificationChannel
from core.logging.logger import logger
from apps.web.jinja import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def admin_notifications_dashboard(
    request: Request,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Главный дашборд уведомлений"""
    try:
        service = AdminNotificationService(db)
        
        # Получаем общую статистику
        stats = await service.get_notifications_stats()
        
        # Получаем статистику по каналам
        channel_stats = await service.get_channel_stats()
        
        # Получаем статистику по типам
        type_stats = await service.get_type_stats()
        
        # Получаем последние уведомления
        recent_notifications = await service.get_recent_notifications(limit=10)
        
        return templates.TemplateResponse("admin/notifications/dashboard.html", {
            "request": request,
            "current_user": current_user,
            "title": "Управление уведомлениями",
            "stats": stats,
            "channel_stats": channel_stats,
            "type_stats": type_stats,
            "recent_notifications": recent_notifications
        })
        
    except Exception as e:
        logger.error(f"Error loading notifications dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки дашборда: {str(e)}")


@router.get("/list", response_class=HTMLResponse)
async def admin_notifications_list(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    channel_filter: Optional[str] = Query(None),
    type_filter: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),  # Принимаем как строку, чтобы обработать пустые значения
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Список уведомлений с фильтрами"""
    try:
        service = AdminNotificationService(db)
        
        # Парсим даты
        date_from_parsed = None
        date_to_parsed = None
        if date_from:
            try:
                date_from_parsed = datetime.fromisoformat(date_from)
            except ValueError:
                pass
        if date_to:
            try:
                date_to_parsed = datetime.fromisoformat(date_to)
            except ValueError:
                pass
        
        # Парсим user_id
        user_id_parsed = None
        if user_id and user_id.strip():
            try:
                user_id_parsed = int(user_id)
            except ValueError:
                pass
        
        # Получаем уведомления с фильтрами
        notifications, total_count = await service.get_notifications_paginated(
            page=page,
            per_page=per_page,
            status_filter=status_filter,
            channel_filter=channel_filter,
            type_filter=type_filter,
            user_id=user_id_parsed,
            date_from=date_from_parsed,
            date_to=date_to_parsed
        )
        
        # Получаем доступные фильтры
        filter_options = await service.get_filter_options()
        
        return templates.TemplateResponse("admin/notifications/list.html", {
            "request": request,
            "current_user": current_user,
            "title": "Список уведомлений",
            "notifications": notifications,
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page,
            "filters": {
                "status": status_filter,
                "channel": channel_filter,
                "type": type_filter,
                "user_id": user_id,
                "date_from": date_from,
                "date_to": date_to
            },
            "filter_options": filter_options
        })
        
    except Exception as e:
        logger.error(f"Error loading notifications list: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки списка: {str(e)}")


@router.get("/analytics", response_class=HTMLResponse)
async def admin_notifications_analytics(
    request: Request,
    period: str = Query("7d", description="Период аналитики: 1d, 7d, 30d, 90d"),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Детальная аналитика уведомлений"""
    try:
        service = AdminNotificationService(db)
        
        # Парсим период
        period_map = {
            "1d": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90)
        }
        period_delta = period_map.get(period, timedelta(days=7))
        
        # Получаем аналитику
        analytics = await service.get_detailed_analytics(period_delta)
        
        # Получаем тренды
        trends = await service.get_trends(period_delta)
        
        # Получаем топ пользователей
        top_users = await service.get_top_users_by_notifications(period_delta, limit=10)
        
        return templates.TemplateResponse("admin/notifications/analytics.html", {
            "request": request,
            "current_user": current_user,
            "title": "Аналитика уведомлений",
            "period": period,
            "analytics": analytics,
            "trends": trends,
            "top_users": top_users
        })
        
    except Exception as e:
        logger.error(f"Error loading notifications analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки аналитики: {str(e)}")


@router.get("/templates/select-static", response_class=HTMLResponse, name="admin_notifications_templates_select_static")
async def admin_notifications_templates_select_static(
    request: Request,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница выбора статического шаблона для переопределения"""
    try:
        service = NotificationTemplateService(db)
        
        # Получаем все статические шаблоны
        static_templates = await service.get_all_static_templates()
        
        # Группируем по категориям
        templates_by_category = {}
        for template in static_templates:
            category = template["category"]
            if category not in templates_by_category:
                templates_by_category[category] = []
            templates_by_category[category].append(template)
        
        return templates.TemplateResponse("admin/notifications/templates/select_static.html", {
            "request": request,
            "current_user": current_user,
            "title": "Выбор шаблона для переопределения",
            "templates_by_category": templates_by_category,
            "categories": ["Смены", "Договоры", "Отзывы", "Платежи", "Системные"]
        })
        
    except Exception as e:
        logger.error(f"Error loading static templates selection: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")


@router.get("/templates/{template_id}/edit", response_class=HTMLResponse)
async def admin_notifications_templates_edit(
    request: Request,
    template_id: int,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Редактирование шаблона"""
    try:
        service = NotificationTemplateService(db)
        
        # Получаем шаблон
        template = await service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        # Получаем доступные типы и каналы
        available_types = await service.get_available_types()
        available_channels = await service.get_available_channels()
        
        return templates.TemplateResponse("admin/notifications/templates/edit.html", {
            "request": request,
            "current_user": current_user,
            "title": "Редактирование шаблона",
            "template": template,
            "available_types": available_types,
            "available_channels": available_channels
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading template edit form: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки формы: {str(e)}")


@router.post("/templates/{template_id}/delete")
async def admin_notifications_templates_delete(
    template_id: int,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Удаление шаблона"""
    try:
        service = NotificationTemplateService(db)
        
        # Проверяем существование шаблона
        template = await service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        # Удаляем шаблон
        await service.delete_template(template_id)
        
        return JSONResponse({
            "status": "success",
            "message": "Шаблон успешно удален"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления шаблона: {str(e)}")


@router.post("/templates/{template_id}/test")
async def admin_notifications_templates_test(
    template_id: int,
    test_data: Dict[str, Any] = Form(...),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Тестирование шаблона"""
    try:
        service = NotificationTemplateService(db)
        
        # Получаем шаблон
        template = await service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        # Тестируем шаблон
        result = await service.test_template(template_id, test_data)
        
        return JSONResponse({
                "status": "success",
                "message": "Тест выполнен успешно",
                "result": result
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка тестирования шаблона: {str(e)}")


@router.get("/settings", response_class=HTMLResponse)
async def admin_notifications_settings(
    request: Request,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Настройки каналов доставки"""
    try:
        service = NotificationChannelService(db)
        
        # Получаем настройки каналов
        channel_settings = await service.get_all_channel_settings()
        
        return templates.TemplateResponse("admin/notifications/settings.html", {
                "request": request,
                "current_user": current_user,
                "title": "Настройки каналов доставки",
                "channel_settings": channel_settings
            })
            
    except Exception as e:
        logger.error(f"Error loading notification settings: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки настроек: {str(e)}")


@router.post("/settings/email")
async def admin_notifications_settings_email(
    settings: Dict[str, Any] = Form(...),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Настройки Email канала"""
    try:
        service = NotificationChannelService(db)
        
        # Обновляем настройки Email
        await service.update_email_settings(settings)
        
        return JSONResponse({
            "status": "success",
            "message": "Настройки Email обновлены"
        })
        
    except Exception as e:
        logger.error(f"Error updating email settings: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления настроек: {str(e)}")


@router.post("/settings/sms")
async def admin_notifications_settings_sms(
    settings: Dict[str, Any] = Form(...),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Настройки SMS канала"""
    try:
        service = NotificationChannelService(db)
        
        # Обновляем настройки SMS
        await service.update_sms_settings(settings)
        
        return JSONResponse({
            "status": "success",
            "message": "Настройки SMS обновлены"
        })
        
    except Exception as e:
        logger.error(f"Error updating SMS settings: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления настроек: {str(e)}")


@router.post("/settings/push")
async def admin_notifications_settings_push(
    settings: Dict[str, Any] = Form(...),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Настройки Push канала"""
    try:
        service = NotificationChannelService(db)
        
        # Обновляем настройки Push
        await service.update_push_settings(settings)
        
        return JSONResponse({
            "status": "success",
            "message": "Настройки Push обновлены"
        })
        
    except Exception as e:
        logger.error(f"Error updating push settings: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления настроек: {str(e)}")


@router.post("/settings/telegram")
async def admin_notifications_settings_telegram(
    settings: Dict[str, Any] = Form(...),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Настройки Telegram канала"""
    try:
        service = NotificationChannelService(db)
        
        # Обновляем настройки Telegram
        await service.update_telegram_settings(settings)
        
        return JSONResponse({
            "status": "success",
            "message": "Настройки Telegram обновлены"
        })
        
    except Exception as e:
        logger.error(f"Error updating telegram settings: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления настроек: {str(e)}")


# ============================================================================
# API ENDPOINTS ДЛЯ ОДИНОЧНЫХ ОПЕРАЦИЙ (Iteration 25, Phase 2)
# ============================================================================

@router.get("/api/{notification_id}")
async def admin_notifications_api_get_notification(
    notification_id: int,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Получение одного уведомления"""
    try:
        service = AdminNotificationService(db)
        
        # Получаем уведомление
        notification = await service.get_notification_by_id(notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="Уведомление не найдено")
        
        return JSONResponse({
            "id": notification.id,
            "type": notification.type.value if notification.type else None,
            "status": notification.status.value if notification.status else None,
            "channel": notification.channel.value if notification.channel else None,
            "priority": notification.priority.value if notification.priority else None,
            "subject": notification.title,  # title используется как subject
            "message": notification.message,
            "user_id": notification.user_id,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
            "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
            "read_at": notification.read_at.isoformat() if notification.read_at else None
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notification: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения уведомления: {str(e)}")


@router.post("/api/{notification_id}/retry")
async def admin_notifications_api_retry_notification(
    notification_id: int,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Повторная отправка уведомления"""
    try:
        service = AdminNotificationService(db)
        
        # Получаем уведомление
        notification = await service.get_notification_by_id(notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="Уведомление не найдено")
        
        # Повторная отправка
        await service.retry_notification(notification_id)
        
        logger.info(f"Notification {notification_id} retried by admin {current_user.get('id')}")
        
        return JSONResponse({
            "status": "success",
            "message": f"Уведомление #{notification_id} поставлено в очередь на отправку"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying notification: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка повторной отправки: {str(e)}")


@router.post("/api/{notification_id}/cancel")
async def admin_notifications_api_cancel_notification(
    notification_id: int,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Отмена уведомления"""
    try:
        service = AdminNotificationService(db)
        
        # Получаем уведомление
        notification = await service.get_notification_by_id(notification_id)
        if not notification:
            raise HTTPException(status_code=404, detail="Уведомление не найдено")
        
        # Отмена
        await service.cancel_notification(notification_id)
        
        logger.info(f"Notification {notification_id} cancelled by admin {current_user.get('id')}")
        
        return JSONResponse({
            "status": "success",
            "message": f"Уведомление #{notification_id} отменено"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling notification: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка отмены уведомления: {str(e)}")


# ============================================================================
# API ENDPOINTS ДЛЯ МАССОВЫХ ОПЕРАЦИЙ (Iteration 25, Phase 2)
# ============================================================================

@router.post("/api/bulk/cancel")
async def admin_notifications_bulk_cancel(
    notification_ids: List[int] = Form(...),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Массовая отмена уведомлений"""
    try:
        service = NotificationBulkService(db)
        
        # Отменяем уведомления
        cancelled_count = await service.cancel_notifications(notification_ids)
        
        return JSONResponse({
                "status": "success",
                "message": f"Отменено {cancelled_count} уведомлений",
                "cancelled_count": cancelled_count
            })
            
    except Exception as e:
        logger.error(f"Error cancelling notifications: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка отмены уведомлений: {str(e)}")


@router.post("/api/bulk/retry")
async def admin_notifications_bulk_retry(
    notification_ids: List[int] = Form(...),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Массовая повторная отправка уведомлений"""
    try:
        service = NotificationBulkService(db)
        
        # Повторно отправляем уведомления
        retried_count = await service.retry_notifications(notification_ids)
        
        return JSONResponse({
                "status": "success",
                "message": f"Повторно отправлено {retried_count} уведомлений",
                "retried_count": retried_count
            })
            
    except Exception as e:
        logger.error(f"Error retrying notifications: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка повторной отправки: {str(e)}")


@router.post("/api/bulk/delete")
async def admin_notifications_bulk_delete(
    notification_ids: List[int] = Form(...),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Массовое удаление уведомлений"""
    try:
        service = NotificationBulkService(db)
        
        # Удаляем уведомления
        deleted_count = await service.delete_notifications(notification_ids)
        
        return JSONResponse({
                "status": "success",
                "message": f"Удалено {deleted_count} уведомлений",
                "deleted_count": deleted_count
            })
            
    except Exception as e:
        logger.error(f"Error deleting notifications: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления уведомлений: {str(e)}")


@router.post("/api/bulk/export")
async def admin_notifications_bulk_export(
    notification_ids: List[int] = Form(...),
    format: str = Form("csv"),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Экспорт уведомлений"""
    try:
        service = NotificationBulkService(db)
        
        # Экспортируем уведомления
        export_data = await service.export_notifications(notification_ids, format)
        
        return JSONResponse({
                "status": "success",
                "message": "Экспорт выполнен успешно",
                "data": export_data
            })
            
    except Exception as e:
        logger.error(f"Error exporting notifications: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта: {str(e)}")


@router.post("/api/test")
async def admin_notifications_test(
    test_data: Dict[str, Any] = Form(...),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Тестовая отправка уведомления"""
    try:
        service = AdminNotificationService(db)
        
        # Отправляем тестовое уведомление
        result = await service.send_test_notification(test_data)
        
        return JSONResponse({
                "status": "success",
                "message": "Тестовое уведомление отправлено",
                "result": result
            })
            
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка отправки тестового уведомления: {str(e)}")


# ============================================================================
# РОУТЫ ДЛЯ УПРАВЛЕНИЯ ШАБЛОНАМИ (Iteration 25, Phase 3)
# ============================================================================

@router.get("/templates", response_class=HTMLResponse, name="admin_notifications_templates_list")
async def admin_notifications_templates_list(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    type_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Список шаблонов уведомлений"""
    try:
        service = NotificationTemplateService(db)
        
        # Преобразуем status_filter в is_active
        is_active = None
        if status_filter == 'active':
            is_active = True
        elif status_filter == 'inactive':
            is_active = False
        
        # Получаем шаблоны
        templates_list, total_count = await service.get_templates_paginated(
            page=page,
            per_page=per_page,
            type_filter=type_filter,
            is_active=is_active
        )
        
        # Получаем доступные типы
        available_types = await service.get_available_types()
        
        # Получаем статистику
        stats = await service.get_template_statistics()
        
        return templates.TemplateResponse("admin/notifications/templates/list.html", {
            "request": request,
            "current_user": current_user,
            "title": "Шаблоны уведомлений",
            "templates": templates_list,
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page,
            "type_filter": type_filter,
            "status_filter": status_filter,
            "available_types": available_types,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Error loading templates list: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки списка шаблонов: {str(e)}")


@router.get("/templates/create", response_class=HTMLResponse, name="admin_notifications_template_create_page")
async def admin_notifications_template_create_page(
    request: Request,
    from_static: str = None,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница создания нового кастомного шаблона"""
    try:
        service = NotificationTemplateService(db)
        
        # Получаем доступные типы и каналы
        available_types = await service.get_available_types()
        available_channels = await service.get_available_channels()
        
        # Если указан параметр from_static, загружаем данные статического шаблона
        prefill_data = None
        if from_static:
            static_templates = await service.get_all_static_templates()
            for template in static_templates:
                if template["type_value"] == from_static:
                    prefill_data = {
                        "template_key": f"{from_static}_custom",
                        "type": template["type_value"],
                        "name": f"{template['title']} (кастомная версия)",
                        "plain_template": template["plain_template"],
                        "html_template": template["html_template"],
                        "subject_template": template["subject_template"],
                        "variables": template["variables"],
                        "category": template["category"]
                    }
                    break
        
        return templates.TemplateResponse("admin/notifications/templates/create.html", {
            "request": request,
            "current_user": current_user,
            "title": "Переопределение шаблона" if from_static else "Создание шаблона уведомления",
            "available_types": available_types,
            "available_channels": available_channels,
            "prefill_data": prefill_data
        })
        
    except Exception as e:
        logger.error(f"Error loading template create page: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки страницы: {str(e)}")


@router.get("/templates/{template_id}", response_class=HTMLResponse)
async def admin_notifications_template_view(
    request: Request,
    template_id: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Просмотр шаблона уведомления"""
    try:
        service = NotificationTemplateService(db)
        
        # Получаем шаблон
        template = await service.get_template_by_id(int(template_id))
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        # Получаем доступные типы и каналы
        available_types = await service.get_available_types()
        available_channels = await service.get_available_channels()
        
        # Парсим variables из JSON
        import json
        variables = json.loads(template.variables) if template.variables else []
        
        return templates.TemplateResponse("admin/notifications/templates/edit.html", {
            "request": request,
            "current_user": current_user,
            "title": f"Просмотр шаблона: {template.name}",
            "template": template,
            "variables": variables,
            "available_types": available_types,
            "available_channels": available_channels,
            "is_readonly": True
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки шаблона: {str(e)}")


@router.post("/api/templates/{template_id}/test")
async def admin_notifications_template_test(
    template_id: str,
    test_data: Dict[str, Any],
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Тестирование шаблона"""
    try:
        service = NotificationTemplateService(db)
        
        # Тестируем шаблон
        result = await service.test_template(template_id, test_data)
        
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"Error testing template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка тестирования шаблона: {str(e)}")


@router.get("/api/templates")
async def admin_notifications_api_templates_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    type_filter: Optional[str] = Query(None),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Список шаблонов"""
    try:
        service = NotificationTemplateService(db)
        
        templates_list, total_count = await service.get_templates_paginated(
            page=page,
            per_page=per_page,
            type_filter=type_filter
        )
        
        return JSONResponse({
            "status": "success",
            "data": {
                "templates": templates_list,
                "total_count": total_count,
                "page": page,
                "per_page": per_page,
                "total_pages": (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения шаблонов: {str(e)}")


@router.get("/api/templates/{template_id}")
async def admin_notifications_api_template_get(
    template_id: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Получение шаблона"""
    try:
        service = NotificationTemplateService(db)
        
        template = await service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        return JSONResponse({
            "status": "success",
            "data": template
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения шаблона: {str(e)}")


@router.get("/api/templates/static/{template_type}")
async def admin_notifications_api_static_template_get(
    template_type: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Получение статического шаблона по типу"""
    try:
        service = NotificationTemplateService(db)
        
        # Получаем все статические шаблоны
        static_templates = await service.get_all_static_templates()
        
        # Находим нужный
        template_data = None
        for template in static_templates:
            if template["type_value"] == template_type:
                template_data = template
                break
        
        if not template_data:
            raise HTTPException(status_code=404, detail="Статический шаблон не найден")
        
        return JSONResponse({
            "status": "success",
            "data": template_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting static template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статического шаблона: {str(e)}")


# ============================================================================
# CRUD API ДЛЯ КАСТОМНЫХ ШАБЛОНОВ (Iteration 25, Phase 3)
# ============================================================================

@router.post("/api/templates/create")
async def admin_notifications_api_template_create(
    request: Request,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Создание нового кастомного шаблона"""
    try:
        # Получаем данные из формы
        form_data = await request.form()
        
        service = NotificationTemplateService(db)
        
        # Парсим данные
        template_key = form_data.get("template_key")
        notification_type = NotificationType(form_data.get("type"))
        channel_value = form_data.get("channel")
        channel = NotificationChannel(channel_value) if channel_value else None
        name = form_data.get("name")
        plain_template = form_data.get("plain_template")
        subject_template = form_data.get("subject_template")
        html_template = form_data.get("html_template")
        description = form_data.get("description")
        variables_str = form_data.get("variables")
        variables = json.loads(variables_str) if variables_str else None
        
        # Создаём шаблон
        template = await service.create_template(
            template_key=template_key,
            notification_type=notification_type,
            channel=channel,
            name=name,
            plain_template=plain_template,
            subject_template=subject_template,
            html_template=html_template,
            description=description,
            variables=variables,
            created_by_user_id=current_user.get("id")
        )
        
        logger.info(f"Template created: {template.id} by user {current_user.get('id')}")
        
        return JSONResponse({
            "status": "success",
            "message": f"Шаблон '{name}' успешно создан",
            "data": {
                "id": template.id,
                "template_key": template.template_key
            }
        })
        
    except ValueError as e:
        logger.error(f"Validation error creating template: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания шаблона: {str(e)}")


@router.get("/templates/edit/{template_id}", response_class=HTMLResponse)
async def admin_notifications_template_edit_page(
    request: Request,
    template_id: int,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница редактирования кастомного шаблона"""
    try:
        service = NotificationTemplateService(db)
        
        # Получаем шаблон
        template = await service.get_template_by_id(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        # Получаем доступные типы и каналы
        available_types = await service.get_available_types()
        available_channels = await service.get_available_channels()
        
        # Парсим variables
        variables = json.loads(template.variables) if template.variables else []
        
        return templates.TemplateResponse("admin/notifications/templates/edit.html", {
            "request": request,
            "current_user": current_user,
            "title": f"Редактирование шаблона: {template.name}",
            "template": template,
            "variables": variables,
            "available_types": available_types,
            "available_channels": available_channels,
            "is_readonly": template.is_default  # Дефолтные шаблоны только для чтения
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading template edit page: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки страницы: {str(e)}")


@router.post("/api/templates/edit/{template_id}")
async def admin_notifications_api_template_update(
    request: Request,
    template_id: int,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Обновление кастомного шаблона"""
    try:
        # Получаем данные из формы
        form_data = await request.form()
        
        service = NotificationTemplateService(db)
        
        # Парсим данные
        name = form_data.get("name")
        plain_template = form_data.get("plain_template")
        subject_template = form_data.get("subject_template")
        html_template = form_data.get("html_template")
        description = form_data.get("description")
        variables_str = form_data.get("variables")
        variables = json.loads(variables_str) if variables_str else None
        is_active_str = form_data.get("is_active")
        is_active = is_active_str == "true" if is_active_str else None
        
        # Обновляем шаблон
        template = await service.update_template(
            template_id=template_id,
            name=name,
            plain_template=plain_template,
            subject_template=subject_template,
            html_template=html_template,
            description=description,
            variables=variables,
            is_active=is_active,
            updated_by_user_id=current_user.get("id")
        )
        
        logger.info(f"Template updated: {template.id} by user {current_user.get('id')}")
        
        return JSONResponse({
            "status": "success",
            "message": f"Шаблон '{template.name}' успешно обновлён (версия {template.version})",
            "data": {
                "id": template.id,
                "version": template.version
            }
        })
        
    except ValueError as e:
        logger.error(f"Validation error updating template: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления шаблона: {str(e)}")


@router.post("/api/templates/delete/{template_id}")
async def admin_notifications_api_template_delete(
    template_id: int,
    hard_delete: bool = Query(False),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Удаление кастомного шаблона (мягкое или жёсткое)"""
    try:
        service = NotificationTemplateService(db)
        
        if hard_delete:
            # Жёсткое удаление
            await service.hard_delete_template(template_id)
            message = "Шаблон удалён из базы данных"
        else:
            # Мягкое удаление (деактивация)
            await service.delete_template(template_id)
            message = "Шаблон деактивирован"
        
        logger.info(f"Template deleted: {template_id} (hard={hard_delete}) by user {current_user.get('id')}")
        
        return JSONResponse({
            "status": "success",
            "message": message
        })
        
    except ValueError as e:
        logger.error(f"Validation error deleting template: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления шаблона: {str(e)}")

@router.post("/api/templates/restore/{template_id}")
async def admin_notifications_api_template_restore(
    template_id: int,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Восстановление кастомного шаблона (активация)"""
    try:
        service = NotificationTemplateService(db)
        await service.restore_template(template_id)
        
        logger.info(f"Template restored: {template_id} by user {current_user.get('id')}")
        
        return JSONResponse({
            "status": "success",
            "message": "Шаблон восстановлён"
        })
        
    except ValueError as e:
        logger.error(f"Validation error restoring template: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error restoring template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка восстановления шаблона: {str(e)}")

@router.post("/api/templates/toggle/{template_id}")
async def admin_notifications_api_template_toggle(
    template_id: int,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Переключение активности шаблона"""
    try:
        service = NotificationTemplateService(db)
        
        # Получаем шаблон
        template = await service.get_template_by_id(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        # Переключаем активность
        new_status = not template.is_active
        await service.update_template(
            template_id=template_id,
            is_active=new_status,
            updated_by_user_id=current_user.get("id")
        )
        
        status_text = "активирован" if new_status else "деактивирован"
        logger.info(f"Template {template_id} {status_text} by user {current_user.get('id')}")
        
        return JSONResponse({
            "status": "success",
            "message": f"Шаблон {status_text}",
            "data": {
                "is_active": new_status
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка переключения статуса: {str(e)}")


# ============================================================================
# РОУТЫ ДЛЯ УПРАВЛЕНИЯ ТИПАМИ УВЕДОМЛЕНИЙ (Iteration 37, Phase 4)
# ============================================================================

@router.get("/types", response_class=HTMLResponse, name="admin_notifications_types_list")
async def admin_notifications_types_list(
    request: Request,
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Список типов уведомлений с фильтрами"""
    try:
        from shared.services.notification_type_meta_service import NotificationTypeMetaService
        service = NotificationTypeMetaService()
        
        # Получаем все типы
        all_types = await service.get_all_types(db, active_only=False)
        
        # Применяем фильтры
        filtered_types = all_types
        
        if category:
            filtered_types = [t for t in filtered_types if t.category == category]
        
        if status == 'active':
            filtered_types = [t for t in filtered_types if t.is_active]
        elif status == 'inactive':
            filtered_types = [t for t in filtered_types if not t.is_active]
        elif status == 'user_configurable':
            filtered_types = [t for t in filtered_types if t.is_user_configurable]
        elif status == 'admin_only':
            filtered_types = [t for t in filtered_types if t.is_admin_only]
        
        # Статистика
        stats = {
            "total": len(all_types),
            "user_configurable": len([t for t in all_types if t.is_user_configurable]),
            "admin_only": len([t for t in all_types if t.is_admin_only]),
        }
        
        # Категории
        categories = await service.get_categories_list(db)
        
        return templates.TemplateResponse("admin/notifications/types/list.html", {
            "request": request,
            "current_user": current_user,
            "title": "Типы уведомлений",
            "types": filtered_types,
            "stats": stats,
            "categories": categories,
            "category_filter": category,
            "status_filter": status
        })
        
    except Exception as e:
        logger.error(f"Error loading types list: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки списка типов: {str(e)}")


@router.get("/api/types/{type_code}")
async def admin_notifications_api_get_type(
    type_code: str,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Получить тип уведомления по коду"""
    try:
        from shared.services.notification_type_meta_service import NotificationTypeMetaService
        service = NotificationTypeMetaService()
        
        type_meta = await service.get_type_by_code(db, type_code)
        if not type_meta:
            raise HTTPException(status_code=404, detail="Тип не найден")
        
        return JSONResponse({
            "id": type_meta.id,
            "type_code": type_meta.type_code,
            "title": type_meta.title,
            "description": type_meta.description,
            "category": type_meta.category,
            "default_priority": type_meta.default_priority,
            "is_user_configurable": type_meta.is_user_configurable,
            "is_admin_only": type_meta.is_admin_only,
            "available_channels": type_meta.available_channels,
            "sort_order": type_meta.sort_order,
            "is_active": type_meta.is_active
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading type {type_code}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки типа: {str(e)}")


@router.post("/api/types/{type_code}/update")
async def admin_notifications_api_update_type(
    type_code: str,
    request: Request,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Обновить мета-информацию типа"""
    try:
        from shared.services.notification_type_meta_service import NotificationTypeMetaService
        service = NotificationTypeMetaService()
        
        data = await request.json()
        
        updated_type = await service.update_type(
            db,
            type_code=type_code,
            title=data.get("title"),
            description=data.get("description"),
            default_priority=data.get("default_priority"),
            available_channels=data.get("available_channels"),
            sort_order=data.get("sort_order")
        )
        
        if not updated_type:
            raise HTTPException(status_code=404, detail="Тип не найден")
        
        logger.info(f"Type {type_code} updated by user {current_user.get('id')}")
        
        return JSONResponse({
            "status": "success",
            "message": "Тип успешно обновлён",
            "data": {
                "id": updated_type.id,
                "type_code": updated_type.type_code,
                "title": updated_type.title,
                "description": updated_type.description,
                "category": updated_type.category,
                "default_priority": updated_type.default_priority,
                "is_user_configurable": updated_type.is_user_configurable,
                "is_admin_only": updated_type.is_admin_only,
                "available_channels": updated_type.available_channels,
                "sort_order": updated_type.sort_order,
                "is_active": updated_type.is_active
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating type {type_code}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления типа: {str(e)}")


@router.post("/api/types/{type_code}/toggle-user-access")
async def admin_notifications_api_toggle_user_access(
    type_code: str,
    request: Request,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Переключить доступность типа для пользователей"""
    try:
        from shared.services.notification_type_meta_service import NotificationTypeMetaService
        service = NotificationTypeMetaService()
        
        data = await request.json()
        enable = data.get("enable", False)
        
        # Получаем тип
        type_meta = await service.get_type_by_code(db, type_code)
        if not type_meta:
            raise HTTPException(status_code=404, detail="Тип не найден")
        
        # Обновляем is_user_configurable
        type_meta.is_user_configurable = enable
        await db.commit()
        
        action = "добавлен в" if enable else "удалён из"
        logger.info(f"Type {type_code} {action} настройки пользователей by user {current_user.get('id')}")
        
        return JSONResponse({
            "status": "success",
            "message": f"Тип {action} настройки пользователей"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling user access for {type_code}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка изменения доступа: {str(e)}")


@router.post("/api/types/{type_code}/toggle-active")
async def admin_notifications_api_toggle_active(
    type_code: str,
    request: Request,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Переключить активность типа"""
    try:
        from shared.services.notification_type_meta_service import NotificationTypeMetaService
        service = NotificationTypeMetaService()
        
        data = await request.json()
        activate = data.get("activate", False)
        
        if activate:
            success = await service.activate_type(db, type_code)
        else:
            success = await service.deactivate_type(db, type_code)
        
        if not success:
            raise HTTPException(status_code=404, detail="Тип не найден")
        
        action = "активирован" if activate else "деактивирован"
        logger.info(f"Type {type_code} {action} by user {current_user.get('id')}")
        
        return JSONResponse({
            "status": "success",
            "message": f"Тип {action}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling active status for {type_code}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка изменения статуса: {str(e)}")

