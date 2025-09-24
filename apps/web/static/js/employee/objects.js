// JavaScript для страницы поиска работы (объектов)

class EmployeeObjectsManager {
    constructor() {
        this.map = null;
        this.objects = [];
        this.filteredObjects = [];
        this.currentView = 'map';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initMap();
        this.loadObjects();
    }

    setupEventListeners() {
        // Переключение между картой и списком
        document.getElementById('view-map').addEventListener('click', () => {
            this.switchView('map');
        });

        document.getElementById('view-list').addEventListener('click', () => {
            this.switchView('list');
        });

        // Применение фильтров
        document.getElementById('apply-filters').addEventListener('click', () => {
            this.applyFilters();
        });

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
            if (response.ok) {
                this.objects = await response.json();
                console.log('Загружено объектов:', this.objects.length);
                console.log('Объекты:', this.objects);
                this.filteredObjects = [...this.objects];
                this.updateObjectsDisplay();
                this.addObjectsToMap();
            } else {
                console.error('Ошибка загрузки объектов:', response.status);
            }
        } catch (error) {
            console.error('Ошибка:', error);
        }
    }

    initMap() {
        // Инициализация карты Leaflet
        this.map = L.map('map').setView([47.2000, 39.7000], 12); // Ростов-на-Дону
        
        // Добавляем слой OpenStreetMap
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);

        console.log('Карта инициализирована');
    }

    addObjectsToMap() {
        if (!this.map) {
            console.log('Карта не инициализирована');
            return;
        }

        console.log('Добавляем объекты на карту. Количество:', this.filteredObjects.length);

        // Очищаем существующие маркеры
        this.map.eachLayer(layer => {
            if (layer instanceof L.Marker) {
                this.map.removeLayer(layer);
            }
        });

        // Добавляем маркеры для каждого объекта
        this.filteredObjects.forEach((object, index) => {
            console.log(`Объект ${index + 1}:`, object.name, 'координаты:', object.latitude, object.longitude);
            
            if (object.latitude && object.longitude && object.latitude !== 0 && object.longitude !== 0) {
                console.log('Добавляем маркер для:', object.name);
                const marker = L.marker([object.latitude, object.longitude])
                    .addTo(this.map)
                    .bindPopup(`
                        <div class="map-popup">
                            <h6>${object.name}</h6>
                            <p><i class="bi bi-geo-alt"></i> ${object.address}</p>
                            <p><i class="bi bi-clock"></i> ${object.opening_time} - ${object.closing_time}</p>
                            <p><i class="bi bi-currency-ruble"></i> ${object.hourly_rate} ₽/час</p>
                            <button class="btn btn-primary btn-sm w-100 apply-btn" data-object-id="${object.id}">
                                <i class="bi bi-file-text"></i> Подать заявку
                            </button>
                        </div>
                    `);
            } else {
                console.log('Пропускаем объект с нулевыми координатами:', object.name);
            }
        });
    }

    switchView(view) {
        this.currentView = view;
        
        // Обновляем кнопки
        document.getElementById('view-map').classList.toggle('active', view === 'map');
        document.getElementById('view-list').classList.toggle('active', view === 'list');
        
        // Показываем/скрываем соответствующие блоки
        document.getElementById('map-view').classList.toggle('d-none', view !== 'map');
        document.getElementById('list-view').classList.toggle('d-none', view !== 'list');
        
        if (view === 'map' && this.map) {
            setTimeout(() => this.map.resize(), 100);
        }
    }

    applyFilters() {
        const filters = {
            workType: document.getElementById('work-type-filter').value,
            schedule: document.getElementById('schedule-filter').value,
            experience: document.getElementById('experience-filter').value,
            salary: document.getElementById('salary-filter').value,
            distance: document.getElementById('distance-filter').value,
            transport: document.getElementById('transport-filter').value,
            flexibility: document.getElementById('flexibility-filter').value
        };

        this.filteredObjects = this.objects.filter(object => {
            // Фильтр по типу работы
            if (filters.workType && !object.shift_tasks.includes(filters.workType)) {
                return false;
            }

            // Фильтр по зарплате
            if (filters.salary && object.hourly_rate < parseInt(filters.salary)) {
                return false;
            }

            // Другие фильтры можно добавить по мере необходимости
            return true;
        });

        this.updateObjectsDisplay();
        this.updateMapMarkers();
    }

    updateObjectsDisplay() {
        const objectsList = document.getElementById('objects-list');
        const objectsCount = document.getElementById('objects-count');
        
        objectsCount.textContent = `${this.filteredObjects.length} объектов`;
        
        // Обновляем список объектов
        objectsList.innerHTML = this.filteredObjects.map(object => `
            <div class="col-md-6 col-lg-4 mb-3 object-item" data-object-id="${object.id}">
                <div class="object-card card h-100">
                    <div class="card-header">
                        <h6 class="mb-0">${object.name}</h6>
                    </div>
                    <div class="card-body">
                        <p class="card-text">
                            <i class="bi bi-geo-alt"></i> ${object.address}
                        </p>
                        <p class="card-text">
                            <i class="bi bi-clock"></i> ${object.opening_time} - ${object.closing_time}
                        </p>
                        <p class="card-text">
                            <i class="bi bi-currency-ruble"></i> ${object.hourly_rate} ₽/час
                        </p>
                        ${object.work_conditions ? `
                            <p class="card-text">
                                <small class="text-muted">${object.work_conditions.substring(0, 100)}${object.work_conditions.length > 100 ? '...' : ''}</small>
                            </p>
                        ` : ''}
                        <div class="mt-3">
                            ${object.shift_tasks.map(category => 
                                `<span class="badge bg-secondary me-1">${category}</span>`
                            ).join('')}
                        </div>
                    </div>
                    <div class="card-footer">
                        <button class="btn btn-primary btn-action w-100 apply-btn" data-object-id="${object.id}">
                            <i class="bi bi-file-text"></i> Подать заявку
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    updateMapMarkers() {
        if (!this.map) return;

        // Добавляем новые маркеры (очистка уже в addObjectsToMap)
        this.addObjectsToMap();
    }

    showApplicationModal(objectId) {
        const object = this.objects.find(obj => obj.id == objectId);
        if (!object) return;

        // Заполняем модальное окно данными объекта
        document.getElementById('object-id').value = object.id;
        document.getElementById('object-name').value = object.name;
        document.getElementById('work-conditions').value = object.work_conditions || '';
        
        // Отображаем задачи на смене
        const tasksList = document.getElementById('shift-tasks-list');
        tasksList.innerHTML = object.shift_tasks.map(task => 
            `<span class="badge bg-primary me-1 mb-1">${task}</span>`
        ).join('');

        // Показываем модальное окно
        const modal = new bootstrap.Modal(document.getElementById('applicationModal'));
        modal.show();
    }

    async submitApplication() {
        const form = document.getElementById('application-form');
        const formData = new FormData(form);
        
        try {
            const response = await fetch('/employee/api/applications', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    object_id: parseInt(formData.get('object_id')),
                    message: formData.get('message'),
                    preferred_schedule: formData.get('preferred_schedule')
                })
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification('Заявка успешно подана!', 'success');
                
                // Закрываем модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('applicationModal'));
                modal.hide();
                
                // Очищаем форму
                form.reset();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Ошибка при подаче заявки', 'error');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            this.showNotification('Ошибка при подаче заявки', 'error');
        }
    }

    showNotification(message, type = 'info') {
        // Создаем уведомление
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
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new EmployeeObjectsManager();
});
