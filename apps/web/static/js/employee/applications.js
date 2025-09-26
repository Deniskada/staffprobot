// JavaScript для страницы заявок сотрудника

class EmployeeApplicationsManager {
    constructor() {
        this.bindActions();
        this.updateStatisticsFromDom();
    }

    bindActions() {
        document.querySelectorAll('[data-action="cancel-application"]').forEach((button) => {
            button.addEventListener('click', () => this.cancelApplication(button.dataset.applicationId));
        });

        document.querySelectorAll('[data-action="view-application"]').forEach((button) => {
            button.addEventListener('click', () => this.viewApplicationDetails(button.dataset.applicationId));
        });

        document.querySelectorAll('[data-action="view-interview"]').forEach((button) => {
            button.addEventListener('click', () => this.viewInterviewDetails(button.dataset.applicationId));
        });
    }

    updateStatisticsFromDom() {
        const stats = {
            pending: 0,
            approved: 0,
            rejected: 0,
            interview: 0
        };

        document.querySelectorAll('.application-card').forEach((card) => {
            const status = card.dataset.status;
            if (status && stats[status] !== undefined) {
                stats[status] += 1;
            }
        });

        const totalBadge = document.getElementById('applications-count');
        if (totalBadge) {
            totalBadge.textContent = `${document.querySelectorAll('.application-card').length} заявок`;
        }

        document.querySelectorAll('[data-status-card]').forEach((card) => {
            const key = card.dataset.statusCard;
            const counter = card.querySelector('[data-status-count]');
            if (counter && stats[key] !== undefined) {
                counter.textContent = stats[key];
            }
        });
    }

    async cancelApplication(applicationId) {
        if (!confirm('Вы уверены, что хотите отозвать эту заявку?')) {
            return;
        }

        try {
            const response = await fetch(`/employee/api/applications/${applicationId}/cancel`, {
                method: 'POST'
            });

            if (response.ok) {
                this.showNotification('Заявка успешно отозвана', 'success');
                setTimeout(() => window.location.reload(), 1200);
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Ошибка при отзыве заявки', 'error');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            this.showNotification('Ошибка при отзыве заявки', 'error');
        }
    }

    async viewApplicationDetails(applicationId) {
        try {
            const response = await fetch(`/employee/api/applications/${applicationId}`);
            if (response.ok) {
                const application = await response.json();
                this.showApplicationDetailsModal(application);
            } else {
                this.showNotification('Ошибка загрузки деталей заявки', 'error');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            this.showNotification('Ошибка загрузки деталей заявки', 'error');
        }
    }

    showApplicationDetailsModal(application) {
        const content = document.getElementById('application-details-content');
        if (!content) return;

        content.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Объект</h6>
                    <p>${application.object_name}</p>
                    <h6>Статус</h6>
                    <span class="badge bg-${this.getStatusColor(application.status)}">${this.getStatusText(application.status)}</span>
                    <h6 class="mt-3">Дата подачи</h6>
                    <p>${new Date(application.created_at).toLocaleString('ru-RU')}</p>
                </div>
                <div class="col-md-6">
                    ${application.preferred_schedule ? `<h6>Предпочитаемый график</h6><p>${application.preferred_schedule}</p>` : ''}
                    ${application.interview_scheduled_at ? `<h6>Собеседование</h6><p>${new Date(application.interview_scheduled_at).toLocaleString('ru-RU')}</p>` : ''}
                    ${application.interview_type ? `<p><span class="badge bg-info">${application.interview_type === 'online' ? 'Онлайн' : 'Очно'}</span></p>` : ''}
                </div>
            </div>
            ${application.message ? `<div class="mt-3"><h6>Ваше сообщение</h6><div class="border p-3 rounded">${application.message}</div></div>` : ''}
            ${application.interview_result ? `<div class="mt-3"><h6>Результат собеседования</h6><div class="border p-3 rounded">${application.interview_result}</div></div>` : ''}
        `;

        const modal = new bootstrap.Modal(document.getElementById('applicationDetailsModal'));
        modal.show();
    }

    async viewInterviewDetails(applicationId) {
        try {
            const response = await fetch(`/employee/api/applications/${applicationId}/interview`);
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
        if (!content) return;

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
                    ${interview.location ? `<h6>Место проведения</h6><p>${interview.location}</p>` : ''}
                    ${interview.contact_person ? `<h6>Контактное лицо</h6><p>${interview.contact_person}</p>` : ''}
                    ${interview.contact_phone ? `<h6>Телефон</h6><p><a href="tel:${interview.contact_phone} ">${interview.contact_phone}</a></p>` : ''}
                </div>
            </div>
            ${interview.notes ? `<div class="mt-3"><h6>Дополнительная информация</h6><div class="border p-3 rounded">${interview.notes}</div></div>` : ''}
            ${interview.result ? `<div class="mt-3"><h6>Результат собеседования</h6><div class="border p-3 rounded">${interview.result}</div></div>` : ''}
        `;

        const modal = new bootstrap.Modal(document.getElementById('interviewDetailsModal'));
        modal.show();
    }

    getStatusColor(status) {
        switch (status) {
            case 'pending': return 'warning';
            case 'approved': return 'success';
            case 'rejected': return 'danger';
            case 'interview': return 'info';
            default: return 'secondary';
        }
    }

    getStatusText(status) {
        switch (status) {
            case 'pending': return 'На рассмотрении';
            case 'approved': return 'Одобрена';
            case 'rejected': return 'Отклонена';
            case 'interview': return 'Собеседование';
            default: return 'Неизвестно';
        }
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
    new EmployeeApplicationsManager();
});
