// Universal Calendar JavaScript for new API - FIXED VERSION

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
        this.isLoadingMonth = false; // Флаг загрузки месяца
        this.isUserNavigating = false; // Флаг пользовательской навигации
        
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
            if (!this.isScrolling && !this.isUserNavigating) {
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
        // Защита от рекурсивных вызовов
        if (this.isLoadingMonth || this.isUserNavigating) return;
        
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
        // Поскольку мы загружаем диапазон 13 месяцев, динамическая загрузка не нужна
        // Просто обновляем текущий видимый месяц
        const { year, month } = visibleMonth;
        const monthKey = `${year}-${month}`;
        
        // Проверяем, что месяц входит в загруженный диапазон
        const currentDate = new Date();
        const currentMonth = currentDate.getMonth() + 1;
        const currentYear = currentDate.getFullYear();
        
        // Проверяем, находится ли видимый месяц в диапазоне ±6 месяцев
        const monthsDiff = (year - currentYear) * 12 + (month - currentMonth);
        if (Math.abs(monthsDiff) <= 6) {
            this.currentVisibleMonth = monthKey;
        }
    }
    
    async loadMonthData(monthInfo) {
        const { year, month } = monthInfo;
        const monthKey = `${year}-${month}`;
        
        if (this.loadedMonths.has(monthKey) || this.isLoadingMonth) return;
        
        this.isLoadingMonth = true;
        
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
        } finally {
            this.isLoadingMonth = false;
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
        
        // Помечаем все месяцы в диапазоне 13 месяцев как загруженные
        const currentDate = new Date();
        const currentMonth = currentDate.getMonth() + 1; // 1-based
        const currentYear = currentDate.getFullYear();
        
        for (let i = -6; i <= 6; i++) {
            const targetMonth = currentMonth + i;
            let targetYear = currentYear;
            let monthNumber = targetMonth;
            
            // Корректируем год и месяц
            if (targetMonth <= 0) {
                monthNumber = 12 + targetMonth;
                targetYear = currentYear - 1;
            } else if (targetMonth > 12) {
                monthNumber = targetMonth - 12;
                targetYear = currentYear + 1;
            }
            
            const monthKey = `${targetYear}-${monthNumber}`;
            this.loadedMonths.add(monthKey);
        }
        
        // Устанавливаем текущий видимый месяц
        this.currentVisibleMonth = `${currentYear}-${currentMonth}`;
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
                const shiftElement = e.target.closest('.shift-item');
                const shiftId = shiftElement.dataset.shiftId;
                if (shiftId && this.onShiftClick) {
                    this.onShiftClick(shiftId);
                }
            }
            
            if (e.target.closest('.timeslot-item')) {
                const timeslotElement = e.target.closest('.timeslot-item');
                const timeslotId = timeslotElement.dataset.timeslotId;
                if (timeslotId && this.onTimeslotClick) {
                    this.onTimeslotClick(timeslotId);
                }
            }
        });
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
            this.showNotification('Ошибка загрузки данных календаря', 'error');
        } finally {
            this.loading = false;
            this.showLoading(false);
        }
    }
    
    calculateDateRange(startDate = null, endDate = null) {
        const start = startDate || new Date(this.currentDate);
        const end = endDate || new Date(this.currentDate);
        
        if (this.viewType === 'month') {
            // Загружаем 13 месяцев: 6 до текущего + текущий + 6 после
            const currentDate = new Date(start);
            const currentMonth = currentDate.getMonth();
            const currentYear = currentDate.getFullYear();
            
            // 6 месяцев назад
            start.setMonth(currentMonth - 6);
            start.setDate(1);
            
            // 6 месяцев вперед
            end.setMonth(currentMonth + 6);
            end.setDate(0); // Последний день 6-го месяца вперед
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
        
        // Group data by date for easier rendering
        this.calendarData.timeslotsByDate = {};
        this.calendarData.shiftsByDate = {};
        this.calendarData.shiftsByTimeslot = {};
        
        // Process timeslots
        this.calendarData.timeslots.forEach(timeslot => {
            const date = timeslot.date;
            if (!this.calendarData.timeslotsByDate[date]) {
                this.calendarData.timeslotsByDate[date] = [];
            }
            this.calendarData.timeslotsByDate[date].push(timeslot);
        });
        
        // Process shifts
        this.calendarData.shifts.forEach(shift => {
            const date = shift.start_time ? shift.start_time.split('T')[0] : null;
            if (date) {
                if (!this.calendarData.shiftsByDate[date]) {
                    this.calendarData.shiftsByDate[date] = [];
                }
                this.calendarData.shiftsByDate[date].push(shift);
            }
            
            // Group by timeslot
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
        this.calendarData.timeslots.forEach(timeslot => {
            const shifts = this.calendarData.shiftsByTimeslot[timeslot.id] || [];
            timeslot.current_employees = shifts.length;
            timeslot.available_slots = Math.max(0, timeslot.max_employees - shifts.length);
        });
    }
    
    updateStatistics() {
        if (!this.calendarData) return;
        
        // Calculate statistics
        const stats = {
            total_timeslots: this.calendarData.timeslots.length,
            total_shifts: this.calendarData.shifts.length,
            planned: this.calendarData.shifts.filter(s => s.status === 'planned').length,
            active: this.calendarData.shifts.filter(s => s.status === 'active').length,
            completed: this.calendarData.shifts.filter(s => s.status === 'completed').length,
            cancelled: this.calendarData.shifts.filter(s => s.status === 'cancelled').length
        };
        
        // Update UI if statistics element exists
        const statsElement = document.getElementById('calendar-stats');
        if (statsElement) {
            statsElement.innerHTML = `
                <div class="row text-center">
                    <div class="col-3">
                        <small class="text-muted">Тайм-слоты</small><br>
                        <strong>${stats.total_timeslots}</strong>
                    </div>
                    <div class="col-3">
                        <small class="text-muted">Запланировано</small><br>
                        <strong>${stats.planned}</strong>
                    </div>
                    <div class="col-3">
                        <small class="text-muted">Активные</small><br>
                        <strong>${stats.active}</strong>
                    </div>
                    <div class="col-3">
                        <small class="text-muted">Завершено</small><br>
                        <strong>${stats.completed}</strong>
                    </div>
                </div>
            `;
        }
    }
    
    navigate(direction) {
        const currentDate = new Date(this.currentDate);
        
        if (direction === 'prev') {
            if (this.viewType === 'month') {
                currentDate.setMonth(currentDate.getMonth() - 1);
            } else {
                currentDate.setDate(currentDate.getDate() - 7);
            }
        } else {
            if (this.viewType === 'month') {
                currentDate.setMonth(currentDate.getMonth() + 1);
            } else {
                currentDate.setDate(currentDate.getDate() + 7);
            }
        }
        
        this.currentDate = currentDate;
        this.loadCalendarData();
        this.updateNavigationTitle();
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
        }
    }
    
    handleTimeslotClick(timeslotId) {
        if (this.onTimeslotClick) {
            this.onTimeslotClick(timeslotId);
        }
    }
    
    updateNavigationTitle() {
        const titleElement = document.getElementById('calendar-title');
        if (titleElement) {
            const monthNames = [
                'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
            ];
            
            const monthName = monthNames[this.currentDate.getMonth()];
            const year = this.currentDate.getFullYear();
            titleElement.textContent = `${monthName} ${year}`;
        }
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
        // Устанавливаем флаг пользовательской навигации
        this.isUserNavigating = true;
        
        // Определяем, нужно ли загружать новые данные
        const targetMonthKey = `${year}-${month}`;
        
        // Если выбранный месяц не загружен, загружаем диапазон
        if (!this.loadedMonths.has(targetMonthKey)) {
            this.loadMonthRange(year, month);
        } else {
            // Если месяц уже загружен, просто позиционируемся на него
            this.scrollToMonth(year, month);
            // Сбрасываем флаг после позиционирования
            setTimeout(() => {
                this.isUserNavigating = false;
            }, 500);
        }
    }
    
    async loadMonthRange(year, month) {
        // Определяем, насколько далеко выбранный месяц от текущего
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear();
        const currentMonth = currentDate.getMonth() + 1;
        
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
                // Сбрасываем флаг после позиционирования
                setTimeout(() => {
                    this.isUserNavigating = false;
                }, 500);
            }, 200); // Увеличиваем задержку для больших диапазонов
            
        } catch (error) {
            console.error(`Error loading month range for ${year}-${month}:`, error);
            this.isUserNavigating = false;
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
        
        const todayElement = document.querySelector(`.calendar-day[data-date="${todayString}"]`);
        if (!todayElement) return;
        
        const scrollableContainer = document.querySelector('.calendar-scrollable');
        if (!scrollableContainer) return;
        
        const containerRect = scrollableContainer.getBoundingClientRect();
        const elementRect = todayElement.getBoundingClientRect();
        
        const elementTop = elementRect.top - containerRect.top + scrollableContainer.scrollTop;
        const containerHeight = scrollableContainer.clientHeight;
        const elementHeight = elementRect.height;
        
        const scrollTo = elementTop - (containerHeight / 2) + (elementHeight / 2);
        
        scrollableContainer.scrollTo({
            top: Math.max(0, scrollTo),
            behavior: 'smooth'
        });
    }
    
    showLoading(show) {
        const loadingElement = document.getElementById('calendar-loading');
        if (loadingElement) {
            loadingElement.style.display = show ? 'block' : 'none';
        }
    }
    
    showNotification(message, type = 'info') {
        // Simple notification implementation
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UniversalCalendarManager;
}
