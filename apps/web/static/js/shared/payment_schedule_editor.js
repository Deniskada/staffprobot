/**
 * Редактор графиков выплат
 * Общий компонент для создания и редактирования кастомных графиков выплат
 */

class PaymentScheduleEditor {
    constructor(modalId, objectId) {
        this.modalId = modalId;
        this.objectId = objectId;
        this.modal = null;
        this.scheduleData = [];
    }
    
    init() {
        this.modal = new bootstrap.Modal(document.getElementById(this.modalId));
        this.attachEventListeners();
    }
    
    attachEventListeners() {
        const frequencySelect = document.getElementById('schedule_frequency');
        if (frequencySelect) {
            frequencySelect.addEventListener('change', () => this.onFrequencyChange());
        }
        
        const saveBtn = document.getElementById('save_schedule_btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveSchedule());
        }
    }
    
    onFrequencyChange() {
        const frequency = document.getElementById('schedule_frequency').value;
        const paramsContainer = document.getElementById('schedule_params');
        
        let html = '';
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        if (frequency === 'daily') {
            html = `
                <div class="mb-3">
                    <label class="form-label">Следующая дата выплаты</label>
                    <input type="date" 
                           id="next_payment_date" 
                           class="form-control" 
                           value="${this.formatDateInput(tomorrow)}"
                           onchange="window.paymentScheduleEditor.generateSchedule()">
                    <small class="text-muted">Дата первой выплаты</small>
                </div>
                <div class="mb-3">
                    <label class="form-label">Выберите дату (за которую производить выплаты)</label>
                    <input type="date" 
                           id="period_date" 
                           class="form-control" 
                           value="${this.formatDateInput(today)}"
                           onchange="window.paymentScheduleEditor.generateSchedule()">
                    <small class="text-muted">За какой день будет выплата</small>
                </div>
            `;
        } else if (frequency === 'weekly') {
            html = `
                <div class="mb-3">
                    <label class="form-label">День недели для выплаты *</label>
                    <select id="payment_day_of_week" class="form-select" onchange="updateNextPaymentDate();window.paymentScheduleEditor.generateSchedule()">
                        <option value="1">Понедельник</option>
                        <option value="2">Вторник</option>
                        <option value="3">Среда</option>
                        <option value="4">Четверг</option>
                        <option value="5" selected>Пятница</option>
                        <option value="6">Суббота</option>
                        <option value="7">Воскресенье</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Следующая дата выплаты</label>
                    <input type="date" 
                           id="next_payment_date" 
                           class="form-control" 
                           value="${this.getNextDayOfWeek(5)}"
                           readonly>
                    <small class="text-muted">Автоматически рассчитывается</small>
                </div>
                <div class="mb-3">
                    <label class="form-label">Выберите дату начала периода (за который производить выплаты)</label>
                    <input type="date" 
                           id="period_start_date" 
                           class="form-control" 
                           onchange="window.paymentScheduleEditor.generateSchedule()">
                </div>
                <div class="mb-3">
                    <label class="form-label">Выберите дату окончания периода (за который производить выплаты)</label>
                    <input type="date" 
                           id="period_end_date" 
                           class="form-control" 
                           onchange="window.paymentScheduleEditor.generateSchedule()">
                </div>
            `;
        } else if (frequency === 'monthly') {
            html = `
                <div class="mb-3">
                    <label class="form-label">Количество выплат в месяц *</label>
                    <input type="number" 
                           id="payments_per_month" 
                           class="form-control" 
                           min="1" 
                           max="30" 
                           value="2"
                           onchange="updateMonthlyPayments()">
                    <small class="text-muted">От 1 до 30</small>
                </div>
                <div id="monthly_payments_container"></div>
            `;
        }
        
        paramsContainer.innerHTML = html;
        
        if (frequency === 'weekly') {
            updateNextPaymentDate();
        } else if (frequency === 'monthly') {
            updateMonthlyPayments();
        }
        
        this.generateSchedule();
    }
    
    generateSchedule() {
        const frequency = document.getElementById('schedule_frequency').value;
        if (!frequency) return;
        
        const schedules = [];
        
        if (frequency === 'daily') {
            const nextPaymentInput = document.getElementById('next_payment_date');
            const periodDateInput = document.getElementById('period_date');
            
            if (!nextPaymentInput || !periodDateInput) return;
            
            const nextPayment = new Date(nextPaymentInput.value);
            const periodDate = new Date(periodDateInput.value);
            
            // Рассчитать смещение
            const offset = Math.floor((periodDate - nextPayment) / (1000 * 60 * 60 * 24));
            
            // Генерация на 365 дней
            for (let i = 0; i < 365; i++) {
                const paymentDate = new Date(nextPayment);
                paymentDate.setDate(nextPayment.getDate() + i);
                
                const periodDate = new Date(paymentDate);
                periodDate.setDate(paymentDate.getDate() + offset);
                
                schedules.push({
                    payment_date: this.formatDate(paymentDate),
                    period_start: this.formatDate(periodDate),
                    period_end: this.formatDate(periodDate)
                });
            }
        } else if (frequency === 'weekly') {
            const nextPaymentInput = document.getElementById('next_payment_date');
            const periodStartInput = document.getElementById('period_start_date');
            const periodEndInput = document.getElementById('period_end_date');
            
            if (!nextPaymentInput || !periodStartInput || !periodEndInput) return;
            
            const nextPayment = new Date(nextPaymentInput.value);
            const periodStart = new Date(periodStartInput.value);
            const periodEnd = new Date(periodEndInput.value);
            
            // Рассчитать смещение от даты выплаты до начала периода
            const startOffset = Math.floor((periodStart - nextPayment) / (1000 * 60 * 60 * 24));
            const endOffset = Math.floor((periodEnd - nextPayment) / (1000 * 60 * 60 * 24));
            
            // Генерация на 52 недели
            for (let i = 0; i < 52; i++) {
                const paymentDate = new Date(nextPayment);
                paymentDate.setDate(nextPayment.getDate() + (i * 7));
                
                const periodStartDate = new Date(paymentDate);
                periodStartDate.setDate(paymentDate.getDate() + startOffset);
                
                const periodEndDate = new Date(paymentDate);
                periodEndDate.setDate(paymentDate.getDate() + endOffset);
                
                schedules.push({
                    payment_date: this.formatDate(paymentDate),
                    period_start: this.formatDate(periodStartDate),
                    period_end: this.formatDate(periodEndDate)
                });
            }
        } else if (frequency === 'monthly') {
            const paymentsPerMonth = parseInt(document.getElementById('payments_per_month')?.value || 2);
            
            // Генерация на 12 месяцев
            for (let month = 0; month < 12; month++) {
                for (let paymentNum = 1; paymentNum <= paymentsPerMonth; paymentNum++) {
                    const nextPaymentInput = document.getElementById(`next_payment_date_${paymentNum}`);
                    const periodStartInput = document.getElementById(`period_start_date_${paymentNum}`);
                    const periodEndInput = document.getElementById(`period_end_date_${paymentNum}`);
                    
                    if (!nextPaymentInput || !periodStartInput || !periodEndInput) continue;
                    
                    const basePaymentDate = new Date(nextPaymentInput.value);
                    const basePeriodStart = new Date(periodStartInput.value);
                    const basePeriodEnd = new Date(periodEndInput.value);
                    
                    // Проверяем, является ли период концом месяца
                    const isEndOfMonth = this.isLastDayOfMonth(basePeriodEnd);
                    const isStartOfMonth = basePeriodStart.getDate() === 1;
                    
                    // Рассчитать смещение месяца периода относительно выплаты
                    const monthOffset = basePeriodStart.getMonth() - basePaymentDate.getMonth();
                    
                    // Добавить месяцы к дате выплаты
                    const paymentDate = new Date(basePaymentDate.getFullYear(), basePaymentDate.getMonth() + month, basePaymentDate.getDate());
                    
                    let periodStart, periodEnd;
                    
                    // Начало периода
                    const periodMonth = paymentDate.getMonth() + monthOffset;
                    const periodYear = paymentDate.getFullYear() + Math.floor(periodMonth / 12);
                    const normalizedPeriodMonth = ((periodMonth % 12) + 12) % 12;
                    
                    if (isStartOfMonth) {
                        // Если базовый период начинается с 1-го числа, всегда 1-е число
                        periodStart = new Date(periodYear, normalizedPeriodMonth, 1);
                    } else {
                        // Используем фиксированный день из базового периода
                        const fixedDay = basePeriodStart.getDate();
                        periodStart = new Date(periodYear, normalizedPeriodMonth, fixedDay);
                    }
                    
                    // Конец периода
                    if (isEndOfMonth) {
                        // Если базовый период заканчивается концом месяца, всегда последний день месяца
                        periodEnd = new Date(periodStart.getFullYear(), periodStart.getMonth() + 1, 0);
                    } else {
                        // Используем фиксированный день
                        const fixedDay = basePeriodEnd.getDate();
                        periodEnd = new Date(periodStart.getFullYear(), periodStart.getMonth(), fixedDay);
                    }
                    
                    schedules.push({
                        payment_date: this.formatDate(paymentDate),
                        period_start: this.formatDate(periodStart),
                        period_end: this.formatDate(periodEnd)
                    });
                }
            }
        }
        
        this.scheduleData = schedules;
        this.renderScheduleTable();
    }
    
    renderScheduleTable() {
        const container = document.getElementById('schedule_preview');
        if (!container) return;
        
        if (this.scheduleData.length === 0) {
            container.innerHTML = `
                <div class="alert alert-secondary">
                    <i class="fas fa-info-circle"></i> 
                    Заполните параметры графика для отображения превью
                </div>
            `;
            return;
        }
        
        // Рассчитать смещение и длительность по первой записи
        let offsetInfo = '';
        if (this.scheduleData.length > 0) {
            const first = this.scheduleData[0];
            const paymentDate = this.parseDate(first.payment_date);
            const periodStart = this.parseDate(first.period_start);
            const periodEnd = this.parseDate(first.period_end);
            
            const offsetDays = Math.floor((periodStart - paymentDate) / (1000 * 60 * 60 * 24));
            const durationDays = Math.floor((periodEnd - periodStart) / (1000 * 60 * 60 * 24)) + 1;
            
            offsetInfo = `
                <div class="alert alert-primary mb-3">
                    <strong>Параметры графика:</strong><br>
                    Смещение: <strong>${offsetDays} дней</strong> (от даты выплаты до начала периода)<br>
                    Длительность периода: <strong>${durationDays} дней</strong>
                </div>
            `;
        }
        
        let html = offsetInfo + `
            <div class="table-responsive" style="max-height: 350px; overflow-y: auto;">
                <table class="table table-sm table-striped table-hover">
                    <thead class="sticky-top bg-white">
                        <tr>
                            <th style="width: 60px;">№</th>
                            <th>Дата выплаты</th>
                            <th>Начало периода</th>
                            <th>Конец периода</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        this.scheduleData.forEach((item, index) => {
            html += `
                <tr>
                    <td>${index + 1}</td>
                    <td><strong>${item.payment_date}</strong></td>
                    <td>${item.period_start}</td>
                    <td>${item.period_end}</td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
            <div class="alert alert-success mt-2">
                <i class="fas fa-check-circle"></i> 
                Всего выплат в году: <strong>${this.scheduleData.length}</strong>
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    parseDate(dateStr) {
        const parts = dateStr.split('.');
        return new Date(parts[2], parts[1] - 1, parts[0]);
    }
    
    formatDate(date) {
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day}.${month}.${year}`;
    }
    
    isLastDayOfMonth(date) {
        // Проверяем, является ли дата последним днем месяца
        const nextDay = new Date(date);
        nextDay.setDate(date.getDate() + 1);
        return nextDay.getMonth() !== date.getMonth();
    }
    
    formatDateInput(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    getNextDayOfWeek(targetDay) {
        const today = new Date();
        const currentDay = today.getDay();
        const adjustedTargetDay = targetDay === 7 ? 0 : targetDay;
        const adjustedCurrentDay = currentDay === 0 ? 7 : currentDay;
        
        let daysUntil = adjustedTargetDay - adjustedCurrentDay;
        if (daysUntil <= 0) daysUntil += 7;
        
        const nextDate = new Date(today);
        nextDate.setDate(today.getDate() + daysUntil);
        
        return this.formatDateInput(nextDate);
    }
    
    async saveSchedule() {
        const frequency = document.getElementById('schedule_frequency').value;
        const scheduleName = document.getElementById('schedule_name').value;
        
        if (!scheduleName) {
            alert('Укажите название графика');
            return;
        }
        
        const scheduleConfig = {
            name: scheduleName,
            frequency: frequency,
            object_id: this.objectId,
            payment_period: this.buildPaymentPeriodConfig(),
            payment_day: this.getPaymentDay()
        };
        
        try {
            const response = await fetch('/owner/payment-schedules/create-custom', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(scheduleConfig)
            });
            
            if (response.ok) {
                const result = await response.json();
                alert('График выплат создан успешно!');
                this.modal.hide();
                // Обновить dropdown
                this.updateScheduleDropdown(result.id, result.name);
            } else {
                const error = await response.json();
                alert(`Ошибка: ${error.detail}`);
            }
        } catch (e) {
            alert(`Ошибка сохранения: ${e.message}`);
        }
    }
    
    buildPaymentPeriodConfig() {
        const frequency = document.getElementById('schedule_frequency').value;
        
        if (frequency === 'daily') {
            const nextPayment = new Date(document.getElementById('next_payment_date').value);
            const periodDate = new Date(document.getElementById('period_date').value);
            const offset = Math.floor((periodDate - nextPayment) / (1000 * 60 * 60 * 24));
            
            return {
                type: 'day',
                offset: offset,
                description: `За день со смещением ${offset} дней`
            };
        } else if (frequency === 'weekly') {
            const nextPayment = new Date(document.getElementById('next_payment_date').value);
            const periodStart = new Date(document.getElementById('period_start_date').value);
            const periodEnd = new Date(document.getElementById('period_end_date').value);
            
            const startOffset = Math.floor((periodStart - nextPayment) / (1000 * 60 * 60 * 24));
            const endOffset = Math.floor((periodEnd - nextPayment) / (1000 * 60 * 60 * 24));
            const duration = Math.floor((periodEnd - periodStart) / (1000 * 60 * 60 * 24)) + 1;
            
            return {
                type: 'week',
                start_offset: startOffset,
                end_offset: endOffset,
                duration: duration,
                description: `За ${duration} дней, смещение начала ${startOffset} дней`
            };
        } else if (frequency === 'monthly') {
            const paymentsPerMonth = parseInt(document.getElementById('payments_per_month').value);
            const payments = [];
            
            for (let i = 1; i <= paymentsPerMonth; i++) {
                const nextPaymentInput = document.getElementById(`next_payment_date_${i}`);
                const periodStartInput = document.getElementById(`period_start_date_${i}`);
                const periodEndInput = document.getElementById(`period_end_date_${i}`);
                
                if (nextPaymentInput && periodStartInput && periodEndInput) {
                    const nextPayment = new Date(nextPaymentInput.value);
                    const periodStart = new Date(periodStartInput.value);
                    const periodEnd = new Date(periodEndInput.value);
                    
                    const startOffset = Math.floor((periodStart - nextPayment) / (1000 * 60 * 60 * 24));
                    const endOffset = Math.floor((periodEnd - nextPayment) / (1000 * 60 * 60 * 24));
                    const isEndOfMonth = this.isLastDayOfMonth(periodEnd);
                    const isStartOfMonth = periodStart.getDate() === 1;
                    
                    payments.push({
                        payment_num: i,
                        next_payment_date: nextPaymentInput.value,
                        start_offset: startOffset,
                        end_offset: endOffset,
                        is_start_of_month: isStartOfMonth,
                        is_end_of_month: isEndOfMonth
                    });
                }
            }
            
            return {
                type: 'month',
                payments_per_month: paymentsPerMonth,
                payments: payments,
                description: `${paymentsPerMonth} раз(а) в месяц`
            };
        }
        
        return {};
    }
    
    getPaymentDay() {
        const frequency = document.getElementById('schedule_frequency').value;
        
        if (frequency === 'daily') {
            return 0;  // Каждый день
        } else if (frequency === 'weekly') {
            return parseInt(document.getElementById('payment_day_of_week')?.value || 5);
        } else if (frequency === 'monthly') {
            return parseInt(document.getElementById('next_payment_date_1')?.value?.split('-')[2] || 15);
        }
        
        return 1;
    }
    
    updateScheduleDropdown(scheduleId, scheduleName) {
        const select = document.getElementById('payment_schedule_id');
        if (select) {
            // Добавить новый option
            const option = document.createElement('option');
            option.value = scheduleId;
            option.text = scheduleName + ' (кастомный)';
            option.selected = true;
            select.appendChild(option);
        }
    }
    
    show() {
        if (this.modal) {
            this.modal.show();
        }
    }
}

// Функция для обновления следующей даты выплаты (еженедельно)
function updateNextPaymentDate() {
    const dayOfWeek = parseInt(document.getElementById('payment_day_of_week').value);
    const nextPaymentInput = document.getElementById('next_payment_date');
    
    if (nextPaymentInput && window.paymentScheduleEditor) {
        nextPaymentInput.value = window.paymentScheduleEditor.getNextDayOfWeek(dayOfWeek);
    }
}

// Функция для обновления полей ежемесячных выплат
function updateMonthlyPayments() {
    const paymentsPerMonth = parseInt(document.getElementById('payments_per_month').value);
    const container = document.getElementById('monthly_payments_container');
    const today = new Date();
    
    let html = '';
    
    for (let i = 1; i <= paymentsPerMonth; i++) {
        // Рассчитываем дату следующей выплаты (1-я = 15-е, 2-я = 30-е и т.д.)
        const nextPaymentDay = i === 1 ? 15 : 30;
        const nextPayment = new Date(today.getFullYear(), today.getMonth(), nextPaymentDay);
        if (nextPayment < today) {
            nextPayment.setMonth(nextPayment.getMonth() + 1);
        }
        
        // Период по умолчанию
        let defaultPeriodStart, defaultPeriodEnd;
        if (i === 1) {
            // 1-я выплата: с 1-го по 15-е
            defaultPeriodStart = new Date(nextPayment.getFullYear(), nextPayment.getMonth(), 1);
            defaultPeriodEnd = new Date(nextPayment.getFullYear(), nextPayment.getMonth(), 15);
        } else {
            // 2-я выплата: с 16-го по конец месяца
            defaultPeriodStart = new Date(nextPayment.getFullYear(), nextPayment.getMonth(), 16);
            defaultPeriodEnd = new Date(nextPayment.getFullYear(), nextPayment.getMonth() + 1, 0);
        }
        
        const formatDateInput = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        html += `
            <div class="card mb-3">
                <div class="card-header bg-light">
                    <h6 class="mb-0"><i class="fas fa-calendar-day"></i> Выплата ${i}</h6>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label">Следующая дата выплаты</label>
                        <input type="date" 
                               id="next_payment_date_${i}" 
                               class="form-control" 
                               value="${formatDateInput(nextPayment)}"
                               onchange="window.paymentScheduleEditor.generateSchedule()">
                        <small class="text-muted">Дата первой выплаты ${i}</small>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Выберите дату начала периода</label>
                        <input type="date" 
                               id="period_start_date_${i}" 
                               class="form-control" 
                               value="${formatDateInput(defaultPeriodStart)}"
                               onchange="window.paymentScheduleEditor.generateSchedule()">
                        <small class="text-muted">С какой даты считается период</small>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Выберите дату окончания периода</label>
                        <input type="date" 
                               id="period_end_date_${i}" 
                               class="form-control" 
                               value="${formatDateInput(defaultPeriodEnd)}"
                               onchange="window.paymentScheduleEditor.generateSchedule()">
                        <small class="text-muted">По какую дату считается период</small>
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
    
    // Пересоздать график
    if (window.paymentScheduleEditor) {
        window.paymentScheduleEditor.generateSchedule();
    }
}

