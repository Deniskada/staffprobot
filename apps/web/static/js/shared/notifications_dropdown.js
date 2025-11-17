/**
 * Дропдаун уведомлений для колокольчика
 * Показывает 10 последних уведомлений и кнопку "Отметить все как прочитанные"
 * Поддерживает owner и manager роли
 */
(() => {
    function initNotificationsDropdown() {
        console.log('[notifications_dropdown] Инициализация...');
        
        // Определяем роль по наличию элементов
        const ownerDropdown = document.getElementById('owner-notifications-dropdown');
        const managerDropdown = document.getElementById('manager-notifications-dropdown');
        
        console.log('[notifications_dropdown] ownerDropdown:', !!ownerDropdown, 'managerDropdown:', !!managerDropdown);
        
        const dropdownElement = ownerDropdown || managerDropdown;
        const listContainer = document.getElementById('notifications-list');
        const markAllBtn = document.getElementById('mark-all-read-btn');
        const dropdownButton = document.getElementById('ownerNotificationsDropdown') || 
                               document.getElementById('managerNotificationsDropdown');
        const badgeId = ownerDropdown ? 'owner-notifications-badge' : 'manager-notifications-badge';

        console.log('[notifications_dropdown] Элементы:', {
            dropdownElement: !!dropdownElement,
            listContainer: !!listContainer,
            markAllBtn: !!markAllBtn,
            dropdownButton: !!dropdownButton,
            badgeId: badgeId
        });

        if (!dropdownElement || !listContainer || !markAllBtn || !dropdownButton) {
            console.warn('[notifications_dropdown] Элементы дропдауна не найдены', {
                dropdownElement: !!dropdownElement,
                listContainer: !!listContainer,
                markAllBtn: !!markAllBtn,
                dropdownButton: !!dropdownButton
            });
            return;
        }
        
        console.log('[notifications_dropdown] Инициализация успешна');

        // Загрузка списка уведомлений
        function loadNotifications() {
            console.log('[notifications_dropdown] loadNotifications вызвана');
            
            if (!listContainer) {
                console.error('[notifications_dropdown] listContainer не найден!');
                return;
            }
            
            listContainer.innerHTML = `
                <div class="text-center py-3 text-muted">
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Загрузка...</span>
                    </div>
                </div>
            `;

            console.log('[notifications_dropdown] Отправка запроса к /api/notifications/list');
            fetch('/api/notifications/list?limit=10', {
                headers: { 'Accept': 'application/json' },
                credentials: 'include'
            })
                .then((response) => {
                    if (!response.ok) {
                        console.error('[notifications_dropdown] HTTP error:', response.status, response.statusText);
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then((data) => {
                    console.log('[notifications_dropdown] Received data:', data);
                    const notifications = data?.notifications || [];
                    
                    if (!Array.isArray(notifications)) {
                        console.error('[notifications_dropdown] Invalid data format, expected array:', notifications);
                        listContainer.innerHTML = `
                            <div class="text-center py-3 text-danger">
                                <i class="bi bi-exclamation-triangle"></i>
                                <p class="mb-0 small">Ошибка формата данных</p>
                            </div>
                        `;
                        return;
                    }
                    
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
                        // Непрочитанные: pending, sent, delivered (но не read)
                        const isUnread = notification.status !== 'read' && notification.status !== 'cancelled' && notification.status !== 'deleted';
                        const createdAt = new Date(notification.created_at);
                        const timeAgo = formatTimeAgo(createdAt);
                        
                        // Преобразуем HTML в текст для дропдауна
                        const messageText = stripHtml(notification.message || '');
                        
                        return `
                            <div class="dropdown-item py-2 ${isUnread ? 'bg-light' : ''}" 
                                 style="white-space: normal; cursor: pointer;"
                                 data-notification-id="${notification.id}">
                                <div class="d-flex align-items-start">
                                    ${isUnread ? '<span class="badge bg-primary me-2" style="font-size: 0.6rem;">●</span>' : '<span class="me-2" style="width: 1rem;"></span>'}
                                    <div class="flex-grow-1">
                                        <div class="fw-semibold small">${escapeHtml(notification.title || 'Уведомление')}</div>
                                        <div class="text-muted small" style="line-height: 1.4; white-space: pre-line;">${escapeHtml(messageText)}</div>
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
                            <p class="mb-0" style="font-size: 0.75rem; color: #999;">${error.message || 'Неизвестная ошибка'}</p>
                        </div>
                    `;
                });
        }

        // Предотвращаем закрытие дропдауна при клике внутри него
        dropdownElement.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Отметить все как прочитанные
        markAllBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
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
                .then((result) => {
                    console.log('[notifications_dropdown] Mark all read result:', result);
                    // Обновляем бейдж через API сразу
                    if (typeof window.updateNotificationsBadge === 'function') {
                        window.updateNotificationsBadge();
                    } else {
                        // Fallback: обновляем бейдж напрямую
                        fetch('/api/notifications/unread-count', {
                            headers: { 'Accept': 'application/json' },
                            credentials: 'include'
                        })
                        .then(response => response.json())
                        .then(data => {
                            const badge = document.getElementById(badgeId);
                            if (badge) {
                                const count = Number(data?.count ?? 0);
                                if (count > 0) {
                                    badge.textContent = String(count);
                                    badge.classList.remove('d-none');
                                } else {
                                    badge.textContent = '';
                                    badge.classList.add('d-none');
                                }
                            }
                        })
                        .catch(err => console.error('[notifications_dropdown] Ошибка обновления бейджа', err));
                    }
                    // Перезагружаем список уведомлений после небольшой задержки (чтобы БД обновилась)
                    setTimeout(() => {
                        loadNotifications();
                    }, 200);
                })
                .catch((error) => {
                    console.error('[notifications_dropdown] Не удалось отметить все как прочитанные', error);
                    alert('Ошибка при отметке уведомлений');
                });
        });

        // Загрузка при открытии дропдауна
        if (dropdownButton) {
            console.log('[notifications_dropdown] Регистрация события открытия дропдауна');
            
            // Используем несколько событий для надежности
            dropdownButton.addEventListener('show.bs.dropdown', () => {
                console.log('[notifications_dropdown] Событие show.bs.dropdown сработало');
                loadNotifications();
            });
            
            // Также слушаем клик на кнопку (на случай, если Bootstrap события не работают)
            dropdownButton.addEventListener('click', (e) => {
                // Проверяем, что дропдаун открыт или открывается
                const isExpanded = dropdownButton.getAttribute('aria-expanded') === 'true';
                if (!isExpanded) {
                    console.log('[notifications_dropdown] Клик на кнопку, загружаем уведомления');
                    // Небольшая задержка, чтобы дропдаун успел открыться
                    setTimeout(() => {
                        loadNotifications();
                    }, 100);
                }
            });
        } else {
            console.error('[notifications_dropdown] dropdownButton не найден!');
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

        // Удаление HTML-тегов и преобразование в текст
        function stripHtml(html) {
            if (!html) return '';
            
            // Создаем временный элемент для парсинга HTML
            const tmp = document.createElement('div');
            tmp.innerHTML = html;
            
            // Заменяем блочные элементы на переносы строк перед извлечением текста
            // Обрабатываем в обратном порядке, чтобы не сломать структуру
            const blockElements = tmp.querySelectorAll('h1, h2, h3, h4, h5, h6, p, br, div, li');
            blockElements.forEach((el) => {
                if (el.tagName === 'BR') {
                    el.replaceWith(document.createTextNode('\n'));
                } else {
                    // Добавляем переносы строк до и после блочного элемента
                    const before = document.createTextNode('\n');
                    const after = document.createTextNode('\n');
                    el.parentNode.insertBefore(before, el);
                    el.parentNode.insertBefore(after, el.nextSibling);
                }
            });
            
            // Извлекаем текст (все теги будут проигнорированы)
            let text = tmp.textContent || tmp.innerText || '';
            
            // Удаляем множественные переносы строк, оставляем максимум 2 подряд
            text = text.replace(/\n{3,}/g, '\n\n');
            
            // Удаляем пробелы в начале и конце строк
            text = text.split('\n').map(line => line.trim()).join('\n');
            
            // Удаляем пустые строки в начале и конце
            text = text.trim();
            
            return text;
        }
    }

    // Инициализация с проверкой готовности DOM и Bootstrap
    function tryInit() {
        // Проверяем, что Bootstrap загружен
        if (typeof bootstrap === 'undefined') {
            console.warn('[notifications_dropdown] Bootstrap не загружен, повторная попытка через 100мс');
            setTimeout(tryInit, 100);
            return;
        }
        
        initNotificationsDropdown();
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', tryInit);
    } else {
        // Если DOM уже загружен, даем небольшую задержку для Bootstrap
        setTimeout(tryInit, 50);
    }
})();


