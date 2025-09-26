(() => {
    function initApplicationsBadge() {
        const scripts = document.querySelectorAll('script[src$="/static/js/shared/applications_badge.js"]');
        if (!scripts.length) {
            console.warn('[applications_badge] Скрипт не найден в DOM');
            return;
        }

        const currentScript = scripts[scripts.length - 1];
        const role = currentScript.dataset.role;
        if (!role) {
            console.error('[applications_badge] Атрибут data-role не задан');
            return;
        }

        const badgeId = role === 'manager'
            ? 'manager-new-applications-badge'
            : 'owner-new-applications-badge';
        const badgeElement = document.getElementById(badgeId);
        if (!badgeElement) {
            console.warn('[applications_badge] Элемент бейджа не найден', { badgeId });
            return;
        }

        const endpoint = role === 'manager'
            ? '/manager/api/applications/count'
            : '/owner/api/applications/count';

        console.debug('[applications_badge] Запрос количества заявок', { role, endpoint });

        fetch(endpoint, {
            headers: {
                'Accept': 'application/json'
            },
            credentials: 'include'
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                const count = Number(data?.count ?? 0);
                console.debug('[applications_badge] Ответ сервера', { role, count, raw: data });
                if (Number.isNaN(count) || count <= 0) {
                    badgeElement.textContent = '';
                    badgeElement.classList.add('d-none');
                    return;
                }

                badgeElement.textContent = String(count);
                badgeElement.classList.remove('d-none');
            })
            .catch((error) => {
                console.error('[applications_badge] Не удалось получить количество заявок', error);
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initApplicationsBadge);
    } else {
        initApplicationsBadge();
    }
})();

