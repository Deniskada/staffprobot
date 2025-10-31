// Управление типами уведомлений (Админ-панель)

let editModal;

document.addEventListener('DOMContentLoaded', function() {
    editModal = new bootstrap.Modal(document.getElementById('editModal'));
    
    // Обработчик формы редактирования
    document.getElementById('editForm').addEventListener('submit', function(e) {
        e.preventDefault();
        saveType();
    });
});

/**
 * Открыть модальное окно редактирования типа
 */
async function editType(typeCode) {
    try {
        const response = await fetch(`/admin/notifications/api/types/${typeCode}`);
        if (!response.ok) throw new Error('Ошибка загрузки типа');
        
        const data = await response.json();
        
        // Заполнить форму
        document.getElementById('edit_type_code').value = data.type_code;
        document.getElementById('edit_title').value = data.title;
        document.getElementById('edit_description').value = data.description || '';
        document.getElementById('edit_priority').value = data.default_priority;
        document.getElementById('edit_sort_order').value = data.sort_order;
        
        // Установить каналы
        document.getElementById('channel_telegram').checked = data.available_channels.includes('telegram');
        document.getElementById('channel_inapp').checked = data.available_channels.includes('inapp');
        document.getElementById('channel_email').checked = data.available_channels.includes('email');
        
        editModal.show();
    } catch (error) {
        console.error('Error:', error);
        showAlert('Ошибка загрузки типа: ' + error.message, 'danger');
    }
}

/**
 * Сохранить изменения типа
 */
async function saveType() {
    const typeCode = document.getElementById('edit_type_code').value;
    const formData = {
        title: document.getElementById('edit_title').value,
        description: document.getElementById('edit_description').value,
        default_priority: document.getElementById('edit_priority').value,
        sort_order: parseInt(document.getElementById('edit_sort_order').value),
        available_channels: []
    };
    
    // Собрать выбранные каналы
    if (document.getElementById('channel_telegram').checked) formData.available_channels.push('telegram');
    if (document.getElementById('channel_inapp').checked) formData.available_channels.push('inapp');
    if (document.getElementById('channel_email').checked) formData.available_channels.push('email');
    
    try {
        const response = await fetch(`/admin/notifications/api/types/${typeCode}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) throw new Error('Ошибка сохранения');
        
        showAlert('Тип успешно обновлён', 'success');
        editModal.hide();
        
        // Перезагрузить страницу через 1 секунду
        setTimeout(() => window.location.reload(), 1000);
    } catch (error) {
        console.error('Error:', error);
        showAlert('Ошибка сохранения: ' + error.message, 'danger');
    }
}

/**
 * Переключить доступность типа для пользователей
 */
async function toggleUserAccess(typeCode, enable) {
    const action = enable ? 'показать пользователям' : 'скрыть от пользователей';
    
    if (!confirm(`Вы уверены, что хотите ${action} этот тип уведомления?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/notifications/api/types/${typeCode}/toggle-user-access`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ enable })
        });
        
        if (!response.ok) throw new Error('Ошибка изменения доступа');
        
        showAlert(`Тип ${enable ? 'добавлен в' : 'удалён из'} настройки пользователей`, 'success');
        
        // Перезагрузить страницу через 1 секунду
        setTimeout(() => window.location.reload(), 1000);
    } catch (error) {
        console.error('Error:', error);
        showAlert('Ошибка: ' + error.message, 'danger');
    }
}

/**
 * Переключить активность типа
 */
async function toggleActive(typeCode, activate) {
    const action = activate ? 'активировать' : 'деактивировать';
    
    if (!confirm(`Вы уверены, что хотите ${action} этот тип уведомления?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/notifications/api/types/${typeCode}/toggle-active`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ activate })
        });
        
        if (!response.ok) throw new Error('Ошибка изменения статуса');
        
        showAlert(`Тип ${activate ? 'активирован' : 'деактивирован'}`, 'success');
        
        // Перезагрузить страницу через 1 секунду
        setTimeout(() => window.location.reload(), 1000);
    } catch (error) {
        console.error('Error:', error);
        showAlert('Ошибка: ' + error.message, 'danger');
    }
}

/**
 * Показать уведомление
 */
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Автоматически скрыть через 5 секунд
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

