// Shared calendar panels functionality
class CalendarPanels {
    constructor(role) {
        this.role = role;
        this.baseUrl = `/${role}/api`;
        this.objectsData = [];  // Кэш объектов в памяти
        this.employeesData = [];  // Кэш сотрудников в памяти
    }

    // Panel toggle functions
    togglePanel() {
        const panel = document.getElementById('dragDropPanel');
        const icon = document.getElementById('panelToggleIcon');
        
        if (panel.classList.contains('collapsed')) {
            panel.classList.remove('collapsed');
            if (icon) icon.className = 'bi bi-chevron-up';
            this.loadObjects();
        } else {
            panel.classList.add('collapsed');
            if (icon) icon.className = 'bi bi-chevron-down';
        }
    }

    toggleEmployeesPanel() {
        const panel = document.getElementById('employeesDragDropPanel');
        const icon = document.getElementById('employeesPanelToggleIcon');
        
        if (panel.classList.contains('collapsed')) {
            panel.classList.remove('collapsed');
            if (icon) icon.className = 'bi bi-chevron-up';
            this.loadEmployees();
        } else {
            panel.classList.add('collapsed');
            if (icon) icon.className = 'bi bi-chevron-down';
        }
    }

    // Load objects for drag&drop panel
    async loadObjects() {
        const objectsList = document.getElementById('objectsList');
        if (!objectsList) {
            return;
        }
        
        try {
            const endpoint = this.role === 'employee' ? `/${this.role}/calendar/api/objects` : `/${this.role}/calendar/api/objects`;
            console.log('[CalendarPanels] Fetching objects:', endpoint);
            const response = await fetch(endpoint, { credentials: 'same-origin' });
            const objects = await response.json();
            console.log('[CalendarPanels] Objects loaded:', Array.isArray(objects) ? objects.length : 'n/a');
            
            // Сохраняем в память для переиспользования
            this.objectsData = objects;
            
            objectsList.innerHTML = '';
            
            if (objects.length === 0) {
                objectsList.innerHTML = '<div class="text-center text-muted">Нет объектов</div>';
                return;
            }
            
            objects.forEach(object => {
                const objectItem = document.createElement('div');
                objectItem.className = 'object-item';
                // Для менеджера отключаем drag&drop (3.7.3)
                objectItem.draggable = this.role !== 'manager';
                objectItem.dataset.objectId = object.id;
                objectItem.dataset.objectName = object.name;
                objectItem.dataset.hourlyRate = object.hourly_rate || 0;
                objectItem.dataset.openingTime = object.opening_time || '09:00';
                objectItem.dataset.closingTime = object.closing_time || '18:00';
                objectItem.innerHTML = `
                    <div class="object-name">${object.name}</div>
                    <div class="object-address">${object.address || ''}</div>
                `;
                
                objectItem.addEventListener('dragstart', function(e) {
                    e.dataTransfer.setData('text/plain', `object:${object.id}`);
                    this.style.opacity = '0.5';
                    
                    // Create drag preview
                    const dragPreview = document.createElement('div');
                    dragPreview.style.cssText = `
                        position: absolute;
                        top: -1000px;
                        left: -1000px;
                        padding: 10px;
                        background: white;
                        border: 1px solid #ddd;
                        border-radius: 6px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        font-size: 14px;
                        z-index: 9999;
                    `;
                    dragPreview.innerHTML = `
                        <div style="font-weight: 600; color: #2c3e50;">${object.name}</div>
                        <div style="font-size: 12px; color: #6c757d;">${object.hourly_rate || 0}₽/час</div>
                    `;
                    document.body.appendChild(dragPreview);
                    e.dataTransfer.setDragImage(dragPreview, 10, 10);
                    
                    setTimeout(() => {
                        if (dragPreview.parentNode) {
                            dragPreview.remove();
                        }
                    }, 0);
                });
                
                objectItem.addEventListener('dragend', function() {
                    this.style.opacity = '1';
                });
                
                // Click to open quick form prefilled
                objectItem.addEventListener('click', function() {
                    const object = {
                        id: this.dataset.objectId,
                        name: this.dataset.objectName,
                        hourlyRate: this.dataset.hourlyRate,
                        openingTime: this.dataset.openingTime,
                        closingTime: this.dataset.closingTime
                    };
                    this.closest('body');
                }.bind(this));
                
                // Attach quick form via shared panels
                objectItem.addEventListener('click', function() {
                    const object = {
                        id: this.dataset.objectId,
                        name: this.dataset.objectName,
                        hourlyRate: this.dataset.hourlyRate,
                        openingTime: this.dataset.openingTime,
                        closingTime: this.dataset.closingTime
                    };
                    this.showQuickCreateForm(object);
                }.bind(this));
                
                objectsList.appendChild(objectItem);
            });
            
            // Update objects count
            const objectsCount = document.getElementById('objectsCountBadge');
            if (objectsCount) {
                objectsCount.textContent = objects.length;
                document.getElementById('objectsCount').style.display = 'inline-block';
            }
        } catch (error) {
            const objectsList = document.getElementById('objectsList');
            if (objectsList) {
                objectsList.innerHTML = '<div class="text-danger">Ошибка загрузки объектов</div>';
            }
        }
    }

    // Simple proxy methods for buttons
    refreshObjects() {
        return this.loadObjects();
    }

    // Load employees for drag&drop panel
    async loadEmployees() {
        const employeesList = document.getElementById('employeesList');
        if (!employeesList) return;
        
        const roleLabels = {
            owner: 'Владелец',
            manager: 'Управляющий',
            employee: 'Сотрудник',
            applicant: 'Соискатель',
            superadmin: 'Администратор',
        };
        
        try {
            const url = `${this.baseUrl}/employees`;
            console.log('[CalendarPanels] Fetching employees:', url);
            const response = await fetch(url, { credentials: 'same-origin' });
            const employees = await response.json();
            console.log('[CalendarPanels] Employees loaded:', Array.isArray(employees) ? employees.length : 'n/a');
            
            // Сохраняем в память для переиспользования
            this.employeesData = employees;
            
            employeesList.innerHTML = '';
            
            if (employees.length === 0) {
                employeesList.innerHTML = '<div class="text-center text-muted">Нет сотрудников</div>';
                return;
            }
            
            employees.forEach(employee => {
                const employeeItem = document.createElement('div');
                employeeItem.className = `employee-item ${employee.is_owner ? 'owner-item' : ''}`;
                // Для менеджера отключаем drag&drop (3.7.3)
                employeeItem.draggable = this.role !== 'manager';
                employeeItem.dataset.employeeId = employee.id;
                employeeItem.dataset.employeeName = employee.name || employee.username;
                employeeItem.dataset.employeeRole = employee.is_owner ? 'owner' : (employee.role || 'employee');
                employeeItem.dataset.employeeStatus = employee.is_active ? 'Активен' : 'Неактивен';
                
                const primaryRole = employee.is_owner ? 'owner' : (employee.role || 'employee');
                const roleLabel = roleLabels[primaryRole] || 'Сотрудник';
                employeeItem.innerHTML = `
                    <div class="employee-name">
                        ${employee.name || employee.username}
                        ${employee.is_owner ? '<i class="bi bi-crown text-warning ms-1" title="Владелец"></i>' : ''}
                    </div>
                    <div class="employee-role ${employee.is_owner ? 'owner-role' : ''}">
                        ${roleLabel}
                    </div>
                `;
                
                employeeItem.addEventListener('dragstart', function(e) {
                    e.dataTransfer.setData('text/plain', `employee:${employee.id}`);
                    this.style.opacity = '0.5';
                    
                    // Create drag preview
                    const dragPreview = document.createElement('div');
                    dragPreview.style.cssText = `
                        position: absolute;
                        top: -1000px;
                        left: -1000px;
                        padding: 10px;
                        background: white;
                        border: 1px solid #ddd;
                        border-radius: 6px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        font-size: 14px;
                        z-index: 9999;
                    `;
                    dragPreview.innerHTML = `
                        <div style="font-weight: 600; color: #2c3e50;">${employee.name || employee.username}</div>
                        <div style="font-size: 12px; color: #6c757d;">${roleLabel}</div>
                    `;
                    document.body.appendChild(dragPreview);
                    e.dataTransfer.setDragImage(dragPreview, 10, 10);
                    
                    setTimeout(() => {
                        if (dragPreview.parentNode) {
                            dragPreview.remove();
                        }
                    }, 0);
                });
                
                employeeItem.addEventListener('dragend', function() {
                    this.style.opacity = '1';
                });
                
                employeesList.appendChild(employeeItem);
            });
            
            // Update employees count
            const employeesCount = document.getElementById('employeesCountBadge');
            if (employeesCount) {
                employeesCount.textContent = employees.length;
                document.getElementById('employeesCount').style.display = 'block';
            }
            
        } catch (error) {
            console.error('Error loading employees:', error);
            employeesList.innerHTML = '<div class="text-center text-danger">Ошибка загрузки сотрудников</div>';
        }
    }

    refreshEmployees() {
        return this.loadEmployees();
    }

    // Quick create form functions
    async showQuickCreateForm(object = null, date = null) {
        const modal = new bootstrap.Modal(document.getElementById('quickCreateModal'));
        
        // Populate objects list in form
        await this.populateQuickCreateObjects();
        
        // 1) Если объект не передан кликом из панели — возьмем активный фильтр из URL
        if (!object) {
            const urlParams = new URLSearchParams(window.location.search);
            const objectIdFromUrl = urlParams.get('object_id');
            if (objectIdFromUrl) {
                const found = (this.objectsData || []).find(o => String(o.id) === String(objectIdFromUrl));
                if (found) {
                    object = {
                        id: found.id,
                        name: found.name,
                        hourlyRate: found.hourly_rate || 0,
                        openingTime: found.opening_time || '09:00',
                        closingTime: found.closing_time || '18:00'
                    };
                }
            } else if (Array.isArray(this.objectsData) && this.objectsData.length === 1) {
                // Если фильтра нет и у пользователя ровно один объект — выбираем его
                const only = this.objectsData[0];
                object = {
                    id: only.id,
                    name: only.name,
                    hourlyRate: only.hourly_rate || 0,
                    openingTime: only.opening_time || '09:00',
                    closingTime: only.closing_time || '18:00'
                };
            }
        }

        // Применяем выбранный объект в форму (если есть)
        if (object) {
            document.getElementById('quickObject').value = object.id;
            document.getElementById('quickRate').value = object.hourlyRate;
        }
        
        if (date) {
            document.getElementById('quickDate').value = date;
        } else {
            document.getElementById('quickDate').value = new Date().toISOString().split('T')[0];
        }
        
        // 2) Логика подстановки времени: рабочие часы объекта или первая "дыра" между существующими тайм-слотами дня
        try {
            const quickObjectId = document.getElementById('quickObject').value;
            const quickDate = document.getElementById('quickDate').value; // YYYY-MM-DD
            let openingTime = '09:00';
            let closingTime = '18:00';
            if (object) {
                openingTime = object.openingTime || openingTime;
                closingTime = object.closingTime || closingTime;
            } else {
                // если объект выбран из select, можно вытащить часы из кеша
                const found = (this.objectsData || []).find(o => String(o.id) === String(quickObjectId));
                if (found) {
                    openingTime = found.opening_time || openingTime;
                    closingTime = found.closing_time || closingTime;
                }
            }

            // Из данных календаря собираем тайм-слоты на дату по объекту (именно тайм-слоты, НЕ смены)
            const data = (window.universalCalendar && window.universalCalendar.calendarData) || null;
            let slots = [];
            if (data && Array.isArray(data.timeslots)) {
                slots = data.timeslots
                    .filter(ts => ts && ts.date === quickDate && String(ts.object_id) === String(quickObjectId))
                    .map(ts => ({
                        start: ts.start_time, // 'HH:MM'
                        end: ts.end_time
                    }));
            }
            // Fallback: если календарные данные ещё не успели загрузиться — подтянем тайм-слоты напрямую из API
            if ((!slots || slots.length === 0) && quickObjectId && quickDate) {
                try {
                    const params = new URLSearchParams({ start_date: quickDate, end_date: quickDate, object_ids: String(quickObjectId) });
                    // Используем правильный API endpoint для роли (owner или manager)
                    const apiEndpoint = `/${this.role}/calendar/api/data`;
                    const resp = await fetch(`${apiEndpoint}?${params.toString()}`, { credentials: 'same-origin' });
                    if (resp.ok) {
                        const payload = await resp.json();
                        const list = Array.isArray(payload?.timeslots) ? payload.timeslots : [];
                        slots = list
                            .filter(t => t && t.date === quickDate && String(t.object_id) === String(quickObjectId))
                            .map(t => ({ start: t.start_time, end: t.end_time }));
                    }
                } catch (e) { /* ignore */ }
            }

            const toMinutes = (hhmm) => {
                const [h, m] = (hhmm || '00:00').split(':').map(Number);
                return (h * 60) + (m || 0);
            };
            const toHHMM = (mins) => {
                const h = Math.floor(mins / 60);
                const m = mins % 60;
                return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
            };

            // Если слотов нет — подставляем рабочие часы объекта
            if (!slots || slots.length === 0) {
                document.getElementById('quickStartTime').value = openingTime;
                document.getElementById('quickEndTime').value = closingTime;
            } else {
                // Ищем первую пустоту в пределах рабочих часов
                const workStart = toMinutes(openingTime);
                const workEnd = toMinutes(closingTime);
                // сортируем интервалы существующих тайм-слотов
                const intervals = slots
                    .map(s => ({ s: toMinutes(s.start), e: toMinutes(s.end) }))
                    .filter(iv => iv.s < iv.e)
                    .sort((a, b) => a.s - b.s);

                let cursor = workStart;
                let foundGap = null;
                for (const iv of intervals) {
                    if (cursor < iv.s) {
                        foundGap = { s: cursor, e: Math.min(iv.s, workEnd) };
                        break;
                    }
                    cursor = Math.max(cursor, iv.e);
                    if (cursor >= workEnd) break;
                }
                // Если пустота не найдена в середине — возможно есть хвост после последнего слота
                if (!foundGap && cursor < workEnd) {
                    foundGap = { s: cursor, e: workEnd };
                }

                if (foundGap && (foundGap.e - foundGap.s) > 0) {
                    // Заполним всю найденную пустоту целиком (или оставим коротким интервалом — как есть)
                    document.getElementById('quickStartTime').value = toHHMM(foundGap.s);
                    document.getElementById('quickEndTime').value = toHHMM(foundGap.e);
                } else {
                    // Пустот нет — не подставляем, оставим пустыми поля времени
                    document.getElementById('quickStartTime').value = '';
                    document.getElementById('quickEndTime').value = '';
                }
            }
        } catch (e) {
            // Fallback на рабочие часы, если что-то пошло не так
            if (object) {
                document.getElementById('quickStartTime').value = object.openingTime || '';
                document.getElementById('quickEndTime').value = object.closingTime || '';
            }
        }

        modal.show();
    }

    async populateQuickCreateObjects() {
        const quickObjectSelect = document.getElementById('quickObject');
        if (!quickObjectSelect) return;
        
        try {
            const response = await fetch(`/${this.role}/calendar/api/objects`, { credentials: 'same-origin' });
            const objects = await response.json();
            // Обновляем кэш объектов, чтобы можно было найти объект по фильтру URL
            this.objectsData = Array.isArray(objects) ? objects : [];
            
            // Clear and populate list
            quickObjectSelect.innerHTML = '<option value="">Выберите объект</option>';
            
            this.objectsData.forEach(object => {
                const option = document.createElement('option');
                option.value = object.id;
                option.dataset.rate = object.hourly_rate || 0;
                option.textContent = object.name;
                quickObjectSelect.appendChild(option);
            });
            
            // Добавляем обработчик изменения объекта для подстановки ставки (если еще не добавлен)
            if (!quickObjectSelect.hasAttribute('data-handler-added')) {
                quickObjectSelect.setAttribute('data-handler-added', 'true');
                quickObjectSelect.addEventListener('change', function() {
                    const selectedOption = this.options[this.selectedIndex];
                    if (selectedOption && selectedOption.value) {
                        const rate = selectedOption.dataset.rate || '';
                        const rateInput = document.getElementById('quickRate');
                        if (rateInput) {
                            rateInput.value = rate;
                        }
                    }
                });
            }
        } catch (error) {
            console.error('Error loading objects for quick create:', error);
        }
    }

    async createQuickTimeslot() {
        const form = document.getElementById('quickCreateForm');
        const formData = new FormData();
        
        formData.append('object_id', document.getElementById('quickObject').value);
        formData.append('slot_date', document.getElementById('quickDate').value);
        formData.append('start_time', document.getElementById('quickStartTime').value);
        formData.append('end_time', document.getElementById('quickEndTime').value);
        formData.append('hourly_rate', parseInt(document.getElementById('quickRate').value));
        
        try {
            const response = await fetch(`/${this.role}/calendar/api/quick-create-timeslot`, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                this.showNotification('Тайм-слот создан успешно', 'success');
                bootstrap.Modal.getInstance(document.getElementById('quickCreateModal')).hide();
                // Reload calendar
                window.location.reload();
            } else {
                const error = await response.json();
                this.showNotification(`Ошибка: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error creating timeslot:', error);
            this.showNotification('Ошибка создания тайм-слота', 'error');
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }

    // Initialize panels
    init() {
        // Load initial data
        if (this.role !== 'employee') {
            this.loadObjects();
        } else {
            // Скрываем панель объектов для сотрудников
            const objectsPanel = document.getElementById('dragDropPanel');
            if (objectsPanel) {
                objectsPanel.style.display = 'none';
            }
        }
        this.loadEmployees();
        
        // Add click handlers for collapsed panels
        const objectsPanel = document.getElementById('dragDropPanel');
        const employeesPanel = document.getElementById('employeesDragDropPanel');
        
        if (objectsPanel) {
            objectsPanel.addEventListener('click', (e) => {
                // Ignore clicks on the toggle button to avoid re-expanding immediately
                if (e.target.closest('button')) return;
                if (objectsPanel.classList.contains('collapsed')) {
                    this.togglePanel();
                }
            });
        }
        
        if (employeesPanel) {
            // Ensure collapsed by default
            employeesPanel.classList.add('collapsed');
            const icon = document.getElementById('employeesPanelToggleIcon');
            if (icon) icon.className = 'bi bi-chevron-down';
            
            employeesPanel.addEventListener('click', (e) => {
                // Ignore clicks on inner controls to prevent accidental toggles
                if (e.target.closest('button')) return;
                if (employeesPanel.classList.contains('collapsed')) {
                    this.toggleEmployeesPanel();
                }
            });
        }
        
        // Expose toggle for templates if needed
        window.toggleEmployeesPanel = () => this.toggleEmployeesPanel();
        window.toggleObjectsPanel = () => this.togglePanel();
        
        // Auto refresh disabled - was causing excessive API calls
        // setInterval(() => {
        //     if (this.role !== 'employee') {
        //         this.loadObjects();
        //     }
        //     this.loadEmployees();
        // }, 3000);
        
        // Handle object select change (обработчик также добавляется в populateQuickCreateObjects)
        // Проверяем, что обработчик еще не добавлен
        const quickObjectSelect = document.getElementById('quickObject');
        if (quickObjectSelect && !quickObjectSelect.hasAttribute('data-handler-added')) {
            quickObjectSelect.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                if (selectedOption && selectedOption.value) {
                    const rate = selectedOption.dataset.rate || '';
                    const rateInput = document.getElementById('quickRate');
                    if (rateInput) {
                        rateInput.value = rate;
                    }
                }
            });
            quickObjectSelect.setAttribute('data-handler-added', 'true');
        }
        
        // Make methods globally available
        window.togglePanel = () => this.togglePanel();
        window.refreshObjects = () => this.loadObjects();
        window.refreshEmployees = () => this.loadEmployees();
        window.showQuickCreateForm = (object, date) => this.showQuickCreateForm(object, date);
        window.createQuickTimeslot = () => this.createQuickTimeslot();
    }
}

// Export for use in other scripts
window.CalendarPanels = CalendarPanels;
