let currentShiftId = null;
let currentShiftType = null;
let currentSortField = null;
let currentSortOrder = 'asc';
let dateRangePicker = null;

// Переменные для выбора дат
let startDate = null;
let endDate = null;
let isSelectingStart = true;

// Переключение фильтров
function toggleFilters() {
    const filtersCard = document.getElementById('filtersCard');
    const toggleBtn = document.getElementById('toggleFiltersBtn');
    
    if (filtersCard.style.display === 'none') {
        filtersCard.style.display = 'block';
        toggleBtn.innerHTML = '<i class="bi bi-funnel-fill"></i> Скрыть фильтры';
    } else {
        // Только при явном нажатии кнопки "Скрыть фильтры"
        clearAllFiltersAndRedirect();
    }
}

// Очистка всех фильтров и перенаправление
function clearAllFiltersAndRedirect() {
    const url = new URL(window.location);
    url.search = ''; // Очищаем все параметры
    window.location.href = url.toString();
}

// Очистка всех фильтров
function clearAllFilters() {
    document.getElementById('status').value = '';
    document.getElementById('object_id').value = '';
    document.getElementById('dateRange').value = '';
    document.getElementById('date_from').value = '';
    document.getElementById('date_to').value = '';
    startDate = null;
    endDate = null;
}

// Инициализация выбора диапазона дат
function initializeDateRangePicker() {
    const dateRangeInput = document.getElementById('dateRange');
    const dateFromInput = document.getElementById('date_from');
    const dateToInput = document.getElementById('date_to');
    const clearBtn = document.getElementById('clearDateRange');
    
    // Устанавливаем начальные значения если есть
    const dateFrom = dateFromInput.value;
    const dateTo = dateToInput.value;
    
    if (dateFrom && dateTo) {
        // Используем строки напрямую - никаких проблем с временными зонами!
        dateRangeInput.value = `${formatDate(dateFrom)} - ${formatDate(dateTo)}`;
    }
    
    // Обработчик клика по полю ввода даты
    dateRangeInput.addEventListener('click', function() {
        if (!dateRangePicker) {
            createDateRangePicker();
        }
        dateRangePicker.show();
    });
    
    // Обработчик очистки
    clearBtn.addEventListener('click', function() {
        dateRangeInput.value = '';
        dateFromInput.value = '';
        dateToInput.value = '';
        startDate = null;
        endDate = null;
    });
}

// Создание календаря для выбора диапазона дат
function createDateRangePicker() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'dateRangeModal';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Выберите период</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div id="datePickerHint" class="alert alert-info">
                        Выберите дату начала
                    </div>
                    <div id="calendarContainer"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                    <button type="button" class="btn btn-primary" id="confirmDateRange">Применить</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const bootstrapModal = new bootstrap.Modal(modal);
    dateRangePicker = bootstrapModal;
    
    // Создаем красивый календарь
    createBeautifulCalendar();
    
    // Обработчик подтверждения
    modal.querySelector('#confirmDateRange').addEventListener('click', function() {
        if (startDate && endDate) {
            dateRangeInput.value = `${formatDate(startDate)} - ${formatDate(endDate)}`;
            dateFromInput.value = formatDateForInput(startDate);
            dateToInput.value = formatDateForInput(endDate);
        }
        bootstrapModal.hide();
    });
    
    // Обработчик закрытия модального окна
    modal.addEventListener('hidden.bs.modal', function() {
        document.body.removeChild(modal);
        dateRangePicker = null;
    });
}

// Создание красивого календаря
function createBeautifulCalendar() {
    const container = document.getElementById('calendarContainer');
    const today = new Date();
    const currentYear = today.getFullYear();
    const currentMonth = today.getMonth();
    
    let html = `
        <div class="calendar-header d-flex justify-content-between align-items-center mb-3">
            <button class="btn btn-outline-primary calendar-nav-btn" onclick="changeMonth(-1)">
                <i class="bi bi-chevron-left"></i>
            </button>
            <h5 class="mb-0" id="currentMonthYear">${getMonthName(currentMonth)} ${currentYear}</h5>
            <button class="btn btn-outline-primary calendar-nav-btn" onclick="changeMonth(1)">
                <i class="bi bi-chevron-right"></i>
            </button>
        </div>
        <div class="calendar-grid">
            <div class="calendar-weekdays">
                <div class="weekday">Пн</div>
                <div class="weekday">Вт</div>
                <div class="weekday">Ср</div>
                <div class="weekday">Чт</div>
                <div class="weekday">Пт</div>
                <div class="weekday">Сб</div>
                <div class="weekday">Вс</div>
            </div>
            <div class="calendar-days">
    `;
    
    const firstDay = new Date(currentYear, currentMonth, 1);
    const lastDay = new Date(currentYear, currentMonth + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay() + 1);
    
    for (let i = 0; i < 42; i++) {
        const date = new Date(startDate);
        date.setDate(startDate.getDate() + i);
        
        const isCurrentMonth = date.getMonth() === currentMonth;
        const isToday = date.toDateString() === today.toDateString();
        
        html += `
            <div class="calendar-day ${isCurrentMonth ? '' : 'disabled'} ${isToday ? 'today' : ''}" 
                 data-date="${String(date.getFullYear()).padStart(4, '0')}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}">
                ${date.getDate()}
            </div>
        `;
    }
    
    html += `
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Добавляем обработчики кликов
    container.querySelectorAll('.calendar-day').forEach(cell => {
        cell.addEventListener('click', function() {
            if (this.classList.contains('disabled')) return;
            
            const dateString = cell.dataset.date; // "2025-10-01"
            if (isSelectingStart) {
                startDate = dateString;
                endDate = null;
                isSelectingStart = false;
                updateCalendarDisplay();
                document.getElementById('datePickerHint').textContent = 'Выберите дату окончания';
            } else {
                if (dateString < startDate) { // String comparison works for YYYY-MM-DD
                    endDate = startDate;
                    startDate = dateString;
                } else {
                    endDate = dateString;
                }
                updateCalendarDisplay();
                document.getElementById('datePickerHint').textContent = 'Период выбран';
            }
        });
    });
    
    // Добавляем стили
    addCalendarStyles();
}

// Добавление стилей для календаря
function addCalendarStyles() {
    if (document.getElementById('calendarStyles')) return;
    
    const style = document.createElement('style');
    style.id = 'calendarStyles';
    style.textContent = `
        .calendar-grid {
            border: 1px solid #dee2e6;
            border-radius: 8px;
            overflow: hidden;
        }
        .calendar-weekdays {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        .weekday {
            padding: 12px 8px;
            text-align: center;
            font-weight: 600;
            color: #6c757d;
            font-size: 0.875rem;
        }
        .calendar-days {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
        }
        .calendar-day {
            padding: 12px 8px;
            text-align: center;
            cursor: pointer;
            border-right: 1px solid #dee2e6;
            border-bottom: 1px solid #dee2e6;
            transition: all 0.2s ease;
            min-height: 45px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .calendar-day:hover {
            background-color: #e9ecef;
        }
        .calendar-day.disabled {
            color: #adb5bd;
            cursor: not-allowed;
        }
        .calendar-day.today {
            background-color: #007bff;
            color: white;
            font-weight: bold;
        }
        .calendar-day.range-start,
        .calendar-day.range-end {
            background-color: #007bff;
            color: white;
            font-weight: bold;
        }
        .calendar-day.in-range {
            background-color: #cce7ff;
        }
        .calendar-nav-btn {
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
    `;
    document.head.appendChild(style);
}

// Обновление отображения календаря
function updateCalendarDisplay() {
    const cells = document.querySelectorAll('.calendar-day');
    
    cells.forEach(cell => {
        cell.classList.remove('range-start', 'range-end', 'in-range');
        
        // Using strings for comparison - no timezone issues!
        const cellDateString = cell.dataset.date;
        if (startDate && cellDateString === startDate) {
            cell.classList.add('range-start');
        }
        if (endDate && cellDateString === endDate) {
            cell.classList.add('range-end');
        }
        if (startDate && endDate && cellDateString > startDate && cellDateString < endDate) {
            cell.classList.add('in-range');
        }
    });
}

// Форматирование даты для отображения
function formatDate(dateString) {
    const [year, month, day] = dateString.split('-');
    return `${day}.${month}.${year}`;
}

// Форматирование даты для input
function formatDateForInput(dateString) {
    return dateString; // Already in YYYY-MM-DD format
}

// Получение названия месяца
function getMonthName(monthIndex) {
    const months = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ];
    return months[monthIndex];
}

// Смена месяца в календаре
function changeMonth(direction) {
    // Простая реализация - пересоздаем календарь
    createBeautifulCalendar();
}

// Инициализация сортировки
function initializeSorting() {
    // Инициализируем текущие параметры сортировки из URL
    const url = new URL(window.location);
    currentSortField = url.searchParams.get('sort');
    currentSortOrder = url.searchParams.get('order') || 'asc';
    
    // Обновляем иконки сортировки для текущего поля
    if (currentSortField) {
        updateSortIcons(currentSortField, currentSortOrder);
    }
    
    const sortableHeaders = document.querySelectorAll('.sortable');
    
    sortableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const sortField = this.dataset.sort;
            sortTable(sortField);
        });
    });
}

// Сортировка таблицы
function sortTable(field) {
    const url = new URL(window.location);
    
    if (currentSortField === field) {
        currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortField = field;
        currentSortOrder = 'asc';
    }
    
    url.searchParams.set('sort', field);
    url.searchParams.set('order', currentSortOrder);
    
    // Обновляем иконки сортировки
    updateSortIcons(field, currentSortOrder);
    
    // Переходим на новую страницу с параметрами сортировки
    window.location.href = url.toString();
}

// Обновление иконок сортировки
function updateSortIcons(field, order) {
    const sortIcons = document.querySelectorAll('.sort-icon');
    sortIcons.forEach(icon => {
        icon.className = 'bi bi-arrow-down-up ms-1 sort-icon';
    });
    
    const currentHeader = document.querySelector(`[data-sort="${field}"] .sort-icon`);
    if (currentHeader) {
        currentHeader.className = `bi bi-arrow-${order === 'asc' ? 'up' : 'down'} ms-1 sort-icon text-primary`;
    }
}

// Инициализация фильтров
function initializeFilters() {
    initializeDateRangePicker();
    initializeSorting();
    
    // Обработчик отправки формы фильтров
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            // Не закрываем панель фильтров при отправке формы
            // Панель должна оставаться открытой
        });
    }
}

// Отмена смены
function cancelShift(shiftId, shiftType) {
    currentShiftId = shiftId;
    currentShiftType = shiftType;
    const modal = new bootstrap.Modal(document.getElementById('cancelModal'));
    modal.show();
}

document.getElementById('confirmCancel').addEventListener('click', async function() {
    if (!currentShiftId || !currentShiftType) return;
    
    try {
        const response = await fetch(`/owner/shifts/${currentShiftId}/cancel?shift_type=${currentShiftType}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Показываем уведомление об успехе
            showNotification(result.message, 'success');
            // Перезагружаем страницу
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showNotification(result.error || 'Ошибка отмены смены', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Ошибка отмены смены', 'error');
    }
    
    // Закрываем модальное окно
    const modal = bootstrap.Modal.getInstance(document.getElementById('cancelModal'));
    modal.hide();
});

function refreshData() {
    window.location.reload();
}

function showNotification(message, type) {
    // Создаем уведомление
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    const icon = type === 'success' ? 'bi-check-circle' : 'bi-exclamation-triangle';
    
    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        <i class="bi ${icon}"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initializeFilters();
});

// ===== ФУНКЦИОНАЛ ПЛАНИРОВАНИЯ СМЕН ДЛЯ ВЛАДЕЛЬЦА =====

// Глобальные переменные для планирования смен
let availableTimeslots = [];
let selectedTimeslots = new Set();
let currentMonth = new Date().getMonth();
let currentYear = new Date().getFullYear();

// Показать модальное окно планирования
function showPlanShiftModal() {
    const modal = new bootstrap.Modal(document.getElementById('planShiftModal'));
    modal.show();
    
    // Ждем, пока модальное окно полностью откроется
    setTimeout(() => {
        loadPlanShiftObjects();
        // Создаем пустой календарь сразу
        createEmptyCalendar();
        // Инициализируем счетчик
        updateSelectedSlotsInfo();
    }, 300);
}

// Загрузка объектов для планирования
async function loadPlanShiftObjects() {
    try {
        const response = await fetch('/owner/calendar/api/objects');
        const objects = await response.json();
        
        const select = document.getElementById('planObjectSelect');
        select.innerHTML = '<option value="">Выберите объект</option>';
        
        if (Array.isArray(objects)) {
            objects.forEach(obj => {
                const option = document.createElement('option');
                option.value = obj.id;
                option.textContent = obj.name;
                select.appendChild(option);
            });
        }
        
                // Обработчик изменения объекта
                select.addEventListener('change', function() {
                    if (this.value) {
                        loadEmployeesForObject(this.value);
                        // Очищаем календарь при смене объекта
                        clearCalendar();
                        // Обновляем счетчик после очистки
                        setTimeout(() => updateSelectedSlotsInfo(), 100);
                    } else {
                        clearCalendar();
                        clearEmployees();
                        // Обновляем счетчик после очистки
                        setTimeout(() => updateSelectedSlotsInfo(), 100);
                    }
                });
        
    } catch (error) {
        console.error('Ошибка загрузки объектов:', error);
    }
}

// Загрузка сотрудников для конкретного объекта
async function loadEmployeesForObject(objectId) {
    try {
        const response = await fetch(`/owner/api/employees/for-object/${objectId}`);
        const employees = await response.json();
        
        const select = document.getElementById('planEmployeeSelect');
        select.innerHTML = '<option value="">Выберите сотрудника</option>';
        
        if (Array.isArray(employees)) {
            employees.forEach(emp => {
                const option = document.createElement('option');
                option.value = emp.id;
                option.textContent = emp.name;
                select.appendChild(option);
            });
        }
        
        // Обработчик изменения сотрудника
        select.addEventListener('change', function() {
            const objectId = document.getElementById('planObjectSelect').value;
            if (this.value && objectId) {
                loadTimeslotsForObject(objectId);
            } else {
                clearCalendar();
                // Обновляем счетчик после очистки
                setTimeout(() => updateSelectedSlotsInfo(), 100);
            }
        });
        
    } catch (error) {
        console.error('Ошибка загрузки сотрудников для объекта:', error);
    }
}

// Очистка списка сотрудников
function clearEmployees() {
    const select = document.getElementById('planEmployeeSelect');
    select.innerHTML = '<option value="">Выберите сотрудника</option>';
}

// Создание пустого календаря
function createEmptyCalendar() {
    const calendarEl = document.getElementById('planShiftCalendar');
    const firstDay = new Date(currentYear, currentMonth, 1);
    const lastDay = new Date(currentYear, currentMonth + 1, 0);
    
    // Правильное вычисление первого понедельника недели
    const firstMonday = new Date(firstDay);
    firstMonday.setDate(firstDay.getDate() - firstDay.getDay() + 1);
    
    const daysOfWeek = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    
    let html = `
        <div class="calendar-weekdays">
            ${daysOfWeek.map(day => `<div class="calendar-weekday">${day}</div>`).join('')}
        </div>
        <div class="calendar-days">
    `;
    
    for (let i = 0; i < 42; i++) {
        const date = new Date(firstMonday);
        date.setDate(firstMonday.getDate() + i);
        
        const isCurrentMonth = date.getMonth() === currentMonth;
        const dateStr = formatDateForAPI(date);
        
        html += `
            <div class="calendar-day ${isCurrentMonth ? '' : 'disabled'}" data-date="${dateStr}">
                <div class="day-number">${date.getDate()}</div>
                <div class="empty-message">Выберите сотрудника</div>
            </div>
        `;
    }
    
    html += '</div>';
    calendarEl.innerHTML = html;
}

// Очистка календаря
function clearCalendar() {
    createEmptyCalendar();
    availableTimeslots = [];
    selectedTimeslots.clear();
    // Не вызываем updateSelectedSlotsInfo здесь, так как модальное окно может быть не готово
}

// Загрузка тайм-слотов для объекта
async function loadTimeslotsForObject(objectId) {
    try {
        const today = new Date();
        const startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        const endDate = new Date(today.getFullYear(), today.getMonth() + 2, 0);
        
        const response = await fetch(`/owner/calendar/api/data?start_date=${formatDateForAPI(startDate)}&end_date=${formatDateForAPI(endDate)}&object_ids=${objectId}`);
        const data = await response.json();
        
        availableTimeslots = data.timeslots || [];
        updateCalendar();
        
    } catch (error) {
        console.error('Ошибка загрузки тайм-слотов:', error);
        alert('Ошибка загрузки тайм-слотов: ' + error.message);
    }
}

// Форматирование даты для API
function formatDateForAPI(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Обновление календаря
function updateCalendar() {
    const calendarEl = document.getElementById('planShiftCalendar');
    const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                       'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
    
    document.getElementById('calendarMonthYear').textContent = `${monthNames[currentMonth]} ${currentYear}`;
    
    // Создаем календарь
    createPlanShiftCalendar();
}

// Создание календаря планирования
function createPlanShiftCalendar() {
    const calendarEl = document.getElementById('planShiftCalendar');
    const firstDay = new Date(currentYear, currentMonth, 1);
    const lastDay = new Date(currentYear, currentMonth + 1, 0);
    
    // Правильное вычисление первого понедельника недели
    const firstMonday = new Date(firstDay);
    firstMonday.setDate(firstDay.getDate() - firstDay.getDay() + 1);
    
    const daysOfWeek = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    
    let html = `
        <div class="calendar-weekdays">
            ${daysOfWeek.map(day => `<div class="calendar-weekday">${day}</div>`).join('')}
        </div>
        <div class="calendar-days">
    `;
    
    for (let i = 0; i < 42; i++) {
        const date = new Date(firstMonday);
        date.setDate(firstMonday.getDate() + i);
        
        const isCurrentMonth = date.getMonth() === currentMonth;
        const dateStr = formatDateForAPI(date);
        const timeslotsForDate = availableTimeslots.filter(ts => {
            const tsDate = ts.date || ts.slot_date || ts.start_date;
            return tsDate === dateStr;
        });
        
        let dayClass = 'calendar-day';
        if (!isCurrentMonth) {
            dayClass += ' disabled';
        } else if (timeslotsForDate.length > 0) {
            dayClass += ' has-timeslots';
        }
        
        html += `<div class="${dayClass}" data-date="${dateStr}">`;
        html += `<div class="day-number">${date.getDate()}</div>`;
        
        if (isCurrentMonth && timeslotsForDate.length > 0) {
            // Отображаем только доступные тайм-слоты
            const availableSlots = timeslotsForDate.filter(ts => (ts.available_slots || 0) > 0);
            
            if (availableSlots.length > 0) {
                availableSlots.forEach((ts, index) => {
                    const startTime = ts.start_time || ts.start_time_str || '09:00';
                    const endTime = ts.end_time || ts.end_time_str || '21:00';
                    const availableSlotsCount = ts.available_slots || 0;
                    const maxSlots = ts.max_employees || 1;
                    
                    html += `<div class="timeslot available" data-timeslot-id="${ts.id}">`;
                    html += `<div class="timeslot-time">${startTime}-${endTime}</div>`;
                    html += `<div class="timeslot-slots">${availableSlotsCount}/${maxSlots}</div>`;
                    html += '</div>';
                });
            } else {
                html += '<div class="no-slots">Нет свободных слотов</div>';
            }
        } else if (isCurrentMonth) {
            html += '<div class="empty-message">Нет тайм-слотов</div>';
        }
        
        html += '</div>';
    }
    
    html += '</div>';
    
    // Добавляем информацию об объекте
    const objectSelect = document.getElementById('planObjectSelect');
    const selectedObject = objectSelect.options[objectSelect.selectedIndex];
    if (selectedObject && selectedObject.value) {
        html += `<div class="mt-3 text-center"><small class="text-muted">Объект: <strong>${selectedObject.text}</strong></small></div>`;
    }
    
    calendarEl.innerHTML = html;
    
    // Добавляем обработчики кликов (убираем старые)
    calendarEl.removeEventListener('click', handleTimeslotClick);
    calendarEl.addEventListener('click', handleTimeslotClick);
}

// Обработка клика по тайм-слоту
async function handleTimeslotClick(e) {
    const timeslot = e.target.closest('.timeslot');
    if (!timeslot || !timeslot.classList.contains('available')) {
        return;
    }
    
    const timeslotId = timeslot.dataset.timeslotId;
    const day = timeslot.closest('.calendar-day');
    const date = day.dataset.date;
    
    const employeeId = document.getElementById('planEmployeeSelect').value;
    if (!employeeId) {
        alert('Сначала выберите сотрудника');
        return;
    }
    
    // Проверяем доступность сотрудника
    const isAvailable = await checkEmployeeAvailability(employeeId, timeslotId);
    
    if (isAvailable) {
        // Переключаем выбор
        const slotKey = `${date}_${timeslotId}`;
        
        if (selectedTimeslots.has(slotKey)) {
            selectedTimeslots.delete(slotKey);
            timeslot.classList.remove('selected');
        } else {
            selectedTimeslots.add(slotKey);
            timeslot.classList.add('selected');
        }
        // Обновляем счетчик с задержкой, чтобы DOM успел обновиться
        setTimeout(() => updateSelectedSlotsInfo(), 100);
    }
}

// Проверка доступности сотрудника
async function checkEmployeeAvailability(employeeId, timeslotId) {
    try {
        // Отправляем запрос на проверку доступности
        const response = await fetch('/owner/api/calendar/check-availability', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                timeslot_id: parseInt(timeslotId),
                employee_id: parseInt(employeeId)
            })
        });
        
        const result = await response.json();
        
        if (result.available) {
            return true;
        } else {
            // Формируем более информативное сообщение
            let message = result.message || 'Сотрудник недоступен в это время';
            
            // Если есть информация о конфликтующей смене
            if (result.conflict_info) {
                const conflict = result.conflict_info;
                message = `Сотрудник в это время работает на объекте "${conflict.object_name}" с ${conflict.start_time} до ${conflict.end_time}`;
            }
            
            alert(message);
            return false;
        }
        
    } catch (error) {
        console.error('Ошибка проверки доступности:', error);
        alert('Ошибка проверки доступности сотрудника');
        return false;
    }
}

// Обновление информации о выбранных слотах
function updateSelectedSlotsInfo() {
    const count = selectedTimeslots.size;
    
    // Ищем элементы внутри модального окна
    const modal = document.getElementById('planShiftModal');
    if (!modal) {
        return;
    }
    
    const infoEl = modal.querySelector('#selectedSlotsInfo');
    const countEl = modal.querySelector('#selectedSlotsCount');
    const confirmBtn = modal.querySelector('#confirmPlanShift');
    
    if (!infoEl || !confirmBtn) {
        return;
    }
    
    // Если countEl не найден, создаем его
    if (!countEl) {
        // Создаем полную структуру alert div
        infoEl.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-check-circle"></i>
                Выбрано тайм-слотов: <span id="selectedSlotsCount">0</span>
            </div>
        `;
    }
    
    // Получаем countEl снова после возможного создания
    const finalCountEl = modal.querySelector('#selectedSlotsCount');
    if (!finalCountEl) {
        return;
    }
    
    if (count > 0) {
        infoEl.style.display = 'block';
        finalCountEl.textContent = count;
        confirmBtn.disabled = false;
    } else {
        infoEl.style.display = 'none';
        confirmBtn.disabled = true;
    }
}

// Подтверждение планирования смен
async function confirmPlanShift() {
    const objectId = document.getElementById('planObjectSelect').value;
    const employeeId = document.getElementById('planEmployeeSelect').value;
    
    if (!objectId || !employeeId || selectedTimeslots.size === 0) {
        alert('Выберите объект, сотрудника и тайм-слоты');
        return;
    }
    
    const confirmBtn = document.getElementById('confirmPlanShift');
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Планирование...';
    
    let successCount = 0;
    let errorCount = 0;
    
    for (const slotKey of selectedTimeslots) {
        try {
            const [date, timeslotId] = slotKey.split('_');
            const timeslot = availableTimeslots.find(ts => ts.id == timeslotId);
            
            if (!timeslot) continue;
            
            const response = await fetch('/owner/api/calendar/plan-shift', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    timeslot_id: parseInt(timeslotId),
                    employee_id: parseInt(employeeId)
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                successCount++;
            } else {
                errorCount++;
                console.error('Ошибка планирования:', result.message);
            }
            
        } catch (error) {
            errorCount++;
            console.error('Ошибка планирования смены:', error);
        }
    }
    
    // Восстанавливаем кнопку
    confirmBtn.disabled = false;
    confirmBtn.innerHTML = '<i class="bi bi-calendar-check"></i> Запланировать смены';
    
    // Показываем результат
    if (successCount > 0) {
        showNotification(`Успешно запланировано смен: ${successCount}${errorCount > 0 ? `, ошибок: ${errorCount}` : ''}`, 'success');
        // Закрываем модальное окно
        const modal = bootstrap.Modal.getInstance(document.getElementById('planShiftModal'));
        modal.hide();
        // Обновляем страницу
        refreshData();
    } else {
        showNotification('Не удалось запланировать ни одной смены', 'error');
    }
}

// Обработчики навигации по месяцам
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('prevMonth')?.addEventListener('click', function() {
        currentMonth--;
        if (currentMonth < 0) {
            currentMonth = 11;
            currentYear--;
        }
        updateCalendar();
    });
    
    document.getElementById('nextMonth')?.addEventListener('click', function() {
        currentMonth++;
        if (currentMonth > 11) {
            currentMonth = 0;
            currentYear++;
        }
        updateCalendar();
    });
    
    document.getElementById('confirmPlanShift')?.addEventListener('click', confirmPlanShift);
});
