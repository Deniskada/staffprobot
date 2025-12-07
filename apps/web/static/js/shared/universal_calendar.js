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
        this.onShiftDelete = options.onShiftDelete || null;
        
        // Data cache
        this.calendarData = null;
        this.loading = false;

        this.selectedShiftId = null;
        this.selectedShiftScheduleId = null;
        this.selectedShiftType = null;
        this.selectedShiftElement = null;
        
        // Dynamic loading
        this.loadedMonths = new Set(); // Кэш загруженных месяцев
        this.currentVisibleMonth = null; // Текущий видимый месяц
        this.scrollDirection = null; // Направление скролла
        this.isScrolling = false;
        this.isLoadingMonth = false; // Флаг загрузки месяца
        this.isUserNavigating = false; // Флаг пользовательской навигации
        this.initialAutoScrollInProgress = false; // Флаг автоскролла при инициализации
        
        // Mobile support
        this.isMobile = this.isMobileDevice();
        this.viewMode = this.initViewMode(); // 'day' | 'month'
        
        this.init();
    }
    
    /**
     * Определяет, является ли устройство мобильным
     * @returns {boolean}
     */
    isMobileDevice() {
        // Проверка через media query
        if (window.matchMedia) {
            return window.matchMedia('(max-width: 768px)').matches;
        }
        // Fallback для старых браузеров
        return window.innerWidth <= 768;
    }
    
    /**
     * Инициализирует режим просмотра (day/month) с сохранением в localStorage
     * @returns {string} 'day' | 'month'
     */
    initViewMode() {
        const storageKey = 'calendar_view_mode';
        
        // Если мобильное устройство
        if (this.isMobile) {
            // Проверяем сохранённое значение
            const saved = localStorage.getItem(storageKey);
            if (saved === 'day' || saved === 'month') {
                return saved;
            }
            // По умолчанию для мобильных - дневной вид
            localStorage.setItem(storageKey, 'day');
            return 'day';
        }
        
        // Для десктопов - месячный вид (текущее поведение)
        const saved = localStorage.getItem(storageKey);
        if (saved === 'day' || saved === 'month') {
            return saved;
        }
        localStorage.setItem(storageKey, 'month');
        return 'month';
    }
    
    /**
     * Переключает режим просмотра
     * @param {string} mode - 'day' | 'month'
     */
    setViewMode(mode) {
        if (mode !== 'day' && mode !== 'month') {
            console.warn(`Invalid view mode: ${mode}. Expected 'day' or 'month'.`);
            return;
        }
        
        this.viewMode = mode;
        localStorage.setItem('calendar_view_mode', mode);
        
        // Перерисовываем календарь
        if (mode === 'day') {
            this.renderDayView(this.currentDate);
        } else {
            this.loadCalendarData();
        }
    }
    
    init() {
        this.bindEvents();
        
        // Инициализируем в зависимости от режима просмотра
        if (this.viewMode === 'day' && this.isMobile) {
            this.renderDayView(this.currentDate);
        } else {
            this.loadCalendarData();
            this.initScrollTracking();
        }
    }

    getShiftById(shiftId) {
        if (!this.calendarData || !Array.isArray(this.calendarData.shifts)) {
            return null;
        }
        return this.calendarData.shifts.find(
            (shift) => String(shift.id) === String(shiftId),
        ) || null;
    }

    _selectShiftElement(element, shiftId) {
        if (this.selectedShiftElement && this.selectedShiftElement !== element) {
            this.selectedShiftElement.classList.remove('shift-item-selected');
        }

        if (!element) {
            this.selectedShiftElement = null;
            this.selectedShiftId = null;
            this.selectedShiftScheduleId = null;
            this.selectedShiftType = null;
            return;
        }

        this.selectedShiftElement = element;
        this.selectedShiftId = shiftId;
        this.selectedShiftElement.classList.add('shift-item-selected');

        const scheduleAttr = this.selectedShiftElement.dataset.scheduleId;
        this.selectedShiftScheduleId = scheduleAttr ? Number(scheduleAttr) : null;

        let shiftType = this.selectedShiftElement.dataset.shiftType || '';
        if (!shiftType && typeof shiftId === 'string' && shiftId.startsWith('schedule_')) {
            shiftType = 'planned';
        }
        this.selectedShiftType = shiftType || null;
    }
    
    // Helpers for local date formatting (avoid UTC shifts)
    pad2(n) { return n.toString().padStart(2, '0'); }
    formatDateLocal(d) {
        return `${d.getFullYear()}-${this.pad2(d.getMonth() + 1)}-${this.pad2(d.getDate())}`;
    }
    parseDateLocal(dateStr) {
        const [y, m, d] = (dateStr || '').split('-').map(Number);
        return new Date(y || 1970, (m || 1) - 1, d || 1);
    }
    
    initScrollTracking() {
        const scrollableContainer = document.querySelector('.calendar-scrollable');
        if (!scrollableContainer) return;
        
        let scrollTimeout;
        let isScrolling = false;
        let lastScrollTime = 0;
        
        // Оптимизированный обработчик прокрутки с дебаунсингом и throttling
        scrollableContainer.addEventListener('scroll', () => {
            const now = Date.now();
            
            // Throttling: не чаще чем раз в 16ms (60fps)
            if (now - lastScrollTime < 16) return;
            lastScrollTime = now;
            
            if (!this.isScrolling && !this.isUserNavigating) {
                this.isScrolling = true;
                
                // Debouncing: выполняем обработку через 100ms после последнего скролла
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    requestAnimationFrame(() => {
                        this.handleScroll();
                        this.isScrolling = false;
                    });
                }, 100);
            }
        }, { passive: true });
    }
    
    handleScroll() {
        // Защита от рекурсивных вызовов
        if (this.isLoadingMonth || this.isUserNavigating || this.initialAutoScrollInProgress) return;
        
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
            const date = this.parseDateLocal(dateStr);
            return { year: date.getFullYear(), month: date.getMonth() + 1 };
        }
        
        return null;
    }
    
    checkAndLoadAdjacentMonths(visibleMonth) {
        // Теперь загружаем только 3 месяца, поэтому нужна динамическая подгрузка
        const { year, month } = visibleMonth;
        const monthKey = `${year}-${month}`;
        
        // Обновляем текущий видимый месяц
        this.currentVisibleMonth = monthKey;
        
        // НЕ загружаем, если:
        // 1. Месяц уже загружен
        // 2. Месяц сейчас загружается
        // 3. Идет пользовательская навигация (клик/выбор месяца)
        if (this.loadedMonths.has(monthKey) || 
            this.loadingMonths?.has(monthKey) || 
            this.isUserNavigating) {
            return;
        }
        
        console.log(`Month ${monthKey} not loaded, triggering loadMonthRange`);
        this.loadMonthRange(year, month);
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
                start_date: this.formatDateLocal(startDate),
                end_date: this.formatDateLocal(endDate)
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
            this.processCalendarData();
            
            // Повторно отрисовываем сетку без сброса позиции
            const scrollableContainer = document.querySelector('.calendar-scrollable');
            const previousScrollTop = scrollableContainer ? scrollableContainer.scrollTop : null;
            
            if (this.onDataLoaded) {
                this.onDataLoaded(this.calendarData);
            } else if (typeof window.renderCalendarGrid === 'function') {
                window.renderCalendarGrid(this.calendarData);
            }
            
            if (scrollableContainer && previousScrollTop !== null) {
                scrollableContainer.scrollTop = previousScrollTop;
            }
            
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
        
        // Обновляем диапазон дат (проверяем оба формата: date_range и metadata)
        const newStart = newData.metadata?.date_range_start || newData.date_range?.start;
        const newEnd = newData.metadata?.date_range_end || newData.date_range?.end;
        const currentStart = this.calendarData.metadata?.date_range_start || this.calendarData.date_range?.start;
        const currentEnd = this.calendarData.metadata?.date_range_end || this.calendarData.date_range?.end;
        
        if (newStart && newEnd) {
            const newStartDate = new Date(newStart);
            const newEndDate = new Date(newEnd);
            const currentStartDate = currentStart ? new Date(currentStart) : newStartDate;
            const currentEndDate = currentEnd ? new Date(currentEnd) : newEndDate;
            
            // Обновляем metadata (новый формат API)
            if (!this.calendarData.metadata) {
                this.calendarData.metadata = {};
            }
            this.calendarData.metadata.date_range_start = newStartDate < currentStartDate ? newStart : currentStart;
            this.calendarData.metadata.date_range_end = newEndDate > currentEndDate ? newEnd : currentEnd;
            
            // Для обратной совместимости
            if (!this.calendarData.date_range) {
                this.calendarData.date_range = {};
            }
            this.calendarData.date_range.start = this.calendarData.metadata.date_range_start;
            this.calendarData.date_range.end = this.calendarData.metadata.date_range_end;
        }
    }
    
    initializeLoadedMonthsCache() {
        if (!this.calendarData) return;
        
        const metadata = this.calendarData.metadata || {};
        const dateRangeStart = metadata.date_range_start || this.calendarData.date_range?.start;
        const dateRangeEnd = metadata.date_range_end || this.calendarData.date_range?.end;
        
        let start = dateRangeStart ? this.parseDateLocal(dateRangeStart) : new Date(this.currentDate);
        let end = dateRangeEnd ? this.parseDateLocal(dateRangeEnd) : new Date(this.currentDate);
        
        // Нормализуем к первому числу месяца
        start = new Date(start.getFullYear(), start.getMonth(), 1);
        end = new Date(end.getFullYear(), end.getMonth(), 1);
        
        console.log(`[UniversalCalendar] Initializing cache for range ${start.getFullYear()}-${start.getMonth() + 1} to ${end.getFullYear()}-${end.getMonth() + 1}`);
        
        const iter = new Date(start);
        while (iter <= end) {
            const monthKey = `${iter.getFullYear()}-${iter.getMonth() + 1}`;
            this.loadedMonths.add(monthKey);
            iter.setMonth(iter.getMonth() + 1);
        }
        
        // Устанавливаем текущий видимый месяц
        this.currentVisibleMonth = `${this.currentDate.getFullYear()}-${this.currentDate.getMonth() + 1}`;
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
        
        // Mobile navigation events
        if (this.isMobile) {
            this.bindMobileEvents();
        }
        
        // Shift and timeslot clicks
        document.addEventListener('click', (e) => {
            const shiftElement = e.target.closest('.shift-item');
            if (shiftElement) {
                const shiftId = shiftElement.dataset.shiftId;
                if (shiftId) {
                    this._selectShiftElement(shiftElement, shiftId);
                    if (typeof this.handleShiftClick === 'function') {
                        this.handleShiftClick(shiftId, e);
                    } else if (this.onShiftClick) {
                        this.onShiftClick(shiftId, e);
                    }
                }
                return;
            }
            
            const timeslotElement = e.target.closest('.timeslot-item');
            if (timeslotElement) {
                this._selectShiftElement(null, null);
                const timeslotId = timeslotElement.dataset.timeslotId;
                if (timeslotId && this.onTimeslotClick) {
                    this.onTimeslotClick(timeslotId);
                }
                return;
            }
            
            const dayElement = e.target.closest('.calendar-day');
            if (dayElement) {
                this._selectShiftElement(null, null);
                if (this.onDateClick) {
                    const dateStr = dayElement.dataset.date;
                    this.onDateClick(dateStr, dayElement);
                }
            }
        });

        if (typeof this.onShiftDelete === 'function') {
            document.addEventListener('keydown', (e) => {
                if (e.key !== 'Delete' && e.key !== 'Backspace') {
                    return;
                }

                const activeElement = document.activeElement;
                if (activeElement) {
                    const tagName = activeElement.tagName ? activeElement.tagName.toLowerCase() : null;
                    if (tagName && ['input', 'textarea', 'select'].includes(tagName)) {
                        return;
                    }
                }

                if (!this.selectedShiftId) {
                    return;
                }

                const shiftData = this.getShiftById(this.selectedShiftId);
                this.onShiftDelete(
                    {
                        id: this.selectedShiftId,
                        scheduleId: this.selectedShiftScheduleId,
                        type: this.selectedShiftType,
                        shift: shiftData,
                        event: e,
                    },
                    e,
                );
            });
        }
    }
    
    async loadCalendarData(startDate = null, endDate = null, objectIds = null, skipAutoScroll = false) {
        if (this.loading) return;
        
        this.loading = true;
        this.showLoading(true);
        
        try {
            // Calculate date range
            const dateRange = this.calculateDateRange(startDate, endDate);
            
            // Build API URL
            const params = new URLSearchParams({
                start_date: this.formatDateLocal(dateRange.start),
                end_date: this.formatDateLocal(dateRange.end)
            });
            
            // Получаем параметры фильтрации из URL
            const urlParams = new URLSearchParams(window.location.search);
            const objectIdFromUrl = urlParams.get('object_id');
            const orgUnitIdFromUrl = urlParams.get('org_unit_id');
            
            if (objectIds && objectIds.length > 0) {
                params.append('object_ids', objectIds.join(','));
            } else if (objectIdFromUrl) {
                params.append('object_ids', objectIdFromUrl);
            }
            
            // Добавляем фильтр по подразделениям если есть (новый формат org_unit_ids или старый org_unit_id)
            const orgUnitIdsFromUrl = urlParams.get('org_unit_ids');
            if (orgUnitIdsFromUrl) {
                params.append('org_unit_ids', orgUnitIdsFromUrl);
            } else if (orgUnitIdFromUrl) {
                params.append('org_unit_id', orgUnitIdFromUrl);
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
            
            // Если мы в дневном виде на мобильном, обновляем дневной вид вместо календарной сетки
            if (this.viewMode === 'day' && this.isMobile) {
                this.renderDayView(this.currentDate);
            } else {
                this.renderCalendar();
                
                // Call callback if provided (только для месячного вида)
                if (this.onDataLoaded) {
                    this.onDataLoaded(this.calendarData);
                }
            }
            
            // Автоскролл к текущему дню при первой загрузке (если не отключен)
            if (!skipAutoScroll) {
                this.initialAutoScrollInProgress = true;
                if (this.viewMode === 'day' && this.isMobile) {
                    // Для дневного вида просто обновляем отображение текущей даты
                    setTimeout(() => {
                        this.initialAutoScrollInProgress = false;
                    }, 100);
                } else {
                    // Для месячного вида прокручиваем к текущему дню
                    setTimeout(() => {
                        this.scrollToToday(() => {
                            // даём время плавному скроллу завершиться, затем снимаем флаг
                            setTimeout(() => {
                                this.initialAutoScrollInProgress = false;
                            }, 400);
                        });
                    }, 200);
                }
            } else {
                this.initialAutoScrollInProgress = false;
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
        const start = startDate ? new Date(startDate) : new Date(this.currentDate);
        const end = endDate ? new Date(endDate) : new Date(this.currentDate);
        
        if (this.viewType === 'month') {
            // Загружаем только текущий месяц
            start.setDate(1);
            end.setDate(1);
            end.setMonth(end.getMonth() + 1);
            end.setDate(0); // последний день текущего месяца
            
            console.log(`[UniversalCalendar] Loading data for month: ${this.formatDateLocal(start)} to ${this.formatDateLocal(end)}`);
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
            // Извлекаем дату из ISO строки или используем как есть
            let date = timeslot.date;
            if (typeof date === 'string') {
                // Если это ISO строка (содержит T), извлекаем только дату
                if (date.includes('T')) {
                    date = date.split('T')[0];
                }
            } else if (date && typeof date.toISOString === 'function') {
                // Если это Date объект
                date = this.formatDateLocal(date);
            }
            
            if (!this.calendarData.timeslotsByDate[date]) {
                this.calendarData.timeslotsByDate[date] = [];
            }
            this.calendarData.timeslotsByDate[date].push(timeslot);
        });
        
        // Process shifts
        this.calendarData.shifts.forEach(shift => {
            // Для запланированных смен используем planned_start, для остальных - start_time
            let date = null;
            if (shift.shift_type === 'planned' && shift.planned_start) {
                date = shift.planned_start.split('T')[0];
            } else if (shift.start_time) {
                date = shift.start_time.split('T')[0];
            }
            
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
    
    /**
     * Отображает дневной вид календаря для мобильных устройств
     * @param {Date} date - Дата для отображения
     */
    async renderDayView(date) {
        if (!date) {
            date = this.currentDate;
        }
        
        this.currentDate = new Date(date);
        this.loading = true;
        
        try {
            const dateStr = this.formatDateLocal(date);
            
            // Получаем object_id из URL
            const urlParams = new URLSearchParams(window.location.search);
            const objectIdFromUrl = urlParams.get('object_id');
            
            const params = new URLSearchParams({
                start_date: dateStr,
                end_date: dateStr
            });
            
            if (objectIdFromUrl) {
                params.append('object_ids', objectIdFromUrl);
            }
            
            // Добавляем фильтр по подразделениям если есть
            const orgUnitIdFromUrl = urlParams.get('org_unit_id');
            const orgUnitIdsFromUrl = urlParams.get('org_unit_ids');
            if (orgUnitIdsFromUrl) {
                params.append('org_unit_ids', orgUnitIdsFromUrl);
            } else if (orgUnitIdFromUrl) {
                params.append('org_unit_id', orgUnitIdFromUrl);
            }
            
            const response = await fetch(`${this.apiEndpoint}?${params}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const dayData = await response.json();
            
            console.log('[DayView] API Response:', {
                dateStr,
                timeslotsCount: dayData.timeslots?.length || 0,
                shiftsCount: dayData.shifts?.length || 0,
                firstTimeslot: dayData.timeslots?.[0],
                firstShift: dayData.shifts?.[0]
            });
            
            // Объединяем данные
            if (!this.calendarData) {
                this.calendarData = dayData;
            } else {
                this.mergeMonthData(dayData);
            }
            
            this.processCalendarData();
            
            console.log('[DayView] After processCalendarData:', {
                timeslotsByDate: this.calendarData.timeslotsByDate?.[dateStr]?.length || 0,
                shiftsByDate: this.calendarData.shiftsByDate?.[dateStr]?.length || 0,
                allTimeslots: this.calendarData.timeslots?.length || 0,
                allShifts: this.calendarData.shifts?.length || 0
            });
            
            // КРИТИЧЕСКИ ВАЖНО: Обновляем window.calendarData для доступа из onShiftClick
            window.calendarData = this.calendarData;
            
            // ДЛЯ DAY VIEW не вызываем onDataLoaded (иначе создаётся grid для month и падает createCalendarGrid)
            // Рендерим дневной вид
            this.renderDayViewHTML(date);
            
            // Обновляем URL
            this.updateURLForDate(date);
            
            // Обновляем input даты
            const dateInput = document.getElementById('mobileDateInput');
            if (dateInput) {
                dateInput.value = this.formatDateLocal(date);
            }
            
            // Обновляем кнопку "Сегодня"
            const todayBtn = document.getElementById('todayBtn');
            if (todayBtn) {
                const today = new Date();
                const isToday = date.toDateString() === today.toDateString();
                if (isToday) {
                    todayBtn.classList.add('active');
                } else {
                    todayBtn.classList.remove('active');
                }
            }
            
            // НЕ вызываем onDataLoaded для дневного вида, т.к. он вызывает renderCalendarGrid для месячного вида
            // Вместо этого мы уже отрендерили дневной вид через renderDayViewHTML
            
        } catch (error) {
            console.error('Error loading day view:', error);
        } finally {
            this.loading = false;
        }
    }
    
    /**
     * Рендерит HTML для дневного вида
     * @param {Date} date - Дата для отображения
     */
    renderDayViewHTML(date) {
        const dateStr = this.formatDateLocal(date);
        
        console.log('[DayView] renderDayViewHTML:', {
            dateStr,
            hasCalendarData: !!this.calendarData,
            timeslotsByDate: this.calendarData?.timeslotsByDate?.[dateStr]?.length || 0,
            allTimeslots: this.calendarData?.timeslots?.length || 0,
            sampleTimeslot: this.calendarData?.timeslots?.[0]
        });
        
        // Получаем тайм-слоты для этой даты
        // Проверяем оба формата: timeslotsByDate (после processCalendarData) и напрямую из timeslots
        let timeslots = this.calendarData?.timeslotsByDate?.[dateStr] || [];
        if (timeslots.length === 0 && this.calendarData?.timeslots) {
            // Если timeslotsByDate пуст, фильтруем напрямую из timeslots
            console.log('[DayView] Filtering timeslots directly, checking dates:', 
                this.calendarData.timeslots.map(ts => ({ id: ts.id, date: ts.date, matches: ts.date === dateStr }))
            );
            timeslots = this.calendarData.timeslots.filter(ts => {
                // Проверяем разные форматы даты
                let tsDate = ts.date;
                if (typeof tsDate === 'string') {
                    // Если это ISO строка (содержит T), извлекаем только дату
                    if (tsDate.includes('T')) {
                        tsDate = tsDate.split('T')[0];
                    }
                } else if (tsDate && typeof tsDate.toISOString === 'function') {
                    // Если это Date объект
                    tsDate = this.formatDateLocal(tsDate);
                }
                // Fallback на start_time если date отсутствует
                if (!tsDate) {
                    tsDate = ts.start_time?.split('T')[0];
                }
                return tsDate === dateStr;
            });
            console.log('[DayView] Filtered timeslots:', timeslots.length);
        }
        
        // Получаем смены для этой даты
        let shifts = this.calendarData?.shiftsByDate?.[dateStr] || [];
        if (shifts.length === 0 && this.calendarData?.shifts) {
            // Если shiftsByDate пуст, фильтруем напрямую из shifts
            shifts = this.calendarData.shifts.filter(shift => {
                let shiftDate = null;
                if (shift.shift_type === 'planned' && shift.planned_start) {
                    shiftDate = shift.planned_start.split('T')[0];
                } else if (shift.start_time) {
                    shiftDate = shift.start_time.split('T')[0];
                }
                return shiftDate === dateStr;
            });
        }
        
        // Группируем тайм-слоты по объектам
        const timeslotsByObject = {};
        timeslots.forEach(ts => {
            const objectId = ts.object_id || 'unknown';
            if (!timeslotsByObject[objectId]) {
                timeslotsByObject[objectId] = {
                    object: {
                        id: objectId,
                        name: ts.object_name || ts.object?.name || 'Неизвестный объект'
                    },
                    timeslots: []
                };
            }
            timeslotsByObject[objectId].timeslots.push(ts);
        });
        
        console.log('[DayView] Final data:', {
            timeslotsCount: timeslots.length,
            shiftsCount: shifts.length,
            timeslotsByObjectCount: Object.keys(timeslotsByObject).length,
            timeslotsByObjectKeys: Object.keys(timeslotsByObject)
        });
        
        // Форматируем дату для отображения
        const dayNames = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];
        const monthNames = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 
                           'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
        const dayName = dayNames[date.getDay()];
        const day = date.getDate();
        const month = monthNames[date.getMonth()];
        const year = date.getFullYear();
        const dateLabel = `${dayName}, ${day} ${month} ${year}`;
        
        // Находим контейнер календаря
        const scrollableContainer = document.querySelector('.calendar-scrollable');
        if (!scrollableContainer) {
            console.error('Calendar scrollable container not found');
            return;
        }
        
        // Создаём HTML для дневного вида
        let html = `
            <div class="calendar-day-view" data-date="${dateStr}">
                <div class="day-view-header">
                    <h3 class="day-view-title">${dateLabel}</h3>
                </div>
                <div class="day-view-content">
        `;
        
        // Разделяем смены по типам
        const plannedShifts = shifts.filter(s => s.shift_type === 'planned' && s.status !== 'cancelled');
        const activeShifts = shifts.filter(s => s.shift_type === 'active' && s.status === 'active');
        const completedShifts = shifts.filter(s => s.shift_type === 'completed' || s.status === 'completed');
        const spontaneousShifts = shifts.filter(s => !s.time_slot_id && s.shift_type !== 'planned' && s.status !== 'cancelled');
        
        // Смены, привязанные к тайм-слотам (для отображения внутри тайм-слотов)
        const shiftsWithTimeslot = shifts.filter(s => s.time_slot_id && s.status !== 'cancelled');
        
        console.log('[DayView] Shifts breakdown:', {
            totalShifts: shifts.length,
            planned: plannedShifts.length,
            active: activeShifts.length,
            completed: completedShifts.length,
            spontaneous: spontaneousShifts.length,
            withTimeslot: shiftsWithTimeslot.length
        });
        
        // Группируем спонтанные смены по объектам
        const spontaneousShiftsByObject = {};
        spontaneousShifts.forEach(shift => {
            const objectId = shift.object_id || 'unknown';
            if (!spontaneousShiftsByObject[objectId]) {
                spontaneousShiftsByObject[objectId] = {
                    object: { name: shift.object_name || 'Неизвестный объект', id: objectId },
                    shifts: []
                };
            }
            spontaneousShiftsByObject[objectId].shifts.push(shift);
        });
        
        // Группируем запланированные смены по объектам
        const plannedShiftsByObject = {};
        plannedShifts.forEach(shift => {
            const objectId = shift.object_id || 'unknown';
            if (!plannedShiftsByObject[objectId]) {
                plannedShiftsByObject[objectId] = {
                    object: { name: shift.object_name || 'Неизвестный объект', id: objectId },
                    shifts: []
                };
            }
            plannedShiftsByObject[objectId].shifts.push(shift);
        });
        
        // Группируем активные смены по объектам
        const activeShiftsByObject = {};
        activeShifts.forEach(shift => {
            const objectId = shift.object_id || 'unknown';
            if (!activeShiftsByObject[objectId]) {
                activeShiftsByObject[objectId] = {
                    object: { name: shift.object_name || 'Неизвестный объект', id: objectId },
                    shifts: []
                };
            }
            activeShiftsByObject[objectId].shifts.push(shift);
        });
        
        // Группируем завершенные смены по объектам
        const completedShiftsByObject = {};
        completedShifts.forEach(shift => {
            const objectId = shift.object_id || 'unknown';
            if (!completedShiftsByObject[objectId]) {
                completedShiftsByObject[objectId] = {
                    object: { name: shift.object_name || 'Неизвестный объект', id: objectId },
                    shifts: []
                };
            }
            completedShiftsByObject[objectId].shifts.push(shift);
        });
        
        // Если нет тайм-слотов и нет смен
        // Проверяем наличие данных: тайм-слоты (даже если не сгруппированы) или любые смены
        const hasAnyData = timeslots.length > 0 || 
                          shifts.length > 0 ||
                          Object.keys(timeslotsByObject).length > 0 || 
                          Object.keys(plannedShiftsByObject).length > 0 ||
                          Object.keys(activeShiftsByObject).length > 0 ||
                          Object.keys(completedShiftsByObject).length > 0 ||
                          Object.keys(spontaneousShiftsByObject).length > 0;
        
        console.log('[DayView] hasAnyData check:', {
            timeslotsLength: timeslots.length,
            shiftsLength: shifts.length,
            timeslotsByObjectKeys: Object.keys(timeslotsByObject).length,
            plannedShiftsByObjectKeys: Object.keys(plannedShiftsByObject).length,
            activeShiftsByObjectKeys: Object.keys(activeShiftsByObject).length,
            completedShiftsByObjectKeys: Object.keys(completedShiftsByObject).length,
            spontaneousShiftsByObjectKeys: Object.keys(spontaneousShiftsByObject).length,
            hasAnyData: hasAnyData
        });
        
        if (!hasAnyData) {
            html += `
                <div class="day-view-empty">
                    <p>На этот день нет запланированных тайм-слотов и смен</p>
                </div>
            `;
        } else {
            // Рендерим тайм-слоты по объектам (если есть)
            if (Object.keys(timeslotsByObject).length > 0) {
                Object.values(timeslotsByObject).forEach(({ object, timeslots: objectTimeslots }) => {
                    // Сначала фильтруем тайм-слоты, которые нужно отобразить
                    const visibleTimeslots = [];
                    objectTimeslots.forEach(timeslot => {
                        const timeslotShifts = shiftsWithTimeslot.filter(s => s.time_slot_id === timeslot.id) || [];
                        const status = this.getTimeslotStatus(timeslot, timeslotShifts);
                        
                        // Определяем занятость: используем количество смен, если current_employees не обновлен
                        const actualEmployees = timeslotShifts.length || (timeslot.current_employees || 0);
                        const maxEmployees = timeslot.max_employees || 1;
                        
                        // Проверяем, есть ли свободное время по покрытию (не только по количеству сотрудников)
                        // Если есть free_minutes > 0, значит тайм-слот частично свободен, даже если сотрудников достаточно
                        const hasFreeTime = timeslot.free_minutes && timeslot.free_minutes > 0;
                        const isFullyOccupied = actualEmployees >= maxEmployees && !hasFreeTime;
                        
                        // Проверяем флаги из API
                        const fullyOccupiedByPlanned = timeslot.fully_occupied || false;
                        const hasFreeTrack = timeslot.has_free_track !== undefined ? timeslot.has_free_track : true;
                        
                        // Скрываем тайм-слот если:
                        // 1. Он полностью покрыт запланированной сменой (fully_occupied)
                        // 2. Или если есть активные смены по плану и нет свободных треков (!has_free_track)
                        const shouldHide = fullyOccupiedByPlanned || (!hasFreeTrack && actualEmployees > 0);
                        
                        // Показываем все тайм-слоты, кроме полностью занятых (и по сотрудникам, и по времени)
                        // Частично занятые тайм-слоты (свободное время) показываем с указанием свободного времени
                        if (!isFullyOccupied && !shouldHide) {
                            visibleTimeslots.push({ timeslot, timeslotShifts, status, actualEmployees, maxEmployees });
                        }
                    });
                    
                    console.log(`[DayView] Object ${object.id}: ${objectTimeslots.length} total timeslots, ${visibleTimeslots.length} visible`);
                    
                    // Выводим название объекта только если есть хотя бы один видимый тайм-слот
                    if (visibleTimeslots.length === 0) {
                        return; // Пропускаем объект, если все тайм-слоты скрыты
                    }
                    
                    html += `
                    <div class="day-view-object" data-object-id="${object.id}">
                        <h4 class="day-view-object-name">${object.name}</h4>
                        <div class="day-view-timeslots">
                `;
                
                visibleTimeslots.forEach(({ timeslot, timeslotShifts, status, actualEmployees, maxEmployees }) => {
                    // Определяем, есть ли запланированные смены
                    const hasPlannedShifts = actualEmployees > 0;
                    
                    // Вычисляем доступные интервалы времени для частично занятых тайм-слотов
                    let availableTimeRange = null;
                    let availableHours = null;
                    
                    if (hasPlannedShifts && timeslotShifts.length > 0) {
                        // Вычисляем доступные интервалы
                        const intervals = this.calculateAvailableIntervals(timeslot, timeslotShifts);
                        if (intervals.length > 0) {
                            // Показываем только первый доступный интервал (самый ранний)
                            const firstInterval = intervals[0];
                            availableTimeRange = {
                                start: firstInterval.start,
                                end: firstInterval.end
                            };
                            
                            // Вычисляем общее количество доступных часов по всем интервалам
                            let totalMinutes = 0;
                            intervals.forEach(interval => {
                                totalMinutes += (interval.endMinutes - interval.startMinutes);
                            });
                            availableHours = this.formatMinutes(totalMinutes);
                        }
                    }
                    
                    // Для частично занятых тайм-слотов показываем как свободные, но с доступным временем
                    const isPartiallyOccupied = hasPlannedShifts && availableTimeRange;
                    const timeslotClass = isPartiallyOccupied ? 'timeslot-free' : (actualEmployees < maxEmployees ? 'timeslot-free' : 'timeslot-occupied');
                    const statusText = 'Свободно';
                    
                    // Определяем время для отображения
                    let displayTime = `${this.formatTime(timeslot.start_time)} - ${this.formatTime(timeslot.end_time)}`;
                    if (isPartiallyOccupied && availableTimeRange) {
                        displayTime = `${this.formatTime(availableTimeRange.start)} - ${this.formatTime(availableTimeRange.end)}`;
                    }
                    
                    html += `
                        <div class="day-view-timeslot ${timeslotClass}" data-timeslot-id="${timeslot.id}">
                            <div class="timeslot-time">
                                ${displayTime}
                            </div>
                            <div class="timeslot-info">
                                <span class="timeslot-status">${statusText}</span>
                                ${availableHours ? `<span class="timeslot-free-time">Доступно: ${availableHours}</span>` : ''}
                            </div>
                            ${timeslot.hourly_rate ? `
                                <div class="timeslot-rate">${timeslot.hourly_rate}₽/ч</div>
                            ` : ''}
                        </div>
                    `;
                });
                
                html += `
                        </div>
                    </div>
                `;
                });
            }
            
            // Добавляем запланированные смены (без тайм-слотов)
            if (Object.keys(plannedShiftsByObject).length > 0) {
                html += `
                    <div class="day-view-planned-section">
                        <h4 class="day-view-section-title">Запланированные смены</h4>
                `;
                
                Object.values(plannedShiftsByObject).forEach(({ object, shifts: objectShifts }) => {
                    html += this.renderShiftsSection(object, objectShifts, 'planned');
                });
                
                html += `</div>`;
            }
            
            // Добавляем активные смены
            if (Object.keys(activeShiftsByObject).length > 0) {
                html += `
                    <div class="day-view-active-section">
                        <h4 class="day-view-section-title">Активные смены</h4>
                `;
                
                Object.values(activeShiftsByObject).forEach(({ object, shifts: objectShifts }) => {
                    html += this.renderShiftsSection(object, objectShifts, 'active');
                });
                
                html += `</div>`;
            }
            
            // Добавляем завершенные смены
            if (Object.keys(completedShiftsByObject).length > 0) {
                html += `
                    <div class="day-view-completed-section">
                        <h4 class="day-view-section-title">Завершенные смены</h4>
                `;
                
                Object.values(completedShiftsByObject).forEach(({ object, shifts: objectShifts }) => {
                    html += this.renderShiftsSection(object, objectShifts, 'completed');
                });
                
                html += `</div>`;
            }
            
            // Добавляем спонтанные смены (без тайм-слотов)
            if (Object.keys(spontaneousShiftsByObject).length > 0) {
                html += `
                    <div class="day-view-spontaneous-section">
                        <h4 class="day-view-section-title">Спонтанные смены</h4>
                `;
                
                Object.values(spontaneousShiftsByObject).forEach(({ object, shifts: objectShifts }) => {
                    html += this.renderShiftsSection(object, objectShifts, 'spontaneous');
                });
                
                html += `</div>`;
            }
        }
        
        html += `
                </div>
            </div>
        `;
        
        scrollableContainer.innerHTML = html;
        
        // Привязываем обработчики событий
        this.bindDayViewEvents();
    }
    
    /**
     * Рендерит секцию смен для объекта
     * @param {Object} object - Объект
     * @param {Array} shifts - Массив смен
     * @param {string} shiftType - Тип смены (planned, active, completed, spontaneous)
     * @returns {string} HTML
     */
    renderShiftsSection(object, shifts, shiftType) {
        let html = `
            <div class="day-view-object" data-object-id="${object.id}">
                <h4 class="day-view-object-name">${object.name}</h4>
                <div class="day-view-shifts-list">
        `;
        
        shifts.forEach(shift => {
            let startTime = '—';
            let endTime = '—';
            
            if (shift.shift_type === 'planned') {
                // Для запланированных используем planned_start и planned_end
                if (shift.planned_start) {
                    startTime = this.formatTime(shift.planned_start);
                }
                if (shift.planned_end) {
                    endTime = this.formatTime(shift.planned_end);
                }
            } else {
                // Для активных/завершенных используем start_time и end_time
                if (shift.start_time) {
                    startTime = this.formatTime(shift.start_time);
                }
                if (shift.end_time) {
                    endTime = this.formatTime(shift.end_time);
                }
            }
            
            const shiftClass = `shift-${shiftType}`;
            const sticker = shift.shift_type === 'planned' ? '<div class="shift-sticker">1/1</div>' : '';
            
            // Определяем текст статуса смены на русском
            let shiftStatusText = '';
            if (shift.shift_type === 'planned') {
                shiftStatusText = 'Запланирована';
            } else if (shift.shift_type === 'active') {
                shiftStatusText = 'Активна';
            } else if (shift.shift_type === 'completed') {
                shiftStatusText = 'Завершена';
            } else if (shiftType === 'spontaneous') {
                shiftStatusText = 'Спонтанная';
            } else {
                shiftStatusText = shift.status_label || shift.status || '';
            }
            
            html += `
                <div class="day-view-shift-item shift-item day-view-shift ${shiftClass}" 
                     data-shift-id="${shift.id}" 
                     data-shift-type="${shift.shift_type || shiftType}"
                     data-schedule-id="${shift.schedule_id || ''}">
                    <div class="shift-time">
                        ${startTime} - ${endTime}
                    </div>
                    <div class="shift-info">
                        <span class="shift-employee">${shift.user_name || shift.employee_name || 'Неизвестно'}</span>
                        <span class="shift-status">${shiftStatusText}</span>
                    </div>
                    ${shift.object_name ? `<div class="shift-object">${shift.object_name}</div>` : ''}
                    ${sticker}
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
        
        return html;
    }
    
    /**
     * Форматирует время для отображения
     * @param {string} timeStr - Время в формате HH:MM или ISO string
     * @returns {string}
     */
    formatTime(timeStr) {
        if (!timeStr) return '';
        // Если это ISO строка, извлекаем время
        if (timeStr.includes('T')) {
            const date = new Date(timeStr);
            return `${this.pad2(date.getHours())}:${this.pad2(date.getMinutes())}`;
        }
        // Если это уже время в формате HH:MM
        return timeStr.substring(0, 5);
    }
    
    /**
     * Определяет статус тайм-слота
     * @param {Object} timeslot - Тайм-слот
     * @param {Array} shifts - Смены в тайм-слоте
     * @returns {Object} { class: string, label: string }
     */
    getTimeslotStatus(timeslot, shifts) {
        const maxEmployees = timeslot.max_employees || 1;
        const currentEmployees = shifts.length;
        const availableSlots = maxEmployees - currentEmployees;
        
        if (availableSlots === 0) {
            return { class: 'timeslot-full', label: 'Заполнено' };
        } else if (currentEmployees === 0) {
            return { class: 'timeslot-free', label: 'Свободно' };
        } else {
            return { class: 'timeslot-partial', label: 'Запланирована' };
        }
    }
    
    /**
     * Привязывает обработчики событий для дневного вида
     */
    bindDayViewEvents() {
        // Клики по сменам
        document.querySelectorAll('.day-view-shift').forEach(element => {
            element.addEventListener('click', (e) => {
                const shiftId = element.dataset.shiftId;
                if (shiftId) {
                    this._selectShiftElement(element, shiftId);
                    if (this.onShiftClick) {
                        this.onShiftClick(shiftId, e);
                    }
                }
            });
        });
        
        // Клики по тайм-слотам
        document.querySelectorAll('.day-view-timeslot').forEach(element => {
            element.addEventListener('click', (e) => {
                // Если клик не по смене
                if (!e.target.closest('.day-view-shift')) {
                    const timeslotId = element.dataset.timeslotId;
                    if (timeslotId && this.onTimeslotClick) {
                        this.onTimeslotClick(timeslotId);
                    }
                }
            });
        });
    }
    
    /**
     * Обновляет URL с параметром date
     * @param {Date} date - Дата
     */
    updateURLForDate(date) {
        const dateStr = this.formatDateLocal(date);
        const url = new URL(window.location);
        url.searchParams.set('date', dateStr);
        window.history.replaceState({}, '', url);
    }
    
    /**
     * Переход на предыдущий день
     */
    navigateDay(direction) {
        const newDate = new Date(this.currentDate);
        if (direction === 'prev') {
            newDate.setDate(newDate.getDate() - 1);
        } else if (direction === 'next') {
            newDate.setDate(newDate.getDate() + 1);
        }
        this.renderDayView(newDate);
    }
    
    /**
     * Переход на сегодня
     */
    goToTodayDay() {
        this.renderDayView(new Date());
    }
    
    /**
     * Привязывает обработчики событий для мобильной навигации
     */
    bindMobileEvents() {
        // Показываем/скрываем мобильную навигацию в зависимости от режима
        this.updateMobileNavigationVisibility();
        
        // Обработчики кнопок навигации
        const prevDayBtn = document.getElementById('prevDayBtn');
        const nextDayBtn = document.getElementById('nextDayBtn');
        const todayBtn = document.getElementById('todayBtn');
        const dateInput = document.getElementById('mobileDateInput');
        const viewToggleBtn = document.getElementById('viewToggleBtn');
        
        if (prevDayBtn) {
            prevDayBtn.addEventListener('click', () => {
                if (this.viewMode === 'day') {
                    this.navigateDay('prev');
                }
            });
        }
        
        if (nextDayBtn) {
            nextDayBtn.addEventListener('click', () => {
                if (this.viewMode === 'day') {
                    this.navigateDay('next');
                }
            });
        }
        
        if (todayBtn) {
            todayBtn.addEventListener('click', () => {
                if (this.viewMode === 'day') {
                    this.goToTodayDay();
                } else {
                    this.goToToday();
                }
            });
        }
        
        if (dateInput) {
            // Устанавливаем текущую дату
            dateInput.value = this.formatDateLocal(this.currentDate);
            
            dateInput.addEventListener('change', (e) => {
                const selectedDate = new Date(e.target.value);
                if (this.viewMode === 'day') {
                    this.renderDayView(selectedDate);
                } else {
                    this.currentDate = selectedDate;
                    this.loadCalendarData();
                }
            });
        }
        
        if (viewToggleBtn) {
            const viewToggleText = document.getElementById('viewToggleText');
            this.updateViewToggleButton();
            
            viewToggleBtn.addEventListener('click', () => {
                const newMode = this.viewMode === 'day' ? 'month' : 'day';
                this.setViewMode(newMode);
                this.updateMobileNavigationVisibility();
                this.updateViewToggleButton();
            });
        }
        
        // Поддержка свайпов
        if (this.viewMode === 'day') {
            this.initSwipeSupport();
        }
        
        // Обработчики модального окна фильтров
        const mobileFiltersBtn = document.getElementById('mobileFiltersBtn');
        const mobileFiltersModal = document.getElementById('mobileFiltersModal');
        const mobileFiltersApply = document.getElementById('mobileFiltersApply');
        const mobileFiltersReset = document.getElementById('mobileFiltersReset');
        const mobileOrgUnitFilter = document.getElementById('mobileOrgUnitFilter');
        const mobileObjectFilter = document.getElementById('mobileObjectFilter');
        
        // Обработчик открытия модального окна
        if (mobileFiltersBtn && mobileFiltersModal) {
            mobileFiltersBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                // Используем стандартный Bootstrap modal API
                if (window.bootstrap && bootstrap.Modal) {
                    // Удаляем старый экземпляр если есть
                    const oldModal = bootstrap.Modal.getInstance(mobileFiltersModal);
                    if (oldModal) {
                        oldModal.dispose();
                    }
                    
                    // Создаем новый экземпляр с правильными настройками
                    const modal = new bootstrap.Modal(mobileFiltersModal, {
                        backdrop: true,
                        keyboard: true,
                        focus: true
                    });
                    
                    // Показываем модальное окно
                    modal.show();
                    
                    // Убеждаемся, что модальное окно имеет правильный z-index и pointer-events
                    setTimeout(() => {
                        const backdrop = document.querySelector('.modal-backdrop');
                        if (backdrop) {
                            backdrop.style.zIndex = '1050';
                            backdrop.style.pointerEvents = 'auto';
                        }
                        mobileFiltersModal.style.zIndex = '1055';
                        mobileFiltersModal.style.pointerEvents = 'auto';
                        const modalDialog = mobileFiltersModal.querySelector('.modal-dialog');
                        if (modalDialog) {
                            modalDialog.style.zIndex = '1056';
                            modalDialog.style.pointerEvents = 'auto';
                        }
                        const modalContent = mobileFiltersModal.querySelector('.modal-content');
                        if (modalContent) {
                            modalContent.style.zIndex = '1057';
                            modalContent.style.pointerEvents = 'auto';
                        }
                        
                        // Устанавливаем фокус на первый инпут в модальном окне
                        const firstInput = mobileFiltersModal.querySelector('select, input, textarea');
                        if (firstInput) {
                            firstInput.focus();
                        } else {
                            // Если нет инпутов, фокусируемся на модальном окне
                            mobileFiltersModal.focus();
                        }
                    }, 100);
                } else {
                    // Fallback если Bootstrap не загружен
                    console.warn('Bootstrap Modal not available, using fallback');
                    mobileFiltersModal.classList.add('show');
                    mobileFiltersModal.style.display = 'block';
                    mobileFiltersModal.style.zIndex = '1055';
                    mobileFiltersModal.setAttribute('aria-hidden', 'false');
                    mobileFiltersModal.setAttribute('aria-modal', 'true');
                    document.body.classList.add('modal-open');
                    
                    // Создаем backdrop только если его еще нет
                    let backdrop = document.querySelector('.modal-backdrop');
                    if (!backdrop) {
                        backdrop = document.createElement('div');
                        backdrop.className = 'modal-backdrop fade show';
                        backdrop.id = 'mobileFiltersBackdrop';
                        backdrop.style.zIndex = '1050';
                        document.body.appendChild(backdrop);
                    }
                }
            });
        }
        
        // Обработчик закрытия модального окна при клике на backdrop
        if (mobileFiltersModal) {
            mobileFiltersModal.addEventListener('click', (e) => {
                // Закрываем только если клик был по самому модальному окну (не по содержимому)
                if (e.target === mobileFiltersModal) {
                    if (window.bootstrap && bootstrap.Modal) {
                        const modal = bootstrap.Modal.getInstance(mobileFiltersModal);
                        if (modal) {
                            modal.hide();
                        }
                    } else {
                        // Fallback
                        mobileFiltersModal.classList.remove('show');
                        mobileFiltersModal.style.display = 'none';
                        mobileFiltersModal.setAttribute('aria-hidden', 'true');
                        mobileFiltersModal.setAttribute('aria-modal', 'false');
                        document.body.classList.remove('modal-open');
                        const backdrop = document.getElementById('mobileFiltersBackdrop');
                        if (backdrop) {
                            backdrop.remove();
                        }
                    }
                }
            });
        }
        
        // Обработчик закрытия при нажатии ESC
        if (mobileFiltersModal) {
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && mobileFiltersModal.classList.contains('show')) {
                    if (window.bootstrap && bootstrap.Modal) {
                        const modal = bootstrap.Modal.getInstance(mobileFiltersModal);
                        if (modal) {
                            modal.hide();
                        }
                    }
                }
            });
        }
        
        if (mobileFiltersApply) {
            mobileFiltersApply.addEventListener('click', () => {
                this.applyMobileFilters();
                if (mobileFiltersModal && window.bootstrap) {
                    const modal = bootstrap.Modal.getInstance(mobileFiltersModal);
                    if (modal) {
                        modal.hide();
                    } else {
                        // Fallback
                        mobileFiltersModal.classList.remove('show');
                        mobileFiltersModal.style.display = 'none';
                        document.body.classList.remove('modal-open');
                        const backdrop = document.getElementById('mobileFiltersBackdrop');
                        if (backdrop) {
                            backdrop.remove();
                        }
                    }
                }
            });
        }
        
        if (mobileFiltersReset) {
            mobileFiltersReset.addEventListener('click', () => {
                this.resetMobileFilters();
            });
        }
        
        // Каскадная фильтрация объектов по подразделениям
        if (mobileOrgUnitFilter && mobileObjectFilter) {
            mobileOrgUnitFilter.addEventListener('change', () => {
                this.filterObjectsByOrgUnit(mobileOrgUnitFilter.value, mobileObjectFilter);
            });
        }
        
            // Обновляем чипсы при загрузке
            this.updateFilterChips();
            
            // Обновляем чипсы при изменении фильтров в модальном окне
            if (mobileOrgUnitFilter) {
                mobileOrgUnitFilter.addEventListener('change', () => {
                    setTimeout(() => this.updateFilterChips(), 100);
                });
            }
            if (mobileObjectFilter) {
                mobileObjectFilter.addEventListener('change', () => {
                    setTimeout(() => this.updateFilterChips(), 100);
                });
            }
        
        // Обработка изменения размера окна
        window.addEventListener('resize', () => {
            const wasMobile = this.isMobile;
            this.isMobile = this.isMobileDevice();
            
            if (wasMobile !== this.isMobile) {
                // Переключаем режим при изменении размера
                this.viewMode = this.initViewMode();
                this.updateMobileNavigationVisibility();
                if (this.viewMode === 'day') {
                    this.renderDayView(this.currentDate);
                } else {
                    this.loadCalendarData();
                }
            }
        });
    }
    
    /**
     * Обновляет видимость мобильной навигации
     */
    updateMobileNavigationVisibility() {
        const mobileNav = document.getElementById('mobileDayNavigation');
        const dayHeaders = document.querySelector('.calendar-day-headers');
        
        if (mobileNav) {
            if (this.isMobile && this.viewMode === 'day') {
                mobileNav.style.display = 'block';
                if (dayHeaders) {
                    dayHeaders.style.display = 'none';
                }
            } else {
                mobileNav.style.display = 'none';
                if (dayHeaders) {
                    dayHeaders.style.display = 'grid';
                }
            }
        }
    }
    
    /**
     * Обновляет текст кнопки переключения вида
     */
    updateViewToggleButton() {
        const viewToggleText = document.getElementById('viewToggleText');
        if (viewToggleText) {
            viewToggleText.textContent = this.viewMode === 'day' ? 'Месяц' : 'День';
        }
    }
    
    /**
     * Инициализирует поддержку свайпов для навигации по дням
     */
    initSwipeSupport() {
        const scrollableContainer = document.querySelector('.calendar-scrollable');
        if (!scrollableContainer) return;
        
        let touchStartX = null;
        let touchStartY = null;
        let touchEndX = null;
        let touchEndY = null;
        const minSwipeDistance = 50;
        
        scrollableContainer.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
            touchStartY = e.changedTouches[0].screenY;
        }, { passive: true });
        
        scrollableContainer.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            touchEndY = e.changedTouches[0].screenY;
            
            if (touchStartX === null || touchEndX === null) return;
            
            const deltaX = touchEndX - touchStartX;
            const deltaY = touchEndY - touchStartY;
            
            // Проверяем, что это горизонтальный свайп (не вертикальный скролл)
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
                if (deltaX > 0) {
                    // Swipe right - предыдущий день
                    this.navigateDay('prev');
                } else {
                    // Swipe left - следующий день
                    this.navigateDay('next');
                }
            }
            
            // Сбрасываем значения
            touchStartX = null;
            touchStartY = null;
            touchEndX = null;
            touchEndY = null;
        }, { passive: true });
    }
    
    /**
     * Применяет фильтры из модального окна
     */
    applyMobileFilters() {
        const url = new URL(window.location);
        const mobileOrgUnitFilter = document.getElementById('mobileOrgUnitFilter');
        const mobileObjectFilter = document.getElementById('mobileObjectFilter');
        
        if (mobileOrgUnitFilter) {
            const orgUnitId = mobileOrgUnitFilter.value;
            if (orgUnitId) {
                // Используем новый формат org_unit_ids (потомки будут добавлены на бэке)
                url.searchParams.set('org_unit_ids', orgUnitId);
                // Удаляем старый формат для совместимости
                url.searchParams.delete('org_unit_id');
            } else {
                url.searchParams.delete('org_unit_ids');
                url.searchParams.delete('org_unit_id');
            }
        }
        
        if (mobileObjectFilter) {
            const objectId = mobileObjectFilter.value;
            if (objectId) {
                url.searchParams.set('object_id', objectId);
            } else {
                url.searchParams.delete('object_id');
            }
        }
        
        // Перезагружаем страницу с новыми фильтрами
        window.location.href = url.toString();
    }
    
    /**
     * Сбрасывает фильтры
     */
    resetMobileFilters() {
        const mobileOrgUnitFilter = document.getElementById('mobileOrgUnitFilter');
        const mobileObjectFilter = document.getElementById('mobileObjectFilter');
        
        if (mobileOrgUnitFilter) {
            mobileOrgUnitFilter.value = '';
        }
        if (mobileObjectFilter) {
            mobileObjectFilter.value = '';
        }
        
        // Применяем сброс
        this.applyMobileFilters();
    }
    
    /**
     * Фильтрует объекты по подразделению в модальном окне
     */
    filterObjectsByOrgUnit(orgUnitId, objectSelect) {
        if (!objectSelect) return;
        
        const allOptions = objectSelect.querySelectorAll('option[data-org-unit]');
        let hasVisibleObjects = false;
        
        allOptions.forEach(option => {
            if (!orgUnitId || orgUnitId === '') {
                option.style.display = '';
                hasVisibleObjects = true;
            } else if (option.dataset.orgUnit && option.dataset.orgUnit === orgUnitId) {
                option.style.display = '';
                hasVisibleObjects = true;
            } else {
                option.style.display = 'none';
            }
        });
        
        // Сбрасываем выбор объекта если он не соответствует подразделению
        if (objectSelect.value) {
            const selectedOption = objectSelect.querySelector(`option[value="${objectSelect.value}"]`);
            if (selectedOption && selectedOption.style.display === 'none') {
                objectSelect.value = '';
            }
        }
    }
    
    /**
     * Обновляет чипсы выбранных фильтров
     */
    updateFilterChips() {
        const chipsContainer = document.getElementById('mobileFilterChips');
        if (!chipsContainer) return;
        
        const urlParams = new URLSearchParams(window.location.search);
        const orgUnitIds = urlParams.get('org_unit_ids');
        const orgUnitId = urlParams.get('org_unit_id'); // Старый формат для совместимости
        const objectId = urlParams.get('object_id');
        
        chipsContainer.innerHTML = '';
        
        if (!orgUnitIds && !orgUnitId && !objectId) {
            chipsContainer.style.display = 'none';
            return;
        }
        
        chipsContainer.style.display = 'flex';
        
        // Чипс подразделения (новый формат org_unit_ids или старый org_unit_id)
        const selectedOrgUnitId = orgUnitIds || orgUnitId;
        if (selectedOrgUnitId) {
            const orgUnitSelect = document.getElementById('mobileOrgUnitFilter') || document.getElementById('orgUnitFilter');
            if (orgUnitSelect) {
                // Если org_unit_ids содержит несколько ID, берем первый (основной)
                const mainOrgUnitId = selectedOrgUnitId.split(',')[0];
                const selectedOption = orgUnitSelect.querySelector(`option[value="${mainOrgUnitId}"]`);
                if (selectedOption) {
                    const chip = document.createElement('span');
                    chip.className = 'filter-chip';
                    chip.innerHTML = `
                        <span>Подразделение: ${selectedOption.textContent.trim()}</span>
                        <span class="chip-remove" data-filter="org_unit_ids">×</span>
                    `;
                    chipsContainer.appendChild(chip);
                    
                    chip.querySelector('.chip-remove').addEventListener('click', () => {
                        const url = new URL(window.location);
                        url.searchParams.delete('org_unit_ids');
                        url.searchParams.delete('org_unit_id');
                        window.location.href = url.toString();
                    });
                }
            }
        }
        
        // Чипс объекта
        if (objectId) {
            const objectSelect = document.getElementById('mobileObjectFilter') || document.getElementById('objectFilter');
            if (objectSelect) {
                const selectedOption = objectSelect.querySelector(`option[value="${objectId}"]`);
                if (selectedOption) {
                    const chip = document.createElement('span');
                    chip.className = 'filter-chip';
                    chip.innerHTML = `
                        <span>Объект: ${selectedOption.textContent}</span>
                        <span class="chip-remove" data-filter="object_id">×</span>
                    `;
                    chipsContainer.appendChild(chip);
                    
                    chip.querySelector('.chip-remove').addEventListener('click', () => {
                        const url = new URL(window.location);
                        url.searchParams.delete('object_id');
                        window.location.href = url.toString();
                    });
                }
            }
        }
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
        // NOTE: Не вызываем здесь, т.к. onDataLoaded уже вызывает renderCalendarGrid
        // Убрано дублирование рендеринга
        // if (typeof window.renderCalendarGrid === 'function') {
        //     window.renderCalendarGrid(this.calendarData);
        // }
        
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
        
        this.calendarData.timeslots.forEach(timeslot => {
            if (typeof timeslot.current_employees !== 'number') {
                const shifts = this.calendarData.shiftsByTimeslot[timeslot.id] || [];
                timeslot.current_employees = shifts.length;
            }
            const maxEmployees = timeslot.max_employees || 1;
            if (typeof timeslot.available_slots !== 'number') {
                timeslot.available_slots = Math.max(0, maxEmployees - (timeslot.current_employees || 0));
            }
            if (typeof timeslot.free_minutes !== 'number') {
                timeslot.free_minutes = 0;
            }
            if (typeof timeslot.occupancy_ratio !== 'number') {
                timeslot.occupancy_ratio = 0;
            }
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
    
    handleShiftClick(shiftId, event) {
        if (this.onShiftClick) {
            this.onShiftClick(shiftId, event);
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
        const monthKey = `${year}-${month}`;
        
        // Защита от повторных загрузок (если уже загружается)
        if (this.loadingMonths?.has(monthKey)) {
            console.log(`Month ${monthKey} is already loading, skipping`);
            return;
        }
        
        // Инициализируем Set для отслеживания загружаемых месяцев
        if (!this.loadingMonths) {
            this.loadingMonths = new Set();
        }
        
        this.loadingMonths.add(monthKey);
        console.log(`Loading month range for ${monthKey}`);
        
        // Загружаем диапазон вокруг выбранного месяца (по умолчанию: текущий и соседние)
        const prevRange = 0;
        const nextRange = 1;
        
        // Загружаем диапазон месяцев вокруг выбранного месяца
        const rangeStart = new Date(year, month - 1, 1);
        rangeStart.setMonth(rangeStart.getMonth() - prevRange);
        const rangeEnd = new Date(year, month - 1, 1);
        rangeEnd.setMonth(rangeEnd.getMonth() + nextRange + 1);
        rangeEnd.setDate(0);
        
        console.log(`[UniversalCalendar] Dynamic loading: ${rangeStart.toISOString().split('T')[0]} to ${rangeEnd.toISOString().split('T')[0]}`);
        
        // Получаем object_id из URL
        const urlParams = new URLSearchParams(window.location.search);
        const objectIdFromUrl = urlParams.get('object_id');
        
        const params = new URLSearchParams({
            start_date: rangeStart.toISOString().split('T')[0],
            end_date: rangeEnd.toISOString().split('T')[0]
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
            this.processCalendarData();
            
            // Повторно отрисовываем сетку без сброса позиции
            const scrollableContainer = document.querySelector('.calendar-scrollable');
            const previousScrollTop = scrollableContainer ? scrollableContainer.scrollTop : null;
            
            if (this.onDataLoaded) {
                this.onDataLoaded(this.calendarData);
            } else if (typeof window.renderCalendarGrid === 'function') {
                window.renderCalendarGrid(this.calendarData);
            }
            
            if (scrollableContainer && previousScrollTop !== null) {
                scrollableContainer.scrollTop = previousScrollTop;
            }
            
            // Помечаем загруженные месяцы в указанном диапазоне
            for (let i = -prevRange; i <= nextRange; i++) {
                let targetMonth = month + i;
                let targetYear = year;
                
                if (targetMonth <= 0) {
                    targetMonth += 12;
                    targetYear -= 1;
                } else if (targetMonth > 12) {
                    targetMonth -= 12;
                    targetYear += 1;
                }
                
                const monthKey = `${targetYear}-${targetMonth}`;
                this.loadedMonths.add(monthKey);
                console.log(`[UniversalCalendar] Marked ${monthKey} as loaded`);
            }
            
            // Обновляем отображение БЕЗ полного рендеринга (избегаем сброса скролла)
            this.renderCalendar(true); // preserveScrollPosition = true
            
            // Позиционируемся на выбранный месяц
            setTimeout(() => {
                this.scrollToMonth(year, month);
                // Сбрасываем флаги после позиционирования
                setTimeout(() => {
                    this.isUserNavigating = false;
                    this.loadingMonths.delete(monthKey);
                    console.log(`Finished loading ${monthKey}`);
                }, 300);
            }, 100);
            
        } catch (error) {
            console.error(`Error loading month range for ${year}-${month}:`, error);
            this.isUserNavigating = false;
            this.loadingMonths.delete(monthKey);
        }
    }
    
    scrollToMonth(year, month) {
        const scrollableContainer = document.querySelector('.calendar-scrollable');
        if (!scrollableContainer) return;
        
        // Находим первый день выбранного месяца
        const monthFirstDay = new Date(year, month - 1, 1);
        const monthFirstDayStr = this.formatDateLocal(monthFirstDay);
        
        // Находим элемент с первым днем месяца
        let monthElement = document.querySelector(`.calendar-day[data-date="${monthFirstDayStr}"]`);
        
        // Если не нашли первый день, ищем любой день этого месяца
        if (!monthElement) {
            const monthElements = document.querySelectorAll('.calendar-day[data-date]');
            for (let element of monthElements) {
                const elementDate = this.parseDateLocal(element.dataset.date);
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
    
    scrollToToday(onComplete = null) {
        const today = new Date();
        this.scrollToDate(today, onComplete);
    }
    
    /**
     * Прокручивает календарь к указанной дате
     * @param {Date} targetDate - Дата для прокрутки
     * @param {Function} onComplete - Callback после завершения прокрутки
     */
    scrollToDate(targetDate, onComplete = null) {
        const dateString = this.formatDateLocal(targetDate); // YYYY-MM-DD format
        
        const dateElement = document.querySelector(`.calendar-day[data-date="${dateString}"]`);
        if (!dateElement) {
            if (typeof onComplete === 'function') {
                onComplete();
            }
            return;
        }
        
        const scrollableContainer = document.querySelector('.calendar-scrollable');
        if (!scrollableContainer) {
            if (typeof onComplete === 'function') {
                onComplete();
            }
            return;
        }
        
        const containerRect = scrollableContainer.getBoundingClientRect();
        const elementRect = dateElement.getBoundingClientRect();
        
        const elementTop = elementRect.top - containerRect.top + scrollableContainer.scrollTop;
        const containerHeight = scrollableContainer.clientHeight;
        const elementHeight = elementRect.height;
        
        const scrollTo = elementTop - (containerHeight / 2) + (elementHeight / 2);
        
        scrollableContainer.scrollTo({
            top: Math.max(0, scrollTo),
            behavior: 'smooth'
        });

        if (typeof onComplete === 'function') {
            setTimeout(onComplete, 100);
        }
    }
    
    filterByObject(objectId) {
        console.log('filterByObject called with:', objectId);
        
        // Получаем текущие параметры из URL
        const currentSearch = window.location.search;
        const params = new URLSearchParams(currentSearch);
        
        if (objectId) {
            params.set('object_id', objectId);
        } else {
            params.delete('object_id');
        }
        
        const newSearch = params.toString();
        const newUrl = newSearch ? `${window.location.pathname}?${newSearch}` : window.location.pathname;
        
        console.log('Filtering by object:', objectId, 'New URL:', newUrl);
        
        // Перезагружаем страницу с новыми параметрами
        window.location.href = newUrl;
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
    
    refresh(targetDate = null) {
        // Перезагрузить данные календаря
        console.log('[UniversalCalendar] Refreshing calendar data...', targetDate ? `targetDate: ${targetDate}` : '');
        
        // Если мы в дневном виде на мобильном, обновляем дневной вид
        if (this.viewMode === 'day' && this.isMobile) {
            const dateToShow = targetDate ? new Date(targetDate) : this.currentDate;
            this.renderDayView(dateToShow);
            return;
        }
        
        // Определяем видимый месяц
        const visibleMonth = this.getVisibleMonthFromScroll();
        if (visibleMonth) {
            // Очищаем кэш для видимого месяца и соседних месяцев, чтобы принудительно перезагрузить
            const monthKey = `${visibleMonth.year}-${visibleMonth.month}`;
            this.loadedMonths.delete(monthKey);
            
            // Очищаем кэш для предыдущего и следующего месяцев
            const prevMonth = new Date(visibleMonth.year, visibleMonth.month - 2, 1);
            const nextMonth = new Date(visibleMonth.year, visibleMonth.month, 1);
            const prevMonthKey = `${prevMonth.getFullYear()}-${prevMonth.getMonth() + 1}`;
            const nextMonthKey = `${nextMonth.getFullYear()}-${nextMonth.getMonth() + 1}`;
            this.loadedMonths.delete(prevMonthKey);
            this.loadedMonths.delete(nextMonthKey);
            
            // Устанавливаем currentDate на видимый месяц для корректной загрузки
            const visibleDate = new Date(visibleMonth.year, visibleMonth.month - 1, 1);
            this.currentDate = visibleDate;
        } else {
            // Если не удалось определить видимый месяц, очищаем весь кэш
            this.loadedMonths.clear();
        }
        
        // Очищаем calendarData, чтобы принудительно перезагрузить
        this.calendarData = null;
        
        // Сохраняем целевую дату для позиционирования после загрузки
        this._refreshTargetDate = targetDate ? new Date(targetDate) : null;
        
        // Загружаем данные с учетом фильтра из URL
        this.loadCalendarData(null, null, null, true).then(() => {
            // После загрузки позиционируемся на целевую дату (или текущую, если не указана)
            if (this._refreshTargetDate) {
                setTimeout(() => {
                    this.scrollToDate(this._refreshTargetDate);
                    this._refreshTargetDate = null;
                }, 300);
            } else {
                // Если целевая дата не указана, позиционируемся на сегодня
                setTimeout(() => {
                    this.scrollToToday();
                }, 300);
            }
        });
    }
    
    /**
     * Вычисляет длительность тайм-слота в минутах
     * @param {Object} timeslot - Тайм-слот
     * @returns {number} Длительность в минутах
     */
    getTimeslotDuration(timeslot) {
        if (!timeslot.start_time || !timeslot.end_time) {
            return 0;
        }
        const start = this.timeStringToMinutes(timeslot.start_time);
        const end = this.timeStringToMinutes(timeslot.end_time);
        return Math.max(0, end - start);
    }
    
    /**
     * Преобразует строку времени в минуты
     * @param {string} timeStr - Время в формате "HH:MM"
     * @returns {number} Количество минут от начала дня
     */
    timeStringToMinutes(timeStr) {
        if (!timeStr) return 0;
        const parts = timeStr.split(':');
        if (parts.length < 2) return 0;
        const hours = parseInt(parts[0], 10) || 0;
        const minutes = parseInt(parts[1], 10) || 0;
        return hours * 60 + minutes;
    }
    
    /**
     * Вычисляет доступные интервалы времени в тайм-слоте
     * @param {Object} timeslot - Тайм-слот
     * @param {Array} shifts - Массив смен в тайм-слоте
     * @returns {Array} Массив доступных интервалов [{start, end, startMinutes, endMinutes}, ...]
     */
    calculateAvailableIntervals(timeslot, shifts) {
        if (!shifts || shifts.length === 0) {
            // Если смен нет, весь тайм-слот доступен
            const startMinutes = this.timeStringToMinutes(timeslot.start_time);
            const endMinutes = this.timeStringToMinutes(timeslot.end_time);
            return [{
                start: timeslot.start_time,
                end: timeslot.end_time,
                startMinutes: startMinutes,
                endMinutes: endMinutes
            }];
        }
        
        // Получаем время начала и конца тайм-слота
        const slotStartMinutes = this.timeStringToMinutes(timeslot.start_time);
        const slotEndMinutes = this.timeStringToMinutes(timeslot.end_time);
        
        // Собираем все занятые интервалы из смен
        const occupiedIntervals = [];
        shifts.forEach(shift => {
            let shiftStart = shift.start_time || shift.planned_start_time || shift.planned_start;
            let shiftEnd = shift.end_time || shift.planned_end_time || shift.planned_end;
            
            // Если время в формате ISO, извлекаем только время
            if (shiftStart) {
                if (typeof shiftStart === 'string' && shiftStart.includes('T')) {
                    shiftStart = shiftStart.split('T')[1].substring(0, 5);
                } else if (typeof shiftStart === 'string' && shiftStart.includes(' ')) {
                    // Если формат "YYYY-MM-DD HH:MM:SS" или "YYYY-MM-DD HH:MM:SS+00"
                    const timePart = shiftStart.split(' ')[1];
                    shiftStart = timePart ? timePart.substring(0, 5) : shiftStart;
                }
            }
            if (shiftEnd) {
                if (typeof shiftEnd === 'string' && shiftEnd.includes('T')) {
                    shiftEnd = shiftEnd.split('T')[1].substring(0, 5);
                } else if (typeof shiftEnd === 'string' && shiftEnd.includes(' ')) {
                    // Если формат "YYYY-MM-DD HH:MM:SS" или "YYYY-MM-DD HH:MM:SS+00"
                    const timePart = shiftEnd.split(' ')[1];
                    shiftEnd = timePart ? timePart.substring(0, 5) : shiftEnd;
                }
            }
            
            if (shiftStart && shiftEnd) {
                const startMinutes = this.timeStringToMinutes(shiftStart);
                const endMinutes = this.timeStringToMinutes(shiftEnd);
                occupiedIntervals.push({
                    start: shiftStart,
                    end: shiftEnd,
                    startMinutes: startMinutes,
                    endMinutes: endMinutes
                });
            }
        });
        
        // Сортируем занятые интервалы по времени начала
        occupiedIntervals.sort((a, b) => a.startMinutes - b.startMinutes);
        
        // Вычисляем доступные интервалы
        const availableIntervals = [];
        let currentTime = slotStartMinutes;
        
        occupiedIntervals.forEach(occupied => {
            // Если есть промежуток до начала занятого интервала
            if (currentTime < occupied.startMinutes) {
                const startTime = this.minutesToTimeString(currentTime);
                const endTime = this.minutesToTimeString(occupied.startMinutes);
                availableIntervals.push({
                    start: startTime,
                    end: endTime,
                    startMinutes: currentTime,
                    endMinutes: occupied.startMinutes
                });
            }
            // Обновляем текущее время на конец занятого интервала
            currentTime = Math.max(currentTime, occupied.endMinutes);
        });
        
        // Добавляем оставшийся интервал после последней занятой смены
        if (currentTime < slotEndMinutes) {
            const startTime = this.minutesToTimeString(currentTime);
            const endTime = this.minutesToTimeString(slotEndMinutes);
            availableIntervals.push({
                start: startTime,
                end: endTime,
                startMinutes: currentTime,
                endMinutes: slotEndMinutes
            });
        }
        
        return availableIntervals;
    }
    
    /**
     * Преобразует минуты в строку времени
     * @param {number} minutes - Количество минут от начала дня
     * @returns {string} Время в формате "HH:MM"
     */
    minutesToTimeString(minutes) {
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
    }
    
    /**
     * Форматирует минуты в строку вида "X ч Y м"
     * @param {number} minutes - Количество минут
     * @returns {string} Отформатированная строка
     */
    formatMinutes(minutes) {
        if (!minutes || minutes <= 0) {
            return '0 м';
        }
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        const parts = [];
        if (hours > 0) {
            parts.push(`${hours} ч`);
        }
        if (mins > 0 || parts.length === 0) {
            parts.push(`${mins} м`);
        }
        return parts.join(' ');
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UniversalCalendarManager;
}
