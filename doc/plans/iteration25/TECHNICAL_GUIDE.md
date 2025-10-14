# 🔧 Техническое руководство: Итерация 25

> **Система управления уведомлениями в админке**  
> **Версия:** 1.0  
> **Дата:** 2024-01-15

---

## 📋 Содержание

1. [Архитектура системы](#архитектура-системы)
2. [Компоненты и структура](#компоненты-и-структура)
3. [API Reference](#api-reference)
4. [База данных](#база-данных)
5. [Кэширование](#кэширование)
6. [Безопасность](#безопасность)
7. [Производительность](#производительность)
8. [Развертывание](#развертывание)
9. [Мониторинг](#мониторинг)
10. [Troubleshooting](#troubleshooting)

---

## 🏗 Архитектура системы

### Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                    Admin Panel                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐│
│  │ Dashboard   │ │ List        │ │ Analytics   │ │ Settings││
│  │ (Stats)     │ │ (Filtered)  │ │ (Charts)    │ │ (Channels││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘│
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                  Service Layer                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐│
│  │ Admin       │ │ Template    │ │ Channel     │ │ Bulk    ││
│  │ Notification│ │ Service     │ │ Service     │ │ Service ││
│  │ Service     │ │             │ │             │ │         ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘│
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                  Data Layer                                │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐│
│  │ PostgreSQL  │ │ Redis Cache │ │ File System │ │ External││
│  │ (Main DB)   │ │ (Stats)     │ │ (Exports)   │ │ APIs    ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Поток данных

```
User Request → Admin Routes → Service Layer → Database/Cache
     ↓              ↓              ↓              ↓
   Auth Check → Validation → Business Logic → Data Access
     ↓              ↓              ↓              ↓
   Response ← Template ← Service Result ← Query Result
```

---

## 🧩 Компоненты и структура

### 1. Роуты (`apps/web/routes/admin_notifications.py`)

```python
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from apps.web.middleware.auth_middleware import require_superadmin
from apps.web.services.admin_notification_service import AdminNotificationService
from apps.web.jinja import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def admin_notifications_dashboard(
    request: Request,
    current_user: dict = Depends(require_superadmin)
):
    """Главный дашборд уведомлений"""
    service = AdminNotificationService()
    stats = await service.get_notifications_stats()
    
    return templates.TemplateResponse("admin/notifications/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "stats": stats
    })

@router.get("/list", response_class=HTMLResponse)
async def admin_notifications_list(
    request: Request,
    current_user: dict = Depends(require_superadmin),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    type_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    channel_filter: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """Список уведомлений с фильтрами"""
    service = AdminNotificationService()
    
    filters = {
        "type": type_filter,
        "status": status_filter,
        "channel": channel_filter,
        "date_from": date_from,
        "date_to": date_to,
        "search": search
    }
    
    notifications, total = await service.get_notifications_list(
        page=page, per_page=per_page, filters=filters
    )
    
    return templates.TemplateResponse("admin/notifications/list.html", {
        "request": request,
        "current_user": current_user,
        "notifications": notifications,
        "total": total,
        "page": page,
        "per_page": per_page,
        "filters": filters
    })

@router.get("/analytics", response_class=HTMLResponse)
async def admin_notifications_analytics(
    request: Request,
    current_user: dict = Depends(require_superadmin),
    period: str = Query("30d"),
    type_filter: Optional[str] = Query(None)
):
    """Детальная аналитика уведомлений"""
    service = AdminNotificationService()
    
    analytics = await service.get_detailed_analytics(
        period=period, type_filter=type_filter
    )
    
    return templates.TemplateResponse("admin/notifications/analytics.html", {
        "request": request,
        "current_user": current_user,
        "analytics": analytics,
        "period": period,
        "type_filter": type_filter
    })
```

### 2. Сервисы

#### AdminNotificationService

```python
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload
from core.database.session import get_async_session
from core.cache.redis_cache import cached
from domain.entities.notification import Notification, NotificationType, NotificationStatus, NotificationChannel
from domain.entities.payment_notification import PaymentNotification
from shared.services.notification_service import NotificationService

class AdminNotificationService(NotificationService):
    """Расширение существующего NotificationService для админской аналитики"""
    
    @cached(ttl=timedelta(minutes=10), key_prefix="admin_notifications_stats")
    async def get_notifications_stats(self) -> Dict[str, Any]:
        """Получение общей статистики уведомлений (включая PaymentNotification)"""
        async with get_async_session() as session:
            # Общее количество
            total_query = select(func.count(Notification.id))
            total_result = await session.execute(total_query)
            total = total_result.scalar()
            
            # По статусам
            status_query = select(
                Notification.status,
                func.count(Notification.id).label('count')
            ).group_by(Notification.status)
            status_result = await session.execute(status_query)
            status_stats = {row.status.value: row.count for row in status_result}
            
            # По каналам
            channel_query = select(
                Notification.channel,
                func.count(Notification.id).label('count')
            ).group_by(Notification.channel)
            channel_result = await session.execute(channel_query)
            channel_stats = {row.channel.value: row.count for row in channel_result}
            
            # По типам
            type_query = select(
                Notification.type,
                func.count(Notification.id).label('count')
            ).group_by(Notification.type)
            type_result = await session.execute(type_query)
            type_stats = {row.type.value: row.count for row in type_result}
            
            return {
                "total": total,
                "status_stats": status_stats,
                "channel_stats": channel_stats,
                "type_stats": type_stats
            }
    
    async def get_notifications_list(
        self,
        page: int = 1,
        per_page: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Notification], int]:
        """Получение списка уведомлений с фильтрами"""
        async with get_async_session() as session:
            query = select(Notification).options(
                selectinload(Notification.user)
            )
            
            # Применяем фильтры
            if filters:
                if filters.get("type"):
                    query = query.where(Notification.type == NotificationType(filters["type"]))
                
                if filters.get("status"):
                    query = query.where(Notification.status == NotificationStatus(filters["status"]))
                
                if filters.get("channel"):
                    query = query.where(Notification.channel == NotificationChannel(filters["channel"]))
                
                if filters.get("date_from"):
                    date_from = datetime.fromisoformat(filters["date_from"])
                    query = query.where(Notification.created_at >= date_from)
                
                if filters.get("date_to"):
                    date_to = datetime.fromisoformat(filters["date_to"])
                    query = query.where(Notification.created_at <= date_to)
                
                if filters.get("search"):
                    search_term = f"%{filters['search']}%"
                    query = query.where(
                        or_(
                            Notification.title.ilike(search_term),
                            Notification.message.ilike(search_term)
                        )
                    )
            
            # Подсчет общего количества
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await session.execute(count_query)
            total = count_result.scalar()
            
            # Пагинация и сортировка
            query = query.order_by(desc(Notification.created_at))
            query = query.offset((page - 1) * per_page).limit(per_page)
            
            result = await session.execute(query)
            notifications = result.scalars().all()
            
            return notifications, total
```

#### NotificationTemplateService

```python
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_
from core.database.session import get_async_session
from domain.entities.notification_template import NotificationTemplate

class NotificationTemplateService:
    """Сервис для управления шаблонами уведомлений"""
    
    async def get_templates(
        self,
        type_filter: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> tuple[List[NotificationTemplate], int]:
        """Получение списка шаблонов"""
        async with get_async_session() as session:
            query = select(NotificationTemplate).where(
                NotificationTemplate.is_deleted == False
            )
            
            if type_filter:
                query = query.where(NotificationTemplate.type == type_filter)
            
            # Подсчет общего количества
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await session.execute(count_query)
            total = count_result.scalar()
            
            # Пагинация
            query = query.order_by(NotificationTemplate.created_at.desc())
            query = query.offset((page - 1) * per_page).limit(per_page)
            
            result = await session.execute(query)
            templates = result.scalars().all()
            
            return templates, total
    
    async def create_template(
        self,
        name: str,
        type: str,
        channel: str,
        title: str,
        message: str,
        variables: Optional[List[str]] = None
    ) -> NotificationTemplate:
        """Создание нового шаблона"""
        async with get_async_session() as session:
            template = NotificationTemplate(
                name=name,
                type=type,
                channel=channel,
                title=title,
                message=message,
                variables=variables or []
            )
            
            session.add(template)
            await session.commit()
            await session.refresh(template)
            
            return template
    
    async def test_template(
        self,
        template_id: int,
        test_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Тестирование шаблона с тестовыми данными"""
        async with get_async_session() as session:
            template_query = select(NotificationTemplate).where(
                NotificationTemplate.id == template_id
            )
            template_result = await session.execute(template_query)
            template = template_result.scalar_one_or_none()
            
            if not template:
                raise ValueError("Template not found")
            
            # Рендеринг шаблона с тестовыми данными
            rendered_title = template.render_title(test_data)
            rendered_message = template.render_message(test_data)
            
            return {
                "rendered_title": rendered_title,
                "rendered_message": rendered_message,
                "variables_used": template.get_used_variables(),
                "missing_variables": template.get_missing_variables(test_data)
            }
```

### 3. Шаблоны

#### Dashboard Template

```html
<!-- apps/web/templates/admin/notifications/dashboard.html -->
{% extends "admin/base_admin.html" %}

{% block title %}Дашборд уведомлений{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <h1 class="h3 mb-4">📊 Дашборд уведомлений</h1>
        </div>
    </div>
    
    <!-- Статистические карточки -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card bg-primary text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h4 class="card-title">📧 Email</h4>
                            <h2 class="mb-0">{{ stats.channel_stats.get('email', 0) }}</h2>
                            <small>95% доставка</small>
                        </div>
                        <div class="align-self-center">
                            <i class="fas fa-envelope fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card bg-success text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h4 class="card-title">📱 SMS</h4>
                            <h2 class="mb-0">{{ stats.channel_stats.get('sms', 0) }}</h2>
                            <small>98% доставка</small>
                        </div>
                        <div class="align-self-center">
                            <i class="fas fa-sms fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card bg-warning text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h4 class="card-title">🔔 Push</h4>
                            <h2 class="mb-0">{{ stats.channel_stats.get('push', 0) }}</h2>
                            <small>92% доставка</small>
                        </div>
                        <div class="align-self-center">
                            <i class="fas fa-bell fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card bg-info text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h4 class="card-title">💬 Telegram</h4>
                            <h2 class="mb-0">{{ stats.channel_stats.get('telegram', 0) }}</h2>
                            <small>99% доставка</small>
                        </div>
                        <div class="align-self-center">
                            <i class="fab fa-telegram fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Графики -->
    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title">📈 Статистика доставки по дням</h5>
                </div>
                <div class="card-body">
                    <canvas id="deliveryChart" width="400" height="200"></canvas>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title">📊 Распределение по каналам</h5>
                </div>
                <div class="card-body">
                    <canvas id="channelChart" width="400" height="200"></canvas>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Топ пользователей -->
    <div class="row mt-4">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title">👥 Топ пользователей по активности</h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Пользователь</th>
                                    <th>Уведомлений</th>
                                    <th>Прочитано</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for user in stats.top_users %}
                                <tr>
                                    <td>{{ user.name }}</td>
                                    <td>{{ user.notifications_count }}</td>
                                    <td>{{ user.read_count }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title">📋 Последние уведомления</h5>
                </div>
                <div class="card-body">
                    <div class="list-group">
                        {% for notification in stats.recent_notifications %}
                        <div class="list-group-item">
                            <div class="d-flex w-100 justify-content-between">
                                <h6 class="mb-1">{{ notification.title }}</h6>
                                <small>{{ notification.created_at|timeago }}</small>
                            </div>
                            <p class="mb-1">{{ notification.message[:100] }}...</p>
                            <small>
                                <span class="badge badge-{{ notification.status|status_color }}">
                                    {{ notification.status|status_label }}
                                </span>
                                <span class="badge badge-secondary">{{ notification.channel|channel_label }}</span>
                            </small>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
// Инициализация графиков
const deliveryCtx = document.getElementById('deliveryChart').getContext('2d');
const deliveryChart = new Chart(deliveryCtx, {
    type: 'line',
    data: {
        labels: {{ stats.delivery_chart.labels|tojson }},
        datasets: [{
            label: 'Доставлено',
            data: {{ stats.delivery_chart.delivered|tojson }},
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            tension: 0.1
        }, {
            label: 'Ошибки',
            data: {{ stats.delivery_chart.failed|tojson }},
            borderColor: 'rgb(255, 99, 132)',
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            tension: 0.1
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});

const channelCtx = document.getElementById('channelChart').getContext('2d');
const channelChart = new Chart(channelCtx, {
    type: 'doughnut',
    data: {
        labels: {{ stats.channel_stats.keys()|list|tojson }},
        datasets: [{
            data: {{ stats.channel_stats.values()|list|tojson }},
            backgroundColor: [
                'rgba(54, 162, 235, 0.8)',
                'rgba(255, 99, 132, 0.8)',
                'rgba(255, 205, 86, 0.8)',
                'rgba(75, 192, 192, 0.8)'
            ]
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: {
                position: 'bottom'
            }
        }
    }
});
</script>
{% endblock %}
```

### 4. JavaScript модули

```javascript
// apps/web/static/js/admin/notifications.js
class AdminNotificationsManager {
    constructor() {
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadInitialData();
    }
    
    bindEvents() {
        // Фильтры
        document.querySelectorAll('.filter-input').forEach(input => {
            input.addEventListener('change', () => this.applyFilters());
        });
        
        // Массовый выбор
        document.getElementById('selectAll').addEventListener('change', (e) => {
            this.toggleSelectAll(e.target.checked);
        });
        
        // Массовые операции
        document.querySelectorAll('.bulk-action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleBulkAction(e.target.dataset.action));
        });
        
        // Обновление каждые 5 минут
        setInterval(() => this.refreshData(), 300000);
    }
    
    async applyFilters() {
        const filters = this.collectFilters();
        const url = new URL(window.location);
        
        // Обновляем URL с параметрами фильтров
        Object.keys(filters).forEach(key => {
            if (filters[key]) {
                url.searchParams.set(key, filters[key]);
            } else {
                url.searchParams.delete(key);
            }
        });
        
        // Загружаем данные
        await this.loadNotifications(url.searchParams);
    }
    
    collectFilters() {
        return {
            type: document.getElementById('typeFilter').value,
            status: document.getElementById('statusFilter').value,
            channel: document.getElementById('channelFilter').value,
            date_from: document.getElementById('dateFrom').value,
            date_to: document.getElementById('dateTo').value,
            search: document.getElementById('searchInput').value
        };
    }
    
    async loadNotifications(params) {
        try {
            this.showLoading();
            
            const response = await fetch(`/admin/api/notifications?${params}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.updateNotificationsTable(data);
            
        } catch (error) {
            this.showError('Ошибка загрузки уведомлений: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    updateNotificationsTable(data) {
        const tbody = document.querySelector('#notificationsTable tbody');
        tbody.innerHTML = '';
        
        data.notifications.forEach(notification => {
            const row = this.createNotificationRow(notification);
            tbody.appendChild(row);
        });
        
        this.updatePagination(data.pagination);
    }
    
    createNotificationRow(notification) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="checkbox" class="notification-checkbox" value="${notification.id}">
            </td>
            <td>${notification.id}</td>
            <td>${notification.user.name}</td>
            <td>
                <span class="badge badge-${this.getTypeColor(notification.type)}">
                    ${this.getTypeLabel(notification.type)}
                </span>
            </td>
            <td>
                <span class="badge badge-${this.getChannelColor(notification.channel)}">
                    ${this.getChannelLabel(notification.channel)}
                </span>
            </td>
            <td>
                <span class="badge badge-${this.getStatusColor(notification.status)}">
                    ${this.getStatusLabel(notification.status)}
                </span>
            </td>
            <td>${notification.title}</td>
            <td>${this.formatDate(notification.created_at)}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="viewNotification(${notification.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteNotification(${notification.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        return row;
    }
    
    async handleBulkAction(action) {
        const selectedIds = this.getSelectedNotificationIds();
        
        if (selectedIds.length === 0) {
            this.showWarning('Выберите уведомления для выполнения операции');
            return;
        }
        
        if (!confirm(`Вы уверены, что хотите ${this.getActionLabel(action)} ${selectedIds.length} уведомлений?`)) {
            return;
        }
        
        try {
            this.showLoading();
            
            const response = await fetch(`/admin/api/notifications/bulk/${action}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ ids: selectedIds })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            this.showSuccess(`Операция выполнена успешно. Обработано: ${result.processed}`);
            
            // Обновляем список
            await this.refreshData();
            
        } catch (error) {
            this.showError('Ошибка выполнения операции: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    getSelectedNotificationIds() {
        const checkboxes = document.querySelectorAll('.notification-checkbox:checked');
        return Array.from(checkboxes).map(cb => parseInt(cb.value));
    }
    
    toggleSelectAll(checked) {
        document.querySelectorAll('.notification-checkbox').forEach(cb => {
            cb.checked = checked;
        });
        this.updateBulkActionButtons();
    }
    
    updateBulkActionButtons() {
        const selectedCount = this.getSelectedNotificationIds().length;
        const buttons = document.querySelectorAll('.bulk-action-btn');
        
        buttons.forEach(btn => {
            btn.disabled = selectedCount === 0;
        });
        
        const counter = document.getElementById('selectedCount');
        if (counter) {
            counter.textContent = selectedCount;
        }
    }
    
    showLoading() {
        const loader = document.getElementById('loadingIndicator');
        if (loader) {
            loader.style.display = 'block';
        }
    }
    
    hideLoading() {
        const loader = document.getElementById('loadingIndicator');
        if (loader) {
            loader.style.display = 'none';
        }
    }
    
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    showError(message) {
        this.showToast(message, 'error');
    }
    
    showWarning(message) {
        this.showToast(message, 'warning');
    }
    
    showToast(message, type) {
        // Реализация toast уведомлений
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }
    
    getTypeColor(type) {
        const colors = {
            'shift_reminder': 'primary',
            'contract_signed': 'success',
            'review_received': 'info',
            'payment_due': 'warning',
            'system_maintenance': 'secondary'
        };
        return colors[type] || 'secondary';
    }
    
    getChannelColor(channel) {
        const colors = {
            'email': 'primary',
            'sms': 'success',
            'push': 'warning',
            'telegram': 'info'
        };
        return colors[channel] || 'secondary';
    }
    
    getStatusColor(status) {
        const colors = {
            'pending': 'warning',
            'sent': 'info',
            'delivered': 'success',
            'failed': 'danger',
            'read': 'primary',
            'cancelled': 'secondary'
        };
        return colors[status] || 'secondary';
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('ru-RU');
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new AdminNotificationsManager();
});
```

---

## 🗄 База данных

### Индексы для оптимизации

```sql
-- Индексы для таблицы notifications
CREATE INDEX CONCURRENTLY idx_notifications_user_id ON notifications(user_id);
CREATE INDEX CONCURRENTLY idx_notifications_status ON notifications(status);
CREATE INDEX CONCURRENTLY idx_notifications_created_at ON notifications(created_at);
CREATE INDEX CONCURRENTLY idx_notifications_type ON notifications(type);
CREATE INDEX CONCURRENTLY idx_notifications_channel ON notifications(channel);
CREATE INDEX CONCURRENTLY idx_notifications_scheduled_at ON notifications(scheduled_at);

-- Составные индексы для сложных запросов
CREATE INDEX CONCURRENTLY idx_notifications_user_status ON notifications(user_id, status);
CREATE INDEX CONCURRENTLY idx_notifications_type_channel ON notifications(type, channel);
CREATE INDEX CONCURRENTLY idx_notifications_created_status ON notifications(created_at, status);

-- Индексы для полнотекстового поиска
CREATE INDEX CONCURRENTLY idx_notifications_title_gin ON notifications USING gin(to_tsvector('russian', title));
CREATE INDEX CONCURRENTLY idx_notifications_message_gin ON notifications USING gin(to_tsvector('russian', message));
```

### Запросы для аналитики

```sql
-- Статистика по каналам за последние 30 дней
SELECT 
    channel,
    COUNT(*) as total,
    COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
    ROUND(
        COUNT(CASE WHEN status = 'delivered' THEN 1 END) * 100.0 / COUNT(*), 
        2
    ) as delivery_rate
FROM notifications 
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY channel
ORDER BY total DESC;

-- Топ пользователей по количеству уведомлений
SELECT 
    u.name,
    u.role,
    COUNT(n.id) as notifications_count,
    COUNT(CASE WHEN n.status = 'read' THEN 1 END) as read_count,
    ROUND(
        COUNT(CASE WHEN n.status = 'read' THEN 1 END) * 100.0 / COUNT(n.id), 
        2
    ) as read_rate
FROM notifications n
JOIN users u ON n.user_id = u.id
WHERE n.created_at >= NOW() - INTERVAL '30 days'
GROUP BY u.id, u.name, u.role
ORDER BY notifications_count DESC
LIMIT 10;

-- Статистика по типам уведомлений
SELECT 
    type,
    COUNT(*) as total,
    COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered,
    COUNT(CASE WHEN status = 'read' THEN 1 END) as read,
    AVG(EXTRACT(EPOCH FROM (read_at - sent_at))/60) as avg_read_time_minutes
FROM notifications 
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY type
ORDER BY total DESC;
```

---

## ⚡ Кэширование

### Стратегия кэширования

```python
from core.cache.redis_cache import cached
from datetime import timedelta

class AdminNotificationService:
    
    @cached(ttl=timedelta(minutes=10), key_prefix="admin_notifications_stats")
    async def get_notifications_stats(self) -> Dict[str, Any]:
        """Кэшируем общую статистику на 10 минут"""
        # ... реализация
    
    @cached(ttl=timedelta(minutes=5), key_prefix="admin_notifications_list")
    async def get_notifications_list(self, **kwargs) -> tuple[List[Notification], int]:
        """Кэшируем список уведомлений на 5 минут"""
        # ... реализация
    
    @cached(ttl=timedelta(minutes=15), key_prefix="admin_notifications_analytics")
    async def get_detailed_analytics(self, **kwargs) -> Dict[str, Any]:
        """Кэшируем аналитику на 15 минут"""
        # ... реализация
    
    async def invalidate_cache(self, cache_keys: List[str]):
        """Инвалидация кэша при изменениях"""
        cache_service = CacheService()
        for key in cache_keys:
            await cache_service.delete(key)
```

### Ключи кэша

```python
# Структура ключей кэша
CACHE_KEYS = {
    "stats": "admin_notifications_stats",
    "list": "admin_notifications_list:{hash}",
    "analytics": "admin_notifications_analytics:{period}:{type_filter}",
    "templates": "admin_notifications_templates:{type_filter}",
    "channel_settings": "admin_notifications_channel_settings"
}
```

---

## 🔒 Безопасность

### Авторизация и права доступа

```python
from apps.web.middleware.auth_middleware import require_superadmin
from fastapi import Depends, HTTPException

@router.get("/admin/notifications/")
async def admin_notifications_dashboard(
    request: Request,
    current_user: dict = Depends(require_superadmin)
):
    """Только суперадмин имеет доступ к админке уведомлений"""
    # ... реализация

# Дополнительная проверка в сервисах
class AdminNotificationService:
    async def validate_admin_access(self, user_id: int) -> bool:
        """Проверка прав доступа к админским функциям"""
        async with get_async_session() as session:
            user_query = select(User).where(User.id == user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            return user and user.role == UserRole.SUPERADMIN
```

### Валидация данных

```python
from pydantic import BaseModel, validator
from typing import Optional, List

class NotificationFilterRequest(BaseModel):
    type: Optional[str] = None
    status: Optional[str] = None
    channel: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    per_page: int = 50
    
    @validator('type')
    def validate_type(cls, v):
        if v and v not in [t.value for t in NotificationType]:
            raise ValueError('Invalid notification type')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v and v not in [s.value for s in NotificationStatus]:
            raise ValueError('Invalid notification status')
        return v
    
    @validator('per_page')
    def validate_per_page(cls, v):
        if v > 100:
            raise ValueError('per_page cannot exceed 100')
        return v
```

### Rate Limiting

```python
from core.middleware.rate_limit import rate_limit

@router.post("/admin/api/notifications/bulk/cancel")
@rate_limit(requests=10, window=60)  # 10 запросов в минуту
async def bulk_cancel_notifications(
    request: BulkActionRequest,
    current_user: dict = Depends(require_superadmin)
):
    """Ограничение на массовые операции"""
    # ... реализация
```

---

## 🚀 Производительность

### Оптимизация запросов

```python
# Использование selectinload для избежания N+1 проблем
async def get_notifications_with_users(self):
    async with get_async_session() as session:
        query = select(Notification).options(
            selectinload(Notification.user)
        ).order_by(desc(Notification.created_at))
        
        result = await session.execute(query)
        return result.scalars().all()

# Использование подзапросов для агрегации
async def get_channel_stats(self):
    async with get_async_session() as session:
        subquery = select(
            Notification.channel,
            func.count(Notification.id).label('total'),
            func.count(CASE(Notification.status == 'delivered', 1)).label('delivered'),
            func.count(CASE(Notification.status == 'failed', 1)).label('failed')
        ).where(
            Notification.created_at >= datetime.now() - timedelta(days=30)
        ).group_by(Notification.channel).subquery()
        
        query = select(subquery)
        result = await session.execute(query)
        return result.fetchall()
```

### Пагинация

```python
async def get_paginated_notifications(
    self,
    page: int = 1,
    per_page: int = 50,
    filters: Optional[Dict[str, Any]] = None
) -> tuple[List[Notification], int, Dict[str, Any]]:
    """Эффективная пагинация с метаданными"""
    async with get_async_session() as session:
        # Базовый запрос
        base_query = select(Notification)
        
        # Применяем фильтры
        if filters:
            base_query = self.apply_filters(base_query, filters)
        
        # Подсчет общего количества
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await session.execute(count_query)
        total = count_result.scalar()
        
        # Вычисляем пагинацию
        total_pages = (total + per_page - 1) // per_page
        offset = (page - 1) * per_page
        
        # Получаем данные
        data_query = base_query.order_by(desc(Notification.created_at))
        data_query = data_query.offset(offset).limit(per_page)
        
        result = await session.execute(data_query)
        notifications = result.scalars().all()
        
        # Метаданные пагинации
        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None
        }
        
        return notifications, total, pagination
```

---

## 🚀 Развертывание

### Docker конфигурация

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  web:
    build: .
    environment:
      - NOTIFICATION_CACHE_TTL=600
      - EXPORT_MAX_RECORDS=10000
      - EXPORT_TEMP_DIR=/tmp
    volumes:
      - ./exports:/app/exports
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: staffprobot_prod
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Миграции

```bash
# Применение миграций
docker compose -f docker-compose.prod.yml exec web alembic upgrade head

# Создание новых миграций
docker compose -f docker-compose.prod.yml exec web alembic revision --autogenerate -m "Add notification admin features"
```

### Переменные окружения

```bash
# .env
# Настройки кэширования
NOTIFICATION_CACHE_TTL=600
ANALYTICS_CACHE_TTL=600

# Настройки экспорта
EXPORT_MAX_RECORDS=10000
EXPORT_TEMP_DIR=/tmp

# Настройки безопасности
ADMIN_RATE_LIMIT=10
ADMIN_RATE_WINDOW=60
```

---

## 📊 Мониторинг

### Метрики для отслеживания

```python
from core.monitoring.metrics import metrics

class AdminNotificationService:
    
    @metrics.timer('admin_notifications_stats_duration')
    async def get_notifications_stats(self):
        """Метрика времени выполнения статистики"""
        # ... реализация
    
    @metrics.counter('admin_notifications_bulk_operations')
    async def bulk_cancel_notifications(self, notification_ids: List[int]):
        """Счетчик массовых операций"""
        metrics.increment('admin_notifications_bulk_cancel', len(notification_ids))
        # ... реализация
```

### Логирование

```python
from core.logging.logger import logger

class AdminNotificationService:
    
    async def bulk_cancel_notifications(self, notification_ids: List[int], admin_user_id: int):
        """Логирование массовых операций"""
        logger.info(
            "Bulk cancel notifications started",
            admin_user_id=admin_user_id,
            notification_count=len(notification_ids),
            notification_ids=notification_ids
        )
        
        try:
            # ... выполнение операции
            
            logger.info(
                "Bulk cancel notifications completed",
                admin_user_id=admin_user_id,
                cancelled_count=cancelled_count
            )
            
        except Exception as e:
            logger.error(
                "Bulk cancel notifications failed",
                admin_user_id=admin_user_id,
                error=str(e),
                notification_ids=notification_ids
            )
            raise
```

---

## 🔧 Troubleshooting

### Частые проблемы

#### 1. Медленная загрузка дашборда

**Проблема:** Дашборд загружается более 5 секунд

**Решение:**
```python
# Проверяем индексы в БД
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'notifications';

# Добавляем недостающие индексы
CREATE INDEX CONCURRENTLY idx_notifications_created_at_status ON notifications(created_at, status);

# Оптимизируем запросы
async def get_notifications_stats_optimized(self):
    async with get_async_session() as session:
        # Используем материализованное представление для статистики
        query = select(text("""
            SELECT 
                channel,
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered
            FROM notifications_mv
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY channel
        """))
        result = await session.execute(query)
        return result.fetchall()
```

#### 2. Ошибки кэширования

**Проблема:** Кэш не обновляется после изменений

**Решение:**
```python
# Инвалидация кэша при изменениях
async def create_notification(self, **kwargs):
    notification = await super().create_notification(**kwargs)
    
    # Инвалидируем связанные кэши
    await self.invalidate_cache([
        "admin_notifications_stats",
        f"admin_notifications_list:*",
        f"admin_notifications_analytics:*"
    ])
    
    return notification
```

#### 3. Проблемы с экспортом

**Проблема:** Экспорт больших объемов данных падает

**Решение:**
```python
# Потоковый экспорт для больших объемов
async def export_notifications_stream(self, filters: Dict[str, Any]):
    """Потоковый экспорт уведомлений"""
    async with get_async_session() as session:
        query = select(Notification).where(
            Notification.created_at >= filters.get('date_from'),
            Notification.created_at <= filters.get('date_to')
        )
        
        # Используем stream для больших результатов
        async for notification in session.stream(query):
            yield notification.to_dict()
```

### Диагностические команды

```bash
# Проверка производительности запросов
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d staffprobot_prod -c "
EXPLAIN ANALYZE SELECT COUNT(*) FROM notifications WHERE created_at >= NOW() - INTERVAL '30 days';
"

# Проверка использования кэша
docker compose -f docker-compose.prod.yml exec redis redis-cli info memory

# Проверка логов
docker compose -f docker-compose.prod.yml logs web | grep "admin_notifications"
```

---

## 📚 Дополнительные ресурсы

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Chart.js Documentation](https://www.chartjs.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)

---

## 🔧 Критические исправления (14 октября 2025)

### Исправление путаницы с активными/неактивными шаблонами

#### Проблема
В списке шаблонов отображались неактивные шаблоны, а кнопка "Удалить" их деактивировала, создавая путаницу в пользовательском интерфейсе.

#### Решение

**1. Фильтрация по умолчанию**
```python
# apps/web/services/notification_template_service.py
async def get_templates_paginated(self, ..., is_active: Optional[bool] = None):
    # По умолчанию показываем только активные шаблоны
    if is_active is None:
        filters.append(NotificationTemplate.is_active == True)
    elif is_active is not None:
        filters.append(NotificationTemplate.is_active == is_active)
```

**2. Фильтр по статусу в UI**
```html
<!-- apps/web/templates/admin/notifications/templates/list.html -->
<div class="col-md-3">
    <label for="status_filter" class="form-label">Статус</label>
    <select class="form-select" id="status_filter" name="status_filter">
        <option value="">Все статусы</option>
        <option value="active">Активные</option>
        <option value="inactive">Неактивные</option>
    </select>
</div>
```

**3. Умные кнопки действий**
```html
{% if template.is_active %}
    <button class="btn btn-sm btn-danger" 
            onclick="deleteTemplate('{{ template.id }}')"
            title="Удалить">
        <i class="fas fa-trash"></i> Удалить
    </button>
{% else %}
    <button class="btn btn-sm btn-success" 
            onclick="restoreTemplate('{{ template.id }}')"
            title="Восстановить">
        <i class="fas fa-undo"></i> Восстановить
    </button>
{% endif %}
```

**4. API для восстановления**
```python
# apps/web/routes/admin_notifications.py
@router.post("/api/templates/restore/{template_id}")
async def admin_notifications_api_template_restore(
    template_id: int,
    current_user: dict = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API: Восстановление кастомного шаблона (активация)"""
    service = NotificationTemplateService(db)
    await service.restore_template(template_id)
    return JSONResponse({"status": "success", "message": "Шаблон восстановлён"})
```

**5. Метод восстановления в сервисе**
```python
# apps/web/services/notification_template_service.py
async def restore_template(self, template_id: int) -> None:
    """Восстановление шаблона (активация)"""
    template = await self.get_template_by_id(template_id)
    if not template:
        raise ValueError(f"Шаблон с ID {template_id} не найден")
    
    template.is_active = True
    await self.session.commit()
```

#### Результат
- ✅ По умолчанию показываются только активные шаблоны
- ✅ Удаление = деактивация (шаблон исчезает из списка)
- ✅ Фильтр "Неактивные" показывает удаленные шаблоны
- ✅ Кнопка "Восстановить" активирует шаблон обратно
- ✅ Логичная и понятная работа с шаблонами

---

**Техническое руководство по итерации 25 завершено! 🚀**
