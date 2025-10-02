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
        
        // Dynamic loading
        this.loadedMonths = new Set(); // Кэш загруженных месяцев
        this.currentVisibleMonth = null; // Текущий видимый месяц
        this.scrollDirection = null; // Направление скролла
        this.isScrolling = false;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadCalendarData();
        this.initScrollTracking();
    }
    
    initScrollTracking() {
        const scrollableContainer = document.querySelector('.calendar-scrollable');
        if (!scrollableContainer) return;
        
        let scrollTimeout;
        
        scrollableContainer.addEventListener('scroll', () => {
            if (!this.isScrolling) {
                this.isScrolling = true;
                requestAnimationFrame(() => {
                    clearTimeout(scrollTimeout);
                    scrollTimeout = setTimeout(() => {
                        this.handleScroll();
                        this.isScrolling = false;
                    }, 100);
                });
            }
        }, { passive: true });
    }
    
    handleScroll() {
        const visibleMonth = this.getVisibleMonthFromScroll();
        if (!visibleMonth) return;
        
        const monthKey = `${visibleMonth.year}-${visibleMonth.month}`;
        
        // Если месяц изменился
        if (this.currentVisibleMonth !== monthKey) {
            this.currentVisibleMonth = monthKey;
            this.checkAndLoadAdjacentMonths(visibleMonth);
        }
    }
    
    getVisibleMonthFromScroll() {
        const scrollableContainer = document.querySelector('.calendar-scrollable');
        if (!scrollableContainer) return null;
        
        const containerRect = scrollableContainer.getBoundingClientRect();
        const containerCenter = containerRect.top + (containerRect.height / 2);
        
        // Находим все дни календаря
        const dayElements = document.querySelectorAll('.calendar-day[data-date]');
        let closestDay = null;
        let minDistance = Infinity;
        
        // Ищем день, ближайший к центру контейнера
        dayElements.forEach(dayElement => {
            const dayRect = dayElement.getBoundingClientRect();
            const dayCenter = dayRect.top + (dayRect.height / 2);
            const distance = Math.abs(dayCenter - containerCenter);
            
            if (distance < minDistance) {
                minDistance = distance;
                closestDay = dayElement;
            }
        });
        
        if (closestDay) {
            const dateStr = closestDay.dataset.date;
            const date = new Date(dateStr);
            return { year: date.getFullYear(), month: date.getMonth() + 1 };
        }
        
        return null;
    }
    
    checkAndLoadAdjacentMonths(visibleMonth) {
        const { year, month } = visibleMonth;
        
        // Определяем предыдущий и следующий месяцы
        const prevMonth = month === 1 ? { year: year - 1, month: 12 } : { year, month: month - 1 };
        const nextMonth = month === 12 ? { year: year + 1, month: 1 } : { year, month: month + 1 };
        
        const prevMonthKey = `${prevMonth.year}-${prevMonth.month}`;
        const nextMonthKey = `${nextMonth.year}-${nextMonth.month}`;
        
        // Проверяем, нужно ли загружать предыдущий месяц
        if (!this.loadedMonths.has(prevMonthKey)) {
            this.loadMonthData(prevMonth);
        }
        
        // Проверяем, нужно ли загружать следующий месяц
        if (!this.loadedMonths.has(nextMonthKey)) {
            this.loadMonthData(nextMonth);
        }
    }
    
    async loadMonthData(monthInfo) {
        const { year, month } = monthInfo;
        const monthKey = `${year}-${month}`;
        
        if (this.loadedMonths.has(monthKey)) return;
        
        try {
            // Определяем диапазон дат для месяца
            const startDate = new Date(year, month - 1, 1);
            const endDate = new Date(year, month, 0); // Последний день месяца
            
            // Получаем object_id из URL
            const urlParams = new URLSearchParams(window.location.search);
            const objectIdFromUrl = urlParams.get('object_id');
            
            const params = new URLSearchParams({
                start_date: startDate.toISOString().split('T')[0],
                end_date: endDate.toISOString().split('T')[0]
            });
            
            if (objectIdFromUrl) {
                params.append('object_ids', objectIdFromUrl);
            }
            
            const response = await fetch(`${this.apiEndpoint}?${params}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const monthData = await response.json();
            
            // Объединяем данные с существующими
            this.mergeMonthData(monthData);
            
            // Помечаем месяц как загруженный
            this.loadedMonths.add(monthKey);
            
            // Обновляем отображение без сброса позиции скролла
            this.renderCalendar(true);
            
        } catch (error) {
            console.error(`Error loading month ${monthKey}:`, error);
        }
    }
    
    mergeMonthData(newData) {
        if (!this.calendarData) {
            this.calendarData = newData;
            return;
        }
        
        // Объединяем тайм-слоты
        const existingTimeslots = new Map();
        this.calendarData.timeslots.forEach(ts => {
            existingTimeslots.set(`${ts.date}-${ts.id}`, ts);
        });
        
        newData.timeslots.forEach(ts => {
            const key = `${ts.date}-${ts.id}`;
            if (!existingTimeslots.has(key)) {
                this.calendarData.timeslots.push(ts);
            }
        });
        
        // Объединяем смены
        const existingShifts = new Map();
        this.calendarData.shifts.forEach(shift => {
            existingShifts.set(shift.id, shift);
        });
        
        newData.shifts.forEach(shift => {
            if (!existingShifts.has(shift.id)) {
                this.calendarData.shifts.push(shift);
            }
        });
        
        // Обновляем диапазон дат
        const newStartDate = new Date(newData.date_range.start);
        const newEndDate = new Date(newData.date_range.end);
        const currentStartDate = new Date(this.calendarData.date_range.start);
        const currentEndDate = new Date(this.calendarData.date_range.end);
        
        this.calendarData.date_range.start = newStartDate < currentStartDate ? 
            newData.date_range.start : this.calendarData.date_range.start;
        this.calendarData.date_range.end = newEndDate > currentEndDate ? 
            newData.date_range.end : this.calendarData.date_range.end;
    }
    
    initializeLoadedMonthsCache() {
        if (!this.calendarData) return;
        
        const startDate = new Date(this.calendarData.date_range.start);
        const endDate = new Date(this.calendarData.date_range.end);
        
        // Помечаем все месяцы в диапазоне как загруженные
        const currentDate = new Date(startDate);
        while (currentDate <= endDate) {
            const monthKey = `${currentDate.getFullYear()}-${currentDate.getMonth() + 1}`;
            this.loadedMonths.add(monthKey);
            currentDate.setMonth(currentDate.getMonth() + 1);
        }
        
        // Устанавливаем текущий видимый месяц
        const today = new Date();
        this.currentVisibleMonth = `${today.getFullYear()}-${today.getMonth() + 1}`;
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
            
            // Получаем object_id из URL параметров
            const urlParams = new URLSearchParams(window.location.search);
            const objectIdFromUrl = urlParams.get('object_id');
            
            if (objectIds && objectIds.length > 0) {
                params.append('object_ids', objectIds.join(','));
            } else if (objectIdFromUrl) {
                params.append('object_ids', objectIdFromUrl);
            }
            
            const response = await fetch(`${this.apiEndpoint}?${params}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.calendarData = await response.json();
            
            // Инициализируем кэш загруженных месяцев
            this.initializeLoadedMonthsCache();
            
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
            // Для много-месячного календаря загружаем данные за 3 месяца
            // Предыдущий месяц
            start.setMonth(start.getMonth() - 1);
            start.setDate(1);
            
            // Следующий месяц
            end.setMonth(end.getMonth() + 1);
            end.setDate(0); // Последний день следующего месяца
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
    
    renderCalendar(preserveScrollPosition = false) {
        // Сохраняем позицию скролла если нужно
        let scrollPosition = null;
        if (preserveScrollPosition) {
            const scrollableContainer = document.querySelector('.calendar-scrollable');
            if (scrollableContainer) {
                scrollPosition = scrollableContainer.scrollTop;
            }
        }
        
        // This will be implemented by the specific calendar grid component
        if (typeof window.renderCalendarGrid === 'function') {
            window.renderCalendarGrid(this.calendarData);
        }
        
        // Update occupancy indicators
        this.updateOccupancyIndicators();
        
        // Update statistics
        this.updateStatistics();
        
        // Восстанавливаем позицию скролла если нужно
        if (preserveScrollPosition && scrollPosition !== null) {
            const scrollableContainer = document.querySelector('.calendar-scrollable');
            if (scrollableContainer) {
                scrollableContainer.scrollTop = scrollPosition;
            }
        }
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
        
        // Скролл к текущему дню после загрузки данных
        setTimeout(() => {
            this.scrollToToday();
        }, 100);
    }
    
    selectMonth(year, month) {
        // Определяем, нужно ли загружать новые данные
        const targetMonthKey = `${year}-${month}`;
        
        // Если выбранный месяц не загружен, загружаем диапазон
        if (!this.loadedMonths.has(targetMonthKey)) {
            this.loadMonthRange(year, month);
        } else {
            // Если месяц уже загружен, просто позиционируемся на него
            this.scrollToMonth(year, month);
        }
    }
    
    async loadMonthRange(year, month) {
        // Определяем, насколько далеко выбранный месяц от текущего
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear();
        const currentMonth = currentDate.getMonth() + 1;
        
        const selectedDate = new Date(year, month - 1, 1);
        const currentDateObj = new Date(currentYear, currentMonth - 1, 1);
        
        const monthsDiff = (year - currentYear) * 12 + (month - currentMonth);
        
        // Если выбранный месяц далеко от текущего, загружаем больше данных
        let rangeMonths = 3; // По умолчанию 3 месяца
        if (Math.abs(monthsDiff) > 6) {
            rangeMonths = 7; // Если далеко, загружаем 7 месяцев
        }
        
        const halfRange = Math.floor(rangeMonths / 2);
        
        // Загружаем диапазон месяцев вокруг выбранного месяца
        const prevMonth = month - halfRange <= 0 ? 
            { year: year - 1, month: 12 + (month - halfRange) } : 
            { year, month: month - halfRange };
        const nextMonth = month + halfRange > 12 ? 
            { year: year + 1, month: (month + halfRange) - 12 } : 
            { year, month: month + halfRange };
        
        const startDate = new Date(prevMonth.year, prevMonth.month - 1, 1);
        const endDate = new Date(nextMonth.year, nextMonth.month, 0);
        
        // Получаем object_id из URL
        const urlParams = new URLSearchParams(window.location.search);
        const objectIdFromUrl = urlParams.get('object_id');
        
        const params = new URLSearchParams({
            start_date: startDate.toISOString().split('T')[0],
            end_date: endDate.toISOString().split('T')[0]
        });
        
        if (objectIdFromUrl) {
            params.append('object_ids', objectIdFromUrl);
        }
        
        try {
            const response = await fetch(`${this.apiEndpoint}?${params}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const newData = await response.json();
            
            // Объединяем данные
            this.mergeMonthData(newData);
            
            // Обновляем кэш
            this.initializeLoadedMonthsCache();
            
            // Обновляем отображение
            this.renderCalendar();
            
            // Позиционируемся на выбранный месяц
            setTimeout(() => {
                this.scrollToMonth(year, month);
            }, 200); // Увеличиваем задержку для больших диапазонов
            
        } catch (error) {
            console.error(`Error loading month range for ${year}-${month}:`, error);
        }
    }
    
    scrollToMonth(year, month) {
        const scrollableContainer = document.querySelector('.calendar-scrollable');
        if (!scrollableContainer) return;
        
        // Находим первый день выбранного месяца
        const monthFirstDay = new Date(year, month - 1, 1);
        const monthFirstDayStr = monthFirstDay.toISOString().split('T')[0];
        
        // Находим элемент с первым днем месяца
        let monthElement = document.querySelector(`.calendar-day[data-date="${monthFirstDayStr}"]`);
        
        // Если не нашли первый день, ищем любой день этого месяца
        if (!monthElement) {
            const monthElements = document.querySelectorAll('.calendar-day[data-date]');
            for (let element of monthElements) {
                const elementDate = new Date(element.dataset.date);
                if (elementDate.getFullYear() === year && elementDate.getMonth() === month - 1) {
                    monthElement = element;
                    break;
                }
            }
        }
        
        if (!monthElement) {
            console.warn(`Could not find element for month ${year}-${month}`);
            return;
        }
        
        // Получаем позицию элемента относительно контейнера
        const containerRect = scrollableContainer.getBoundingClientRect();
        const elementRect = monthElement.getBoundingClientRect();
        
        // Вычисляем позицию для прокрутки (показываем элемент в верхней части)
        const elementTop = elementRect.top - containerRect.top + scrollableContainer.scrollTop;
        
        // Плавная прокрутка к началу выбранного месяца
        scrollableContainer.scrollTo({
            top: Math.max(0, elementTop - 20),
            behavior: 'smooth'
        });
    }
    
    scrollToToday() {
        const today = new Date();
        const todayString = today.toISOString().split('T')[0]; // YYYY-MM-DD format
        
        // Ищем элемент с текущей датой
        const todayElement = document.querySelector(`[data-date="${todayString}"]`);
        if (todayElement) {
            // Плавный скролл к элементу
            todayElement.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
                inline: 'center'
            });
            
            // Добавляем подсветку на 2 секунды
            todayElement.classList.add('today-highlight');
            setTimeout(() => {
                todayElement.classList.remove('today-highlight');
            }, 2000);
        }
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
