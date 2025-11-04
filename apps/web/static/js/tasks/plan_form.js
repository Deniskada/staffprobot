// JS логика формы создания плана задач v2
(function() {
  const $ = (id) => document.getElementById(id);

  function setRecurNoneLabel() {
    const plannedDate = $('planned_date').value;
    const label = $('recur_none_label');
    if (!label) return;
    // Если дата пустая: это ежедневное повторение (семантически recurring None без даты = каждый день)
    label.textContent = plannedDate ? 'Не повторять' : 'Повторять каждый день';
  }

  function updateDateLabel() {
    const plannedDateLabel = $('planned_date_label');
    const rt = document.querySelector('input[name="recurrence_type"]:checked')?.value || '';
    if (rt === 'weekdays' || rt === 'day_interval') {
      plannedDateLabel.textContent = 'Дата начала периода повторения';
      $('planned_date_hint').textContent = 'Оставьте пустым, чтобы начать с ближайшей подходящей даты';
    } else {
      plannedDateLabel.textContent = 'Дата (опционально)';
      $('planned_date_hint').textContent = 'Оставьте пустым для постоянного назначения';
    }
  }

  function toRuWeekday(date) {
    const names = ['Воскресенье','Понедельник','Вторник','Среда','Четверг','Пятница','Суббота'];
    return names[date.getDay()];
  }

  function fmt(d) {
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yy = String(d.getFullYear()).slice(-2);
    return `${dd}.${mm}.${yy}`;
  }

  function parseISO(dateStr) {
    if (!dateStr) return null;
    const d = new Date(dateStr + 'T00:00:00');
    return isNaN(d.getTime()) ? null : d;
    }

  function computePreview() {
    const preview = $('recurrence_preview');
    if (!preview) return;

    const rt = document.querySelector('input[name="recurrence_type"]:checked')?.value || '';
    const startDate = parseISO($('planned_date').value) || new Date();

    let dates = [];
    if (!rt) {
      // Нет повторения: если дата задана — один раз; иначе — ежедневно
      if ($('planned_date').value) {
        dates = [startDate];
      } else {
        // ежедневные 2 ближайшие даты
        dates = [new Date(startDate), new Date(startDate.getTime() + 24*3600*1000)];
      }
    } else if (rt === 'weekdays') {
      const checked = Array.from(document.querySelectorAll('input[name="weekday"]:checked')).map(i => parseInt(i.value, 10));
      if (checked.length === 0) {
        preview.textContent = '';
        return;
      }
      let d = new Date(startDate);
      while (dates.length < 3) {
        const iso = (d.getDay() === 0 ? 7 : d.getDay()); // 1..7
        if (checked.includes(iso)) dates.push(new Date(d));
        d.setDate(d.getDate() + 1);
        // Защита от бесконечного цикла
        if (dates.length === 0 && d.getTime() - startDate.getTime() > 14 * 24 * 3600 * 1000) break;
      }
    } else if (rt === 'day_interval') {
      let interval = parseInt($('day_interval').value || '1', 10);
      if (!interval || interval < 1) interval = 1;
      dates = [new Date(startDate), new Date(startDate.getTime() + interval*24*3600*1000)];
    }

    if (dates.length === 0) { preview.textContent = ''; return; }
    const parts = dates.map(d => `${toRuWeekday(d)}, ${fmt(d)}`);
    preview.textContent = `В следующий раз эта задача будет назначена: ${parts.join(', ')}`;
  }

  function toggleCreationMode() {
    const mode = document.querySelector('input[name="creation_mode"]:checked')?.value || 'template';
    const tplGroup = $('template_select_group');
    const disabled = (mode !== 'template');
    tplGroup.style.display = disabled ? 'none' : 'block';

    // Переключение доступности полей при режиме без шаблона
    const title = $('task_title');
    const desc = $('task_description');
    const amount = $('task_amount');
    const mandatory = $('task_mandatory');
    const media = $('task_media');
    const geolocation = $('task_geolocation');
    const code = $('task_code');
    if (mode === 'template') {
      [title, desc, amount].forEach(f => { f.disabled = true; f.style.backgroundColor = '#e9ecef'; });
      [mandatory, media].forEach(f => { f.disabled = true; f.parentElement.style.opacity = '0.6'; });
      code.disabled = true; code.style.backgroundColor = '#e9ecef';
      fillFromTemplate();
    } else {
      [title, desc, amount].forEach(f => { f.disabled = false; f.style.backgroundColor = ''; });
      [mandatory, media, geolocation].forEach(f => { f.disabled = false; f.parentElement.style.opacity = '1'; });
      code.disabled = true; code.style.backgroundColor = '#e9ecef'; code.value = '[авто]';
    }
  }

  function fillFromTemplate() {
    const select = $('template_id');
    const opt = select.options[select.selectedIndex];
    if (!opt || !opt.value) {
      $('task_title').value = '';
      $('task_description').value = '';
      $('task_mandatory').checked = false;
      $('task_media').checked = false;
      $('task_geolocation').checked = false;
      $('task_amount').value = '';
      $('task_code').value = '';
      return;
    }
    $('task_title').value = opt.dataset.title || '';
    $('task_description').value = opt.dataset.description || '';
    $('task_mandatory').checked = (opt.dataset.mandatory === 'True');
    $('task_media').checked = (opt.dataset.media === 'True');
    $('task_geolocation').checked = (opt.dataset.geolocation === 'True');
    $('task_amount').value = opt.dataset.amount || '';
    $('task_code').value = opt.dataset.code || '';
  }

  function onRecurrenceChange() {
    const rt = document.querySelector('input[name="recurrence_type"]:checked')?.value || '';
    $('weekdays_group').style.display = (rt === 'weekdays') ? 'block' : 'none';
    $('interval_group').style.display = (rt === 'day_interval') ? 'block' : 'none';
    $('end_date_group').style.display = (rt ? 'block' : 'none');
    updateDateLabel();
    setRecurNoneLabel();
    computePreview();
  }

  function init() {
    // Инициализация начальных состояний
    toggleCreationMode();
    onRecurrenceChange();
    setRecurNoneLabel();
    computePreview();

    // Слушатели событий
    document.querySelectorAll('input[name="creation_mode"]').forEach(el => el.addEventListener('change', toggleCreationMode));
    $('template_id')?.addEventListener('change', fillFromTemplate);
    document.querySelectorAll('input[name="recurrence_type"]').forEach(el => el.addEventListener('change', onRecurrenceChange));
    document.querySelectorAll('input[name="weekday"]').forEach(el => el.addEventListener('change', computePreview));
    $('planned_date')?.addEventListener('input', () => { setRecurNoneLabel(); updateDateLabel(); computePreview(); });
    $('day_interval')?.addEventListener('input', computePreview);
  }

  document.addEventListener('DOMContentLoaded', init);
})();


