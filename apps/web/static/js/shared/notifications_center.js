/**
 * Центр уведомлений (Notification Center)
 * Управляет отображением, фильтрацией, группировкой и действиями с уведомлениями
 */

class NotificationCenter {
    constructor(userRole = 'owner') {
        this.userRole = userRole;
        this.notifications = [];
        this.selectedNotifications = new Set();
        this.offset = 0;
        this.limit = 30;
        this.hasMore = true;
        this.loading = false;
        this.viewMode = 'grouped'; // 'list' or 'grouped'
        this.filters = {
            status: 'unread',
            category: '',
            sortBy: 'date'
        };
        
        this.init();
    }
    
    init() {
        console.log('[NotificationCenter] Initializing...');
        console.log('[NotificationCenter] View mode:', this.viewMode);
        
        // Проверяем наличие ключевых элементов
        const center = document.getElementById('notifications-center');
        const grouped = document.getElementById('notifications-grouped-view');
        const list = document.getElementById('notifications-list-view');
        
        console.log('[NotificationCenter] Elements found:', {
            center: !!center,
            grouped: !!grouped,
            list: !!list
        });
        
        if (!center) {
            console.error('[NotificationCenter] Main container #notifications-center not found! Cannot initialize.');
            return;
        }
        
        this.setupEventListeners();
        this.setupInfiniteScroll();
        this.loadNotifications(true);
        this.updateUnreadCount();
    }
    
    setupEventListeners() {
        // Фильтры
        document.getElementById('status-filter')?.addEventListener('change', (e) => {
            this.filters.status = e.target.value;
            this.resetAndReload();
        });
        
        document.getElementById('category-filter')?.addEventListener('change', (e) => {
            this.filters.category = e.target.value;
            this.resetAndReload();
        });
        
        document.getElementById('sort-by')?.addEventListener('change', (e) => {
            this.filters.sortBy = e.target.value;
            this.resetAndReload();
        });
        
        document.getElementById('view-mode')?.addEventListener('change', (e) => {
            this.viewMode = e.target.value;
            // При смене режима перезагружаем данные
            this.resetAndReload();
        });
        
        // Отметить все как прочитанные
        document.getElementById('mark-all-read-btn')?.addEventListener('click', () => {
            this.markAllAsRead();
        });
        
        // Массовые действия
        document.getElementById('bulk-mark-read')?.addEventListener('click', () => {
            this.bulkMarkAsRead();
        });
        
        document.getElementById('bulk-delete')?.addEventListener('click', () => {
            this.bulkDelete();
        });
        
        document.getElementById('bulk-cancel')?.addEventListener('click', () => {
            this.clearSelection();
        });
    }
    
    setupInfiniteScroll() {
        const sentinel = document.getElementById('end-of-list');
        if (!sentinel) {
            console.warn('[NotificationCenter] Sentinel element not found for infinite scroll');
            return;
        }
        
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && !this.loading && this.hasMore) {
                this.loadNotifications(false);
            }
        }, { threshold: 0.1 });
        
        observer.observe(sentinel);
    }
    
    async loadNotifications(reset = false) {
        if (this.loading) return;
        
        if (reset) {
            this.offset = 0;
            this.notifications = [];
            this.hasMore = true;
        }
        
        this.loading = true;
        this.showLoading(true);
        
        try {
            const params = new URLSearchParams({
                limit: this.limit,
                offset: this.offset,
                status_filter: this.filters.status,
                sort_by: this.filters.sortBy
            });
            
            if (this.filters.category) {
                // Для категорий нужно передать все типы этой категории
                const categoryTypes = this.getCategoryTypes(this.filters.category);
                // Для простоты используем grouped endpoint
            }
            
            // Используем правильный endpoint в зависимости от режима
            let endpoint = '/api/notifications/center';
            if (this.viewMode === 'grouped') {
                endpoint = '/api/notifications/center/grouped';
                params.set('limit', 100); // Для grouped загружаем больше
            }
            
            const response = await fetch(`${endpoint}?${params}`, {
                headers: { 'Accept': 'application/json' },
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (this.viewMode === 'grouped' && data.grouped) {
                this.handleGroupedData(data, reset);
            } else {
                this.handleListData(data, reset);
            }
            
        } catch (error) {
            console.error('[NotificationCenter] Error loading notifications:', error);
            this.showError('Ошибка загрузки уведомлений');
        } finally {
            this.loading = false;
            this.showLoading(false);
        }
    }
    
    handleListData(data, reset) {
        const newNotifications = data.notifications || [];
        
        if (reset) {
            this.notifications = newNotifications;
        } else {
            this.notifications.push(...newNotifications);
        }
        
        this.hasMore = data.has_more || false;
        this.offset += newNotifications.length;
        
        this.renderNotifications();
        this.updateEmptyState();
    }
    
    handleGroupedData(data, reset) {
        // Для grouped view объединяем уведомления из всех групп
        const grouped = data.grouped || {};
        const allNotifications = [];
        
        for (const category in grouped) {
            for (const type in grouped[category]) {
                allNotifications.push(...grouped[category][type]);
            }
        }
        
        if (reset) {
            this.notifications = allNotifications;
        } else {
            this.notifications.push(...allNotifications);
        }
        
        this.hasMore = false; // Grouped загружает все сразу
        
        this.renderNotifications();
        this.updateEmptyState();
    }
    
    renderNotifications() {
        if (this.viewMode === 'grouped') {
            this.renderGroupedView();
        } else {
            this.renderListView();
        }
    }
    
    renderListView() {
        const container = document.getElementById('notifications-list-view');
        const groupedContainer = document.getElementById('notifications-grouped-view');
        
        if (!container || !groupedContainer) {
            console.error('[NotificationCenter] Containers not found for list view');
            return;
        }
        
        container.classList.remove('d-none');
        groupedContainer.classList.add('d-none');
        
        container.innerHTML = this.notifications.map(n => this.renderNotificationCard(n)).join('');
        
        // Добавляем обработчики событий
        this.attachCardEventListeners();
    }
    
    renderGroupedView() {
        const container = document.getElementById('notifications-grouped-view');
        const listContainer = document.getElementById('notifications-list-view');
        
        if (!container || !listContainer) {
            console.error('[NotificationCenter] Containers not found for grouped view');
            return;
        }
        
        container.classList.remove('d-none');
        listContainer.classList.add('d-none');
        
        // Группируем уведомления по категориям
        const grouped = this.groupNotificationsByCategory(this.notifications);
        
        let html = '';
        for (const [category, notifications] of Object.entries(grouped)) {
            if (notifications.length === 0) continue;
            
            const categoryLabel = this.getCategoryLabel(category);
            const categoryIcon = this.getCategoryIcon(category);
            const categoryId = `category-${category}`;
            
            html += `
                <div class="accordion-item mb-3">
                    <h2 class="accordion-header category-header category-${category}" id="heading-${category}">
                        <button class="accordion-button" type="button" data-bs-toggle="collapse" 
                                data-bs-target="#${categoryId}" aria-expanded="true" aria-controls="${categoryId}">
                            <div class="d-flex align-items-center w-100">
                                <span class="notification-type-icon icon-${category} me-3">
                                    <i class="bi ${categoryIcon}"></i>
                                </span>
                                <span class="flex-grow-1">${categoryLabel}</span>
                                <span class="badge bg-primary rounded-pill">${notifications.length}</span>
                            </div>
                        </button>
                    </h2>
                    <div id="${categoryId}" class="accordion-collapse collapse show" 
                         aria-labelledby="heading-${category}">
                        <div class="accordion-body">
                            ${notifications.map(n => this.renderNotificationCard(n)).join('')}
                        </div>
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = html;
        
        // Добавляем обработчики событий
        this.attachCardEventListeners();
    }
    
    renderNotificationCard(notification) {
        const isUnread = notification.status !== 'read';
        const isUrgent = notification.priority === 'urgent';
        const createdAt = new Date(notification.created_at);
        const timeAgo = this.getTimeAgo(createdAt);
        
        const priorityBadge = this.getPriorityBadge(notification.priority);
        const typeBadge = this.getTypeBadge(notification.type);
        
        return `
            <div class="notification-item ${isUnread ? 'unread' : 'read'} ${isUrgent ? 'urgent' : ''} with-checkbox" 
                 data-id="${notification.id}">
                <input type="checkbox" class="form-check-input notification-checkbox" 
                       data-id="${notification.id}">
                <div class="notification-header">
                    <div class="notification-title">${this.escapeHtml(notification.title)}</div>
                    <div>
                        ${priorityBadge}
                        ${typeBadge}
                    </div>
                </div>
                <div class="notification-message">${this.escapeHtml(notification.message)}</div>
                <div class="notification-meta">
                    <span><i class="bi bi-clock"></i> ${timeAgo}</span>
                    ${isUnread ? '<span class="badge bg-primary">Новое</span>' : ''}
                </div>
                <div class="notification-actions">
                    ${isUnread ? `
                        <button class="btn btn-sm btn-outline-primary mark-read-btn" data-id="${notification.id}">
                            <i class="bi bi-check"></i> Прочитано
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-outline-success action-btn" data-id="${notification.id}">
                        <i class="bi bi-box-arrow-up-right"></i> Перейти
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${notification.id}">
                        <i class="bi bi-trash"></i> Удалить
                    </button>
                </div>
            </div>
        `;
    }
    
    attachCardEventListeners() {
        // Чекбоксы
        document.querySelectorAll('.notification-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const id = parseInt(e.target.dataset.id);
                if (e.target.checked) {
                    this.selectedNotifications.add(id);
                } else {
                    this.selectedNotifications.delete(id);
                }
                this.updateBulkActionsPanel();
            });
        });
        
        // Отметить как прочитанное
        document.querySelectorAll('.mark-read-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.dataset.id);
                this.markAsRead(id);
            });
        });
        
        // Перейти к объекту
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = parseInt(e.target.dataset.id);
                await this.navigateToAction(id);
            });
        });
        
        // Удалить
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.dataset.id);
                this.deleteNotification(id);
            });
        });
    }
    
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/api/notifications/${notificationId}/mark-read`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            
            if (response.ok) {
                // Обновляем локальное состояние
                const notification = this.notifications.find(n => n.id === notificationId);
                if (notification) {
                    notification.status = 'read';
                }
                this.renderNotifications();
                this.updateUnreadCount();
            }
        } catch (error) {
            console.error('[NotificationCenter] Error marking as read:', error);
        }
    }
    
    async deleteNotification(notificationId) {
        if (!confirm('Удалить это уведомление?')) return;
        
        try {
            const response = await fetch(`/api/notifications/${notificationId}/delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            
            if (response.ok) {
                // Удаляем из локального массива
                this.notifications = this.notifications.filter(n => n.id !== notificationId);
                this.renderNotifications();
                this.updateEmptyState();
                this.updateUnreadCount();
            }
        } catch (error) {
            console.error('[NotificationCenter] Error deleting notification:', error);
        }
    }
    
    async navigateToAction(notificationId) {
        try {
            const response = await fetch(`/api/notifications/${notificationId}/action-url`, {
                headers: { 'Accept': 'application/json' },
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.action_url) {
                    window.location.href = data.action_url;
                } else {
                    alert('Нет доступного действия для этого уведомления');
                }
            }
        } catch (error) {
            console.error('[NotificationCenter] Error getting action URL:', error);
        }
    }
    
    async markAllAsRead() {
        if (!confirm('Отметить все уведомления как прочитанные?')) return;
        
        try {
            const response = await fetch('/api/notifications/mark-all-read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            
            if (response.ok) {
                // Обновляем все уведомления
                this.notifications.forEach(n => n.status = 'read');
                this.renderNotifications();
                this.updateUnreadCount();
            }
        } catch (error) {
            console.error('[NotificationCenter] Error marking all as read:', error);
        }
    }
    
    async bulkMarkAsRead() {
        const ids = Array.from(this.selectedNotifications);
        if (ids.length === 0) return;
        
        try {
            const response = await fetch('/api/notifications/mark-read-bulk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ notification_ids: ids })
            });
            
            if (response.ok) {
                // Обновляем локальное состояние
                ids.forEach(id => {
                    const notification = this.notifications.find(n => n.id === id);
                    if (notification) notification.status = 'read';
                });
                this.clearSelection();
                this.renderNotifications();
                this.updateUnreadCount();
            }
        } catch (error) {
            console.error('[NotificationCenter] Error in bulk mark as read:', error);
        }
    }
    
    async bulkDelete() {
        const ids = Array.from(this.selectedNotifications);
        if (ids.length === 0) return;
        
        if (!confirm(`Удалить выбранные уведомления (${ids.length})?`)) return;
        
        try {
            const response = await fetch('/api/notifications/delete-bulk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ notification_ids: ids })
            });
            
            if (response.ok) {
                // Удаляем из локального массива
                this.notifications = this.notifications.filter(n => !ids.includes(n.id));
                this.clearSelection();
                this.renderNotifications();
                this.updateEmptyState();
                this.updateUnreadCount();
            }
        } catch (error) {
            console.error('[NotificationCenter] Error in bulk delete:', error);
        }
    }
    
    clearSelection() {
        this.selectedNotifications.clear();
        document.querySelectorAll('.notification-checkbox').forEach(cb => cb.checked = false);
        this.updateBulkActionsPanel();
    }
    
    updateBulkActionsPanel() {
        const panel = document.getElementById('bulk-actions-panel');
        const count = document.getElementById('selected-count');
        
        if (this.selectedNotifications.size > 0) {
            panel.classList.remove('d-none');
            count.textContent = this.selectedNotifications.size;
        } else {
            panel.classList.add('d-none');
        }
    }
    
    async updateUnreadCount() {
        try {
            const response = await fetch('/api/notifications/unread-count', {
                headers: { 'Accept': 'application/json' },
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                const count = data.count || 0;
                
                const countElement = document.getElementById('unread-count-text');
                if (countElement) {
                    countElement.textContent = `${count} непрочитанных`;
                }
                
                // Обновляем бейдж в колокольчике
                const badge = document.getElementById(`${this.userRole}-notifications-badge`);
                if (badge) {
                    if (count > 0) {
                        badge.textContent = count;
                        badge.classList.remove('d-none');
                    } else {
                        badge.classList.add('d-none');
                    }
                }
            }
        } catch (error) {
            console.error('[NotificationCenter] Error updating unread count:', error);
        }
    }
    
    resetAndReload() {
        this.selectedNotifications.clear();
        this.updateBulkActionsPanel();
        this.loadNotifications(true);
    }
    
    showLoading(show) {
        const indicator = document.getElementById('loading-indicator');
        if (indicator) {
            indicator.classList.toggle('d-none', !show);
        }
    }
    
    updateEmptyState() {
        const empty = document.getElementById('no-notifications');
        const endOfList = document.getElementById('end-of-list');
        
        if (!empty || !endOfList) {
            return;
        }
        
        if (this.notifications.length === 0) {
            empty.classList.remove('d-none');
            endOfList.classList.add('d-none');
        } else {
            empty.classList.add('d-none');
            if (!this.hasMore) {
                endOfList.classList.remove('d-none');
            } else {
                endOfList.classList.add('d-none');
            }
        }
    }
    
    showError(message) {
        // TODO: Implement proper error UI
        alert(message);
    }
    
    groupNotificationsByCategory(notifications) {
        const CATEGORY_MAP = {
            shift_reminder: 'shifts', shift_confirmed: 'shifts', shift_cancelled: 'shifts',
            shift_started: 'shifts', shift_completed: 'shifts',
            object_opened: 'objects', object_closed: 'objects', object_late_opening: 'objects',
            object_no_shifts_today: 'objects', object_early_closing: 'objects',
            contract_signed: 'contracts', contract_terminated: 'contracts',
            contract_expiring: 'contracts', contract_updated: 'contracts',
            review_received: 'reviews', review_moderated: 'reviews',
            appeal_submitted: 'reviews', appeal_decision: 'reviews',
            task_assigned: 'tasks', task_completed: 'tasks', task_overdue: 'tasks',
            payment_due: 'payments', payment_success: 'payments', payment_failed: 'payments',
            subscription_expiring: 'payments', subscription_expired: 'payments',
            usage_limit_warning: 'payments', usage_limit_exceeded: 'payments',
            welcome: 'system', password_reset: 'system', account_suspended: 'system',
            account_activated: 'system', system_maintenance: 'system', feature_announcement: 'system'
        };
        
        const grouped = {};
        
        notifications.forEach(notification => {
            const category = CATEGORY_MAP[notification.type] || 'other';
            if (!grouped[category]) {
                grouped[category] = [];
            }
            grouped[category].push(notification);
        });
        
        // Фильтруем по выбранной категории
        if (this.filters.category) {
            return { [this.filters.category]: grouped[this.filters.category] || [] };
        }
        
        return grouped;
    }
    
    getCategoryLabel(category) {
        const labels = {
            shifts: 'Смены',
            objects: 'Объекты',
            contracts: 'Договоры',
            reviews: 'Отзывы',
            tasks: 'Задачи',
            payments: 'Платежи',
            system: 'Системные'
        };
        return labels[category] || category;
    }
    
    getCategoryIcon(category) {
        const icons = {
            shifts: 'bi-clock-history',
            objects: 'bi-building',
            contracts: 'bi-file-text',
            reviews: 'bi-star',
            tasks: 'bi-check2-square',
            payments: 'bi-credit-card',
            system: 'bi-gear'
        };
        return icons[category] || 'bi-bell';
    }
    
    getCategoryTypes(category) {
        // Возвращает все типы уведомлений для категории
        const types = {
            shifts: ['shift_reminder', 'shift_confirmed', 'shift_cancelled', 'shift_started', 'shift_completed'],
            objects: ['object_opened', 'object_closed', 'object_late_opening', 'object_no_shifts_today', 'object_early_closing'],
            contracts: ['contract_signed', 'contract_terminated', 'contract_expiring', 'contract_updated'],
            reviews: ['review_received', 'review_moderated', 'appeal_submitted', 'appeal_decision'],
            tasks: ['task_assigned', 'task_completed', 'task_overdue'],
            payments: ['payment_due', 'payment_success', 'payment_failed', 'subscription_expiring', 'subscription_expired', 'usage_limit_warning', 'usage_limit_exceeded'],
            system: ['welcome', 'password_reset', 'account_suspended', 'account_activated', 'system_maintenance', 'feature_announcement']
        };
        return types[category] || [];
    }
    
    getPriorityBadge(priority) {
        const badges = {
            urgent: '<span class="badge bg-danger notification-badge">Срочно</span>',
            high: '<span class="badge bg-warning notification-badge">Важно</span>',
            normal: '',
            low: ''
        };
        return badges[priority] || '';
    }
    
    getTypeBadge(type) {
        // Упрощенная версия - просто текст типа
        const typeLabels = {
            shift_started: 'Смена началась',
            shift_completed: 'Смена завершена',
            shift_confirmed: 'Смена подтверждена',
            shift_cancelled: 'Смена отменена',
            // ... добавьте остальные по необходимости
        };
        const label = typeLabels[type] || type.replace(/_/g, ' ');
        return `<span class="badge bg-secondary notification-badge">${label}</span>`;
    }
    
    getTimeAgo(date) {
        const now = new Date();
        const diff = Math.floor((now - date) / 1000); // в секундах
        
        if (diff < 60) return 'только что';
        if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`;
        if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`;
        if (diff < 604800) return `${Math.floor(diff / 86400)} д назад`;
        
        return date.toLocaleDateString('ru-RU');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Определяем роль из URL или другого источника
    const path = window.location.pathname;
    let userRole = 'owner';
    if (path.includes('/manager/')) userRole = 'manager';
    else if (path.includes('/employee/')) userRole = 'employee';
    else if (path.includes('/admin/')) userRole = 'admin';
    
    // Создаем глобальный экземпляр
    window.notificationCenter = new NotificationCenter(userRole);
});

