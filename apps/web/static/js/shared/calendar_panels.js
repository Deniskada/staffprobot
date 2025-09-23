// Shared calendar panels functionality
class CalendarPanels {
    constructor(role) {
        this.role = role;
        this.baseUrl = `/${role}/api`;
    }

    // Panel toggle functions
    togglePanel() {
        const panel = document.getElementById('dragDropPanel');
        const icon = document.getElementById('panelToggleIcon');
        
        if (panel.classList.contains('collapsed')) {
            panel.classList.remove('collapsed');
            icon.className = 'bi bi-chevron-up';
            this.loadObjects();
        } else {
            panel.classList.add('collapsed');
            icon.className = 'bi bi-chevron-down';
        }
    }

    toggleEmployeesPanel() {
        const panel = document.getElementById('employeesDragDropPanel');
        const icon = document.getElementById('employeesPanelToggleIcon');
        
        if (panel.classList.contains('collapsed')) {
            panel.classList.remove('collapsed');
            icon.className = 'bi bi-chevron-up';
            this.loadEmployees();
        } else {
            panel.classList.add('collapsed');
            icon.className = 'bi bi-chevron-down';
        }
    }

    // Load objects for drag&drop panel
    async loadObjects() {
        const objectsList = document.getElementById('objectsList');
        if (!objectsList) {
            return;
        }
        
        try {
            const response = await fetch(`/${this.role}/calendar/api/objects`);
            const objects = await response.json();
            
            objectsList.innerHTML = '';
            
            if (objects.length === 0) {
                objectsList.innerHTML = '<div class="text-center text-muted">Нет объектов</div>';
                return;
            }
            
            objects.forEach(object => {
                const objectItem = document.createElement('div');
                objectItem.className = 'object-item';
                objectItem.draggable = true;
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

    // Load employees for drag&drop panel
    async loadEmployees() {
        const employeesList = document.getElementById('employeesList');
        if (!employeesList) return;
        
        try {
            const response = await fetch(`${this.baseUrl}/employees`);
            const employees = await response.json();
            
            employeesList.innerHTML = '';
            
            if (employees.length === 0) {
                employeesList.innerHTML = '<div class="text-center text-muted">Нет сотрудников</div>';
                return;
            }
            
            employees.forEach(employee => {
                const employeeItem = document.createElement('div');
                employeeItem.className = 'employee-item';
                employeeItem.draggable = true;
                employeeItem.dataset.employeeId = employee.id;
                employeeItem.innerHTML = `
                    <div class="employee-name">${employee.name}</div>
                    <div class="employee-role">${employee.role || 'Сотрудник'}</div>
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
                        <div style="font-weight: 600; color: #2c3e50;">${employee.name}</div>
                        <div style="font-size: 12px; color: #6c757d;">${employee.role || 'Сотрудник'}</div>
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

    // Quick create form functions
    async showQuickCreateForm(object = null, date = null) {
        const modal = new bootstrap.Modal(document.getElementById('quickCreateModal'));
        
        // Populate objects list in form
        await this.populateQuickCreateObjects();
        
        if (object) {
            document.getElementById('quickObject').value = object.id;
            document.getElementById('quickRate').value = object.hourlyRate;
            document.getElementById('quickStartTime').value = object.openingTime;
            document.getElementById('quickEndTime').value = object.closingTime;
        }
        
        if (date) {
            document.getElementById('quickDate').value = date;
        } else {
            document.getElementById('quickDate').value = new Date().toISOString().split('T')[0];
        }
        
        modal.show();
    }

    async populateQuickCreateObjects() {
        const quickObjectSelect = document.getElementById('quickObject');
        if (!quickObjectSelect) return;
        
        try {
            const response = await fetch(`/${this.role}/calendar/api/objects`);
            const objects = await response.json();
            
            // Clear and populate list
            quickObjectSelect.innerHTML = '<option value="">Выберите объект</option>';
            
            objects.forEach(object => {
                const option = document.createElement('option');
                option.value = object.id;
                option.dataset.rate = object.hourly_rate || 0;
                option.textContent = object.name;
                quickObjectSelect.appendChild(option);
            });
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
                body: formData
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
        this.loadObjects();
        this.loadEmployees();
        
        // Add click handlers for collapsed panels
        const objectsPanel = document.getElementById('dragDropPanel');
        const employeesPanel = document.getElementById('employeesDragDropPanel');
        
        if (objectsPanel) {
            objectsPanel.addEventListener('click', (e) => {
                if (objectsPanel.classList.contains('collapsed')) {
                    this.togglePanel();
                }
            });
        }
        
        if (employeesPanel) {
            employeesPanel.addEventListener('click', (e) => {
                if (employeesPanel.classList.contains('collapsed')) {
                    this.toggleEmployeesPanel();
                }
            });
        }
        
        // Auto refresh counts occasionally
        setInterval(() => {
            this.refreshObjects();
            this.refreshEmployees();
        }, 3000);
        
        // Handle object select change
        const quickObjectSelect = document.getElementById('quickObject');
        if (quickObjectSelect) {
            quickObjectSelect.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                if (selectedOption.value) {
                    document.getElementById('quickRate').value = selectedOption.dataset.rate || '';
                }
            });
        }
        
        // Make methods globally available
        window.togglePanel = () => this.togglePanel();
        window.toggleEmployeesPanel = () => this.toggleEmployeesPanel();
        window.refreshObjects = () => this.loadObjects();
        window.refreshEmployees = () => this.loadEmployees();
        window.showQuickCreateForm = (object, date) => this.showQuickCreateForm(object, date);
        window.createQuickTimeslot = () => this.createQuickTimeslot();
    }
}

// Export for use in other scripts
window.CalendarPanels = CalendarPanels;
