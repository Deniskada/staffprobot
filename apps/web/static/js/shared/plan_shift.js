(() => {
  const config = window.planShiftConfig || null;
  if (!config) {
    console.error('planShiftConfig is not defined. Skip plan_shift.js initialization.');
    return;
  }

  const DEFAULT_API_BASE = '/owner';

  const settings = {
    apiBase: config.apiBase || DEFAULT_API_BASE,
    calendarDataEndpoint: config.calendarDataEndpoint || `${config.apiBase || DEFAULT_API_BASE}/calendar/api/data`,
    employeesEndpointBase: config.employeesEndpointBase || `${config.apiBase || DEFAULT_API_BASE}/api/employees/for-object`,
    checkAvailabilityEndpoint: config.checkAvailabilityEndpoint || `${config.apiBase || DEFAULT_API_BASE}/api/calendar/check-availability`,
    planShiftEndpoint: config.planShiftEndpoint || `${config.apiBase || DEFAULT_API_BASE}/api/calendar/plan-shift`,
    cancelScheduledShiftBase: config.cancelScheduledShiftBase || `${config.apiBase || DEFAULT_API_BASE}/shifts_legacy`,
    returnToUrl: config.returnToUrl || null,
    selectedObjectId: (config.selectedObjectId !== undefined && config.selectedObjectId !== null && config.selectedObjectId !== 'null')
      ? Number(config.selectedObjectId)
      : null,
    preselectedEmployeeId: config.preselectedEmployeeId ? Number(config.preselectedEmployeeId) : null,
    hideEmployeeSelect: Boolean(config.hideEmployeeSelect),
    allowCancelPlannedShifts: config.allowCancelPlannedShifts !== false,
    role: config.role || 'owner'
  };

  const state = {
    selectedTimeslots: new Set(),
    timeslotSelectionDetails: new Map(),
    availableTimeslots: [],
    calendarShifts: [],
    employeePlannedShifts: [],
    selectedPlannedShiftIds: new Set(),
    initialPlannedShiftIds: new Set(),
    currentEmployeeId: null,
    currentMonth: new Date().getMonth(),
    currentYear: new Date().getFullYear()
  };

  const DOM = {};

  document.addEventListener('DOMContentLoaded', () => {
    DOM.objectSelect = document.getElementById('planObjectSelect');
    DOM.employeeSelect = document.getElementById('planEmployeeSelect');
    DOM.calendarContainer = document.getElementById('planShiftCalendar');
    DOM.monthLabel = document.getElementById('calendarMonthYear');
    DOM.prevBtn = document.getElementById('prevMonth');
    DOM.nextBtn = document.getElementById('nextMonth');
    DOM.confirmBtn = document.getElementById('confirmPlanShift');
    DOM.selectedInfo = document.getElementById('selectedSlotsInfo');
    DOM.selectedTimeslotsCount = document.getElementById('selectedTimeslotsCount');
    DOM.selectedPlannedCount = document.getElementById('selectedPlannedCount');
    DOM.cancelPlannedCount = document.getElementById('cancelPlannedCount');
    DOM.cancelInfoLine = document.getElementById('cancelInfoLine');

    if (!DOM.calendarContainer) {
      console.error('planShiftCalendar element not found. Abort plan_shift.js initialization.');
      return;
    }

    if (settings.selectedObjectId && DOM.objectSelect) {
      DOM.objectSelect.value = String(settings.selectedObjectId);
    }

    if (settings.hideEmployeeSelect && DOM.employeeSelect) {
      if (settings.preselectedEmployeeId !== null) {
        DOM.employeeSelect.value = String(settings.preselectedEmployeeId);
        state.currentEmployeeId = settings.preselectedEmployeeId;
      }
      DOM.employeeSelect.setAttribute('disabled', 'true');
    }

    createEmptyCalendar();
    updateSelectedSlotsInfo();

    DOM.prevBtn?.addEventListener('click', () => {
      state.currentMonth--;
      if (state.currentMonth < 0) {
        state.currentMonth = 11;
        state.currentYear--;
      }
      updateCalendar();
    });

    DOM.nextBtn?.addEventListener('click', () => {
      state.currentMonth++;
      if (state.currentMonth > 11) {
        state.currentMonth = 0;
        state.currentYear++;
      }
      updateCalendar();
    });

    DOM.objectSelect?.addEventListener('change', () => {
      const value = DOM.objectSelect.value;
      if (value) {
        state.selectedTimeslots.clear();
        state.timeslotSelectionDetails.clear();
        state.employeePlannedShifts = [];
        state.selectedPlannedShiftIds.clear();
        state.initialPlannedShiftIds.clear();
        if (!settings.hideEmployeeSelect) {
          state.currentEmployeeId = null;
          loadEmployeesForObject(value);
          clearCalendar(true);
        } else {
          loadTimeslotsForObject(value);
        }
      } else {
        state.selectedTimeslots.clear();
        state.timeslotSelectionDetails.clear();
        state.employeePlannedShifts = [];
        state.selectedPlannedShiftIds.clear();
        state.initialPlannedShiftIds.clear();
        clearCalendar(true);
        if (!settings.hideEmployeeSelect) {
          clearEmployees();
        }
      }
      updateSelectedSlotsInfo();
    });

    DOM.employeeSelect?.addEventListener('change', () => {
      const objectId = DOM.objectSelect?.value;
      if (DOM.employeeSelect.value && objectId) {
        state.currentEmployeeId = Number(DOM.employeeSelect.value);
        state.selectedTimeslots.clear();
        state.timeslotSelectionDetails.clear();
        state.employeePlannedShifts = [];
        state.selectedPlannedShiftIds.clear();
        state.initialPlannedShiftIds.clear();
        loadTimeslotsForObject(objectId);
      } else {
        state.currentEmployeeId = null;
        state.selectedTimeslots.clear();
        state.timeslotSelectionDetails.clear();
        state.employeePlannedShifts = [];
        state.selectedPlannedShiftIds.clear();
        state.initialPlannedShiftIds.clear();
        clearCalendar(true);
      }
      updateSelectedSlotsInfo();
    });

    DOM.confirmBtn?.addEventListener('click', confirmPlanShift);

    if (!settings.hideEmployeeSelect && settings.selectedObjectId) {
      loadEmployeesForObject(settings.selectedObjectId);
    } else {
      if (settings.selectedObjectId) {
        loadTimeslotsForObject(settings.selectedObjectId);
      }
      if (settings.hideEmployeeSelect && settings.preselectedEmployeeId !== null) {
        state.currentEmployeeId = settings.preselectedEmployeeId;
      }
    }
  });

  function buildCancelScheduleUrl(scheduleId) {
    if (settings.role === 'employee') {
      return settings.cancelScheduledShiftBase || null;
    }
    if (!settings.cancelScheduledShiftBase) {
      return null;
    }
    const base = settings.cancelScheduledShiftBase.replace(/\/$/, '');
    return `${base}/schedule_${scheduleId}/cancel`;
  }

  function createEmptyCalendar() {
    if (!DOM.calendarContainer) {
      return;
    }
    const firstDay = new Date(state.currentYear, state.currentMonth, 1);
    const firstMonday = new Date(firstDay);
    firstMonday.setDate(firstDay.getDate() - firstDay.getDay() + 1);
    const daysOfWeek = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    let html = `
        <div class="calendar-weekdays">
            ${daysOfWeek.map((day) => `<div class="calendar-weekday">${day}</div>`).join('')}
        </div>
        <div class="calendar-days">
    `;
    for (let i = 0; i < 35; i++) {
      const date = new Date(firstMonday);
      date.setDate(firstMonday.getDate() + i);
      const isCurrentMonth = date.getMonth() === state.currentMonth;
      const dateStr = formatDateForAPI(date);
      html += `
            <div class="calendar-day ${isCurrentMonth ? '' : 'disabled'}" data-date="${dateStr}">
                <div class="day-number">${date.getDate()}</div>
                <div class="empty-message">Выберите сотрудника</div>
            </div>
        `;
    }
    html += '</div>';
    DOM.calendarContainer.innerHTML = html;
  }

  function clearCalendar(resetPlanned = false) {
    createEmptyCalendar();
    state.availableTimeslots = [];
    state.selectedTimeslots.clear();
    state.timeslotSelectionDetails.clear();
    if (resetPlanned) {
      state.employeePlannedShifts = [];
      state.selectedPlannedShiftIds.clear();
      state.initialPlannedShiftIds.clear();
    }
  }

  function clearEmployees() {
    if (DOM.employeeSelect) {
      DOM.employeeSelect.innerHTML = '<option value="">Выберите сотрудника</option>';
    }
  }

  async function loadEmployeesForObject(objectId) {
    if (!DOM.employeeSelect || !settings.employeesEndpointBase || settings.hideEmployeeSelect) {
      return;
    }
    try {
      const response = await fetch(`${settings.employeesEndpointBase.replace(/\/$/, '')}/${objectId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const rawEmployees = await response.json();
      const normalizedEmployees = normalizeEmployeesResponse(rawEmployees);
      const activeEmployees = normalizedEmployees.filter((emp) => !emp.isFormer);
      const formerEmployees = normalizedEmployees.filter((emp) => emp.isFormer);

      let options = [];
      if (normalizedEmployees.length) {
        options.push('<option value="">Выберите сотрудника</option>');
        activeEmployees.forEach((emp) => {
          options.push(`<option value="${emp.id}">${escapeHtml(emp.name)}</option>`);
        });
        if (formerEmployees.length) {
          options.push('<option value="" disabled>— Бывшие —</option>');
          formerEmployees.forEach((emp) => {
            options.push(`<option value="${emp.id}">${escapeHtml(emp.name)} (бывший)</option>`);
          });
        }
      } else {
        options = ['<option value="">Нет доступных сотрудников</option>'];
      }

      DOM.employeeSelect.innerHTML = options.join('');

      if (settings.preselectedEmployeeId !== null) {
        const preselectedValue = String(settings.preselectedEmployeeId);
        DOM.employeeSelect.value = preselectedValue;
        if (DOM.employeeSelect.value !== preselectedValue) {
          const fallbackEmployee = normalizedEmployees.find((emp) => emp.id === preselectedValue);
          let fallbackName = fallbackEmployee?.name || 'Выбранный сотрудник';
          if (fallbackEmployee?.isFormer && !fallbackName.toLowerCase().includes('бывш')) {
            fallbackName = `${fallbackName} (бывший)`;
          }
          DOM.employeeSelect.innerHTML += `<option value="${preselectedValue}">${escapeHtml(fallbackName)}</option>`;
          DOM.employeeSelect.value = preselectedValue;
        }
        state.currentEmployeeId = settings.preselectedEmployeeId;
        loadTimeslotsForObject(objectId);
      } else {
        state.currentEmployeeId = null;
      }
    } catch (error) {
      console.error('Ошибка загрузки сотрудников для объекта:', error);
      DOM.employeeSelect.innerHTML = '<option value="">Ошибка загрузки сотрудников</option>';
    }
  }

  async function loadTimeslotsForObject(objectId) {
    if (!objectId) {
      state.availableTimeslots = [];
      state.employeePlannedShifts = [];
      state.selectedPlannedShiftIds.clear();
      state.initialPlannedShiftIds.clear();
      updateCalendar();
      updateSelectedSlotsInfo();
      return;
    }

    const objectNumericId = Number(objectId);
    if (Number.isNaN(objectNumericId)) {
      state.availableTimeslots = [];
      state.employeePlannedShifts = [];
      state.selectedPlannedShiftIds.clear();
      state.initialPlannedShiftIds.clear();
      updateCalendar();
      updateSelectedSlotsInfo();
      return;
    }

    try {
      const today = new Date();
      const startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const endDate = new Date(today.getFullYear(), today.getMonth() + 2, 0);
      state.selectedTimeslots.clear();
      state.timeslotSelectionDetails.clear();

      const query = new URLSearchParams({
        start_date: formatDateForAPI(startDate),
        end_date: formatDateForAPI(endDate),
        object_ids: String(objectId)
      });

      const response = await fetch(`${settings.calendarDataEndpoint.replace(/\/$/, '')}?${query.toString()}`);
      const data = await response.json();

      const timeslots = Array.isArray(data.timeslots) ? data.timeslots : [];
      state.calendarShifts = Array.isArray(data.shifts) ? data.shifts : [];

      const relevantShifts = state.calendarShifts.filter((shift) => Number(shift.object_id) === objectNumericId);

      state.availableTimeslots = timeslots
        .filter((ts) => Number(ts.object_id) === objectNumericId)
        .map((ts) => {
          const status = (ts.status || '').toLowerCase();
          const availability = calculateTimeslotAvailability(ts, relevantShifts);
          if (!availability || !availability.hasFreeCapacity) {
            return null;
          }
          const firstFree = availability.firstFree;
          return {
            ...ts,
            status,
            positions: availability.positions,
            first_free_start: firstFree ? firstFree.startStr : null,
            first_free_end: firstFree ? firstFree.endStr : null,
            first_free_duration: firstFree ? firstFree.durationMinutes : 0,
            first_free_position: firstFree ? firstFree.positionIndex : null
          };
        })
        .filter(Boolean)
        .sort((a, b) => {
          const dateA = new Date((a.date || a.slot_date || a.start_date) + 'T00:00:00');
          const dateB = new Date((b.date || b.slot_date || b.start_date) + 'T00:00:00');
          if (dateA.getTime() === dateB.getTime()) {
            const timeA = timeStringToMinutes(a.first_free_start || a.start_time || a.start_time_str || '00:00') || 0;
            const timeB = timeStringToMinutes(b.first_free_start || b.start_time || b.start_time_str || '00:00') || 0;
            return timeA - timeB;
          }
          return dateA - dateB;
        });

      const todayStart = new Date();
      todayStart.setHours(0, 0, 0, 0);

      const employeeId = settings.hideEmployeeSelect
        ? settings.preselectedEmployeeId
        : (DOM.employeeSelect ? Number(DOM.employeeSelect.value) : null);

      if (employeeId !== null && !Number.isNaN(employeeId)) {
        state.currentEmployeeId = employeeId;
        const employeeRelevantShifts = relevantShifts.filter(
          (shift) => Number(shift.user_id) === employeeId && shift.schedule_id !== undefined && shift.schedule_id !== null
        );

        state.employeePlannedShifts = employeeRelevantShifts
          .filter((shift) => {
            const shiftType = (shift.shift_type || '').toLowerCase();
            if (shiftType !== 'planned') {
              return false;
            }
            const status = (shift.status || '').toLowerCase();
            if (!ALLOWED_SHIFT_STATUSES.has(status)) {
              return false;
            }
            const endISO = shift.planned_end || shift.end_time || shift.start_time;
            if (!endISO) {
              return false;
            }
            const endDate = new Date(endISO);
            if (Number.isNaN(endDate.getTime())) {
              return false;
            }
            return endDate >= todayStart;
          })
          .map((shift) => {
            const scheduleId = Number(shift.schedule_id);
            if (Number.isNaN(scheduleId)) {
              return null;
            }
            const shiftDateStr = getISODateString(shift.planned_start || shift.start_time);
            if (!shiftDateStr) {
              return null;
            }
            const startLabel = formatISOTimeToLocal(shift.planned_start || shift.start_time);
            const endLabel = formatISOTimeToLocal(shift.planned_end || shift.end_time);
            return {
              schedule_id: scheduleId,
              time_slot_id: shift.time_slot_id !== undefined && shift.time_slot_id !== null ? Number(shift.time_slot_id) : null,
              date: shiftDateStr,
              start_time: startLabel,
              end_time: endLabel,
              time_range: `${startLabel || '—'} - ${endLabel || '—'}`,
              object_name: shift.object_name || '',
              status: shift.status || 'planned',
              original: shift
            };
          })
          .filter(Boolean)
          .sort((a, b) => {
            if (a.date === b.date) {
              const timeA = timeStringToMinutes(a.start_time) || 0;
              const timeB = timeStringToMinutes(b.start_time) || 0;
              return timeA - timeB;
            }
            const dateA = new Date(`${a.date}T00:00:00`);
            const dateB = new Date(`${b.date}T00:00:00`);
            return dateA - dateB;
          });
      } else {
        state.employeePlannedShifts = [];
      }

      state.initialPlannedShiftIds = new Set(state.employeePlannedShifts.map((shift) => shift.schedule_id));
      state.selectedPlannedShiftIds = new Set(state.initialPlannedShiftIds);

      updateCalendar();
      updateSelectedSlotsInfo();
    } catch (error) {
      console.error('Ошибка загрузки тайм-слотов:', error);
      alert('Ошибка загрузки тайм-слотов: ' + error.message);
      updateSelectedSlotsInfo();
    }
  }

  function updateCalendar() {
    if (DOM.monthLabel) {
      const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
      DOM.monthLabel.textContent = `${monthNames[state.currentMonth]} ${state.currentYear}`;
    }
    createPlanShiftCalendar();
  }

  function createPlanShiftCalendar() {
    if (!DOM.calendarContainer) {
      return;
    }

    const firstDay = new Date(state.currentYear, state.currentMonth, 1);
    const firstMonday = new Date(firstDay);
    firstMonday.setDate(firstDay.getDate() - firstDay.getDay() + 1);
    const daysOfWeek = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

    let html = `
            <div class="calendar-weekdays">
                ${daysOfWeek.map((day) => `<div class="calendar-weekday">${day}</div>`).join('')}
            </div>
            <div class="calendar-days">
        `;

    const renderedSlotKeys = new Set();

    for (let i = 0; i < 35; i++) {
      const date = new Date(firstMonday);
      date.setDate(firstMonday.getDate() + i);

      const isCurrentMonth = date.getMonth() === state.currentMonth;
      const dateStr = formatDateForAPI(date);
      const timeslotsForDate = state.availableTimeslots.filter((ts) => {
        const tsDate = ts.date || ts.slot_date || ts.start_date;
        return tsDate === dateStr;
      });
      const plannedShiftsForDate = state.employeePlannedShifts.filter((shift) => shift.date === dateStr);

      let dayClass = 'calendar-day';
      if (!isCurrentMonth) {
        dayClass += ' disabled';
      } else if (timeslotsForDate.length > 0) {
        dayClass += ' has-timeslots';
      }

      html += `<div class="${dayClass}" data-date="${dateStr}">`;
      html += `<div class="day-number">${date.getDate()}</div>`;

      if (isCurrentMonth && plannedShiftsForDate.length > 0) {
        plannedShiftsForDate.forEach((shift) => {
          const isSelected = state.selectedPlannedShiftIds.has(shift.schedule_id);
          const timeRange = shift.time_range || `${shift.start_time || '—'} - ${shift.end_time || '—'}`;
          const objectLine = shift.object_name ? `<div class="planned-shift-object">${escapeHtml(shift.object_name)}</div>` : '';

          html += `<div class="planned-shift ${isSelected ? 'selected' : ''}" data-schedule-id="${shift.schedule_id}">`;
          html += `<div class="shift-badge shift-badge-default">Запланировано</div>`;
          html += `<div class="planned-shift-time">${timeRange}</div>`;
          html += objectLine;
          html += '</div>';
        });
      }

      if (isCurrentMonth && timeslotsForDate.length > 0) {
        const displaySlots = timeslotsForDate.filter((ts) => {
          if (Array.isArray(ts.positions)) {
            return ts.positions.some((pos) => Array.isArray(pos.freeIntervals) && pos.freeIntervals.length > 0);
          }
          return (ts.first_free_duration || 0) > 0;
        });

        if (displaySlots.length > 0) {
          displaySlots.forEach((ts) => {
            const fullStart = ts.start_time || ts.start_time_str || '09:00';
            const fullEnd = ts.end_time || ts.end_time_str || '21:00';
            const fallbackDuration = Math.max(
              0,
              (timeStringToMinutes(fullEnd) || 0) - (timeStringToMinutes(fullStart) || 0)
            );
            const positions = Array.isArray(ts.positions) ? ts.positions : [];

            const intervalsForRender = [];

            if (positions.length > 0) {
              positions.forEach((pos) => {
                if (!Array.isArray(pos.freeIntervals) || pos.freeIntervals.length === 0) {
                  return;
                }
                pos.freeIntervals.forEach((interval, idx) => {
                  if (!interval?.startStr || !interval?.endStr) {
                    return;
                  }
                  intervalsForRender.push({
                    positionIndex: pos.index,
                    intervalIndex: idx,
                    interval
                  });
                });
              });
            }

            if (intervalsForRender.length === 0 && ts.first_free_start && ts.first_free_end) {
              intervalsForRender.push({
                positionIndex: ts.first_free_position ?? null,
                intervalIndex: 0,
                interval: {
                  startStr: ts.first_free_start,
                  endStr: ts.first_free_end,
                  durationMinutes: ts.first_free_duration ?? fallbackDuration,
                  startMinutes: timeStringToMinutes(ts.first_free_start),
                  endMinutes: timeStringToMinutes(ts.first_free_end)
                }
              });
            }

            intervalsForRender
              .sort((a, b) => {
                const startA = a.interval.startMinutes ?? timeStringToMinutes(a.interval.startStr) ?? 0;
                const startB = b.interval.startMinutes ?? timeStringToMinutes(b.interval.startStr) ?? 0;
                return startA - startB;
              })
              .forEach((entry) => {
                const interval = entry.interval;
                const startStr = interval.startStr;
                const endStr = interval.endStr;
                if (!startStr || !endStr) {
                  return;
                }

                const durationMinutes = interval.durationMinutes ?? Math.max(
                  0,
                  (interval.endMinutes ?? timeStringToMinutes(endStr) ?? 0)
                    - (interval.startMinutes ?? timeStringToMinutes(startStr) ?? 0)
                );
                const positionPart = entry.positionIndex !== null && entry.positionIndex !== undefined
                  ? entry.positionIndex
                  : 0;
                const slotKey = `${dateStr}_${ts.id}_${positionPart}_${startStr}_${endStr}`;
                renderedSlotKeys.add(slotKey);
                const isSelected = state.selectedTimeslots.has(slotKey);
                const statusLabel = (startStr === fullStart && endStr === fullEnd) ? 'Свободен' : 'Частично свободен';
                const positionLabel = entry.positionIndex
                  ? `Время смены ${entry.positionIndex}`
                  : 'Свободное время';
                const durationLabel = formatFreeMinutes(durationMinutes || fallbackDuration);

                html += `<div class="timeslot available ${isSelected ? 'selected' : ''}" data-slot-key="${slotKey}" data-timeslot-id="${ts.id}" data-position-index="${entry.positionIndex ?? ''}" data-interval-index="${entry.intervalIndex}" data-start-time="${startStr}" data-end-time="${endStr}" data-free-start="${startStr}" data-free-end="${endStr}">`;
                html += `<div class="timeslot-time">${fullStart}-${fullEnd}</div>`;
                html += `<div class="timeslot-slots">${positionLabel}: <strong>${startStr}-${endStr}</strong></div>`;
                html += `<div class="timeslot-slots">${statusLabel}. Доступно: ${durationLabel}</div>`;
                if (positions.length > 1) {
                  html += `<div class="timeslot-slots text-muted">Всего позиций: ${positions.length}</div>`;
                }
                html += '</div>';
              });
          });
        } else {
          html += '<div class="no-slots">Нет свободных окон</div>';
        }
      } else if (isCurrentMonth) {
        html += '<div class="empty-message">Нет тайм-слотов</div>';
      }

      html += '</div>';
    }

    html += '</div>';
    DOM.calendarContainer.innerHTML = html;

    Array.from(state.selectedTimeslots).forEach((key) => {
      if (!renderedSlotKeys.has(key)) {
        state.selectedTimeslots.delete(key);
        state.timeslotSelectionDetails.delete(key);
      }
    });

    DOM.calendarContainer.removeEventListener('click', handleCalendarClick);
    DOM.calendarContainer.addEventListener('click', handleCalendarClick);
    updateSelectedSlotsInfo();
  }

  function handleCalendarClick(e) {
    const timeslotEl = e.target.closest('.timeslot');
    if (timeslotEl && timeslotEl.classList.contains('available')) {
      handleTimeslotClick(e, timeslotEl);
      return;
    }
    const plannedShiftEl = e.target.closest('.planned-shift');
    if (plannedShiftEl) {
      handlePlannedShiftClick(e, plannedShiftEl);
      return;
    }
  }

  async function handleTimeslotClick(event, element) {
    const day = element.closest('.calendar-day');
    if (!day || day.classList.contains('disabled')) {
      return;
    }

    if (!DOM.employeeSelect && settings.preselectedEmployeeId === null) {
      alert('Выберите сотрудника');
      return;
    }

    const employeeIdValue = settings.hideEmployeeSelect ? settings.preselectedEmployeeId : DOM.employeeSelect.value;
    if (!employeeIdValue && employeeIdValue !== 0) {
      alert('Сначала выберите сотрудника');
      return;
    }

    const employeeId = Number(employeeIdValue);
    const timeslotId = element.dataset.timeslotId;
    const date = day.dataset.date;

    const isAvailable = await checkEmployeeAvailability(employeeId, timeslotId);
    if (!isAvailable) {
      return;
    }

    const slotKey = element.dataset.slotKey || `${date}_${timeslotId}`;
    const positionIndexAttr = element.dataset.positionIndex;
    const intervalIndexAttr = element.dataset.intervalIndex;
    const startTime = element.dataset.startTime || element.dataset.freeStart || null;
    const endTime = element.dataset.endTime || element.dataset.freeEnd || null;
    const positionIndex = positionIndexAttr !== undefined && positionIndexAttr !== ''
      ? Number(positionIndexAttr)
      : null;
    const intervalIndex = intervalIndexAttr !== undefined && intervalIndexAttr !== ''
      ? Number(intervalIndexAttr)
      : null;

    if (state.selectedTimeslots.has(slotKey)) {
      state.selectedTimeslots.delete(slotKey);
      state.timeslotSelectionDetails.delete(slotKey);
      element.classList.remove('selected');
    } else {
      state.selectedTimeslots.add(slotKey);
      state.timeslotSelectionDetails.set(slotKey, {
        timeslotId,
        startTime,
        endTime,
        positionIndex,
        intervalIndex,
        date
      });
      element.classList.add('selected');
    }
    setTimeout(() => updateSelectedSlotsInfo(), 100);
  }

  function handlePlannedShiftClick(event, element) {
    event.preventDefault();
    if (!settings.allowCancelPlannedShifts) {
      return;
    }

    const scheduleId = Number(element.dataset.scheduleId);
    if (Number.isNaN(scheduleId)) {
      return;
    }

    if (state.selectedPlannedShiftIds.has(scheduleId)) {
      state.selectedPlannedShiftIds.delete(scheduleId);
      element.classList.remove('selected');
    } else {
      state.selectedPlannedShiftIds.add(scheduleId);
      element.classList.add('selected');
    }

    updateSelectedSlotsInfo();
  }

  async function checkEmployeeAvailability(employeeId, timeslotId) {
    try {
      const response = await fetch(settings.checkAvailabilityEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          timeslot_id: parseInt(timeslotId, 10),
          employee_id: parseInt(employeeId, 10)
        })
      });
      const result = await response.json();
      if (result.available) {
        return true;
      }
      let message = result.message || 'Сотрудник недоступен в это время';
      if (result.conflict_info) {
        const conflict = result.conflict_info;
        message = `Сотрудник в это время работает на объекте "${conflict.object_name}" с ${conflict.start_time} до ${conflict.end_time}`;
      }
      alert(message);
      return false;
    } catch (error) {
      console.error('Ошибка проверки доступности:', error);
      alert('Ошибка проверки доступности сотрудника');
      return false;
    }
  }

  function updateSelectedSlotsInfo() {
    if (!DOM.selectedInfo || !DOM.confirmBtn) {
      return;
    }

    const newTimeslotCount = state.selectedTimeslots.size;
    const selectedPlannedCount = state.selectedPlannedShiftIds.size;
    const initialPlannedCount = state.initialPlannedShiftIds.size;
    const cancelCount = Math.max(0, initialPlannedCount - selectedPlannedCount);

    if (DOM.selectedTimeslotsCount) {
      DOM.selectedTimeslotsCount.textContent = String(newTimeslotCount);
    }
    if (DOM.selectedPlannedCount) {
      DOM.selectedPlannedCount.textContent = String(selectedPlannedCount);
    }
    if (DOM.cancelPlannedCount) {
      DOM.cancelPlannedCount.textContent = String(cancelCount);
    }
    if (DOM.cancelInfoLine) {
      if (cancelCount > 0) {
        DOM.cancelInfoLine.classList.remove('text-muted');
        DOM.cancelInfoLine.classList.add('text-warning');
      } else {
        DOM.cancelInfoLine.classList.remove('text-warning');
        DOM.cancelInfoLine.classList.add('text-muted');
      }
    }

    const shouldShow =
      newTimeslotCount > 0 || initialPlannedCount > 0 || selectedPlannedCount > 0 || (settings.allowCancelPlannedShifts && cancelCount > 0);
    DOM.selectedInfo.style.display = shouldShow ? 'block' : 'none';

    const hasAction = newTimeslotCount > 0 || (settings.allowCancelPlannedShifts && cancelCount > 0);
    DOM.confirmBtn.disabled = !hasAction;
  }

  async function confirmPlanShift() {
    const objectId = DOM.objectSelect ? DOM.objectSelect.value : settings.selectedObjectId;
    const employeeIdValue = settings.hideEmployeeSelect ? settings.preselectedEmployeeId : (DOM.employeeSelect ? DOM.employeeSelect.value : null);

    if (!objectId || !employeeIdValue) {
      alert('Выберите объект и сотрудника');
      return;
    }

    const timeslotsToPlan = Array.from(state.selectedTimeslots);
    const shiftsToCancel = settings.allowCancelPlannedShifts
      ? Array.from(state.initialPlannedShiftIds).filter((id) => !state.selectedPlannedShiftIds.has(id))
      : [];

    if (timeslotsToPlan.length === 0 && shiftsToCancel.length === 0) {
      alert('Нет изменений для сохранения');
      return;
    }

    if (DOM.confirmBtn) {
      DOM.confirmBtn.disabled = true;
      DOM.confirmBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Обработка...';
    }

    let planSuccess = 0;
    let planErrors = 0;
    let cancelSuccess = 0;
    let cancelErrors = 0;

    const alreadyCancelledMessageMatcher = (message) => {
      if (!message || typeof message !== 'string') {
        return false;
      }
      const normalized = message.toLowerCase();
      return normalized.includes('не найдена') && normalized.includes('уже отменена');
    };

    const isEmployeeRole = settings.role === 'employee';

    if (settings.allowCancelPlannedShifts) {
      for (const scheduleId of shiftsToCancel) {
        const cancelUrl = buildCancelScheduleUrl(scheduleId);
        if (!cancelUrl) {
          cancelErrors++;
          continue;
        }
        try {
          const requestInit = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
          };
          if (isEmployeeRole) {
            requestInit.body = JSON.stringify({ schedule_id: Number(scheduleId) });
          }
          const response = await fetch(cancelUrl, {
            ...requestInit
          });
          let result = null;
          try {
            result = await response.json();
          } catch (parseError) {
            result = null;
          }
          if (response.ok && result && (result.success || result.status === 'ok')) {
            cancelSuccess++;
          } else {
            const message = result?.detail || result?.message || response.statusText;
            if (alreadyCancelledMessageMatcher(message || '')) {
              cancelSuccess++;
              console.warn('Смена уже была отменена ранее, считаем операцию успешной.');
            } else {
              cancelErrors++;
              console.error('Ошибка отмены смены:', message);
            }
          }
        } catch (error) {
          cancelErrors++;
          console.error('Ошибка отмены смены:', error);
        }
      }
    }

    for (const slotKey of timeslotsToPlan) {
      try {
        const parts = slotKey.split('_');
        if (parts.length < 2) {
          planErrors++;
          console.error('Некорректный ключ тайм-слота', slotKey);
          continue;
        }
        const rawTimeslotId = parts[1];
        const detail = state.timeslotSelectionDetails.get(slotKey);
        const timeslotId = detail?.timeslotId ?? rawTimeslotId;
        const timeslot = state.availableTimeslots.find((ts) => String(ts.id) === String(timeslotId));
        if (!timeslot) {
          planErrors++;
          console.error('Не найден тайм-слот для планирования', timeslotId);
          continue;
        }
        const freeStart =
          detail?.startTime
          || timeslot.first_free_start
          || timeslot.start_time
          || timeslot.start_time_str;
        const freeEnd =
          detail?.endTime
          || timeslot.first_free_end
          || timeslot.end_time
          || timeslot.end_time_str;
        if (!freeStart || !freeEnd) {
          planErrors++;
          console.error('Не удалось определить свободный интервал для тайм-слота', timeslotId);
          continue;
        }
        const response = await fetch(settings.planShiftEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            timeslot_id: parseInt(timeslotId, 10),
            employee_id: parseInt(employeeIdValue, 10),
            start_time: freeStart,
            end_time: freeEnd
          })
        });
        let result = null;
        try {
          result = await response.json();
        } catch (parseError) {
          result = null;
        }
        if (response.ok && result && result.success) {
          planSuccess++;
        } else {
          planErrors++;
          console.error('Ошибка планирования:', result?.message || response.statusText);
        }
      } catch (error) {
        planErrors++;
        console.error('Ошибка планирования смены:', error);
      }
    }

    try {
      if (objectId) {
        await loadTimeslotsForObject(objectId);
      } else {
        updateSelectedSlotsInfo();
      }
    } finally {
      if (DOM.confirmBtn) {
        DOM.confirmBtn.disabled = false;
        DOM.confirmBtn.innerHTML = '<i class="bi bi-calendar-check"></i> Запланировать смены';
      }
    }

    const summaryParts = [];
    if (planSuccess > 0) {
      summaryParts.push(`Запланировано смен: ${planSuccess}`);
    }
    if (cancelSuccess > 0) {
      summaryParts.push(`Отменено смен: ${cancelSuccess}`);
    }
    if (planErrors > 0) {
      summaryParts.push(`Ошибок планирования: ${planErrors}`);
    }
    if (cancelErrors > 0) {
      summaryParts.push(`Ошибок отмены: ${cancelErrors}`);
    }

    if (summaryParts.length > 0) {
      alert(summaryParts.join('\n'));
    } else {
      alert('Изменений не выполнено');
    }

    if ((planSuccess > 0 || cancelSuccess > 0) && settings.returnToUrl) {
      window.location.href = settings.returnToUrl;
    }
  }

  function formatDateForAPI(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function timeStringToMinutes(value) {
    if (!value || typeof value !== 'string') {
      return null;
    }
    const [hoursStr, minutesStr] = value.split(':');
    const hours = Number(hoursStr);
    const minutes = Number(minutesStr);
    if (Number.isNaN(hours) || Number.isNaN(minutes)) {
      return null;
    }
    return hours * 60 + minutes;
  }

  function minutesToTime(minutesTotal) {
    if (typeof minutesTotal !== 'number' || Number.isNaN(minutesTotal)) {
      return '';
    }
    const hours = Math.floor(minutesTotal / 60);
    const minutes = minutesTotal % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  }

  function formatFreeMinutes(minutesTotal) {
    const total = Math.max(0, Math.round(minutesTotal));
    const hours = Math.floor(total / 60);
    const minutes = total % 60;
    if (hours > 0 && minutes > 0) {
      return `${hours} ч ${minutes} м`;
    }
    if (hours > 0) {
      return `${hours} ч`;
    }
    return `${minutes} м`;
  }

  function formatISOTimeToLocal(isoString) {
    if (!isoString) {
      return '';
    }
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
      return '';
    }
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  }

  function buildEmployeeDisplayName(employee) {
    if (!employee || typeof employee !== 'object') {
      return 'Сотрудник';
    }
    if (employee.name) {
      return String(employee.name);
    }
    const lastName = employee.last_name ?? employee.lastName ?? '';
    const firstName = employee.first_name ?? employee.firstName ?? '';
    const middleName = employee.middle_name ?? employee.middleName ?? '';
    const parts = [lastName, firstName, middleName].map((part) => String(part || '').trim()).filter(Boolean);
    if (parts.length) {
      return parts.join(' ');
    }
    if (employee.username) {
      return String(employee.username);
    }
    if (employee.telegram_id || employee.telegramId) {
      return `ID ${employee.telegram_id || employee.telegramId}`;
    }
    if (employee.id !== undefined) {
      return `ID ${employee.id}`;
    }
    return 'Сотрудник';
  }

  function normalizeEmployeesResponse(raw) {
    const map = new Map();

    const pushEmployee = (emp, forceFormer = null) => {
      if (!emp || typeof emp !== 'object') {
        return;
      }
      const numericId = Number(emp.id);
      if (!Number.isFinite(numericId)) {
        return;
      }

      let isFormer = forceFormer;
      if (isFormer === null) {
        if (typeof emp.is_former === 'boolean') {
          isFormer = emp.is_former;
        } else if (typeof emp.isFormer === 'boolean') {
          isFormer = emp.isFormer;
        } else if (typeof emp.is_active === 'boolean') {
          isFormer = !emp.is_active;
        } else {
          isFormer = false;
        }
      }

      const displayName = buildEmployeeDisplayName(emp);
      const existing = map.get(numericId);

      if (existing) {
        if (!isFormer) {
          existing.isFormer = false;
        }
        if (displayName && displayName !== existing.name) {
          existing.name = displayName;
        }
      } else {
        map.set(numericId, {
          id: String(numericId),
          name: displayName,
          isFormer: Boolean(isFormer),
        });
      }
    };

    if (Array.isArray(raw)) {
      raw.forEach((emp) => pushEmployee(emp));
    } else if (raw && typeof raw === 'object') {
      const collections = [
        { list: raw.active, flag: false },
        { list: raw.current, flag: false },
        { list: raw.employees, flag: null },
        { list: raw.former, flag: true },
      ];
      collections.forEach(({ list, flag }) => {
        if (Array.isArray(list)) {
          list.forEach((emp) => pushEmployee(emp, flag));
        }
      });
    }

    return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }));
  }

  function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') {
      return '';
    }
    return unsafe
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  const ALLOWED_SHIFT_STATUSES = new Set(['planned', 'confirmed', 'active', 'completed']);

  function getISODateString(isoString) {
    if (!isoString) {
      return null;
    }
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
      return null;
    }
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function extractShiftInterval(shift, slotStartMinutes, slotEndMinutes) {
    const startISO = shift.planned_start || shift.start_time;
    const endISO = shift.planned_end || shift.end_time;
    if (!startISO || !endISO) {
      return null;
    }
    const startDate = new Date(startISO);
    const endDate = new Date(endISO);
    if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
      return null;
    }
    const startMinutes = startDate.getHours() * 60 + startDate.getMinutes();
    const endMinutes = endDate.getHours() * 60 + endDate.getMinutes();
    if (endMinutes <= startMinutes) {
      return null;
    }
    const overlapStart = Math.max(slotStartMinutes, startMinutes);
    const overlapEnd = Math.min(slotEndMinutes, endMinutes);
    if (overlapEnd <= overlapStart) {
      return null;
    }
    return [overlapStart, overlapEnd];
  }

  function mergeIntervals(intervals) {
    if (!Array.isArray(intervals) || intervals.length === 0) {
      return [];
    }
    const sorted = intervals
      .filter((interval) => Array.isArray(interval) && interval.length === 2)
      .map((interval) => interval.slice())
      .sort((a, b) => a[0] - b[0]);

    if (sorted.length === 0) {
      return [];
    }

    const merged = [sorted[0]];
    for (let i = 1; i < sorted.length; i += 1) {
      const current = sorted[i];
      const last = merged[merged.length - 1];
      if (current[0] <= last[1]) {
        last[1] = Math.max(last[1], current[1]);
      } else {
        merged.push(current);
      }
    }
    return merged;
  }

  function calculateFreeRanges(slotStartMinutes, slotEndMinutes, busyIntervals) {
    if (slotStartMinutes === null || slotEndMinutes === null || slotEndMinutes <= slotStartMinutes) {
      return [];
    }
    if (!busyIntervals || busyIntervals.length === 0) {
      return [[slotStartMinutes, slotEndMinutes]];
    }
    const merged = mergeIntervals(busyIntervals);
    const freeRanges = [];
    let cursor = slotStartMinutes;

    merged.forEach(([start, end]) => {
      if (start > cursor) {
        freeRanges.push([cursor, Math.min(start, slotEndMinutes)]);
      }
      cursor = Math.max(cursor, end);
    });

    if (cursor < slotEndMinutes) {
      freeRanges.push([cursor, slotEndMinutes]);
    }

    return freeRanges.filter(([start, end]) => end > start);
  }

  function calculateTimeslotAvailability(timeslot, shifts) {
    const slotStartStr = timeslot.start_time || timeslot.start_time_str;
    const slotEndStr = timeslot.end_time || timeslot.end_time_str;
    const slotDateStr = timeslot.date || timeslot.slot_date || timeslot.start_date;

    const slotStartMinutes = timeStringToMinutes(slotStartStr);
    const slotEndMinutes = timeStringToMinutes(slotEndStr);

    if (!slotDateStr || slotStartMinutes === null || slotEndMinutes === null || slotEndMinutes <= slotStartMinutes) {
      return null;
    }

    const timeslotId = Number(timeslot.id);
    const maxEmployees = Math.max(1, Number(timeslot.max_employees) || 1);

    const plannedIntervals = [];
    shifts.forEach((shift) => {
      const status = (shift.status || '').toLowerCase();
      if (!ALLOWED_SHIFT_STATUSES.has(status)) {
        return;
      }
      const shiftTimeslotId = shift.time_slot_id !== undefined && shift.time_slot_id !== null ? Number(shift.time_slot_id) : null;
      const matchesTimeslot = !Number.isNaN(timeslotId) && shiftTimeslotId === timeslotId;
      const shiftDateStr = getISODateString(shift.planned_start || shift.start_time);
      const matchesDate = shiftDateStr === slotDateStr;
      const shouldApply = matchesTimeslot || (shiftTimeslotId === null && matchesDate);
      if (!shouldApply) {
        return;
      }
      const interval = extractShiftInterval(shift, slotStartMinutes, slotEndMinutes);
      if (interval) {
        plannedIntervals.push({
          startMinutes: interval[0],
          endMinutes: interval[1]
        });
      }
    });

    plannedIntervals.sort((a, b) => a.startMinutes - b.startMinutes);

    const positions = Array.from({ length: maxEmployees }, (_value, index) => ({
      index: index + 1,
      busy: []
    }));

    plannedIntervals.forEach((interval) => {
      let assigned = false;
      for (const position of positions) {
        const lastBusy = position.busy[position.busy.length - 1];
        if (!lastBusy || lastBusy[1] <= interval.startMinutes) {
          position.busy.push([interval.startMinutes, interval.endMinutes]);
          assigned = true;
          break;
        }
      }
      if (!assigned) {
        positions[0].busy.push([interval.startMinutes, interval.endMinutes]);
      }
    });

    const positionOutputs = positions.map((position) => {
      const mergedBusy = mergeIntervals(position.busy);
      const freeRanges = calculateFreeRanges(slotStartMinutes, slotEndMinutes, mergedBusy);
      return {
        index: position.index,
        freeIntervals: freeRanges.map(([start, end]) => ({
          startMinutes: start,
          endMinutes: end,
          startStr: minutesToTime(start),
          endStr: minutesToTime(end),
          durationMinutes: end - start
        }))
      };
    });

    const freeCandidates = positionOutputs
      .map((pos) => (pos.freeIntervals.length > 0 ? { positionIndex: pos.index, ...pos.freeIntervals[0] } : null))
      .filter(Boolean)
      .map((candidate) => ({
        positionIndex: candidate.positionIndex,
        startMinutes: candidate.startMinutes,
        endMinutes: candidate.endMinutes,
        startStr: candidate.startStr,
        endStr: candidate.endStr,
        durationMinutes: candidate.durationMinutes
      }))
      .sort((a, b) => a.startMinutes - b.startMinutes);

    return {
      positions: positionOutputs,
      firstFree: freeCandidates.length > 0 ? freeCandidates[0] : null,
      hasFreeCapacity: freeCandidates.length > 0
    };
  }
})();

