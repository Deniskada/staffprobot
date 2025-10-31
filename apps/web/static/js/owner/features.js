/**
 * Управление функциями системы
 */

document.addEventListener('DOMContentLoaded', function() {
    loadFeatures();
});

async function loadFeatures() {
    try {
        const response = await fetch('/owner/profile/features/api/status');
        const data = await response.json();
        
        if (data.success) {
            displayFeatures(data.features);
        }
    } catch (error) {
        console.error('Error loading features:', error);
        document.getElementById('featuresContainer').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Ошибка загрузки функций
            </div>
        `;
    }
}

function displayFeatures(features) {
    const container = document.getElementById('featuresContainer');
    container.innerHTML = '';
    
    // Группируем функции
    const activeFeatures = features.filter(f => f.available && f.enabled);
    const availableFeatures = features.filter(f => f.available && !f.enabled);
    const unavailableFeatures = features.filter(f => !f.available);
    
    // Активные функции
    if (activeFeatures.length > 0) {
        const header = document.createElement('h6');
        header.className = 'small text-success mb-2';
        header.innerHTML = '<i class="bi bi-check-circle me-2"></i>Активные функции';
        container.appendChild(header);
        activeFeatures.forEach(feature => renderFeatureItem(container, feature, true));
    }
    
    // Доступные но выключенные
    if (availableFeatures.length > 0) {
        const header = document.createElement('h6');
        header.className = 'small text-muted mb-2 mt-3';
        header.innerHTML = '<i class="bi bi-toggle-left me-2"></i>Доступные функции';
        container.appendChild(header);
        availableFeatures.forEach(feature => renderFeatureItem(container, feature, true));
    }
    
    // Недоступные в тарифе
    if (unavailableFeatures.length > 0) {
        const header = document.createElement('h6');
        header.className = 'small text-warning mb-2 mt-3';
        header.innerHTML = '<i class="bi bi-lock me-2"></i>Требуют обновления тарифа';
        container.appendChild(header);
        unavailableFeatures.forEach(feature => renderFeatureItem(container, feature, false));
    }
}

function renderFeatureItem(container, feature, available) {
    const item = document.createElement('div');
    item.className = `feature-item mb-3 p-3 border rounded ${!available ? 'bg-light' : ''}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'd-flex justify-content-between align-items-center';
    
    // Левая часть - название и описание
    const infoDiv = document.createElement('div');
    infoDiv.className = 'flex-grow-1';
    infoDiv.innerHTML = `
        <strong>${feature.name}</strong>
        <div class="small text-muted">${feature.description}</div>
    `;
    
    // Правая часть - toggle или lock
    const controlDiv = document.createElement('div');
    
    if (available) {
        const switchDiv = document.createElement('div');
        switchDiv.className = 'form-check form-switch';
        
        const checkbox = document.createElement('input');
        checkbox.className = 'form-check-input feature-toggle';
        checkbox.type = 'checkbox';
        checkbox.id = `feature_${feature.key}`;
        checkbox.checked = feature.enabled;
        checkbox.style.cursor = 'pointer';
        checkbox.onchange = function() {
            toggleFeature(feature.key, this.checked);
        };
        
        switchDiv.appendChild(checkbox);
        controlDiv.appendChild(switchDiv);
    } else {
        controlDiv.innerHTML = `
            <div>
                <i class="bi bi-lock text-warning me-2"></i>
                <a href="/owner/tariff/change" class="btn btn-sm btn-warning">
                    Сменить тариф
                </a>
            </div>
        `;
    }
    
    contentDiv.appendChild(infoDiv);
    contentDiv.appendChild(controlDiv);
    item.appendChild(contentDiv);
    container.appendChild(item);
}

async function toggleFeature(featureKey, enabled) {
    console.log('Toggling feature:', featureKey, 'to', enabled);
    
    try {
        const response = await fetch('/owner/profile/features/api/toggle', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({feature_key: featureKey, enabled: enabled})
        });
        
        const data = await response.json();
        console.log('Toggle response:', data);
        
        if (!data.success) {
            alert('Ошибка: ' + (data.error || 'Функция недоступна'));
            // Откатываем toggle
            const checkbox = document.getElementById(`feature_${featureKey}`);
            if (checkbox) checkbox.checked = !enabled;
            return;
        }
        
        // Показать уведомление
        showNotification(
            enabled ? 'Функция включена' : 'Функция отключена',
            'success'
        );
        
        // Перезагрузка через 1 секунду для обновления меню
        setTimeout(() => {
            location.reload();
        }, 1000);
        
    } catch (error) {
        console.error('Error toggling feature:', error);
        alert('Ошибка при изменении состояния функции');
        // Откатываем toggle
        const checkbox = document.getElementById(`feature_${featureKey}`);
        if (checkbox) checkbox.checked = !enabled;
    }
}

function showNotification(message, type) {
    // Простое уведомление через alert (можно заменить на toast)
    const icon = type === 'success' ? '✓' : '⚠';
    console.log(`${icon} ${message}`);
}

