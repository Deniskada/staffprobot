// Основной JavaScript для StaffProBot Web

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация всех компонентов
    initializeTooltips();
    initializeAlerts();
    initializeForms();
    initializeCharts();
});

// Инициализация тултипов Bootstrap
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Инициализация алертов
function initializeAlerts() {
    // Автоматическое скрытие алертов через 5 секунд
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

// Инициализация форм
function initializeForms() {
    // Валидация форм
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Автоматическая отправка форм с HTMX
    const htmxForms = document.querySelectorAll('form[hx-post]');
    htmxForms.forEach(form => {
        form.addEventListener('htmx:beforeRequest', function(event) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="loading"></span> Загрузка...';
            }
        });
        
        form.addEventListener('htmx:afterRequest', function(event) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = submitBtn.getAttribute('data-original-text') || 'Отправить';
            }
        });
    });
}

// Инициализация графиков
function initializeCharts() {
    // Настройки по умолчанию для Chart.js
    Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
    Chart.defaults.color = '#6c757d';
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
}

// Утилиты для работы с API
const API = {
    // Отправка запроса к API
    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        const config = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },
    
    // GET запрос
    async get(url) {
        return this.request(url, { method: 'GET' });
    },
    
    // POST запрос
    async post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    // PUT запрос
    async put(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    // DELETE запрос
    async delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
};

// Утилиты для работы с уведомлениями
const Notifications = {
    // Показать уведомление
    show(message, type = 'info', duration = 5000) {
        const alertClass = `alert-${type}`;
        const alertId = `alert-${Date.now()}`;
        
        const alertHTML = `
            <div id="${alertId}" class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Добавляем уведомление в контейнер
        let container = document.querySelector('.notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notifications-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        
        container.insertAdjacentHTML('beforeend', alertHTML);
        
        // Автоматическое скрытие
        if (duration > 0) {
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                }
            }, duration);
        }
    },
    
    // Успех
    success(message, duration = 5000) {
        this.show(message, 'success', duration);
    },
    
    // Ошибка
    error(message, duration = 0) {
        this.show(message, 'danger', duration);
    },
    
    // Предупреждение
    warning(message, duration = 5000) {
        this.show(message, 'warning', duration);
    },
    
    // Информация
    info(message, duration = 5000) {
        this.show(message, 'info', duration);
    }
};

// Утилиты для работы с модальными окнами
const Modals = {
    // Показать модальное окно
    show(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        }
    },
    
    // Скрыть модальное окно
    hide(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        }
    }
};

// Утилиты для работы с календарем
const Calendar = {
    // Инициализация FullCalendar
    init(elementId, options = {}) {
        const calendarEl = document.getElementById(elementId);
        if (!calendarEl) return null;
        
        const defaultOptions = {
            initialView: 'dayGridMonth',
            locale: 'ru',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            buttonText: {
                today: 'Сегодня',
                month: 'Месяц',
                week: 'Неделя',
                day: 'День'
            },
            events: [],
            eventClick: function(info) {
                console.log('Event clicked:', info.event);
            }
        };
        
        const config = { ...defaultOptions, ...options };
        return new FullCalendar.Calendar(calendarEl, config);
    }
};

// Утилиты для работы с таблицами
const Tables = {
    // Инициализация DataTables (если используется)
    init(tableId, options = {}) {
        const table = document.getElementById(tableId);
        if (!table) return null;
        
        // Здесь можно добавить инициализацию DataTables
        return table;
    },
    
    // Экспорт таблицы в CSV
    exportToCSV(tableId, filename = 'export.csv') {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        const rows = Array.from(table.querySelectorAll('tr'));
        const csvContent = rows.map(row => {
            const cells = Array.from(row.querySelectorAll('td, th'));
            return cells.map(cell => `"${cell.textContent.trim()}"`).join(',');
        }).join('\n');
        
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
    }
};

// Обработчики HTMX событий
document.addEventListener('htmx:beforeRequest', function(event) {
    // Показываем индикатор загрузки
    const target = event.target;
    if (target.dataset.loading) {
        target.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';
    }
});

document.addEventListener('htmx:afterRequest', function(event) {
    // Скрываем индикатор загрузки
    const target = event.target;
    if (target.dataset.loading) {
        // Восстанавливаем оригинальный контент
        target.innerHTML = target.dataset.originalContent || '';
    }
});

// Экспорт утилит в глобальную область видимости
window.API = API;
window.Notifications = Notifications;
window.Modals = Modals;
window.Calendar = Calendar;
window.Tables = Tables;
