// Universal Calendar JavaScript for new API

class UniversalCalendarManager {
    constructor(options = {}) {
        this.currentDate = options.currentDate || new Date();
        this.viewType = options.viewType || 'month';
        this.baseUrl = options.baseUrl || window.location.pathname;
        this.userRole = options.userRole || 'employee';
        this.apiEndpoint = options.apiEndpoint || '/api/calendar/data';
        
        // Callbacks
        this.onShiftClick = options.onShiftClick || null;
        this.onTimeslotClick = options.onTimeslotClick || null;
        this.onDateClick = options.onDateClick || null;
        this.onDataLoaded = options.onDataLoaded || null;
        
        // Data cache
        this.calendarData = null;
        this.loading = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadCalendarData();
    }
    
    bindEvents() {
        // Navigation events
        document.addEventListener('click', (e) => {
            if (e.target.matches('[onclick*="navigateCalendar"]')) {
                e.preventDefault();
                const direction = e.target.getAttribute('onclick').includes('prev') ? 'prev' : 'next';
                this.navigate(direction);
            }
            
            if (e.target.matches('[onclick*="goToToday"]')) {
                e.preventDefault();
                this.goToToday();
            }
            
            if (e.target.matches('[onclick*="switchView"]')) {
                e.preventDefault();
                const viewType = e.target.getAttribute('onclick').includes('month') ? 'month' : 'week';
                this.switchView(viewType);
            }
        });
        
        // Shift and timeslot clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.shift-item')) {
                e.preventDefault();
                const shiftId = e.target.closest('.shift-item').dataset.shiftId;
                this.handleShiftClick(shiftId);
            }
            
            if (e.target.closest('.timeslot-item')) {
                e.preventDefault();
                const timeslotId = e.target.closest('.timeslot-item').dataset.timeslotId;
                this.handleTimeslotClick(timeslotId);
            }
        });
        
        // Object filter changes
        const objectFilter = document.getElementById('objectFilter');
        if (objectFilter) {
            objectFilter.addEventListener('change', (e) => {
                this.filterByObject(e.target.value);
            });
        }
    }
    
    async loadCalendarData(startDate = null, endDate = null, objectIds = null) {
        if (this.loading) return;
        
        this.loading = true;
        this.showLoading(true);
        
        try {
            // Calculate date range
            const dateRange = this.calculateDateRange(startDate, endDate);
            
            // Build API URL
            const params = new URLSearchParams({
                start_date: dateRange.start.toISOString().split('T')[0],
                end_date: dateRange.end.toISOString().split('T')[0]
            });
            
            if (objectIds && objectIds.length > 0) {
                params.append('object_ids', objectIds.join(','));
            }
            
            const response = await fetch(`${this.apiEndpoint}?${params}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.calendarData = await response.json();
            
            // Process and display data
            this.processCalendarData();
            this.renderCalendar();
            
            // Call callback if provided
            if (this.onDataLoaded) {
                this.onDataLoaded(this.calendarData);
            }
            
        } catch (error) {
            console.error('Error loading calendar data:', error);
            this.showError('Ошибка загрузки данных календаря');
        } finally {
            this.loading = false;
            this.showLoading(false);
        }
    }
    
    calculateDateRange(startDate = null, endDate = null) {
        const start = startDate || new Date(this.currentDate);
        const end = endDate || new Date(this.currentDate);
        
        if (this.viewType === 'month') {
            // Start from first day of month, end at last day
            start.setDate(1);
            end.setMonth(end.getMonth() + 1, 0);
        } else if (this.viewType === 'week') {
            // Start from Monday of current week
            const dayOfWeek = start.getDay();
            const monday = new Date(start);
            monday.setDate(start.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
            start.setTime(monday.getTime());
            
            // End at Sunday
            end.setTime(start.getTime());
            end.setDate(start.getDate() + 6);
        }
        
        return { start, end };
    }
    
    processCalendarData() {
        if (!this.calendarData) return;
        
        // Group timeslots by date
        this.calendarData.timeslotsByDate = {};
        this.calendarData.timeslots.forEach(timeslot => {
            const date = timeslot.date;
            if (!this.calendarData.timeslotsByDate[date]) {
                this.calendarData.timeslotsByDate[date] = [];
            }
            this.calendarData.timeslotsByDate[date].push(timeslot);
        });
        
        // Group shifts by date
        this.calendarData.shiftsByDate = {};
        this.calendarData.shifts.forEach(shift => {
            const date = shift.planned_start ? 
                shift.planned_start.split('T')[0] : 
                shift.start_time.split('T')[0];
            
            if (!this.calendarData.shiftsByDate[date]) {
                this.calendarData.shiftsByDate[date] = [];
            }
            this.calendarData.shiftsByDate[date].push(shift);
        });
        
        // Group shifts by timeslot
        this.calendarData.shiftsByTimeslot = {};
        this.calendarData.shifts.forEach(shift => {
            if (shift.time_slot_id) {
                if (!this.calendarData.shiftsByTimeslot[shift.time_slot_id]) {
                    this.calendarData.shiftsByTimeslot[shift.time_slot_id] = [];
                }
                this.calendarData.shiftsByTimeslot[shift.time_slot_id].push(shift);
            }
        });
    }
    
    renderCalendar() {
        // This will be implemented by the specific calendar grid component
        if (typeof window.renderCalendarGrid === 'function') {
            window.renderCalendarGrid(this.calendarData);
        }
        
        // Update occupancy indicators
        this.updateOccupancyIndicators();
        
        // Update statistics
        this.updateStatistics();
    }
    
    updateOccupancyIndicators() {
        if (!this.calendarData) return;
        
        // Update timeslot occupancy based on shifts
        Object.keys(this.calendarData.shiftsByTimeslot).forEach(timeslotId => {
            const shifts = this.calendarData.shiftsByTimeslot[timeslotId];
            const activeShifts = shifts.filter(shift => 
                shift.status !== 'cancelled' && shift.shift_type !== 'cancelled'
            );
            
            // Find timeslot element
            const timeslotElement = document.querySelector(`[data-timeslot-id="${timeslotId}"]`);
            if (timeslotElement) {
                const maxEmployees = parseInt(timeslotElement.dataset.maxEmployees) || 1;
                const currentEmployees = activeShifts.length;
                
                // Update occupancy
                if (typeof window.updateTimeslotOccupancy === 'function') {
                    window.updateTimeslotOccupancy(timeslotId, currentEmployees, maxEmployees);
                }
                
                // Hide if fully occupied
                if (currentEmployees >= maxEmployees) {
                    timeslotElement.style.display = 'none';
                } else {
                    timeslotElement.style.display = '';
                }
            }
        });
    }
    
    updateStatistics() {
        if (!this.calendarData) return;
        
        const stats = {
            totalTimeslots: this.calendarData.timeslots.length,
            totalShifts: this.calendarData.shifts.length,
            plannedShifts: this.calendarData.shifts.filter(s => s.shift_type === 'planned').length,
            activeShifts: this.calendarData.shifts.filter(s => s.shift_type === 'active').length,
            completedShifts: this.calendarData.shifts.filter(s => s.shift_type === 'completed').length
        };
        
        // Update statistics display if exists
        const statsElement = document.getElementById('calendar-stats');
        if (statsElement) {
            statsElement.innerHTML = `
                <div class="stat-item">
                    <span class="stat-label">Тайм-слоты:</span>
                    <span class="stat-value">${stats.totalTimeslots}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Запланировано:</span>
                    <span class="stat-value">${stats.plannedShifts}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Активно:</span>
                    <span class="stat-value">${stats.activeShifts}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Завершено:</span>
                    <span class="stat-value">${stats.completedShifts}</span>
                </div>
            `;
        }
    }
    
    navigate(direction) {
        const currentDate = new Date(this.currentDate);
        
        if (this.viewType === 'month') {
            if (direction === 'prev') {
                currentDate.setMonth(currentDate.getMonth() - 1);
            } else {
                currentDate.setMonth(currentDate.getMonth() + 1);
            }
        } else if (this.viewType === 'week') {
            if (direction === 'prev') {
                currentDate.setDate(currentDate.getDate() - 7);
            } else {
                currentDate.setDate(currentDate.getDate() + 7);
            }
        }
        
        this.currentDate = currentDate;
        this.loadCalendarData();
        this.updateNavigationTitle();
    }
    
    goToToday() {
        this.currentDate = new Date();
        this.loadCalendarData();
        this.updateNavigationTitle();
    }
    
    switchView(viewType) {
        this.viewType = viewType;
        this.loadCalendarData();
        this.updateNavigationTitle();
    }
    
    filterByObject(objectId) {
        const objectIds = objectId ? [parseInt(objectId)] : null;
        this.loadCalendarData(null, null, objectIds);
    }
    
    updateNavigationTitle() {
        const titleElement = document.querySelector('.calendar-title');
        if (titleElement) {
            if (this.viewType === 'month') {
                const monthNames = [
                    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
                ];
                const year = this.currentDate.getFullYear();
                const month = monthNames[this.currentDate.getMonth()];
                titleElement.textContent = `${month} ${year}`;
            } else if (this.viewType === 'week') {
                const startOfWeek = new Date(this.currentDate);
                const dayOfWeek = startOfWeek.getDay();
                const monday = new Date(startOfWeek);
                monday.setDate(startOfWeek.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
                
                const endOfWeek = new Date(monday);
                endOfWeek.setDate(monday.getDate() + 6);
                
                const formatDate = (date) => {
                    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
                };
                
                titleElement.textContent = `${formatDate(monday)} - ${formatDate(endOfWeek)}`;
            }
        }
    }
    
    handleShiftClick(shiftId) {
        if (this.onShiftClick) {
            this.onShiftClick(shiftId);
        } else {
            // Default behavior
            console.log('Shift clicked:', shiftId);
        }
    }
    
    handleTimeslotClick(timeslotId) {
        if (this.onTimeslotClick) {
            this.onTimeslotClick(timeslotId);
        } else {
            // Default behavior
            console.log('Timeslot clicked:', timeslotId);
        }
    }
    
    showLoading(show) {
        const loadingElement = document.getElementById('calendar-loading');
        if (loadingElement) {
            loadingElement.style.display = show ? 'block' : 'none';
        }
    }
    
    showError(message) {
        const errorElement = document.getElementById('calendar-error');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        } else {
            console.error('Calendar error:', message);
        }
    }
    
    // Utility methods
    getTimeslotsForDate(date) {
        if (!this.calendarData || !this.calendarData.timeslotsByDate) return [];
        return this.calendarData.timeslotsByDate[date] || [];
    }
    
    getShiftsForDate(date) {
        if (!this.calendarData || !this.calendarData.shiftsByDate) return [];
        return this.calendarData.shiftsByDate[date] || [];
    }
    
    getShiftsForTimeslot(timeslotId) {
        if (!this.calendarData || !this.calendarData.shiftsByTimeslot) return [];
        return this.calendarData.shiftsByTimeslot[timeslotId] || [];
    }
    
    refresh() {
        this.loadCalendarData();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UniversalCalendarManager;
} else {
    window.UniversalCalendarManager = UniversalCalendarManager;
}
