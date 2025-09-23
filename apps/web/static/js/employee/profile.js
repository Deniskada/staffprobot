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

        // Сохранение профиля
        document.addEventListener('click', (e) => {
            if (e.target.id === 'save-profile-btn') {
                this.saveProfile();
            }
        });
    }

    toggleEditMode() {
        this.isEditing = !this.isEditing;
        
        const editBtn = document.getElementById('edit-profile-btn');
        const inputs = document.querySelectorAll('input, select, textarea');
        
        if (this.isEditing) {
            // Включаем режим редактирования
            editBtn.innerHTML = '<i class="bi bi-check"></i> Сохранить';
            editBtn.className = 'btn btn-success';
            
            // Делаем поля редактируемыми
            inputs.forEach(input => {
                if (input.id !== 'avatar-input') {
                    input.readOnly = false;
                    input.disabled = false;
                }
            });
            
            // Добавляем кнопку отмены
            if (!document.getElementById('cancel-profile-btn')) {
                const cancelBtn = document.createElement('button');
                cancelBtn.type = 'button';
                cancelBtn.className = 'btn btn-outline-secondary ms-2';
                cancelBtn.id = 'cancel-profile-btn';
                cancelBtn.innerHTML = '<i class="bi bi-x"></i> Отмена';
                cancelBtn.addEventListener('click', () => {
                    this.cancelEdit();
                });
                editBtn.parentNode.appendChild(cancelBtn);
            }
        } else {
            // Сохраняем изменения
            this.saveProfile();
        }
    }

    cancelEdit() {
        this.isEditing = false;
        
        const editBtn = document.getElementById('edit-profile-btn');
        const cancelBtn = document.getElementById('cancel-profile-btn');
        const inputs = document.querySelectorAll('input, select, textarea');
        
        // Возвращаем кнопку в исходное состояние
        editBtn.innerHTML = '<i class="bi bi-pencil"></i> Редактировать';
        editBtn.className = 'btn btn-primary';
        
        // Убираем кнопку отмены
        if (cancelBtn) {
            cancelBtn.remove();
        }
        
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
        const formData = {
            first_name: document.getElementById('first-name').value,
            last_name: document.getElementById('last-name').value,
            phone: document.getElementById('phone').value,
            email: document.getElementById('email').value,
            birth_date: document.getElementById('birth-date').value,
            experience: document.getElementById('experience').value,
            education: document.getElementById('education').value,
            skills: document.getElementById('skills').value,
            about: document.getElementById('about').value,
            preferred_schedule: document.getElementById('preferred-schedule').value,
            min_salary: document.getElementById('min-salary').value,
            preferred_work_types: Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
                .map(checkbox => checkbox.value)
        };

        try {
            const response = await fetch('/employee/api/profile', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
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
        const cancelBtn = document.getElementById('cancel-profile-btn');
        const inputs = document.querySelectorAll('input, select, textarea');
        
        // Возвращаем кнопку в исходное состояние
        editBtn.innerHTML = '<i class="bi bi-pencil"></i> Редактировать';
        editBtn.className = 'btn btn-primary';
        
        // Убираем кнопку отмены
        if (cancelBtn) {
            cancelBtn.remove();
        }
        
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
