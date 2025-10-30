(() => {
    function initNotificationsBadge() {
        // Находим текущий <script>: учитываем query (?v=)
        const scriptByCurrent = document.currentScript;
        let currentScript = scriptByCurrent;
        if (!currentScript) {
            const byContains = document.querySelector('script[src*="/static/js/shared/applications_badge.js"]');
            currentScript = byContains || null;
        }
        if (!currentScript) {
            console.warn('[applications_badge] Скрипт не найден в DOM');
            return;
        }

        const role = currentScript.dataset.role;
        if (!role) {
            console.error('[applications_badge] Атрибут data-role не задан');
            return;
        }

        // Поддержка старых id (applications) и новых (notifications)
        const candidateIds = role === 'manager'
            ? ['manager-notifications-badge', 'manager-new-applications-badge']
            : ['owner-notifications-badge', 'owner-new-applications-badge'];
        const badgeElement = candidateIds
            .map((id) => document.getElementById(id))
            .find((el) => !!el) || null;
        if (!badgeElement) {
            console.warn('[applications_badge] Элемент бейджа не найден', { candidateIds });
            return;
        }

        const endpoint = '/api/notifications/unread-count';
        const update = () => {
            fetch(endpoint, {
                headers: { 'Accept': 'application/json' },
                credentials: 'include'
            })
                .then((response) => {
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    return response.json();
                })
                .then((data) => {
                    const count = Number(data?.count ?? 0);
                    if (Number.isNaN(count) || count <= 0) {
                        badgeElement.textContent = '';
                        badgeElement.classList.add('d-none');
                        return;
                    }
                    badgeElement.textContent = String(count);
                    badgeElement.classList.remove('d-none');
                })
                .catch((error) => {
                    console.error('[applications_badge] Не удалось получить количество уведомлений', error);
                });
        };

        // Первая загрузка и простой пуллинг
        update();
        setInterval(update, 30000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNotificationsBadge);
    } else {
        initNotificationsBadge();
    }
})();

