// JavaScript для календаря собеседований сотрудника

class EmployeeCalendarManager {
    constructor() {
        this.currentDate = new Date();
        this.interviews = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInterviews();
        this.renderCalendar();
    }

    setupEventListeners() {
        // Навигация по месяцам
        document.getElementById('prev-month').addEventListener('click', () => {
            this.currentDate.setMonth(this.currentDate.getMonth() - 1);
            this.updateCalendar();
        });

        document.getElementById('next-month').addEventListener('click', () => {
            this.currentDate.setMonth(this.currentDate.getMonth() + 1);
            this.updateCalendar();
        });

        // Глобальная функция для просмотра деталей собеседования
        window.viewInterviewDetails = (interviewId) => {
            this.viewInterviewDetails(interviewId);
        };
    }

    async loadInterviews() {
        try {
            const year = this.currentDate.getFullYear();
            const month = this.currentDate.getMonth() + 1;
            
            const response = await fetch(`/employee/api/interviews?year=${year}&month=${month}`);
            if (response.ok) {
                this.interviews = await response.json();
                this.updateStatistics();
            } else {
                console.error('Ошибка загрузки собеседований');
            }
        } catch (error) {
            console.error('Ошибка:', error);
        }
    }

    updateCalendar() {
        this.updateMonthDisplay();
        this.loadInterviews();
        this.renderCalendar();
    }

    updateMonthDisplay() {
        const monthNames = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ];
        
        const monthText = `${monthNames[this.currentDate.getMonth()]} ${this.currentDate.getFullYear()}`;
        document.getElementById('current-month-text').textContent = monthText;
    }

    renderCalendar() {
        const calendarGrid = document.getElementById('calendar-grid');
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        
        // Получаем первый день месяца и количество дней
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startingDayOfWeek = firstDay.getDay();
        
        // Создаем заголовки дней недели
        const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
        let calendarHTML = '<div class="calendar-header row mb-2">';
        dayNames.forEach(day => {
            calendarHTML += `<div class="col text-center fw-bold">${day}</div>`;
        });
        calendarHTML += '</div>';
        
        // Создаем сетку календаря
        calendarHTML += '<div class="calendar-body">';
        
        let currentWeek = 0;
        let dayCount = 1;
        
        // Заполняем первую неделю
        calendarHTML += '<div class="row calendar-week">';
        for (let i = 0; i < 7; i++) {
            if (i < startingDayOfWeek - 1) {
                // Пустые ячейки в начале месяца
                calendarHTML += '<div class="col calendar-day empty"></div>';
            } else {
                calendarHTML += this.createDayCell(dayCount, month, year);
                dayCount++;
            }
        }
        calendarHTML += '</div>';
        
        // Заполняем остальные недели
        while (dayCount <= daysInMonth) {
            calendarHTML += '<div class="row calendar-week">';
            for (let i = 0; i < 7 && dayCount <= daysInMonth; i++) {
                calendarHTML += this.createDayCell(dayCount, month, year);
                dayCount++;
            }
            // Заполняем оставшиеся пустые ячейки
            while (calendarHTML.split('</div>').length % 7 !== 0) {
                calendarHTML += '<div class="col calendar-day empty"></div>';
            }
            calendarHTML += '</div>';
        }
        
        calendarHTML += '</div>';
        calendarGrid.innerHTML = calendarHTML;
    }

    createDayCell(day, month, year) {
        const date = new Date(year, month, day);
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const dayInterviews = this.interviews.filter(interview => {
            const interviewDate = new Date(interview.scheduled_at);
            return interviewDate.toDateString() === date.toDateString();
        });
        
        let cellClass = 'col calendar-day';
        let cellContent = `<div class="day-number">${day}</div>`;
        
        if (dayInterviews.length > 0) {
            cellClass += ' has-interviews';
            
            // Определяем стиль в зависимости от статуса собеседований
            const hasToday = dayInterviews.some(interview => {
                const interviewDate = new Date(interview.scheduled_at);
                const today = new Date();
                return interviewDate.toDateString() === today.toDateString();
            });
            
            const hasCompleted = dayInterviews.some(interview => interview.status === 'completed');
            const hasCancelled = dayInterviews.some(interview => interview.status === 'cancelled');
            
            if (hasToday) {
                cellClass += ' today';
            } else if (hasCompleted) {
                cellClass += ' completed';
            } else if (hasCancelled) {
                cellClass += ' cancelled';
            } else {
                cellClass += ' scheduled';
            }
            
            // Добавляем информацию о собеседованиях
            cellContent += '<div class="interviews-info">';
            dayInterviews.forEach(interview => {
                const time = new Date(interview.scheduled_at).toLocaleTimeString('ru-RU', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
                cellContent += `
                    <div class="interview-item" data-interview-id="${interview.id}">
                        <small>${time}</small>
                        <div class="interview-object">${interview.object_name}</div>
                    </div>
                `;
            });
            cellContent += '</div>';
        }
        
        return `<div class="${cellClass}" data-date="${dateStr}">${cellContent}</div>`;
    }

    updateStatistics() {
        const today = new Date();
        const stats = {
            scheduled: 0,
            completed: 0,
            today: 0,
            cancelled: 0
        };
        
        this.interviews.forEach(interview => {
            const interviewDate = new Date(interview.scheduled_at);
            
            if (interview.status === 'completed') {
                stats.completed++;
            } else if (interview.status === 'cancelled') {
                stats.cancelled++;
            } else {
                stats.scheduled++;
            }
            
            if (interviewDate.toDateString() === today.toDateString()) {
                stats.today++;
            }
        });
        
        // Обновляем счетчики
        document.getElementById('scheduled-count').textContent = stats.scheduled;
        document.getElementById('completed-count').textContent = stats.completed;
        document.getElementById('today-count').textContent = stats.today;
        document.getElementById('cancelled-count').textContent = stats.cancelled;
    }

    async viewInterviewDetails(interviewId) {
        try {
            const response = await fetch(`/employee/api/interviews/${interviewId}`);
            if (response.ok) {
                const interview = await response.json();
                this.showInterviewDetailsModal(interview);
            } else {
                this.showNotification('Ошибка загрузки деталей собеседования', 'error');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            this.showNotification('Ошибка загрузки деталей собеседования', 'error');
        }
    }

    showInterviewDetailsModal(interview) {
        const content = document.getElementById('interview-details-content');
        content.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Объект</h6>
                    <p>${interview.object_name}</p>
                    
                    <h6>Дата и время</h6>
                    <p>${new Date(interview.scheduled_at).toLocaleString('ru-RU')}</p>
                    
                    <h6>Тип собеседования</h6>
                    <span class="badge bg-info">${interview.type === 'online' ? 'Онлайн' : 'Очно'}</span>
                </div>
                <div class="col-md-6">
                    ${interview.location ? `
                        <h6>Место проведения</h6>
                        <p>${interview.location}</p>
                    ` : ''}
                    
                    ${interview.contact_person ? `
                        <h6>Контактное лицо</h6>
                        <p>${interview.contact_person}</p>
                    ` : ''}
                    
                    ${interview.contact_phone ? `
                        <h6>Телефон</h6>
                        <p><a href="tel:${interview.contact_phone}">${interview.contact_phone}</a></p>
                    ` : ''}
                </div>
            </div>
            
            ${interview.notes ? `
                <div class="mt-3">
                    <h6>Дополнительная информация</h6>
                    <div class="border p-3 rounded">
                        ${interview.notes}
                    </div>
                </div>
            ` : ''}
            
            ${interview.result ? `
                <div class="mt-3">
                    <h6>Результат собеседования</h6>
                    <div class="border p-3 rounded">
                        ${interview.result}
                    </div>
                </div>
            ` : ''}
        `;

        const modal = new bootstrap.Modal(document.getElementById('interviewDetailsModal'));
        modal.show();
    }

    showNotification(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show position-fixed`;
        alertDiv.style.top = '20px';
        alertDiv.style.right = '20px';
        alertDiv.style.zIndex = '9999';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new EmployeeCalendarManager();
});
