(() => {
  const SNAP_INTERVAL_MINUTES = 30;

  const defaultConfig = {
    role: 'owner',
    timeslotDetailEndpoint: (timeslotId) => `/owner/calendar/api/timeslot/${timeslotId}`,
    employeesForObjectEndpoint: (objectId) => `/owner/api/employees/for-object/${objectId}`,
    planShiftEndpoint: '/owner/api/calendar/plan-shift',
    preselectedEmployeeId: null,
    lockedEmployeeId: null,
    lockedEmployeeName: null,
    lockEmployeeSelection: false,
    scheduleId: null,  // ID запланированной смены для режима редактирования
    notify: (message, type = 'info') => {
      if (type === 'error') {
        window.alert(message);
      } else if (type === 'success') {
        console.log(`[success] ${message}`);
      } else {
        console.log(`[info] ${message}`);
      }
    },
    onSuccess: () => {
      if (window.universalCalendar && typeof window.universalCalendar.refresh === 'function') {
        window.universalCalendar.refresh();
      } else {
        window.location.reload();
      }
    },
    onError: (error) => console.error(error),
    refreshCalendar: null
  };

  let activeConfig = { ...defaultConfig };

  function minutesToTimeString(minutesTotal) {
    const hours = Math.floor(minutesTotal / 60);
    const minutes = minutesTotal % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  }

  function escapeHtml(value) {
    if (value === null || value === undefined) {
      return '';
    }
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function timeStringToMinutes(value) {
    if (!value || typeof value !== 'string') {
      return null;
    }
    const [hoursPart, minutesPart] = value.split(':');
    const hours = Number(hoursPart);
    const minutes = Number(minutesPart);
    if (Number.isNaN(hours) || Number.isNaN(minutes)) {
      return null;
    }
    return hours * 60 + minutes;
  }

  function formatDurationText(minutesTotal) {
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

  function normalizeEmployeesData(raw) {
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
          id: numericId,
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

  function formatTimeFromISO(isoString) {
    if (!isoString) {
      return null;
    }
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
      return null;
    }
    return date.toTimeString().slice(0, 5);
  }

  function calculateFreeIntervals(slotStart, slotEnd, planned) {
    const slotStartMinutes = timeStringToMinutes(slotStart);
    const slotEndMinutes = timeStringToMinutes(slotEnd);
    if (slotStartMinutes === null || slotEndMinutes === null || slotEndMinutes <= slotStartMinutes) {
      return [];
    }

    const intervals = planned
      .map((shift) => {
        const start = timeStringToMinutes(shift.start_time);
        const end = timeStringToMinutes(shift.end_time);
        if (start === null || end === null || end <= start) {
          return null;
        }
        return {
          startMinutes: Math.max(slotStartMinutes, Math.min(start, slotEndMinutes)),
          endMinutes: Math.max(slotStartMinutes, Math.min(end, slotEndMinutes))
        };
      })
      .filter(Boolean)
      .sort((a, b) => a.startMinutes - b.startMinutes);

    const merged = [];
    intervals.forEach((interval) => {
      if (!merged.length) {
        merged.push(interval);
        return;
      }
      const last = merged[merged.length - 1];
      if (interval.startMinutes <= last.endMinutes) {
        last.endMinutes = Math.max(last.endMinutes, interval.endMinutes);
      } else {
        merged.push(interval);
      }
    });

    const freeIntervals = [];
    let cursor = slotStartMinutes;

    merged.forEach((interval) => {
      if (interval.startMinutes > cursor) {
        freeIntervals.push({ start: minutesToTimeString(cursor), end: minutesToTimeString(interval.startMinutes) });
      }
      cursor = Math.max(cursor, interval.endMinutes);
    });

    if (cursor < slotEndMinutes) {
      freeIntervals.push({ start: minutesToTimeString(cursor), end: minutesToTimeString(slotEndMinutes) });
    }

    if (!freeIntervals.length && !merged.length) {
      return [{ start: minutesToTimeString(slotStartMinutes), end: minutesToTimeString(slotEndMinutes) }];
    }

    return freeIntervals;
  }

  function selectDefaultInterval(slotStart, slotEnd, freeIntervals) {
    if (freeIntervals.length) {
      return freeIntervals[0];
    }
    return {
      start: slotStart || '',
      end: slotEnd || ''
    };
  }

  function ensureSchedulerStyles() {
    if (document.getElementById('timeslotSchedulerStyles')) {
      return;
    }
    const style = document.createElement('style');
    style.id = 'timeslotSchedulerStyles';
    style.textContent = `
      .scheduler-wrapper { background: #f5f9ff; border: 1px solid rgba(25,118,210,0.2); border-radius: 14px; padding: 16px 18px; position: relative; }
      .scheduler-track-switcher { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }
      .scheduler-track-tab { border:1px solid rgba(25,118,210,0.25); background:#fff; color:#0d47a1; padding:8px 14px; border-radius:999px; font-size:13px; font-weight:600; cursor:pointer; transition:all 0.15s ease; display:flex; flex-direction:column; align-items:flex-start; gap:2px; min-width:120px; }
      .scheduler-track-tab .scheduler-track-tab-info { font-size:11px; font-weight:500; color:rgba(13,71,161,0.7); }
      .scheduler-track-tab.existing { border-color:rgba(30,136,229,0.45); background:rgba(187,222,251,0.35); }
      .scheduler-track-tab.disabled { cursor:default; opacity:0.6; }
      .scheduler-track-tab.active { background:#1976d2; color:#fff; box-shadow:0 6px 18px rgba(25,118,210,0.25); }
      .scheduler-track-tab.active .scheduler-track-tab-info { color:rgba(255,255,255,0.85); }
      .scheduler-position-tabs { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
      .scheduler-position-tab { border:1px solid rgba(25,118,210,0.3); background:#fff; color:#0d47a1; padding:8px 14px; border-radius:12px; font-size:13px; font-weight:600; cursor:pointer; transition:all 0.15s ease; display:flex; flex-direction:column; align-items:flex-start; gap:2px; min-width:140px; }
      .scheduler-position-tab strong { font-weight:700; }
      .scheduler-position-tab .scheduler-position-info { font-size:11px; font-weight:500; color:rgba(13,71,161,0.7); }
      .scheduler-position-tab.active { background:#1976d2; color:#fff; border-color:#1976d2; box-shadow:0 6px 18px rgba(25,118,210,0.25); }
      .scheduler-position-tab.active .scheduler-position-info { color:rgba(255,255,255,0.9); }
      .scheduler-track-container { position:relative; height:44px; margin:18px 0 18px; }
      .scheduler-track { position:absolute; top:50%; left:0; width:100%; height:14px; background:rgba(25,118,210,0.18); border-radius:999px; overflow:hidden; transform:translateY(-50%); }
      .scheduler-track .scheduler-segment { position:absolute; top:0; height:100%; border-radius:999px; }
      .scheduler-segment.occupied { background:rgba(229,57,53,0.45); }
      .scheduler-segment.selection { background:rgba(76,175,80,0.65); box-shadow:0 0 12px rgba(76,175,80,0.35); }
      .scheduler-segment.existing { background:rgba(30,136,229,0.55); box-shadow:0 0 10px rgba(30,136,229,0.25); }
      .scheduler-range-input { position:absolute; left:0; width:100%; height:44px; pointer-events:none; background:transparent; -webkit-appearance:none; appearance:none; }
      .scheduler-range-input::-webkit-slider-thumb { pointer-events:all; width:20px; height:20px; border-radius:50%; background:#1976d2; border:3px solid #fff; box-shadow:0 2px 8px rgba(25,118,210,0.35); -webkit-appearance:none; appearance:none; transition:transform 0.1s ease, box-shadow 0.1s ease; }
      .scheduler-range-input::-webkit-slider-thumb:hover { transform:scale(1.05); box-shadow:0 4px 12px rgba(25,118,210,0.45); }
      .scheduler-range-input::-moz-range-thumb { pointer-events:all; width:20px; height:20px; border-radius:50%; background:#1976d2; border:3px solid #fff; box-shadow:0 2px 8px rgba(25,118,210,0.35); transition:transform 0.1s ease, box-shadow 0.1s ease; }
      .scheduler-range-input::-moz-range-thumb:hover { transform:scale(1.05); box-shadow:0 4px 12px rgba(25,118,210,0.45); }
      .scheduler-range-input::-webkit-slider-runnable-track, .scheduler-range-input::-moz-range-track { height:100%; background:transparent; }
      .scheduler-labels { display:flex; justify-content:space-between; font-size:12px; color:#0d47a1; font-weight:600; }
      .scheduler-summary-box { margin-top:12px; background:rgba(25,118,210,0.08); border-radius:10px; padding:10px 14px; display:flex; flex-wrap:wrap; gap:12px; font-size:13px; color:#0d47a1; }
      .scheduler-summary-box span strong { font-weight:700; color:#1976d2; }
      .scheduler-existing ul { max-height:160px; overflow-y:auto; }
      .scheduler-static-wrapper { padding:4px 2px 6px; }
      .scheduler-static-wrapper .scheduler-summary-box { background:rgba(30,136,229,0.08); }
      .scheduler-track-info { font-size:12px; color:rgba(13,71,161,0.7); margin-bottom:6px; }
      .scheduler-freechips { display:flex; flex-wrap:wrap; gap:6px; margin-top:4px; }
      .scheduler-freechip { border:1px solid rgba(25,118,210,0.35); border-radius:999px; padding:4px 10px; font-size:11px; font-weight:600; color:#1976d2; cursor:pointer; background:rgba(25,118,210,0.1); transition:all 0.15s ease; }
      .scheduler-freechip:hover { background:rgba(25,118,210,0.16); }
      .scheduler-freechip.active { background:#1976d2; color:#fff; border-color:#115293; box-shadow:0 4px 14px rgba(25,118,210,0.28); }
    `;
    document.head.appendChild(style);
  }

  function calculatePositionPercent(valueMinutes, slotStartMinutes, slotEndMinutes) {
    return ((valueMinutes - slotStartMinutes) / (slotEndMinutes - slotStartMinutes)) * 100;
  }

  function calculateWidthPercent(startMinutes, endMinutes, slotStartMinutes, slotEndMinutes) {
    return ((endMinutes - startMinutes) / (slotEndMinutes - slotStartMinutes)) * 100;
  }

  function toNumber(value) {
    if (value === null || value === undefined || value === '') {
      return null;
    }
    const num = Number(value);
    return Number.isNaN(num) ? null : num;
  }

  function initializeScheduler(config) {
    const container = document.getElementById('timeslotScheduler');
    const modalElement = document.getElementById('addEmployeeToTimeslotModal');
    const confirmButton = document.getElementById('confirmAddEmployeeBtn');

    if (!container || !modalElement) {
      return;
    }

    const slotStartMinutes = timeStringToMinutes(config.slotStart);
    const slotEndMinutes = timeStringToMinutes(config.slotEnd);
    if (slotStartMinutes === null || slotEndMinutes === null || slotEndMinutes <= slotStartMinutes) {
      container.innerHTML = '<div class="alert alert-danger">Не удалось определить границы тайм-слота.</div>';
      if (confirmButton) {
        confirmButton.disabled = true;
      }
      return;
    }

    const scheduleId = config.scheduleId;
    const editingShift = config.editingShift;
    const isEditMode = scheduleId !== null && scheduleId !== undefined && editingShift !== null;
    
    const plannedIntervals = (config.plannedShifts || [])
      .map((shift, index) => {
        const start = timeStringToMinutes(shift.start_time);
        const end = timeStringToMinutes(shift.end_time);
        if (start === null || end === null || end <= start) {
          return null;
        }
        const userKey =
          shift.user_id !== undefined && shift.user_id !== null
            ? String(shift.user_id)
            : `unknown_${index}`;
        const trackId = `employee-${userKey}`;
        const isEditing = isEditMode && (shift.id === scheduleId || String(shift.id) === String(scheduleId));
        return {
          startMinutes: Math.max(slotStartMinutes, Math.min(start, slotEndMinutes)),
          endMinutes: Math.max(slotStartMinutes, Math.min(end, slotEndMinutes)),
          userId: shift.user_id ?? `unknown_${index}`,
          userName: shift.user_name,
          trackId,
          original: shift,
          isEditing: isEditing
        };
      })
      .filter(Boolean)
      .sort((a, b) => a.startMinutes - b.startMinutes);

    // Исключаем редактируемую смену из занятых диапазонов, чтобы можно было её изменять
    const occupiedRanges = plannedIntervals
      .filter(interval => !interval.isEditing)
      .map((interval) => [interval.startMinutes, interval.endMinutes]);

    // Сначала строим стандартные freeRanges (для не-редактируемого режима)
    let freeRanges = (config.freeIntervals?.length ? config.freeIntervals : [{ start: config.slotStart, end: config.slotEnd }])
      .map((range) => {
        const start = timeStringToMinutes(range.start);
        const end = timeStringToMinutes(range.end);
        if (start === null || end === null || end <= start) {
          return null;
        }
        return {
          start: Math.max(slotStartMinutes, Math.min(start, slotEndMinutes)),
          end: Math.max(slotStartMinutes, Math.min(end, slotEndMinutes))
        };
      })
      .filter(Boolean)
      .sort((a, b) => a.start - b.start);

    if (!freeRanges.length) {
      freeRanges.push({ start: slotStartMinutes, end: slotEndMinutes });
    }

    const maxSlots = Number(config.maxEmployees) || 1;
    const positionTracks = Array.from({ length: maxSlots }, (_, index) => ({
      id: `position-${index + 1}`,
      intervals: [],
      userNames: new Set()
    }));

    const sortedPlanned = plannedIntervals.slice().sort((a, b) => a.startMinutes - b.startMinutes);
    sortedPlanned.forEach((interval) => {
      let assignedIndex = positionTracks.findIndex((track) => {
        if (!track.intervals.length) {
          return true;
        }
        const lastInterval = track.intervals[track.intervals.length - 1];
        return lastInterval.endMinutes <= interval.startMinutes;
      });
      if (assignedIndex === -1) {
        assignedIndex = positionTracks.findIndex((track) => track.intervals.length === 0);
      }
      if (assignedIndex === -1) {
        assignedIndex = 0;
      }
      const track = positionTracks[assignedIndex];
      track.intervals.push(interval);
      if (interval.userName) {
        track.userNames.add(interval.userName);
      }
    });

    positionTracks.forEach((track) => {
      track.userNames = Array.from(track.userNames);
    });

    const anchors = new Set([slotStartMinutes, slotEndMinutes]);
    plannedIntervals.forEach((interval) => {
      anchors.add(interval.startMinutes);
      anchors.add(interval.endMinutes);
    });
    freeRanges.forEach((range) => {
      anchors.add(range.start);
      anchors.add(range.end);
    });
    for (let point = slotStartMinutes; point <= slotEndMinutes; point += SNAP_INTERVAL_MINUTES) {
      anchors.add(point);
    }
    const sortedAnchors = Array.from(anchors).sort((a, b) => a - b);

    const parseOrDefault = (value, fallback) => {
      const parsed = timeStringToMinutes(value);
      if (parsed === null) {
        return fallback;
      }
      return parsed;
    };

    // В режиме редактирования используем время редактируемой смены
    let defaultStart, defaultEnd;
    let activeRange = null;
    let editingTrack = null;
    let editingTrackIndex = -1;
    
    if (isEditMode && editingShift) {
      const editStart = timeStringToMinutes(editingShift.start_time);
      const editEnd = timeStringToMinutes(editingShift.end_time);
      
      if (editStart !== null && editEnd !== null) {
        // Находим трек, на котором находится редактируемая смена
        const editingInterval = plannedIntervals.find(interval => interval.isEditing);
        
        if (editingInterval) {
          // Ищем трек, на котором находится редактируемая смена
          // Используем original.id для точного совпадения
          const editingId = editingInterval.original?.id;
          for (let i = 0; i < positionTracks.length; i++) {
            const track = positionTracks[i];
            const found = track.intervals.some(interval => {
              if (editingId && interval.original?.id) {
                return interval.original.id === editingId || String(interval.original.id) === String(editingId);
              }
              // Fallback: сравнение по времени и userId
              return interval.startMinutes === editingInterval.startMinutes && 
                     interval.endMinutes === editingInterval.endMinutes &&
                     interval.userId === editingInterval.userId;
            });
            if (found) {
              editingTrack = track;
              editingTrackIndex = i;
              break;
            }
          }
        }
        
        // Вычисляем свободное время в треке редактируемой смены
        // ВАЖНО: Редактируемая смена должна быть исключена из занятых интервалов,
        // чтобы свободное время до и после неё было правильно вычислено
        const trackIntervalsWithoutEditing = editingTrack 
          ? editingTrack.intervals.filter(interval => !interval.isEditing)
          : [];
        
        // Находим свободное время в треке, исключая редактируемую смену из занятых
        // ВАЖНО: Редактируемая смена НЕ считается занятой, поэтому свободное время
        // до и после неё должно быть доступно для планирования
        const trackFreeIntervals = [];
        let cursor = slotStartMinutes;
        
        // Сортируем занятые интервалы (БЕЗ редактируемой смены)
        const sortedOccupied = trackIntervalsWithoutEditing
          .sort((a, b) => a.startMinutes - b.startMinutes);
        
        sortedOccupied.forEach((interval) => {
          // Свободное время до этого занятого интервала
          if (interval.startMinutes > cursor) {
            trackFreeIntervals.push({ start: cursor, end: interval.startMinutes });
          }
          cursor = Math.max(cursor, interval.endMinutes);
        });
        
        // Свободное время после всех занятых интервалов
        if (cursor < slotEndMinutes) {
          trackFreeIntervals.push({ start: cursor, end: slotEndMinutes });
        }
        
        // КРИТИЧНО: Нужно правильно определить freeBefore и freeAfter относительно редактируемой смены
        // freeBefore: свободное время, которое заканчивается в начале редактируемой смены (editStart)
        // freeAfter: свободное время, которое начинается в конце редактируемой смены (editEnd)
        
        // Ищем интервалы, которые примыкают к редактируемой смене
        const freeBefore = trackFreeIntervals.find(range => range.end === editStart);
        const freeAfter = trackFreeIntervals.find(range => range.start === editEnd);
        
        // Если не нашли точное совпадение, проверяем, может быть редактируемая смена находится внутри свободного интервала
        let actualFreeBefore = freeBefore;
        let actualFreeAfter = freeAfter;
        
        if (!actualFreeBefore) {
          // Ищем интервал, который содержит начало редактируемой смены
          const containingBefore = trackFreeIntervals.find(r => 
            r.start <= editStart && r.end >= editStart
          );
          if (containingBefore) {
            // Разбиваем интервал: до редактируемой смены и после
            actualFreeBefore = { start: containingBefore.start, end: editStart };
            // Если после редактируемой смены тоже есть место в этом интервале, добавляем его
            if (containingBefore.end > editEnd) {
              trackFreeIntervals.push({ start: editEnd, end: containingBefore.end });
            }
          } else {
            // Ищем ближайший интервал, который заканчивается до редактируемой смены
            actualFreeBefore = trackFreeIntervals
              .filter(r => r.end <= editStart)
              .sort((a, b) => b.end - a.end)[0];
          }
        }
        
        if (!actualFreeAfter) {
          // Ищем интервал, который содержит конец редактируемой смены
          const containingAfter = trackFreeIntervals.find(r => 
            r.start <= editEnd && r.end >= editEnd
          );
          if (containingAfter) {
            // Разбиваем интервал: до редактируемой смены и после
            actualFreeAfter = { start: editEnd, end: containingAfter.end };
            // Если до редактируемой смены тоже есть место в этом интервале, добавляем его
            if (containingAfter.start < editStart) {
              trackFreeIntervals.push({ start: containingAfter.start, end: editStart });
            }
          } else {
            // Ищем ближайший интервал, который начинается после редактируемой смены
            actualFreeAfter = trackFreeIntervals
              .filter(r => r.start >= editEnd)
              .sort((a, b) => a.start - b.start)[0];
          }
        }
        
        // Объединяем: свободное время слева + редактируемая смена + свободное время справа
        const rangeStart = actualFreeBefore ? actualFreeBefore.start : editStart;
        const rangeEnd = actualFreeAfter ? actualFreeAfter.end : editEnd;
        
        activeRange = { start: rangeStart, end: rangeEnd };
        
        // Пересчитываем freeRanges для режима редактирования: включаем редактируемую смену и примыкающее свободное время
        // ВАЖНО: Объединяем все в один диапазон, чтобы бегунки могли двигаться по всей области
        freeRanges = [{ start: rangeStart, end: rangeEnd }];
        
        // Устанавливаем бегунки на края запланированной смены
        defaultStart = editStart;
        defaultEnd = editEnd;
      } else {
        defaultStart = parseOrDefault(config.startValue, freeRanges[0].start);
        defaultEnd = parseOrDefault(config.endValue, freeRanges[0].end);
        activeRange = freeRanges[0];
      }
    } else {
      defaultStart = parseOrDefault(config.startValue, freeRanges[0].start);
      defaultEnd = parseOrDefault(config.endValue, freeRanges[0].end);
      activeRange = freeRanges[0];
    }

    const snapToGrid = (value) => Math.round(value / SNAP_INTERVAL_MINUTES) * SNAP_INTERVAL_MINUTES;

    if (!activeRange) {
      activeRange = freeRanges[0] || { start: slotStartMinutes, end: slotEndMinutes };
    }

    defaultStart = snapToGrid(defaultStart);
    defaultEnd = snapToGrid(defaultEnd);

    // Ограничиваем бегунки пределами activeRange
    if (defaultStart < activeRange.start) {
      defaultStart = activeRange.start;
    }
    if (defaultEnd > activeRange.end) {
      defaultEnd = activeRange.end;
    }
    if (defaultEnd <= defaultStart) {
      defaultEnd = Math.min(activeRange.end, defaultStart + SNAP_INTERVAL_MINUTES);
    }

    const state = {
      slotStartMinutes,
      slotEndMinutes,
      startMinutes: defaultStart,
      endMinutes: defaultEnd,
      anchors: sortedAnchors,
      occupiedRanges,
      freeRanges,
      activeRange,
      lastMoved: null,
      activePositionIndex: isEditMode && editingTrackIndex >= 0 ? editingTrackIndex + 1 : 1,
      maxEmployees: maxSlots,
      positionTracks,
      currentTrack: editingTrack || (positionTracks[0] || { intervals: [], userNames: [] }),
      allPlannedIntervals: plannedIntervals,
      isEditMode: isEditMode,
      scheduleId: scheduleId,
      editingShift: editingShift,
      editingTrack: editingTrack
    };
    

    const calculateTrackFreeIntervals = (track) => {
      const intervalsSource = track && Array.isArray(track.intervals) ? track.intervals : [];
      if (!intervalsSource.length) {
        return [{ start: slotStartMinutes, end: slotEndMinutes }];
      }
      const busy = intervalsSource
        .map((interval) => [
          Math.max(slotStartMinutes, interval.startMinutes),
          Math.min(slotEndMinutes, interval.endMinutes)
        ])
        .filter(([start, end]) => end > start)
        .sort((a, b) => a[0] - b[0]);

      const result = [];
      let cursor = slotStartMinutes;
      busy.forEach(([start, end]) => {
        if (start > cursor) {
          result.push({ start: cursor, end: start });
        }
        cursor = Math.max(cursor, end);
      });
      if (cursor < slotEndMinutes) {
        result.push({ start: cursor, end: slotEndMinutes });
      }
      return result;
    };

    const positionTabsHtml =
      maxSlots > 1
        ? `<div class="scheduler-position-tabs" id="schedulerPositionTabs">
            ${Array.from({ length: maxSlots }).map((_, index) => {
              const track = state.positionTracks[index];
              const freeIntervals = calculateTrackFreeIntervals(track);
      const freeRange = freeIntervals[0] || null;
              const occupantText = track.userNames.length
                ? track.userNames.join(', ')
                : 'Свободно';
      const rangeLabel = freeRange
        ? `${minutesToTimeString(freeRange.start)} – ${minutesToTimeString(freeRange.end)}`
        : 'Нет свободного времени';
              return `
                <button type="button"
                        class="scheduler-position-tab ${index === 0 ? 'active' : ''}"
                        data-position-index="${index + 1}">
                  <span><strong>Время смены ${index + 1}</strong></span>
                  <span class="scheduler-position-info">${occupantText}</span>
                  <span class="scheduler-position-info">${rangeLabel}</span>
                </button>
              `;
            }).join('')}
           </div>`
        : '';

    container.innerHTML = `
      ${positionTabsHtml}
      <div class="scheduler-wrapper">
        <div class="scheduler-track-container">
          <div class="scheduler-track" id="schedulerTrack"></div>
          <input type="range" class="scheduler-range-input" id="schedulerStartRange" min="${state.slotStartMinutes}" max="${state.slotEndMinutes}" step="${SNAP_INTERVAL_MINUTES}" value="${state.startMinutes}">
          <input type="range" class="scheduler-range-input" id="schedulerEndRange" min="${state.slotStartMinutes}" max="${state.slotEndMinutes}" step="${SNAP_INTERVAL_MINUTES}" value="${state.endMinutes}">
        </div>
        <div class="scheduler-labels">
          <span>${config.slotStart}</span>
          <span>${config.slotEnd}</span>
        </div>
        <div class="scheduler-static-wrapper" id="schedulerSummaryWrapper"></div>
      </div>
      <div id="schedulerExistingSummary" class="mt-3"></div>
    `;

    const trackElement = document.getElementById('schedulerTrack');
    const startRange = document.getElementById('schedulerStartRange');
    const endRange = document.getElementById('schedulerEndRange');
    const summaryWrapper = document.getElementById('schedulerSummaryWrapper');
    const existingSummary = document.getElementById('schedulerExistingSummary');
    const positionTabs = document.getElementById('schedulerPositionTabs');

    if (!trackElement || !startRange || !endRange || !summaryWrapper) {
      return;
    }

    const updatePositionTabsUI = () => {
      if (!positionTabs) {
        return;
      }
      positionTabs.querySelectorAll('.scheduler-position-tab').forEach((button) => {
        const index = Number(button.dataset.positionIndex);
        button.classList.toggle('active', index === state.activePositionIndex);
      });
    };

    function computeFreeRangesFromIntervals(intervals) {
      const busy = intervals
        .map((interval) => [
          Math.max(state.slotStartMinutes, interval.startMinutes),
          Math.min(state.slotEndMinutes, interval.endMinutes)
        ])
        .filter(([start, end]) => end > start)
        .sort((a, b) => a[0] - b[0]);

      const result = [];
      let cursor = state.slotStartMinutes;
      busy.forEach(([start, end]) => {
        if (start > cursor) {
          result.push({ start: cursor, end: start });
        }
        cursor = Math.max(cursor, end);
      });
      if (cursor < state.slotEndMinutes) {
        result.push({ start: cursor, end: state.slotEndMinutes });
      }
      if (!result.length) {
        result.push({ start: state.slotStartMinutes, end: state.slotEndMinutes });
      }
      return result;
    }

    function findRangeContaining(start, end, ranges) {
      return (
        ranges.find((range) => start >= range.start && end <= range.end) ||
        ranges[0]
      );
    }

    const updateConfirmButtonState = () => {
      if (!confirmButton) {
        return;
      }
      const employeeSelect = document.getElementById('employeeSelectModal');
      const employeeSelected = Boolean(employeeSelect && employeeSelect.value);
      const hasAvailableRange = state.freeRanges.length > 0 && state.endMinutes > state.startMinutes;
      confirmButton.disabled = !(employeeSelected && hasAvailableRange);
    };

    function updateContextRanges({ resetSelection = false } = {}) {
      const currentTrack = state.positionTracks[state.activePositionIndex - 1] || {
        intervals: [],
        userNames: []
      };
      state.currentTrack = currentTrack;
      const busyIntervals = currentTrack.intervals || [];
      // В режиме редактирования исключаем редактируемую смену из occupiedRanges
      state.occupiedRanges = busyIntervals
        .filter(interval => !interval.isEditing)
        .map((interval) => [
          interval.startMinutes,
          interval.endMinutes
        ]);
      
      // В режиме редактирования пересчитываем freeRanges с учетом редактируемой смены
      if (state.isEditMode && state.editingShift) {
        const editStart = timeStringToMinutes(state.editingShift.start_time);
        const editEnd = timeStringToMinutes(state.editingShift.end_time);
        
        if (editStart !== null && editEnd !== null && state.editingTrack) {
          // Вычисляем свободное время в треке редактируемой смены (исключая саму редактируемую смену)
          const trackIntervalsWithoutEditing = state.editingTrack.intervals.filter(interval => !interval.isEditing);
          
          // Находим свободное время в треке
          const trackFreeIntervals = [];
          let cursor = state.slotStartMinutes;
          trackIntervalsWithoutEditing
            .sort((a, b) => a.startMinutes - b.startMinutes)
            .forEach((interval) => {
              if (interval.startMinutes > cursor) {
                trackFreeIntervals.push({ start: cursor, end: interval.startMinutes });
              }
              cursor = Math.max(cursor, interval.endMinutes);
            });
          if (cursor < state.slotEndMinutes) {
            trackFreeIntervals.push({ start: cursor, end: state.slotEndMinutes });
          }
          
          // Находим свободное время, которое находится вплотную слева и справа от редактируемой смены
          const freeBefore = trackFreeIntervals.find(range => range.end === editStart);
          const freeAfter = trackFreeIntervals.find(range => range.start === editEnd);
          
          // Объединяем: свободное время слева + редактируемая смена + свободное время справа
          if (freeBefore && freeAfter) {
            state.freeRanges = [{ start: freeBefore.start, end: freeAfter.end }];
          } else if (freeBefore) {
            state.freeRanges = [{ start: freeBefore.start, end: editEnd }];
          } else if (freeAfter) {
            state.freeRanges = [{ start: editStart, end: freeAfter.end }];
          } else {
            state.freeRanges = [{ start: editStart, end: editEnd }];
          }
        } else {
          state.freeRanges = calculateTrackFreeIntervals(currentTrack);
        }
      } else {
        state.freeRanges = calculateTrackFreeIntervals(currentTrack);
      }
      if (!state.freeRanges.length) {
        state.activeRange = null;
        state.startMinutes = state.slotStartMinutes;
        state.endMinutes = state.slotStartMinutes;
        state.lastMoved = null;
        return;
      }
      let targetRange = findRangeContaining(
        state.startMinutes,
        state.endMinutes,
        state.freeRanges
      );
      if (resetSelection || !targetRange) {
        targetRange = state.freeRanges[0];
        state.startMinutes = targetRange.start;
        state.endMinutes = targetRange.end;
        if (state.endMinutes <= state.startMinutes) {
          state.endMinutes = targetRange.end;
        }
        state.lastMoved = null;
      } else {
        state.startMinutes = Math.max(targetRange.start, Math.min(state.startMinutes, targetRange.end - SNAP_INTERVAL_MINUTES));
        state.endMinutes = Math.max(state.startMinutes + SNAP_INTERVAL_MINUTES, Math.min(state.endMinutes, targetRange.end));
      }
      state.activeRange = targetRange;
    }

    function renderTrack() {
      trackElement.innerHTML = '';

      // Отображаем занятые диапазоны (красные)
      state.occupiedRanges.forEach(([start, end]) => {
        const segment = document.createElement('div');
        segment.className = 'scheduler-segment occupied';
        segment.style.left = `${calculatePositionPercent(start, state.slotStartMinutes, state.slotEndMinutes)}%`;
        segment.style.width = `${calculateWidthPercent(start, end, state.slotStartMinutes, state.slotEndMinutes)}%`;
        trackElement.appendChild(segment);
      });

      // В режиме редактирования отображаем все доступные freeRanges как зеленые (доступные для планирования)
      if (state.isEditMode && state.freeRanges.length > 0) {
        state.freeRanges.forEach((range) => {
          const availableSegment = document.createElement('div');
          availableSegment.className = 'scheduler-segment selection';
          availableSegment.style.opacity = '0.4'; // Полупрозрачный зеленый для всего доступного диапазона
          availableSegment.style.left = `${calculatePositionPercent(range.start, state.slotStartMinutes, state.slotEndMinutes)}%`;
          availableSegment.style.width = `${calculateWidthPercent(range.start, range.end, state.slotStartMinutes, state.slotEndMinutes)}%`;
          trackElement.appendChild(availableSegment);
        });
      }

      // В режиме редактирования показываем исходное время редактируемой смены более ярким зеленым
      if (state.isEditMode && state.editingShift) {
        const editStart = timeStringToMinutes(state.editingShift.start_time);
        const editEnd = timeStringToMinutes(state.editingShift.end_time);
        if (editStart !== null && editEnd !== null) {
          const existingSegment = document.createElement('div');
          existingSegment.className = 'scheduler-segment existing';
          existingSegment.style.left = `${calculatePositionPercent(editStart, state.slotStartMinutes, state.slotEndMinutes)}%`;
          existingSegment.style.width = `${calculateWidthPercent(editStart, editEnd, state.slotStartMinutes, state.slotEndMinutes)}%`;
          trackElement.appendChild(existingSegment);
        }
      }

      // Отображаем текущий выбор (яркий зеленый) - поверх доступных диапазонов
      if (state.freeRanges.length > 0 && state.endMinutes > state.startMinutes) {
        const selection = document.createElement('div');
        selection.className = 'scheduler-segment selection';
        selection.style.left = `${calculatePositionPercent(state.startMinutes, state.slotStartMinutes, state.slotEndMinutes)}%`;
        selection.style.width = `${calculateWidthPercent(state.startMinutes, state.endMinutes, state.slotStartMinutes, state.slotEndMinutes)}%`;
        trackElement.appendChild(selection);
      }
    }

    function renderSelectionSummary() {
      if (!state.freeRanges.length || state.endMinutes <= state.startMinutes) {
        return `
          <div class="scheduler-summary-box text-muted">
            <span>Все доступное время для этой позиции уже занято.</span>
          </div>
        `;
      }
      const duration = state.endMinutes - state.startMinutes;
      return `
        <div class="scheduler-summary-box">
          <span>Начало: <strong>${minutesToTimeString(state.startMinutes)}</strong></span>
          <span>Окончание: <strong>${minutesToTimeString(state.endMinutes)}</strong></span>
          <span>Длительность: <strong>${formatDurationText(duration)}</strong></span>
        </div>
      `;
    }

    function renderFreeChips() {
      if (!state.freeRanges.length) {
        return '';
      }
      return `
        <div class="scheduler-freechips">
          ${state.freeRanges
            .map((range) => {
              const isActive = state.startMinutes >= range.start && state.endMinutes <= range.end;
              return `
                <div class="scheduler-freechip ${isActive ? 'active' : ''}"
                     data-range-start="${range.start}" data-range-end="${range.end}">
                  ${minutesToTimeString(range.start)} – ${minutesToTimeString(range.end)}
                </div>
              `;
            })
            .join('')}
        </div>
      `;
    }

    function renderExistingSummary() {
      if (!existingSummary) {
        return;
      }
      const currentTrack = state.currentTrack || {
        intervals: [],
        userNames: []
      };
      const intervals = currentTrack.intervals || [];
      const headerLabel = currentTrack.userNames && currentTrack.userNames.length
        ? currentTrack.userNames.join(', ')
        : 'Свободно';
      const listContent = intervals.length
        ? intervals
            .map(
              (interval) => `
                <li class="d-flex justify-content-between align-items-center py-1 px-2 rounded bg-white border mb-1">
                  <span class="text-primary fw-semibold">
                    ${minutesToTimeString(interval.startMinutes)} – ${minutesToTimeString(interval.endMinutes)}
                  </span>
                  <span class="text-muted small">${interval.userName || 'Сотрудник'}</span>
                </li>
              `
            )
            .join('')
        : '<li class="py-1 px-2 text-muted">Нет запланированных смен по этой позиции</li>';
      existingSummary.innerHTML = `
        <div class="scheduler-existing border rounded-3 p-3 bg-light mt-3">
          <div class="fw-semibold text-primary mb-2">${headerLabel}</div>
          <ul class="list-unstyled mb-0">
            ${listContent}
          </ul>
        </div>
      `;
    }

    function updateSummary() {
      summaryWrapper.innerHTML = renderSelectionSummary() + renderFreeChips();
      summaryWrapper.querySelectorAll('.scheduler-freechip').forEach((chip) => {
        chip.addEventListener('click', () => {
          const start = toNumber(chip.getAttribute('data-range-start'));
          const end = toNumber(chip.getAttribute('data-range-end'));
          if (start === null || end === null) {
            return;
          }
          state.activeRange = state.freeRanges.find((range) => range.start === start && range.end === end) || { start, end };
          state.startMinutes = start;
          state.endMinutes = Math.max(start + SNAP_INTERVAL_MINUTES, end);
          if (state.endMinutes > end) {
            state.endMinutes = end;
          }
          state.lastMoved = 'chip';
          applyStateChanges();
        });
      });
      renderExistingSummary();
      updateConfirmButtonState();
    }

    function clampToActiveRange(value) {
      if (!state.activeRange) {
        return value;
      }
      let clamped = value;
      if (clamped < state.activeRange.start) {
        clamped = state.activeRange.start;
      }
      if (clamped > state.activeRange.end) {
        clamped = state.activeRange.end;
      }
      return clamped;
    }

    function snapValue(value) {
      let closest = value;
      let bestDiff = Number.POSITIVE_INFINITY;
      state.anchors.forEach((anchor) => {
        const diff = Math.abs(anchor - value);
        if (diff < bestDiff) {
          bestDiff = diff;
          closest = anchor;
        }
      });
      return closest;
    }

    function resolveCollisions() {
      state.occupiedRanges.forEach(([occStart, occEnd]) => {
        const overlaps = state.startMinutes < occEnd && state.endMinutes > occStart;
        if (!overlaps) {
          return;
        }
        if (state.lastMoved === 'end') {
          state.endMinutes = occStart;
        } else {
          state.startMinutes = occEnd;
        }
      });
    }

    function enforceSingleGap() {
      // В режиме редактирования не перезаписываем activeRange, он уже правильно установлен при инициализации
      if (state.isEditMode && state.activeRange) {
        // Просто проверяем, что бегунки в пределах activeRange
        if (state.startMinutes < state.activeRange.start) {
          state.startMinutes = state.activeRange.start;
        }
        if (state.endMinutes > state.activeRange.end) {
          state.endMinutes = state.activeRange.end;
        }
        return;
      }
      
      // Для обычного режима используем стандартную логику
      const validRange = state.freeRanges.find((range) => state.startMinutes >= range.start && state.endMinutes <= range.end);
      if (validRange) {
        state.activeRange = validRange;
      } else {
        let bestRange = state.freeRanges[0];
        let bestSize = bestRange.end - bestRange.start;
        state.freeRanges.forEach((range) => {
          const size = range.end - range.start;
          if (size > bestSize) {
            bestRange = range;
            bestSize = size;
          }
        });
        state.activeRange = bestRange;
        state.startMinutes = bestRange.start;
        state.endMinutes = Math.min(bestRange.end, state.startMinutes + Math.max(SNAP_INTERVAL_MINUTES, bestRange.end - bestRange.start));
      }

      const startDetached = state.startMinutes > state.activeRange.start;
      const endDetached = state.endMinutes < state.activeRange.end;
      if (startDetached && endDetached) {
        if (state.lastMoved === 'start') {
          state.endMinutes = state.activeRange.end;
        } else if (state.lastMoved === 'end') {
          state.startMinutes = state.activeRange.start;
        } else {
          state.startMinutes = state.activeRange.start;
        }
      }
    }

    function applyStateChanges() {
      // В режиме редактирования не вызываем updateContextRanges, чтобы не перезаписывать activeRange
      if (!state.isEditMode) {
        updateContextRanges();
      }

      if (!state.freeRanges.length || !state.activeRange) {
        renderTrack();
        updateSummary();
        startRange.value = String(state.slotStartMinutes);
        endRange.value = String(state.slotStartMinutes);
        modalElement.dataset.selectedStart = '';
        modalElement.dataset.selectedEnd = '';
        startRange.setAttribute('disabled', 'true');
        endRange.setAttribute('disabled', 'true');
        updateConfirmButtonState();
        return;
      }

      // Ограничиваем общими границами тайм-слота
      state.startMinutes = Math.max(state.slotStartMinutes, Math.min(state.startMinutes, state.slotEndMinutes - SNAP_INTERVAL_MINUTES));
      state.endMinutes = Math.max(state.startMinutes + SNAP_INTERVAL_MINUTES, Math.min(state.endMinutes, state.slotEndMinutes));

      // В режиме редактирования не проверяем коллизии с занятыми диапазонами, так как мы уже исключили редактируемую смену
      if (!state.isEditMode) {
        resolveCollisions();
      }

      // Ограничиваем пределами activeRange (который включает свободное время слева и справа в режиме редактирования)
      state.startMinutes = clampToActiveRange(state.startMinutes);
      state.endMinutes = clampToActiveRange(state.endMinutes);
      if (state.endMinutes <= state.startMinutes) {
        state.endMinutes = Math.min(state.activeRange.end, state.startMinutes + SNAP_INTERVAL_MINUTES);
        if (state.endMinutes <= state.startMinutes) {
          state.startMinutes = Math.max(state.activeRange.start, state.endMinutes - SNAP_INTERVAL_MINUTES);
        }
      }

      enforceSingleGap();

      startRange.value = String(state.startMinutes);
      endRange.value = String(state.endMinutes);

      renderTrack();
      updateSummary();

      const startLabel = minutesToTimeString(state.startMinutes);
      const endLabel = minutesToTimeString(state.endMinutes);
      modalElement.dataset.selectedStart = startLabel;
      modalElement.dataset.selectedEnd = endLabel;
      updateConfirmButtonState();
    }

    function setActivePosition(positionIndex, { resetSelection = false } = {}) {
      state.activePositionIndex = positionIndex;
      modalElement.dataset.activePositionIndex = String(positionIndex);
      state.lastMoved = null;
      updatePositionTabsUI();
      // В режиме редактирования НЕ пересчитываем контекст, чтобы не потерять расширенный activeRange
      if (!state.isEditMode) {
        updateContextRanges({ resetSelection });
      }
      startRange.removeAttribute('disabled');
      endRange.removeAttribute('disabled');
      applyStateChanges();
    }

    if (positionTabs) {
      positionTabs.querySelectorAll('.scheduler-position-tab').forEach((button) => {
        button.addEventListener('click', () => {
          const index = Number(button.dataset.positionIndex) || 1;
          setActivePosition(index, { resetSelection: true });
        });
      });
      updatePositionTabsUI();
    }

    startRange.addEventListener('input', () => {
      const rawValue = Number(startRange.value);
      state.lastMoved = 'start';
      state.startMinutes = clampToActiveRange(snapValue(rawValue));
      if (state.startMinutes >= state.endMinutes) {
        state.endMinutes = Math.min(state.slotEndMinutes, state.startMinutes + SNAP_INTERVAL_MINUTES);
      }
      applyStateChanges();
    });

    endRange.addEventListener('input', () => {
      const rawValue = Number(endRange.value);
      state.lastMoved = 'end';
      state.endMinutes = clampToActiveRange(snapValue(rawValue));
      if (state.endMinutes <= state.startMinutes) {
        state.startMinutes = Math.max(state.slotStartMinutes, state.endMinutes - SNAP_INTERVAL_MINUTES);
      }
      applyStateChanges();
    });

    if (!positionTabs) {
      updatePositionTabsUI();
    }

    // В режиме редактирования не сбрасываем выбор, чтобы сохранить activeRange
    setActivePosition(state.activePositionIndex, { resetSelection: !state.isEditMode });
    modalElement.addEventListener('planshift:employee-changed', updateConfirmButtonState);
    updateConfirmButtonState();
  }

  async function fetchJson(url) {
    const response = await fetch(url, { credentials: 'include' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  }

  async function openModal(timeslotId) {
    try {
      const notify = activeConfig.notify || defaultConfig.notify;
      const timeslotElement = document.querySelector(`[data-timeslot-id="${timeslotId}"]`);
      const detailUrl = activeConfig.timeslotDetailEndpoint(timeslotId);
      
      const timeslotData = await fetchJson(detailUrl);

      const slotInfo = timeslotData?.slot ?? {};
      const scheduledShiftsRaw = Array.isArray(timeslotData?.scheduled) ? timeslotData.scheduled : [];

      const slotStartRaw = slotInfo.start_time || null;
      const slotEndRaw = slotInfo.end_time || null;
      const fallbackSlotStart = timeslotElement?.dataset.timeslotStartTime || null;
      const fallbackSlotEnd = timeslotElement?.dataset.timeslotEndTime || null;

      const slotStart = slotStartRaw || fallbackSlotStart || null;
      const slotEnd = slotEndRaw || fallbackSlotEnd || null;
      const objectId = slotInfo.object_id || timeslotElement?.dataset.timeslotObjectId || timeslotElement?.dataset.objectId;
      const objectName = slotInfo.object_name || timeslotElement?.dataset.timeslotObjectName || null;
      const slotDate = slotInfo.date || timeslotElement?.dataset.timeslotDate || '';
      const timeRange = slotStart && slotEnd ? `${slotStart} - ${slotEnd}` : '';

      if (!objectId) {
        notify('Не удалось определить объект тайм-слота', 'error');
        return;
      }

      const normalizeTimeLabel = (value) => {
        if (!value) {
          return '';
        }
        if (typeof value === 'string') {
          if (/^\d{2}:\d{2}$/.test(value)) {
            return value;
          }
          if (/^\d{2}:\d{2}:\d{2}$/.test(value)) {
            return value.slice(0, 5);
          }
          const iso = formatTimeFromISO(value);
          if (iso) {
            return iso;
          }
        }
        return '';
      };

      const plannedShifts = scheduledShiftsRaw
        .map((shift) => {
          const startSource = shift.planned_start || shift.start_time;
          const endSource = shift.planned_end || shift.end_time;
          const startLabel = normalizeTimeLabel(startSource);
          const endLabel = normalizeTimeLabel(endSource);
          return {
            id: shift.id,
            user_id: shift.user_id,
            user_name: shift.user_name || 'Без имени',
            start_iso: typeof shift.planned_start === 'string' ? shift.planned_start : null,
            end_iso: typeof shift.planned_end === 'string' ? shift.planned_end : null,
            start_time: startLabel,
            end_time: endLabel
          };
        })
        .filter((shift) => shift.start_time && shift.end_time)
        .sort((a, b) => (timeStringToMinutes(a.start_time) - timeStringToMinutes(b.start_time)));

      const effectiveSlotStart = slotStart || fallbackSlotStart || '';
      const effectiveSlotEnd = slotEnd || fallbackSlotEnd || '';

      const freeIntervals = calculateFreeIntervals(effectiveSlotStart, effectiveSlotEnd, plannedShifts);
      // Определяем, есть ли запланированная смена для редактирования
      const scheduleId = activeConfig.scheduleId;
      const isEditMode = scheduleId !== null && scheduleId !== undefined;
      
      // Находим редактируемую смену в списке запланированных
      let editingShift = null;
      if (isEditMode) {
        editingShift = plannedShifts.find(s => s.id === scheduleId || String(s.id) === String(scheduleId));
        
      }

      const defaultInterval = selectDefaultInterval(effectiveSlotStart, effectiveSlotEnd, freeIntervals);
      let startValue = defaultInterval.start || effectiveSlotStart || '';
      let endValue = defaultInterval.end || effectiveSlotEnd || '';

      // В режиме редактирования всегда берем границы из редактируемой смены
      if (isEditMode && editingShift && editingShift.start_time && editingShift.end_time) {
        startValue = editingShift.start_time;
        endValue = editingShift.end_time;
      }

      const normalizedStartValue = minutesToTimeString(timeStringToMinutes(startValue));
      const normalizedEndValue = minutesToTimeString(timeStringToMinutes(endValue));

      const existingModal = document.getElementById('addEmployeeToTimeslotModal');
      if (existingModal) {
        existingModal.remove();
      }

      const modalHtml = `
        <div class="modal fade" id="addEmployeeToTimeslotModal" tabindex="-1" data-timeslot-id="${timeslotId}" data-object-id="${objectId}">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title"><i class="bi bi-person-plus"></i> Добавить сотрудника в тайм-слот</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <div class="mb-3">
                  <div class="d-flex flex-wrap gap-2 mb-3" style="gap: 0.5rem;">
                    <span class="badge bg-secondary">${slotDate || '—'}</span>
                    <span class="badge bg-secondary">${timeRange || '—'}</span>
                    <span class="badge bg-secondary">${objectName || '—'}</span>
                  </div>
                  <label for="employeeSelectModal" class="form-label">Выберите сотрудника *</label>
                  <select class="form-select" id="employeeSelectModal" required>
                    <option value="">Загрузка сотрудников...</option>
                  </select>
                </div>
                <div class="mb-3">
                  <label class="form-label">Время смены в тайм-слоте *</label>
                  <div id="timeslotScheduler"></div>
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Отмена</button>
                ${isEditMode ? `<button type="button" class="btn btn-danger me-auto" id="deleteShiftBtn">
                  <i class="bi bi-trash"></i> Удалить
                </button>` : ''}
                <button type="button" class="btn btn-success" id="confirmAddEmployeeBtn">
                  <i class="bi bi-check-lg"></i> Добавить
                </button>
              </div>
            </div>
          </div>
        </div>
      `;

      document.body.insertAdjacentHTML('beforeend', modalHtml);
      ensureSchedulerStyles();

      const modalElement = document.getElementById('addEmployeeToTimeslotModal');
      const confirmButton = document.getElementById('confirmAddEmployeeBtn');
      if (!modalElement || !confirmButton) {
        notify('Не удалось открыть окно', 'error');
        return;
      }
      
      // Изменяем заголовок и текст кнопки для режима редактирования
      const modalTitle = modalElement.querySelector('.modal-title');
      if (modalTitle) {
        modalTitle.innerHTML = isEditMode 
          ? '<i class="bi bi-pencil"></i> Изменить смену'
          : '<i class="bi bi-calendar-plus"></i> Запланировать смену';
      }
      
      // Изменяем текст кнопки
      if (isEditMode) {
        confirmButton.innerHTML = '<i class="bi bi-check-lg"></i> Изменить';
      } else {
        confirmButton.innerHTML = '<i class="bi bi-check-lg"></i> Добавить';
      }

      modalElement.dataset.selectedStart = normalizedStartValue || startValue;
      modalElement.dataset.selectedEnd = normalizedEndValue || endValue;
      const maxEmployees = Number(slotInfo.max_employees ?? timeslotElement?.dataset.timeslotMaxEmployees ?? 1) || 1;

      // Дублируем для совместимости со старой логикой
      modalElement.dataset.selectedStart = normalizedStartValue || startValue;
      modalElement.dataset.selectedEnd = normalizedEndValue || endValue;
      modalElement.dataset.activePositionIndex = '1';
      modalElement.dataset.maxEmployees = String(maxEmployees);

      modalElement.addEventListener('hidden.bs.modal', () => {
        modalElement.remove();
      });

      initializeScheduler({
        slotStart: effectiveSlotStart || '',
        slotEnd: effectiveSlotEnd || '',
        startValue,
        endValue,
        freeIntervals,
        plannedShifts,
        slotDate: slotDate || '',
        maxEmployees,
        scheduleId: scheduleId,
        editingShift: editingShift
      });

      const employeesResponse = await fetchJson(activeConfig.employeesForObjectEndpoint(objectId));
      const normalizedEmployees = normalizeEmployeesData(employeesResponse);
      const activeEmployees = normalizedEmployees.filter((emp) => !emp.isFormer);
      const formerEmployees = normalizedEmployees.filter((emp) => emp.isFormer);
      const select = document.getElementById('employeeSelectModal');
      if (select) {
        const preselectedId = activeConfig.preselectedEmployeeId;
        const lockedId = activeConfig.lockEmployeeSelection
          ? (activeConfig.lockedEmployeeId ?? preselectedId)
          : null;
        const lockedNameFromConfig = activeConfig.lockedEmployeeName;
        
        // В режиме редактирования используем сотрудника из редактируемой смены
        const editModeEmployeeId = isEditMode && editingShift ? editingShift.user_id : null;

        if (activeConfig.lockEmployeeSelection && lockedId !== null && !isEditMode) {
          let displayName = lockedNameFromConfig;
          if (!displayName) {
            const match = normalizedEmployees.find((emp) => Number(emp.id) === Number(lockedId));
            if (match) {
              displayName = match.name;
              if (match.isFormer) {
                displayName = `${displayName} (бывший)`;
              }
            }
          }
          if (!displayName) {
            displayName = 'Выбранный сотрудник';
          }
          select.innerHTML = `<option value="${lockedId}">${escapeHtml(displayName)}</option>`;
          select.value = String(lockedId);
          select.setAttribute('disabled', 'true');
        } else if (normalizedEmployees.length) {
          const options = ['<option value="">Выберите сотрудника</option>'];

          activeEmployees.forEach((emp) => {
            options.push(`<option value="${emp.id}">${escapeHtml(emp.name)}</option>`);
          });

          if (formerEmployees.length) {
            options.push('<option value="" disabled>— Бывшие —</option>');
            formerEmployees.forEach((emp) => {
              options.push(`<option value="${emp.id}">${escapeHtml(emp.name)} (бывший)</option>`);
            });
          }

          select.innerHTML = options.join('');
          
          // В режиме редактирования выбираем сотрудника из редактируемой смены
          const employeeIdToSelect = isEditMode && editModeEmployeeId !== null 
            ? editModeEmployeeId 
            : preselectedId;
          
          if (employeeIdToSelect !== null) {
            select.value = String(employeeIdToSelect);
            if (select.value !== String(employeeIdToSelect)) {
              const fallbackEmployee = normalizedEmployees.find((emp) => Number(emp.id) === Number(employeeIdToSelect));
              let fallbackName =
                lockedNameFromConfig
                || fallbackEmployee?.name
                || 'Выбранный сотрудник';
              if (!lockedNameFromConfig && fallbackEmployee?.isFormer && !fallbackName.toLowerCase().includes('бывш')) {
                fallbackName = `${fallbackName} (бывший)`;
              }
              select.innerHTML += `<option value="${employeeIdToSelect}">${escapeHtml(fallbackName)}</option>`;
              select.value = String(employeeIdToSelect);
            }
          }
        } else {
          const fallbackId = preselectedId;
          const fallbackEmployee = normalizedEmployees.find((emp) => Number(emp.id) === Number(preselectedId));
          let fallbackName =
            lockedNameFromConfig
            || fallbackEmployee?.name
            || (fallbackId !== null ? 'Выбранный сотрудник' : null);
          if (!lockedNameFromConfig && fallbackEmployee?.isFormer && fallbackName && !fallbackName.toLowerCase().includes('бывш')) {
            fallbackName = `${fallbackName} (бывший)`;
          }

          if (preselectedId !== null) {
            select.innerHTML = `<option value="${preselectedId}">${escapeHtml(fallbackName)}</option>`;
            select.value = String(preselectedId);
            if (activeConfig.lockEmployeeSelection) {
              select.setAttribute('disabled', 'true');
            }
          } else {
            select.innerHTML = '<option value="">Нет сотрудников с доступом к объекту</option>';
          }
        }

        select.addEventListener('change', () => {
          modalElement.dispatchEvent(new CustomEvent('planshift:employee-changed'));
        });
        modalElement.dispatchEvent(new CustomEvent('planshift:employee-changed'));
      }

      // Обработчик кнопки удаления (только в режиме редактирования)
      const deleteButton = document.getElementById('deleteShiftBtn');
      if (deleteButton && isEditMode && scheduleId !== null) {
        deleteButton.addEventListener('click', async () => {
          if (!confirm('Вы уверены, что хотите удалить эту запланированную смену?')) {
            return;
          }

          deleteButton.setAttribute('disabled', 'true');
          deleteButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Удаление...';

          try {
            // Используем endpoint для удаления
            const deleteEndpoint = activeConfig.planShiftEndpoint || '/owner/api/calendar/plan-shift';
            const response = await fetch(`${deleteEndpoint}/${scheduleId}`, {
              method: 'DELETE',
              headers: { 'Content-Type': 'application/json' }
            });

            let result = null;
            try {
              result = await response.json();
            } catch (parseError) {
              result = null;
            }

            if (!response.ok || (result && result.success === false)) {
              const message = result?.detail || result?.message || 'Ошибка удаления смены';
              throw new Error(message);
            }

            const modalInstance = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
            modalInstance.hide();
            notify(result?.message || 'Смена успешно удалена', 'success');

            if (activeConfig.onSuccess) {
              activeConfig.onSuccess({ 
                message: result?.message, 
                raw: result,
                action: 'delete'
              });
            }
            // Принудительно очищаем кэш и обновляем календарь
            if (window.calendarData) {
              window.calendarData = null;
            }
            if (window.universalCalendar) {
              if (window.universalCalendar.calendarData) {
                window.universalCalendar.calendarData = null;
              }
              // Принудительная перезагрузка данных
              if (window.universalCalendar.isMobile && window.universalCalendar.currentDate) {
                // Для мобильной версии перезагружаем текущий день
                const currentDate = window.universalCalendar.currentDate;
                if (window.universalCalendar.renderDayView) {
                  window.universalCalendar.renderDayView(currentDate);
                }
              } else if (window.universalCalendar.loadCalendarData) {
                // Для полного календаря перезагружаем данные
                window.universalCalendar.loadCalendarData(window.universalCalendar.currentDate || new Date());
              }
            }
            if (activeConfig.refreshCalendar) {
              activeConfig.refreshCalendar();
            } else if (window.universalCalendar && typeof window.universalCalendar.refresh === 'function') {
              window.universalCalendar.refresh();
            }
          } catch (error) {
            notify(error.message || 'Ошибка удаления смены', 'error');
            if (activeConfig.onError) {
              activeConfig.onError(error);
            }
          } finally {
            deleteButton.removeAttribute('disabled');
            deleteButton.innerHTML = '<i class="bi bi-trash"></i> Удалить';
          }
        });
      }

      confirmButton.addEventListener('click', async () => {
        const selectEl = document.getElementById('employeeSelectModal');
        if (!selectEl) {
          notify('Не удалось найти элементы формы', 'error');
          return;
        }
        const employeeId = selectEl.value;
        if (!employeeId) {
          notify('Выберите сотрудника', 'error');
          return;
        }

        const selectedStart = modalElement.dataset.selectedStart || startValue;
        const selectedEnd = modalElement.dataset.selectedEnd || endValue;
        const startMinutes = timeStringToMinutes(selectedStart);
        const endMinutes = timeStringToMinutes(selectedEnd);
        if (startMinutes === null || endMinutes === null || endMinutes <= startMinutes) {
          notify('Проверьте корректность времени', 'error');
          return;
        }

        confirmButton.setAttribute('disabled', 'true');
        confirmButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Назначение...';

        try {
          const requestBody = {
            timeslot_id: Number(timeslotId),
            employee_id: Number(employeeId),
            start_time: selectedStart,
            end_time: selectedEnd
          };
          
          // В режиме редактирования добавляем schedule_id
          if (isEditMode && scheduleId !== null) {
            requestBody.schedule_id = Number(scheduleId);
          }
          
          const response = await fetch(activeConfig.planShiftEndpoint, {
            method: isEditMode ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
          });

          let result = null;
          try {
            result = await response.json();
          } catch (parseError) {
            result = null;
          }

          if (!response.ok || (result && result.success === false)) {
            const message = result?.detail || result?.message || 'Ошибка планирования смены';
            throw new Error(message);
          }

          const modalInstance = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
          modalInstance.hide();
          notify(result?.message || (isEditMode ? 'Смена успешно обновлена' : 'Смена успешно запланирована'), 'success');

          // Извлекаем дату планирования из ответа или из формы
          let plannedDate = null;
          if (result && result.shift && result.shift.planned_start) {
            plannedDate = new Date(result.shift.planned_start);
          } else if (result && result.planned_date) {
            plannedDate = new Date(result.planned_date);
          } else {
            // Пытаемся извлечь из формы
            const dateInput = modalElement.querySelector('input[name="date"]');
            const startTimeInput = modalElement.querySelector('input[name="start_time"]');
            if (dateInput && startTimeInput) {
              const dateStr = dateInput.value;
              const timeStr = startTimeInput.value;
              if (dateStr && timeStr) {
                plannedDate = new Date(`${dateStr}T${timeStr}`);
              }
            }
          }
          
          // Принудительно очищаем кэш и обновляем календарь после обновления/создания смены
          if (window.calendarData) {
            window.calendarData = null;
          }
          if (window.universalCalendar) {
            if (window.universalCalendar.calendarData) {
              window.universalCalendar.calendarData = null;
            }
            // Принудительная перезагрузка данных
            if (window.universalCalendar.isMobile && window.universalCalendar.currentDate) {
              // Для мобильной версии перезагружаем текущий день
              const currentDate = window.universalCalendar.currentDate;
              if (window.universalCalendar.renderDayView) {
                window.universalCalendar.renderDayView(currentDate);
              }
            } else if (window.universalCalendar.loadCalendarData) {
              // Для полного календаря перезагружаем данные
              window.universalCalendar.loadCalendarData(window.universalCalendar.currentDate || new Date());
            }
          }
          
          if (activeConfig.onSuccess) {
            activeConfig.onSuccess({ 
              message: result?.message, 
              raw: result,
              plannedDate: plannedDate,
              action: isEditMode ? 'update' : 'create'
            });
          }
          if (activeConfig.refreshCalendar) {
            activeConfig.refreshCalendar(plannedDate);
          } else if (window.universalCalendar && typeof window.universalCalendar.refresh === 'function') {
            window.universalCalendar.refresh(plannedDate);
          }
        } catch (error) {
          notify(error.message || 'Ошибка планирования смены', 'error');
          if (activeConfig.onError) {
            activeConfig.onError(error);
          }
        } finally {
          confirmButton.removeAttribute('disabled');
          // Восстанавливаем текст кнопки в зависимости от режима
          const isEditMode = activeConfig.scheduleId !== null && activeConfig.scheduleId !== undefined;
          confirmButton.innerHTML = isEditMode 
            ? '<i class="bi bi-check-lg"></i> Изменить'
            : '<i class="bi bi-check-lg"></i> Добавить';
        }
      });

      const modalInstance = new bootstrap.Modal(modalElement);
      modalInstance.show();
    } catch (error) {
      activeConfig.notify?.(error.message || 'Ошибка открытия окна назначения', 'error');
      if (activeConfig.onError) {
        activeConfig.onError(error);
      }
    }
  }

  window.PlanShiftModal = {
    configure(options) {
      activeConfig = { ...activeConfig, ...options };
    },
    open(timeslotId) {
      return openModal(timeslotId);
    }
  };
})();
