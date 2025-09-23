// JavaScript для профиля сотрудника

class EmployeeProfileManager {
    constructor() {
        this.isEditing = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Кнопка редактирования профиля
        document.getElementById('edit-profile-btn').addEventListener('click', () => {
            this.toggleEditMode();
        });

        // Кнопка сохранения профиля
        document.getElementById('save-profile-btn').addEventListener('click', () => {
            this.saveProfile();
        });

        // Кнопка отмены редактирования
        document.getElementById('cancel-edit-btn').addEventListener('click', () => {
            this.cancelEdit();
        });

        // Кнопка изменения аватара
        document.getElementById('change-avatar-btn').addEventListener('click', () => {
            this.showAvatarModal();
        });

        // Предпросмотр аватара
        document.getElementById('avatar-input').addEventListener('change', (e) => {
            this.previewAvatar(e.target.files[0]);
        });

        // Сохранение аватара
        document.getElementById('save-avatar').addEventListener('click', () => {
            this.saveAvatar();
        });
    }

    toggleEditMode() {
        this.isEditing = true;
        
        const editBtn = document.getElementById('edit-profile-btn');
        const saveBtn = document.getElementById('save-profile-btn');
        const cancelBtn = document.getElementById('cancel-edit-btn');
        const inputs = document.querySelectorAll('input, select, textarea');
        
        // Скрываем кнопку редактирования, показываем кнопки сохранения и отмены
        editBtn.style.display = 'none';
        saveBtn.style.display = 'inline-block';
        cancelBtn.style.display = 'inline-block';
        
        // Делаем поля редактируемыми
        inputs.forEach(input => {
            if (input.id !== 'avatar-input') {
                input.readOnly = false;
                input.disabled = false;
            }
        });
    }

    cancelEdit() {
        this.isEditing = false;
        
        const editBtn = document.getElementById('edit-profile-btn');
        const saveBtn = document.getElementById('save-profile-btn');
        const cancelBtn = document.getElementById('cancel-edit-btn');
        const inputs = document.querySelectorAll('input, select, textarea');
        
        // Показываем кнопку редактирования, скрываем кнопки сохранения и отмены
        editBtn.style.display = 'inline-block';
        saveBtn.style.display = 'none';
        cancelBtn.style.display = 'none';
        
        // Делаем поля только для чтения
        inputs.forEach(input => {
            if (input.id !== 'avatar-input') {
                input.readOnly = true;
                input.disabled = true;
            }
        });
        
        // Перезагружаем страницу для восстановления исходных значений
        location.reload();
    }

    async saveProfile() {
        const form = document.getElementById('profile-form');
        const formData = new FormData(form);

        try {
            const response = await fetch('/employee/profile', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                this.showNotification('Профиль успешно обновлен!', 'success');
                this.exitEditMode();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Ошибка при сохранении профиля', 'error');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            this.showNotification('Ошибка при сохранении профиля', 'error');
        }
    }

    exitEditMode() {
        this.isEditing = false;
        
        const editBtn = document.getElementById('edit-profile-btn');
        const saveBtn = document.getElementById('save-profile-btn');
        const cancelBtn = document.getElementById('cancel-edit-btn');
        const inputs = document.querySelectorAll('input, select, textarea');
        
        // Показываем кнопку редактирования, скрываем кнопки сохранения и отмены
        editBtn.style.display = 'inline-block';
        saveBtn.style.display = 'none';
        cancelBtn.style.display = 'none';
        
        // Делаем поля только для чтения
        inputs.forEach(input => {
            if (input.id !== 'avatar-input') {
                input.readOnly = true;
                input.disabled = true;
            }
        });
    }

    showAvatarModal() {
        const modal = new bootstrap.Modal(document.getElementById('avatarModal'));
        modal.show();
    }

    previewAvatar(file) {
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const preview = document.getElementById('avatar-preview');
                preview.src = e.target.result;
                preview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    }

    async saveAvatar() {
        const fileInput = document.getElementById('avatar-input');
        const file = fileInput.files[0];
        
        if (!file) {
            this.showNotification('Выберите файл для загрузки', 'error');
            return;
        }

        // Проверяем размер файла (максимум 5MB)
        if (file.size > 5 * 1024 * 1024) {
            this.showNotification('Размер файла не должен превышать 5MB', 'error');
            return;
        }

        // Проверяем тип файла
        if (!file.type.startsWith('image/')) {
            this.showNotification('Выберите изображение', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('avatar', file);

        try {
            const response = await fetch('/employee/api/profile/avatar', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification('Фото профиля успешно обновлено!', 'success');
                
                // Обновляем аватар на странице
                document.getElementById('profile-avatar').src = result.avatar_url;
                
                // Закрываем модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('avatarModal'));
                modal.hide();
                
                // Очищаем форму
                document.getElementById('avatar-form').reset();
                document.getElementById('avatar-preview').style.display = 'none';
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Ошибка при загрузке фото', 'error');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            this.showNotification('Ошибка при загрузке фото', 'error');
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
    new EmployeeProfileManager();
});
