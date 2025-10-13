/**
 * Admin Notifications Management
 * JavaScript для управления уведомлениями в админ-панели
 * 
 * Iteration 25, Phase 2
 */

// ============================================================================
// КОНФИГУРАЦИЯ
// ============================================================================

const NOTIFICATION_API_BASE = '/admin/api/notifications';

// ============================================================================
// UTILS
// ============================================================================

/**
 * Получить CSRF токен из cookies
 */
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Показать Toast уведомление
 */
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        console.error('Toast container not found');
        return;
    }

    const toastId = 'toast-' + Date.now();
    const bgClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    }[type] || 'bg-info';

    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();

    // Удалить из DOM после скрытия
    toastElement.addEventListener('hidden.bs.toast', function () {
        toastElement.remove();
    });
}

/**
 * Показать индикатор загрузки
 */
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.disabled = true;
        const originalHtml = element.innerHTML;
        element.setAttribute('data-original-html', originalHtml);
        element.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Загрузка...';
    }
}

/**
 * Скрыть индикатор загрузки
 */
function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.disabled = false;
        const originalHtml = element.getAttribute('data-original-html');
        if (originalHtml) {
            element.innerHTML = originalHtml;
            element.removeAttribute('data-original-html');
        }
    }
}

// ============================================================================
// ФИЛЬТРАЦИЯ И ПОИСК
// ============================================================================

/**
 * Применить фильтры с AJAX обновлением
 */
function applyFilters() {
    const form = document.getElementById('filtersForm');
    if (!form) return;

    const formData = new FormData(form);
    const params = new URLSearchParams(formData);
    
    // Обновить URL без перезагрузки страницы
    const newUrl = window.location.pathname + '?' + params.toString();
    window.history.pushState({}, '', newUrl);
    
    // Загрузить данные через AJAX
    loadNotificationsList(params.toString());
}

/**
 * Сбросить фильтры
 */
function resetFilters() {
    const form = document.getElementById('filtersForm');
    if (!form) return;

    form.reset();
    window.history.pushState({}, '', window.location.pathname);
    loadNotificationsList('');
}

/**
 * Загрузить список уведомлений через AJAX
 */
async function loadNotificationsList(queryString) {
    const container = document.getElementById('notificationsTableContainer');
    if (!container) return;

    try {
        showLoading('applyFiltersBtn');
        
        const response = await fetch(`/admin/notifications/list?${queryString}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load notifications');
        }

        const html = await response.text();
        
        // Извлечь только таблицу из HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newTable = doc.querySelector('.table-responsive');
        
        if (newTable) {
            const currentTable = container.querySelector('.table-responsive');
            if (currentTable) {
                currentTable.replaceWith(newTable);
            }
        }

        showToast('Список обновлен', 'success');

    } catch (error) {
        console.error('Error loading notifications:', error);
        showToast('Ошибка загрузки списка', 'error');
    } finally {
        hideLoading('applyFiltersBtn');
    }
}

// ============================================================================
// ВЫБОР УВЕДОМЛЕНИЙ
// ============================================================================

/**
 * Переключить выбор всех уведомлений
 */
function toggleSelectAll() {
    const selectAll = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('.notification-checkbox');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll.checked;
    });

    updateSelectedCount();
}

/**
 * Обновить счетчик выбранных уведомлений
 */
function updateSelectedCount() {
    const count = getSelectedNotificationIds().length;
    const badge = document.getElementById('selectedCount');
    
    if (badge) {
        if (count > 0) {
            badge.textContent = `Выбрано: ${count}`;
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }
    }
}

/**
 * Получить IDs выбранных уведомлений
 */
function getSelectedNotificationIds() {
    const checkboxes = document.querySelectorAll('.notification-checkbox:checked');
    return Array.from(checkboxes).map(cb => parseInt(cb.value));
}

// ============================================================================
// ОПЕРАЦИИ С УВЕДОМЛЕНИЯМИ
// ============================================================================

/**
 * Просмотр уведомления
 */
async function viewNotification(id) {
    try {
        const response = await fetch(`${NOTIFICATION_API_BASE}/${id}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load notification');
        }

        const data = await response.json();
        
        // Показать в модальном окне
        showNotificationModal(data);

    } catch (error) {
        console.error('Error viewing notification:', error);
        showToast('Ошибка загрузки уведомления', 'error');
    }
}

/**
 * Показать уведомление в модальном окне
 */
function showNotificationModal(notification) {
    const modal = document.getElementById('notificationModal');
    if (!modal) return;

    // Заполнить данные
    document.getElementById('modalNotificationId').textContent = notification.id;
    document.getElementById('modalNotificationType').textContent = notification.type;
    document.getElementById('modalNotificationStatus').textContent = notification.status;
    document.getElementById('modalNotificationChannel').textContent = notification.channel;
    document.getElementById('modalNotificationSubject').textContent = notification.subject;
    document.getElementById('modalNotificationMessage').textContent = notification.message;
    document.getElementById('modalNotificationCreatedAt').textContent = notification.created_at;

    // Показать модальное окно
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Повторить отправку уведомления
 */
async function retryNotification(id) {
    if (!confirm(`Повторить отправку уведомления #${id}?`)) {
        return;
    }

    try {
        const response = await fetch(`${NOTIFICATION_API_BASE}/${id}/retry`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (!response.ok) {
            throw new Error('Failed to retry notification');
        }

        const data = await response.json();
        showToast('Уведомление поставлено в очередь на отправку', 'success');
        
        // Обновить строку в таблице
        setTimeout(() => location.reload(), 1500);

    } catch (error) {
        console.error('Error retrying notification:', error);
        showToast('Ошибка повторной отправки', 'error');
    }
}

/**
 * Отменить уведомление
 */
async function cancelNotification(id) {
    if (!confirm(`Отменить уведомление #${id}?`)) {
        return;
    }

    try {
        const response = await fetch(`${NOTIFICATION_API_BASE}/${id}/cancel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (!response.ok) {
            throw new Error('Failed to cancel notification');
        }

        showToast('Уведомление отменено', 'success');
        
        // Обновить строку в таблице
        setTimeout(() => location.reload(), 1500);

    } catch (error) {
        console.error('Error cancelling notification:', error);
        showToast('Ошибка отмены уведомления', 'error');
    }
}

/**
 * Просмотр пользователя
 */
function viewUser(userId) {
    window.open(`/admin/users/${userId}`, '_blank');
}

// ============================================================================
// МАССОВЫЕ ОПЕРАЦИИ
// ============================================================================

/**
 * Массовая отмена уведомлений
 */
async function bulkCancel() {
    const ids = getSelectedNotificationIds();
    if (ids.length === 0) {
        showToast('Выберите уведомления для отмены', 'warning');
        return;
    }

    if (!confirm(`Отменить ${ids.length} уведомлений?`)) {
        return;
    }

    try {
        const response = await fetch(`${NOTIFICATION_API_BASE}/bulk/cancel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ notification_ids: ids })
        });

        if (!response.ok) {
            throw new Error('Failed to cancel notifications');
        }

        const data = await response.json();
        showToast(`Отменено ${data.cancelled_count} уведомлений`, 'success');
        
        setTimeout(() => location.reload(), 1500);

    } catch (error) {
        console.error('Error cancelling notifications:', error);
        showToast('Ошибка массовой отмены', 'error');
    }
}

/**
 * Массовая повторная отправка
 */
async function bulkRetry() {
    const ids = getSelectedNotificationIds();
    if (ids.length === 0) {
        showToast('Выберите уведомления для повторной отправки', 'warning');
        return;
    }

    if (!confirm(`Повторно отправить ${ids.length} уведомлений?`)) {
        return;
    }

    try {
        const response = await fetch(`${NOTIFICATION_API_BASE}/bulk/retry`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ notification_ids: ids })
        });

        if (!response.ok) {
            throw new Error('Failed to retry notifications');
        }

        const data = await response.json();
        showToast(`Поставлено в очередь ${data.retried_count} уведомлений`, 'success');
        
        setTimeout(() => location.reload(), 1500);

    } catch (error) {
        console.error('Error retrying notifications:', error);
        showToast('Ошибка массовой повторной отправки', 'error');
    }
}

/**
 * Массовое удаление уведомлений
 */
async function bulkDelete() {
    const ids = getSelectedNotificationIds();
    if (ids.length === 0) {
        showToast('Выберите уведомления для удаления', 'warning');
        return;
    }

    if (!confirm(`Удалить ${ids.length} уведомлений? Это действие необратимо!`)) {
        return;
    }

    try {
        const response = await fetch(`${NOTIFICATION_API_BASE}/bulk/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ notification_ids: ids })
        });

        if (!response.ok) {
            throw new Error('Failed to delete notifications');
        }

        const data = await response.json();
        showToast(`Удалено ${data.deleted_count} уведомлений`, 'success');
        
        setTimeout(() => location.reload(), 1500);

    } catch (error) {
        console.error('Error deleting notifications:', error);
        showToast('Ошибка массового удаления', 'error');
    }
}

/**
 * Экспорт уведомлений
 */
async function exportNotifications(format = 'csv') {
    const ids = getSelectedNotificationIds();
    if (ids.length === 0) {
        showToast('Выберите уведомления для экспорта', 'warning');
        return;
    }

    try {
        const response = await fetch(`${NOTIFICATION_API_BASE}/bulk/export`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ 
                notification_ids: ids,
                format: format 
            })
        });

        if (!response.ok) {
            throw new Error('Failed to export notifications');
        }

        // Скачать файл
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `notifications_${Date.now()}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showToast(`Экспортировано ${ids.length} уведомлений`, 'success');

    } catch (error) {
        console.error('Error exporting notifications:', error);
        showToast('Ошибка экспорта', 'error');
    }
}

// ============================================================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Добавить обработчики на чекбоксы
    const checkboxes = document.querySelectorAll('.notification-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedCount);
    });

    // Инициализировать счетчик
    updateSelectedCount();

    console.log('Admin Notifications Management initialized');
});

