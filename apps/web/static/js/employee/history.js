// JavaScript для истории сотрудника

class EmployeeHistoryManager {
    constructor() {
        this.currentView = 'timeline';
        this.events = [];
        this.filteredEvents = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadEvents();
    }

    setupEventListeners() {
        // Переключение между видами
        document.getElementById('view-timeline').addEventListener('click', () => {
            this.switchView('timeline');
        });

        document.getElementById('view-stats').addEventListener('click', () => {
            this.switchView('stats');
        });

        // Применение фильтров
        document.getElementById('apply-filters').addEventListener('click', () => {
            this.applyFilters();
        });
    }

    switchView(view) {
        this.currentView = view;
        
        // Обновляем кнопки
        document.getElementById('view-timeline').classList.toggle('active', view === 'timeline');
        document.getElementById('view-stats').classList.toggle('active', view === 'stats');
        
        // Показываем/скрываем соответствующие блоки
        document.getElementById('timeline-view').classList.toggle('d-none', view !== 'timeline');
        document.getElementById('stats-view').classList.toggle('d-none', view !== 'stats');
        document.getElementById('detailed-stats').classList.toggle('d-none', view !== 'stats');
        
        if (view === 'stats') {
            this.renderCharts();
        }
    }

    async loadEvents() {
        try {
            const response = await fetch('/employee/api/history');
            if (response.ok) {
                this.events = await response.json();
                this.filteredEvents = [...this.events];
                this.updateEventsDisplay();
            } else {
                console.error('Ошибка загрузки истории');
            }
        } catch (error) {
            console.error('Ошибка:', error);
        }
    }

    applyFilters() {
        const filters = {
            eventType: document.getElementById('event-type-filter').value,
            status: document.getElementById('status-filter').value,
            period: document.getElementById('period-filter').value
        };

        this.filteredEvents = this.events.filter(event => {
            // Фильтр по типу события
            if (filters.eventType && event.type !== filters.eventType) {
                return false;
            }

            // Фильтр по статусу
            if (filters.status && event.status !== filters.status) {
                return false;
            }

            // Фильтр по периоду
            if (filters.period) {
                const eventDate = new Date(event.created_at);
                const now = new Date();
                
                switch (filters.period) {
                    case 'week':
                        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                        if (eventDate < weekAgo) {
                            return false;
                        }
                        break;
                    case 'month':
                        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                        if (eventDate < monthAgo) {
                            return false;
                        }
                        break;
                    case 'quarter':
                        const quarterAgo = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
                        if (eventDate < quarterAgo) {
                            return false;
                        }
                        break;
                    case 'year':
                        const yearAgo = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
                        if (eventDate < yearAgo) {
                            return false;
                        }
                        break;
                }
            }

            return true;
        });

        this.updateEventsDisplay();
    }

    updateEventsDisplay() {
        const eventsCount = document.getElementById('events-count');
        eventsCount.textContent = `${this.filteredEvents.length} событий`;
        
        // Обновляем отображение событий
        this.renderTimeline();
    }

    renderTimeline() {
        const timeline = document.querySelector('.timeline');
        if (!timeline) return;

        timeline.innerHTML = this.filteredEvents.map(event => {
            const eventDate = new Date(event.created_at);
            const statusClass = this.getStatusClass(event.status);
            const iconClass = this.getIconClass(event.type);
            
            return `
                <div class="history-item ${statusClass}" data-event-type="${event.type}">
                    <div class="row">
                        <div class="col-md-2">
                            <div class="event-date">
                                <div class="date-day">${eventDate.getDate().toString().padStart(2, '0')}</div>
                                <div class="date-month">${eventDate.toLocaleDateString('ru-RU', { month: 'short' })}</div>
                                <div class="date-year">${eventDate.getFullYear()}</div>
                            </div>
                        </div>
                        <div class="col-md-1">
                            <div class="event-icon">
                                <i class="${iconClass}"></i>
                            </div>
                        </div>
                        <div class="col-md-7">
                            <div class="event-content">
                                <h6 class="event-title">${event.title}</h6>
                                <p class="event-description">${event.description}</p>
                                ${event.object_name ? `
                                    <p class="event-object">
                                        <i class="bi bi-geo-alt"></i> ${event.object_name}
                                    </p>
                                ` : ''}
                            </div>
                        </div>
                        <div class="col-md-2 text-end">
                            <div class="event-status">
                                <span class="badge ${this.getStatusBadgeClass(event.status)}">${this.getStatusText(event.status)}</span>
                            </div>
                            <div class="event-time">
                                <small class="text-muted">${eventDate.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderCharts() {
        this.renderEventsChart();
        this.renderActivityChart();
    }

    renderEventsChart() {
        const ctx = document.getElementById('events-chart');
        if (!ctx) return;

        // Подсчитываем события по типам
        const eventTypes = {};
        this.filteredEvents.forEach(event => {
            eventTypes[event.type] = (eventTypes[event.type] || 0) + 1;
        });

        const labels = Object.keys(eventTypes).map(type => {
            switch (type) {
                case 'application': return 'Заявки';
                case 'interview': return 'Собеседования';
                case 'profile': return 'Профиль';
                case 'system': return 'Система';
                default: return type;
            }
        });
        const data = Object.values(eventTypes);
        const colors = ['#007bff', '#17a2b8', '#28a745', '#6c757d'];

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    renderActivityChart() {
        const ctx = document.getElementById('activity-chart');
        if (!ctx) return;

        // Подсчитываем активность по месяцам
        const monthlyActivity = {};
        this.filteredEvents.forEach(event => {
            const eventDate = new Date(event.created_at);
            const monthKey = `${eventDate.getFullYear()}-${(eventDate.getMonth() + 1).toString().padStart(2, '0')}`;
            monthlyActivity[monthKey] = (monthlyActivity[monthKey] || 0) + 1;
        });

        const labels = Object.keys(monthlyActivity).sort().map(key => {
            const [year, month] = key.split('-');
            const date = new Date(year, month - 1);
            return date.toLocaleDateString('ru-RU', { year: 'numeric', month: 'short' });
        });
        const data = Object.keys(monthlyActivity).sort().map(key => monthlyActivity[key]);

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'События',
                    data: data,
                    backgroundColor: '#007bff',
                    borderColor: '#0056b3',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    getStatusClass(status) {
        switch (status) {
            case 'success': return 'status-success';
            case 'pending': return 'status-warning';
            case 'cancelled': return 'status-danger';
            case 'rejected': return 'status-danger';
            default: return '';
        }
    }

    getIconClass(type) {
        switch (type) {
            case 'application': return 'bi bi-file-text text-primary';
            case 'interview': return 'bi bi-calendar-event text-info';
            case 'profile': return 'bi bi-person text-success';
            case 'system': return 'bi bi-gear text-secondary';
            default: return 'bi bi-circle text-secondary';
        }
    }

    getStatusBadgeClass(status) {
        switch (status) {
            case 'success': return 'bg-success';
            case 'pending': return 'bg-warning';
            case 'cancelled': return 'bg-secondary';
            case 'rejected': return 'bg-danger';
            default: return 'bg-secondary';
        }
    }

    getStatusText(status) {
        switch (status) {
            case 'success': return 'Успешно';
            case 'pending': return 'В процессе';
            case 'cancelled': return 'Отменено';
            case 'rejected': return 'Отклонено';
            default: return 'Неизвестно';
        }
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new EmployeeHistoryManager();
});
