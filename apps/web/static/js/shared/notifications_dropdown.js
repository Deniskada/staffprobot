/**
 * Дропдаун уведомлений для колокольчика
 * Показывает 10 последних уведомлений и кнопку "Отметить все как прочитанные"
 */
(() => {
    function initNotificationsDropdown() {
        const dropdownElement = document.getElementById('owner-notifications-dropdown');
        const listContainer = document.getElementById('notifications-list');
        const markAllBtn = document.getElementById('mark-all-read-btn');
        const dropdownButton = document.getElementById('ownerNotificationsDropdown');

        if (!dropdownElement || !listContainer || !markAllBtn) {
            console.warn('[notifications_dropdown] Элементы дропдауна не найдены');
            return;
        }

        // Загрузка списка уведомлений
        function loadNotifications() {
            listContainer.innerHTML = `
                <div class="text-center py-3 text-muted">
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Загрузка...</span>
                    </div>
                </div>
            `;

            fetch('/api/notifications/list?limit=10', {
                headers: { 'Accept': 'application/json' },
                credentials: 'include'
            })
                .then((response) => {
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    return response.json();
                })
                .then((data) => {
                    const notifications = data?.notifications || [];
                    if (notifications.length === 0) {
                        listContainer.innerHTML = `
                            <div class="text-center py-4 text-muted">
                                <i class="bi bi-inbox" style="font-size: 2rem;"></i>
                                <p class="mb-0 mt-2">Нет новых уведомлений</p>
                            </div>
                        `;
                        return;
                    }

                    listContainer.innerHTML = notifications.map((notification) => {
                        const isUnread = notification.status === 'pending';
                        const createdAt = new Date(notification.created_at);
                        const timeAgo = formatTimeAgo(createdAt);
                        
                        return `
                            <div class="dropdown-item py-2 ${isUnread ? 'bg-light' : ''}" 
                                 style="white-space: normal; cursor: pointer;"
                                 data-notification-id="${notification.id}">
                                <div class="d-flex align-items-start">
                                    ${isUnread ? '<span class="badge bg-primary me-2" style="font-size: 0.6rem;">●</span>' : '<span class="me-2" style="width: 1rem;"></span>'}
                                    <div class="flex-grow-1">
                                        <div class="fw-semibold small">${escapeHtml(notification.title || 'Уведомление')}</div>
                                        <div class="text-muted small">${escapeHtml(notification.message || '')}</div>
                                        <div class="text-muted" style="font-size: 0.75rem;">${timeAgo}</div>
                                    </div>
                                </div>
                            </div>
                        `;
                    }).join('');

                    // Клик по уведомлению для перехода (если есть link)
                    listContainer.querySelectorAll('[data-notification-id]').forEach((item) => {
                        item.addEventListener('click', () => {
                            const notificationId = item.dataset.notificationId;
                            const notification = notifications.find((n) => String(n.id) === notificationId);
                            if (notification && notification.link) {
                                window.location.href = notification.link;
                            }
                        });
                    });
                })
                .catch((error) => {
                    console.error('[notifications_dropdown] Не удалось загрузить уведомления', error);
                    listContainer.innerHTML = `
                        <div class="text-center py-3 text-danger">
                            <i class="bi bi-exclamation-triangle"></i>
                            <p class="mb-0 small">Ошибка загрузки</p>
                        </div>
                    `;
                });
        }

        // Отметить все как прочитанные
        markAllBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            fetch('/api/notifications/mark-all-read', {
                method: 'POST',
                headers: { 
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            })
                .then((response) => {
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    return response.json();
                })
                .then(() => {
                    // Обновить бейдж и список
                    const badge = document.getElementById('owner-notifications-badge');
                    if (badge) {
                        badge.textContent = '';
                        badge.classList.add('d-none');
                    }
                    loadNotifications();
                })
                .catch((error) => {
                    console.error('[notifications_dropdown] Не удалось отметить все как прочитанные', error);
                    alert('Ошибка при отметке уведомлений');
                });
        });

        // Загрузка при открытии дропдауна
        if (dropdownButton) {
            dropdownButton.addEventListener('show.bs.dropdown', () => {
                loadNotifications();
            });
        }

        // Форматирование времени
        function formatTimeAgo(date) {
            const now = new Date();
            const diffMs = now - date;
            const diffSec = Math.floor(diffMs / 1000);
            const diffMin = Math.floor(diffSec / 60);
            const diffHour = Math.floor(diffMin / 60);
            const diffDay = Math.floor(diffHour / 24);

            if (diffSec < 60) return 'только что';
            if (diffMin < 60) return `${diffMin} мин назад`;
            if (diffHour < 24) return `${diffHour} ч назад`;
            if (diffDay < 7) return `${diffDay} дн назад`;
            
            return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
        }

        // Экранирование HTML
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNotificationsDropdown);
    } else {
        initNotificationsDropdown();
    }
})();

