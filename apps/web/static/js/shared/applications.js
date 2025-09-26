// JavaScript для работы с заявками (shared компонент)

class ApplicationsManager {
    constructor() {
        this.approveEndpoint = '/owner/api/applications/approve';
        this.rejectEndpoint = '/owner/api/applications/reject';
        this.currentRole = 'owner';
        this.init();
    }

    init() {
        document.addEventListener('click', (e) => {
            const approveBtn = e.target.closest('.approve-application');
            if (approveBtn) {
                this.approveEndpoint = approveBtn.dataset.endpoint || this.approveEndpoint;
                this.currentRole = approveBtn.dataset.role || this.currentRole;
                const form = document.getElementById('approve-application-form');
                form.dataset.endpoint = this.approveEndpoint;
                form.dataset.role = this.currentRole;
                this.showApproveModal(approveBtn.dataset.applicationId);
                return;
            }

            const rejectBtn = e.target.closest('.reject-application');
            if (rejectBtn) {
                this.rejectEndpoint = rejectBtn.dataset.endpoint || this.rejectEndpoint;
                this.currentRole = rejectBtn.dataset.role || this.currentRole;
                const form = document.getElementById('reject-application-form');
                form.dataset.endpoint = this.rejectEndpoint;
                form.dataset.role = this.currentRole;
                this.showRejectModal(rejectBtn.dataset.applicationId);
                return;
            }

            if (e.target.id === 'confirm-approve') {
                this.approveApplication();
            }

            if (e.target.id === 'confirm-reject') {
                this.rejectApplication();
            }
        });

        document.addEventListener('click', (e) => {
            const viewBtn = e.target.closest('.view-application');
            if (viewBtn) {
                this.viewApplicationDetails(viewBtn.dataset.applicationId, viewBtn.dataset.role || this.currentRole);
                return;
            }
        });
    }

    showApproveModal(applicationId) {
        const applicationCard = document.querySelector(`[data-application-id="${applicationId}"]`);
        if (!applicationCard) return;

        const button = document.querySelector(`.approve-application[data-application-id="${applicationId}"]`);
        if (button) {
            this.approveEndpoint = button.dataset.endpoint || this.approveEndpoint;
            this.currentRole = button.dataset.role || this.currentRole;
        }

        const form = document.getElementById('approve-application-form');
        form.dataset.endpoint = this.approveEndpoint;
        form.dataset.role = this.currentRole;

        // Заполняем модальное окно
        const applicantName = applicationCard.querySelector('.card-header h6').textContent.trim();
        const objectName = applicationCard.querySelector('.card-header small').textContent.trim();

        document.getElementById('approve-application-id').value = applicationId;
        document.getElementById('approve-applicant-name').value = applicantName;
        document.getElementById('approve-object-name').value = objectName;

        // Устанавливаем минимальную дату (завтра)
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        const minDate = tomorrow.toISOString().slice(0, 16);
        document.getElementById('interview-datetime').min = minDate;

        // Показываем модальное окно
        const modal = new bootstrap.Modal(document.getElementById('approveApplicationModal'));
        modal.show();
    }

    showRejectModal(applicationId) {
        const applicationCard = document.querySelector(`[data-application-id="${applicationId}"]`);
        if (!applicationCard) return;

        const button = document.querySelector(`.reject-application[data-application-id="${applicationId}"]`);
        if (button) {
            this.rejectEndpoint = button.dataset.endpoint || this.rejectEndpoint;
            this.currentRole = button.dataset.role || this.currentRole;
        }

        const form = document.getElementById('reject-application-form');
        form.dataset.endpoint = this.rejectEndpoint;
        form.dataset.role = this.currentRole;

        // Заполняем модальное окно
        const applicantName = applicationCard.querySelector('.card-header h6').textContent.trim();
        const objectName = applicationCard.querySelector('.card-header small').textContent.trim();

        document.getElementById('reject-application-id').value = applicationId;
        document.getElementById('reject-applicant-name').value = applicantName;
        document.getElementById('reject-object-name').value = objectName;

        // Показываем модальное окно
        const modal = new bootstrap.Modal(document.getElementById('rejectApplicationModal'));
        modal.show();
    }

    async approveApplication() {
        const form = document.getElementById('approve-application-form');
        const formData = new FormData(form);
        
        try {
            console.debug('[Applications] approve endpoint', this.approveEndpoint);
            const response = await fetch(this.approveEndpoint, {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Заявка одобрена:', result);
                
                // Закрываем модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('approveApplicationModal'));
                modal.hide();
                
                // Показываем уведомление
                this.showSuccess('Заявка одобрена и собеседование назначено!');
                
                // Обновляем страницу
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
                
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка одобрения заявки');
            }
        } catch (error) {
            console.error('Ошибка одобрения заявки:', error);
            this.showError('Ошибка одобрения заявки: ' + error.message);
        }
    }

    async rejectApplication() {
        const form = document.getElementById('reject-application-form');
        const formData = new FormData(form);

        try {
            const endpoint = form.dataset.endpoint || this.rejectEndpoint;
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Заявка отклонена:', result);
                
                // Закрываем модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('rejectApplicationModal'));
                modal.hide();
                
                // Показываем уведомление
                this.showSuccess('Заявка отклонена!');
                
                // Обновляем страницу
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
                
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка отклонения заявки');
            }
        } catch (error) {
            console.error('Ошибка отклонения заявки:', error);
            this.showError('Ошибка отклонения заявки: ' + error.message);
        }
    }

    async viewApplicationDetails(applicationId, role = 'manager') {
        try {
            const response = await fetch(`/${role}/api/applications/${applicationId}`);
            if (!response.ok) {
                throw new Error('Не удалось загрузить информацию о заявке');
            }

            const data = await response.json();
            const modalBody = document.getElementById('applicationDetailsModalBody');
            if (!modalBody) {
                throw new Error('Модальное окно не найдено');
            }

            modalBody.innerHTML = this.buildApplicationDetailsHtml(data);
            const modal = new bootstrap.Modal(document.getElementById('applicationDetailsModal'));
            modal.show();
        } catch (error) {
            console.error('Ошибка загрузки заявки:', error);
            this.showError(error.message || 'Ошибка загрузки заявки');
        }
    }

    buildApplicationDetailsHtml(data) {
        const applicant = data.applicant || {};
        return `
            <div class="row">
                <div class="col-md-6">
                    <h6>Объект</h6>
                    <p>${data.object_name || 'Не указан'}</p>
                    ${data.object_address ? `<p class="text-muted">${data.object_address}</p>` : ''}
                    <h6>Статус</h6>
                    <span class="badge bg-${this.getStatusColor(data.status?.toLowerCase())}">${this.getStatusText(data.status?.toLowerCase())}</span>
                    <h6 class="mt-3">Дата подачи</h6>
                    <p>${data.created_at ? new Date(data.created_at).toLocaleString('ru-RU') : 'Неизвестно'}</p>
                </div>
                <div class="col-md-6">
                    <h6>Соискатель</h6>
                    <p>${applicant.full_name || `${applicant.first_name || ''} ${applicant.last_name || ''}`.trim() || 'Без имени'}</p>
                    ${applicant.phone ? `<p><i class="bi bi-telephone"></i> <a href="tel:${applicant.phone}">${applicant.phone}</a></p>` : ''}
                    ${applicant.email ? `<p><i class="bi bi-envelope"></i> <a href="mailto:${applicant.email}">${applicant.email}</a></p>` : ''}
                    ${applicant.preferred_schedule ? `<p><span class="badge bg-secondary">${applicant.preferred_schedule}</span></p>` : ''}
                </div>
            </div>
            ${data.message ? `<div class="mt-3"><h6>Сообщение</h6><div class="border rounded p-3">${data.message}</div></div>` : ''}
            ${applicant.about ? `<div class="mt-3"><h6>О себе</h6><div class="border rounded p-3">${applicant.about}</div></div>` : ''}
            ${applicant.skills ? `<div class="mt-3"><h6>Навыки</h6><div class="border rounded p-3">${applicant.skills}</div></div>` : ''}
            ${applicant.work_experience ? `<div class="mt-3"><h6>Опыт работы</h6><div class="border rounded p-3">${applicant.work_experience}</div></div>` : ''}
            ${applicant.education ? `<div class="mt-3"><h6>Образование</h6><div class="border rounded p-3">${applicant.education}</div></div>` : ''}
        `;
    }

    getStatusColor(status = '') {
        switch (status.toLowerCase()) {
            case 'pending':
                return 'warning';
            case 'approved':
                return 'success';
            case 'rejected':
                return 'danger';
            case 'interview':
                return 'info';
            default:
                return 'secondary';
        }
    }

    getStatusText(status = '') {
        switch (status.toLowerCase()) {
            case 'pending':
                return 'На рассмотрении';
            case 'approved':
                return 'Одобрена';
            case 'rejected':
                return 'Отклонена';
            case 'interview':
                return 'Собеседование';
            default:
                return 'Неизвестно';
        }
    }

    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    showError(message) {
        this.showAlert(message, 'danger');
    }

    showAlert(message, type) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }
}

// Инициализируем при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new ApplicationsManager();
});
