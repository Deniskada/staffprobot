// Shared Calendar JavaScript

class CalendarManager {
    constructor(options = {}) {
        this.currentDate = options.currentDate || new Date();
        this.viewType = options.viewType || 'month';
        this.baseUrl = options.baseUrl || window.location.pathname;
        this.onShiftClick = options.onShiftClick || null;
        this.onTimeslotClick = options.onTimeslotClick || null;
        this.onDateClick = options.onDateClick || null;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        // Delay setupDragDrop to ensure calendar elements are loaded
        setTimeout(() => {
            this.setupDragDrop();
        }, 100);
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
            
            if (e.target.closest('.calendar-day')) {
                e.preventDefault();
                const date = e.target.closest('.calendar-day').dataset.date;
                this.handleDateClick(date);
            }
        });
    }
    
    setupDragDrop() {
        // Setup drag and drop for employee assignment and object creation
        const timeslots = document.querySelectorAll('.timeslot-item');
        console.log('Setting up drag&drop for', timeslots.length, 'timeslots');
        
        // Remove existing event listeners to prevent duplicates
        timeslots.forEach(timeslot => {
            timeslot.removeEventListener('dragover', this.handleDragOver);
            timeslot.removeEventListener('dragleave', this.handleDragLeave);
            timeslot.removeEventListener('drop', this.handleDrop);
        });
        
        // Bind methods to this context
        this.handleDragOver = this.handleDragOver.bind(this);
        this.handleDragLeave = this.handleDragLeave.bind(this);
        this.handleDrop = this.handleDrop.bind(this);
        
        timeslots.forEach(timeslot => {
            timeslot.addEventListener('dragover', this.handleDragOver);
            timeslot.addEventListener('dragleave', this.handleDragLeave);
            timeslot.addEventListener('drop', this.handleDrop);
        });
    }
    
    handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add('drag-over');
    }
    
    handleDragLeave(e) {
        e.currentTarget.classList.remove('drag-over');
    }
    
    handleDrop(e) {
        e.preventDefault();
        const timeslot = e.currentTarget;
        timeslot.classList.remove('drag-over');
        
        const data = e.dataTransfer.getData('text/plain');
        const timeslotId = timeslot.dataset.timeslotId;
        
        console.log('Drop event:', data, 'on timeslot:', timeslotId);
        
        if (data.startsWith('employee:')) {
            const employeeId = data.replace('employee:', '');
            console.log('Assigning employee:', employeeId);
            this.assignEmployeeToTimeslot(employeeId, timeslotId);
        } else if (data.startsWith('object:')) {
            const objectId = data.replace('object:', '');
            console.log('Creating timeslot from object:', objectId);
            this.createTimeslotFromObject(objectId, timeslotId);
        }
    }
    
    navigate(direction) {
        const newDate = new Date(this.currentDate);
        
        if (direction === 'prev') {
            if (this.viewType === 'month') {
                newDate.setMonth(newDate.getMonth() - 1);
            } else {
                newDate.setDate(newDate.getDate() - 7);
            }
        } else {
            if (this.viewType === 'month') {
                newDate.setMonth(newDate.getMonth() + 1);
            } else {
                newDate.setDate(newDate.getDate() + 7);
            }
        }
        
        this.loadCalendar(newDate);
    }
    
    goToToday() {
        this.loadCalendar(new Date());
    }
    
    switchView(viewType) {
        this.viewType = viewType;
        this.loadCalendar(this.currentDate);
    }
    
    loadCalendar(date) {
        const params = new URLSearchParams(window.location.search);
        params.set('year', date.getFullYear());
        params.set('month', date.getMonth() + 1);
        params.set('day', date.getDate());
        params.set('view', this.viewType);
        
        window.location.search = params.toString();
    }
    
    handleShiftClick(shiftId) {
        if (this.onShiftClick) {
            this.onShiftClick(shiftId);
        } else {
            // Default behavior - show shift details
            this.showShiftDetails(shiftId);
        }
    }
    
    handleTimeslotClick(timeslotId) {
        if (this.onTimeslotClick) {
            this.onTimeslotClick(timeslotId);
        } else {
            // Default behavior - show timeslot details
            this.showTimeslotDetails(timeslotId);
        }
    }
    
    handleDateClick(date) {
        if (this.onDateClick) {
            this.onDateClick(date);
        } else {
            // Default behavior - show date details
            this.showDateDetails(date);
        }
    }
    
    showShiftDetails(shiftId) {
        // This should be implemented by the parent template
        console.log('Show shift details:', shiftId);
    }
    
    showTimeslotDetails(timeslotId) {
        // This should be implemented by the parent template
        console.log('Show timeslot details:', timeslotId);
    }
    
    showDateDetails(date) {
        // This should be implemented by the parent template
        console.log('Show date details:', date);
    }
    
    assignEmployeeToTimeslot(employeeId, timeslotId) {
        // This should be implemented by the parent template
        console.log('Assign employee:', employeeId, 'to timeslot:', timeslotId);
    }
    
    createTimeslotFromObject(objectId, timeslotId) {
        // This should be implemented by the parent template
        console.log('Create timeslot from object:', objectId, 'timeslot:', timeslotId);
    }
    
    refresh() {
        window.location.reload();
    }
    
    toggleFilters() {
        const filtersPanel = document.getElementById('calendar-filters');
        if (filtersPanel) {
            filtersPanel.style.display = filtersPanel.style.display === 'none' ? 'block' : 'none';
        }
    }
}

// Utility functions
function formatDate(date) {
    return new Date(date).toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function formatTime(time) {
    return new Date(`2000-01-01T${time}`).toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getDateRange(date, viewType) {
    const start = new Date(date);
    const end = new Date(date);
    
    if (viewType === 'week') {
        const dayOfWeek = start.getDay();
        const monday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
        start.setDate(start.getDate() + monday);
        end.setDate(start.getDate() + 6);
    } else {
        start.setDate(1);
        end.setMonth(end.getMonth() + 1);
        end.setDate(0);
    }
    
    return { start, end };
}

// Export for use in other scripts
window.CalendarManager = CalendarManager;
window.CalendarUtils = {
    formatDate,
    formatTime,
    getDateRange
};
