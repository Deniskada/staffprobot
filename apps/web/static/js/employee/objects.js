// JavaScript для страницы поиска работы (объектов) с Яндекс Картами

class EmployeeObjectsManager {
    constructor() {
        this.map = null;
        this.objects = [];
        this.filteredObjects = [];
        this.markers = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initMap();
        this.loadObjects();
    }

    setupEventListeners() {
        // Кнопки подачи заявок
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('apply-btn')) {
                const objectId = e.target.dataset.objectId;
                this.showApplicationModal(objectId);
            }
        });

        // Отправка заявки
        document.getElementById('submit-application').addEventListener('click', () => {
            this.submitApplication();
        });
    }

    async loadObjects() {
        try {
            console.log('Загружаем объекты...');
            const response = await fetch('/employee/api/objects');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.objects = data.objects || [];
            this.filteredObjects = [...this.objects];
            
            console.log('Объекты загружены:', this.objects.length);
            
            // Добавляем объекты на карту если она готова
            if (this.map) {
                this.addObjectsToMap();
            }
            
        } catch (error) {
            console.error('Ошибка загрузки объектов:', error);
            this.showError('Ошибка загрузки объектов. Попробуйте обновить страницу.');
        }
    }

    initMap() {
        // Проверяем, что Яндекс Maps API загружен
        if (typeof ymaps === 'undefined') {
            console.error('Яндекс Maps API не загружен, ждем...');
            // Ждем загрузки API
            setTimeout(() => this.initMap(), 100);
            return;
        }

        // Инициализируем карту
        ymaps.ready(() => {
            this.map = new ymaps.Map('map', {
                center: [47.2000, 39.7000], // Ростов-на-Дону
                zoom: 12,
                controls: ['zoomControl', 'typeSelector', 'fullscreenControl']
            });

            console.log('Яндекс карта инициализирована');
            
            // Если объекты уже загружены, добавляем их на карту
            if (this.objects.length > 0) {
                this.addObjectsToMap();
            }
        });
    }

    addObjectsToMap() {
        if (!this.map) {
            console.log('Карта не инициализирована');
            return;
        }

        console.log('Добавляем объекты на карту. Количество:', this.filteredObjects.length);

        // Очищаем существующие маркеры
        this.map.geoObjects.removeAll();

        this.filteredObjects.forEach(object => {
            if (object.latitude && object.longitude) {
                const marker = new ymaps.Placemark(
                    [object.latitude, object.longitude],
                    {
                        balloonContentHeader: `<strong>${object.name}</strong>`,
                        balloonContentBody: this.createBalloonContent(object),
                        balloonContentFooter: `<button class="btn btn-primary btn-sm apply-btn" data-object-id="${object.id}">Подать заявку</button>`,
                        hintContent: object.name
                    },
                    {
                        preset: 'islands#redDotIcon',
                        iconColor: '#ff0000'
                    }
                );

                this.map.geoObjects.add(marker);
                this.markers.push(marker);
            }
        });

        // Если есть объекты, центрируем карту на них
        if (this.filteredObjects.length > 0) {
            const bounds = this.map.geoObjects.getBounds();
            if (bounds) {
                this.map.setBounds(bounds, { checkZoomRange: true });
            }
        }
    }

    createBalloonContent(object) {
        const tasks = object.shift_tasks ? object.shift_tasks.join(', ') : 'Стандартные задачи';
        return `
            <div class="map-popup">
                <p><strong>Адрес:</strong> ${object.address}</p>
                <p><strong>Время работы:</strong> ${object.opening_time} - ${object.closing_time}</p>
                <p><strong>Ставка:</strong> ${object.hourly_rate} ₽/час</p>
                <p><strong>Условия:</strong> ${object.work_conditions}</p>
                <p><strong>Задачи:</strong> ${tasks}</p>
            </div>
        `;
    }






    showApplicationModal(objectId) {
        const object = this.objects.find(obj => obj.id == objectId);
        if (!object) return;

        document.getElementById('object-id').value = objectId;
        document.getElementById('object-name').value = object.name;
        document.getElementById('work-conditions').value = object.work_conditions;
        
        const tasksList = document.getElementById('shift-tasks-list');
        tasksList.innerHTML = '';
        if (object.shift_tasks) {
            object.shift_tasks.forEach(task => {
                const taskItem = document.createElement('div');
                taskItem.className = 'form-control-plaintext';
                taskItem.textContent = `• ${task}`;
                tasksList.appendChild(taskItem);
            });
        }

        const modal = new bootstrap.Modal(document.getElementById('applicationModal'));
        modal.show();
    }

    async submitApplication() {
        const form = document.getElementById('application-form');
        const formData = new FormData(form);
        
        try {
            const response = await fetch('/employee/api/applications', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Заявка отправлена:', result);
                
                // Закрываем модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('applicationModal'));
                modal.hide();
                
                // Показываем уведомление
                this.showSuccess('Заявка успешно отправлена!');
                
                // Очищаем форму
                form.reset();
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка отправки заявки');
            }
        } catch (error) {
            console.error('Ошибка отправки заявки:', error);
            this.showError('Ошибка отправки заявки: ' + error.message);
        }
    }

    showSuccess(message) {
        // Создаем уведомление об успехе
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show position-fixed';
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }

    showError(message) {
        // Создаем уведомление об ошибке
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);
        
        // Автоматически скрываем через 10 секунд
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 10000);
    }
}

// Инициализируем менеджер объектов при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new EmployeeObjectsManager();
});