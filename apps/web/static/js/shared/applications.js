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
