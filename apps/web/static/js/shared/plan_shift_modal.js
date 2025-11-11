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
        return {
          startMinutes: Math.max(slotStartMinutes, Math.min(start, slotEndMinutes)),
          endMinutes: Math.max(slotStartMinutes, Math.min(end, slotEndMinutes)),
          userId: shift.user_id ?? `unknown_${index}`,
          userName: shift.user_name,
          trackId,
          original: shift
        };
      })
      .filter(Boolean)
      .sort((a, b) => a.startMinutes - b.startMinutes);

    const occupiedRanges = plannedIntervals.map((interval) => [interval.startMinutes, interval.endMinutes]);

    const freeRanges = (config.freeIntervals?.length ? config.freeIntervals : [{ start: config.slotStart, end: config.slotEnd }])
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

    let defaultStart = parseOrDefault(config.startValue, freeRanges[0].start);
    let defaultEnd = parseOrDefault(config.endValue, freeRanges[0].end);

    const snapToGrid = (value) => Math.round(value / SNAP_INTERVAL_MINUTES) * SNAP_INTERVAL_MINUTES;

    const findContainingRange = (startMinutes, endMinutes) =>
      freeRanges.find((range) => startMinutes >= range.start && endMinutes <= range.end) || freeRanges[0];

    let activeRange = findContainingRange(defaultStart, defaultEnd);
    defaultStart = snapToGrid(defaultStart);
    defaultEnd = snapToGrid(defaultEnd);

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
      activePositionIndex: 1,
      maxEmployees: maxSlots,
      positionTracks,
      currentTrack: positionTracks[0] || { intervals: [], userNames: [] },
      allPlannedIntervals: plannedIntervals
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
      <div class="mt-2 text-muted" style="font-size: 12px;">
        Бегунки прилипают к границам тайм-слота, уже запланированных смен и шагу ${SNAP_INTERVAL_MINUTES} минут.
      </div>
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
      state.occupiedRanges = busyIntervals.map((interval) => [
        interval.startMinutes,
        interval.endMinutes
      ]);
      state.freeRanges = calculateTrackFreeIntervals(currentTrack);
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

      state.occupiedRanges.forEach(([start, end]) => {
        const segment = document.createElement('div');
        segment.className = 'scheduler-segment occupied';
        segment.style.left = `${calculatePositionPercent(start, state.slotStartMinutes, state.slotEndMinutes)}%`;
        segment.style.width = `${calculateWidthPercent(start, end, state.slotStartMinutes, state.slotEndMinutes)}%`;
        trackElement.appendChild(segment);
      });

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
      updateContextRanges();

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

      state.startMinutes = Math.max(state.slotStartMinutes, Math.min(state.startMinutes, state.slotEndMinutes - SNAP_INTERVAL_MINUTES));
      state.endMinutes = Math.max(state.startMinutes + SNAP_INTERVAL_MINUTES, Math.min(state.endMinutes, state.slotEndMinutes));

      resolveCollisions();

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
      updateContextRanges({ resetSelection });
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

    setActivePosition(state.activePositionIndex, { resetSelection: true });
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
      const defaultInterval = selectDefaultInterval(effectiveSlotStart, effectiveSlotEnd, freeIntervals);
      const startValue = defaultInterval.start || effectiveSlotStart || '';
      const endValue = defaultInterval.end || effectiveSlotEnd || '';

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
                  <div class="alert alert-secondary mb-3">
                    <div><strong>Дата:</strong> ${slotDate || '—'}</div>
                    <div><strong>Время:</strong> ${timeRange || '—'}</div>
                    <div><strong>Объект:</strong> ${objectName || '—'}</div>
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

      modalElement.dataset.selectedStart = startValue;
      modalElement.dataset.selectedEnd = endValue;
      const maxEmployees = Number(slotInfo.max_employees ?? timeslotElement?.dataset.timeslotMaxEmployees ?? 1) || 1;

      modalElement.dataset.selectedStart = startValue;
      modalElement.dataset.selectedEnd = endValue;
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
        maxEmployees
      });

      const employees = await fetchJson(activeConfig.employeesForObjectEndpoint(objectId));
      const select = document.getElementById('employeeSelectModal');
      if (select) {
        const preselectedId = activeConfig.preselectedEmployeeId;
        const lockedId = activeConfig.lockEmployeeSelection
          ? (activeConfig.lockedEmployeeId ?? preselectedId)
          : null;
        const lockedNameFromConfig = activeConfig.lockedEmployeeName;

        if (activeConfig.lockEmployeeSelection && lockedId !== null) {
          let displayName = lockedNameFromConfig;
          if (!displayName && Array.isArray(employees)) {
            const match = employees.find((emp) => Number(emp.id) === Number(lockedId));
            if (match && match.name) {
              displayName = match.name;
            }
          }
          if (!displayName) {
            displayName = 'Выбранный сотрудник';
          }
          select.innerHTML = `<option value="${lockedId}">${escapeHtml(displayName)}</option>`;
          select.value = String(lockedId);
          select.setAttribute('disabled', 'true');
        } else if (Array.isArray(employees) && employees.length) {
          const options = ['<option value="">Выберите сотрудника</option>']
            .concat(
              employees.map(
                (emp) =>
                  `<option value="${emp.id}">${escapeHtml(emp.name)}</option>`
              )
            )
            .join('');
          select.innerHTML = options;
          if (preselectedId !== null) {
            select.value = String(preselectedId);
          }
        } else {
          if (preselectedId !== null) {
            const fallbackName = lockedNameFromConfig || 'Выбранный сотрудник';
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
          const response = await fetch(activeConfig.planShiftEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              timeslot_id: Number(timeslotId),
              employee_id: Number(employeeId),
              start_time: selectedStart,
              end_time: selectedEnd
            })
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
          notify(result?.message || 'Смена успешно запланирована', 'success');

          if (activeConfig.onSuccess) {
            activeConfig.onSuccess({ message: result?.message, raw: result });
          }
          if (activeConfig.refreshCalendar) {
            activeConfig.refreshCalendar();
          } else if (window.universalCalendar && typeof window.universalCalendar.refresh === 'function') {
            window.universalCalendar.refresh();
          }
        } catch (error) {
          notify(error.message || 'Ошибка планирования смены', 'error');
          if (activeConfig.onError) {
            activeConfig.onError(error);
          }
        } finally {
          confirmButton.removeAttribute('disabled');
          confirmButton.innerHTML = '<i class="bi bi-check-lg"></i> Добавить';
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
