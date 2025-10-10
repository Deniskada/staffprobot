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
        
        if (frequency === 'daily') {
            html = `
                <div class="mb-3">
                    <label class="form-label">Время выплаты</label>
                    <input type="time" id="payment_time" class="form-control" value="12:00">
                </div>
                <div class="mb-3">
                    <label class="form-label">Период расчета</label>
                    <select id="period_type" class="form-select">
                        <option value="previous_day">За предыдущий день</option>
                        <option value="current_day">За текущий день</option>
                    </select>
                </div>
            `;
        } else if (frequency === 'weekly' || frequency === 'biweekly') {
            const weekLabel = frequency === 'biweekly' ? 'каждые 2 недели' : 'каждую неделю';
            html = `
                <div class="mb-3">
                    <label class="form-label">День недели для выплаты</label>
                    <select id="payment_day" class="form-select">
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
                    <label class="form-label">Начало расчетного периода (день недели)</label>
                    <select id="period_start_day" class="form-select">
                        <option value="1" selected>Понедельник</option>
                        <option value="2">Вторник</option>
                        <option value="3">Среда</option>
                        <option value="4">Четверг</option>
                        <option value="5">Пятница</option>
                        <option value="6">Суббота</option>
                        <option value="7">Воскресенье</option>
                    </select>
                    <small class="text-muted">С какого дня начинается рабочая неделя</small>
                </div>
                <div class="mb-3">
                    <label class="form-label">Конец расчетного периода (день недели)</label>
                    <select id="period_end_day" class="form-select">
                        <option value="1">Понедельник</option>
                        <option value="2">Вторник</option>
                        <option value="3">Среда</option>
                        <option value="4">Четверг</option>
                        <option value="5">Пятница</option>
                        <option value="6">Суббота</option>
                        <option value="7" selected>Воскресенье</option>
                    </select>
                    <small class="text-muted">На какой день заканчивается рабочая неделя</small>
                </div>
            `;
        } else if (frequency === 'monthly') {
            html = `
                <div class="mb-3">
                    <label class="form-label">Количество выплат в месяц</label>
                    <select id="payments_per_month" class="form-select" onchange="updateMonthlyPayments()">
                        <option value="1">1 раз в месяц</option>
                        <option value="2" selected>2 раза в месяц</option>
                        <option value="3">3 раза в месяц</option>
                        <option value="4">4 раза в месяц</option>
                    </select>
                </div>
                <div id="monthly_payments_container"></div>
            `;
        }
        
        paramsContainer.innerHTML = html;
        
        if (frequency === 'monthly') {
            updateMonthlyPayments();
        }
        
        this.generateSchedule();
    }
    
    generateSchedule() {
        const frequency = document.getElementById('schedule_frequency').value;
        const today = new Date();
        const schedules = [];
        
        if (frequency === 'daily') {
            // Генерация ежедневных выплат на месяц вперед
            for (let i = 0; i < 30; i++) {
                const paymentDate = new Date(today);
                paymentDate.setDate(today.getDate() + i);
                
                const periodStart = new Date(paymentDate);
                periodStart.setDate(paymentDate.getDate() - 1);
                
                schedules.push({
                    payment_date: this.formatDate(paymentDate),
                    period_start: this.formatDate(periodStart),
                    period_end: this.formatDate(periodStart)
                });
            }
        } else if (frequency === 'weekly') {
            const paymentDay = parseInt(document.getElementById('payment_day')?.value || 5);
            const periodStartDay = parseInt(document.getElementById('period_start_day')?.value || 1);
            
            // Найти ближайшую пятницу (или выбранный день)
            let current = new Date(today);
            while (current.getDay() !== (paymentDay === 7 ? 0 : paymentDay)) {
                current.setDate(current.getDate() + 1);
            }
            
            // Генерация на 12 недель вперед
            for (let i = 0; i < 12; i++) {
                const paymentDate = new Date(current);
                paymentDate.setDate(current.getDate() + (i * 7));
                
                // Расчетный период - предыдущая неделя
                const periodEnd = new Date(paymentDate);
                periodEnd.setDate(paymentDate.getDate() - 1);
                
                const periodStart = new Date(periodEnd);
                periodStart.setDate(periodEnd.getDate() - 6);
                
                schedules.push({
                    payment_date: this.formatDate(paymentDate),
                    period_start: this.formatDate(periodStart),
                    period_end: this.formatDate(periodEnd)
                });
            }
        } else if (frequency === 'biweekly') {
            const paymentDay = parseInt(document.getElementById('payment_day')?.value || 5);
            
            let current = new Date(today);
            while (current.getDay() !== (paymentDay === 7 ? 0 : paymentDay)) {
                current.setDate(current.getDate() + 1);
            }
            
            // Генерация на 6 периодов (12 недель)
            for (let i = 0; i < 6; i++) {
                const paymentDate = new Date(current);
                paymentDate.setDate(current.getDate() + (i * 14));
                
                const periodEnd = new Date(paymentDate);
                periodEnd.setDate(paymentDate.getDate() - 1);
                
                const periodStart = new Date(periodEnd);
                periodStart.setDate(periodEnd.getDate() - 13);
                
                schedules.push({
                    payment_date: this.formatDate(paymentDate),
                    period_start: this.formatDate(periodStart),
                    period_end: this.formatDate(periodEnd)
                });
            }
        } else if (frequency === 'monthly') {
            const paymentsPerMonth = parseInt(document.getElementById('payments_per_month')?.value || 2);
            
            // Генерация на 12 месяцев вперед
            for (let month = 0; month < 12; month++) {
                for (let paymentNum = 1; paymentNum <= paymentsPerMonth; paymentNum++) {
                    const dayInput = document.getElementById(`payment_day_${paymentNum}`);
                    if (!dayInput) continue;
                    
                    const paymentDay = parseInt(dayInput.value);
                    const paymentDate = new Date(today.getFullYear(), today.getMonth() + month, paymentDay);
                    
                    let periodStart, periodEnd;
                    
                    if (paymentsPerMonth === 1) {
                        // Весь предыдущий месяц
                        periodStart = new Date(paymentDate.getFullYear(), paymentDate.getMonth() - 1, 1);
                        periodEnd = new Date(paymentDate.getFullYear(), paymentDate.getMonth(), 0);
                    } else if (paymentsPerMonth === 2) {
                        if (paymentNum === 1) {
                            // С 16-го прошлого месяца по 15-е текущего
                            periodStart = new Date(paymentDate.getFullYear(), paymentDate.getMonth() - 1, 16);
                            periodEnd = new Date(paymentDate.getFullYear(), paymentDate.getMonth(), 15);
                        } else {
                            // С 16-го по конец текущего месяца
                            periodStart = new Date(paymentDate.getFullYear(), paymentDate.getMonth(), 16);
                            periodEnd = new Date(paymentDate.getFullYear(), paymentDate.getMonth() + 1, 0);
                        }
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
        
        let html = `
            <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                <table class="table table-sm table-striped">
                    <thead class="sticky-top bg-white">
                        <tr>
                            <th>№</th>
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
                    <td>${item.payment_date}</td>
                    <td>${item.period_start}</td>
                    <td>${item.period_end}</td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
            <div class="alert alert-info mt-2">
                <i class="fas fa-info-circle"></i> 
                Всего выплат в году: <strong>${this.scheduleData.length}</strong>
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    formatDate(date) {
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day}.${month}.${year}`;
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
            return {
                type: 'day',
                calc_rules: {
                    period: document.getElementById('period_type').value
                }
            };
        } else if (frequency === 'weekly' || frequency === 'biweekly') {
            return {
                type: frequency === 'weekly' ? 'week' : 'biweek',
                calc_rules: {
                    start_day: parseInt(document.getElementById('period_start_day').value),
                    end_day: parseInt(document.getElementById('period_end_day').value)
                }
            };
        } else if (frequency === 'monthly') {
            const paymentsPerMonth = parseInt(document.getElementById('payments_per_month').value);
            const payments = [];
            
            for (let i = 1; i <= paymentsPerMonth; i++) {
                const dayInput = document.getElementById(`payment_day_${i}`);
                if (dayInput) {
                    payments.push({
                        day: parseInt(dayInput.value),
                        period_start: document.getElementById(`period_start_${i}`).value,
                        period_end: document.getElementById(`period_end_${i}`).value
                    });
                }
            }
            
            return {
                type: 'month',
                calc_rules: {
                    payments_per_month: paymentsPerMonth,
                    payments: payments
                }
            };
        }
        
        return {};
    }
    
    getPaymentDay() {
        const frequency = document.getElementById('schedule_frequency').value;
        
        if (frequency === 'daily') {
            return 0;  // Каждый день
        } else if (frequency === 'weekly' || frequency === 'biweekly') {
            return parseInt(document.getElementById('payment_day').value);
        } else if (frequency === 'monthly') {
            return parseInt(document.getElementById('payment_day_1')?.value || 5);
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

// Функция для обновления полей ежемесячных выплат
function updateMonthlyPayments() {
    const paymentsPerMonth = parseInt(document.getElementById('payments_per_month').value);
    const container = document.getElementById('monthly_payments_container');
    
    let html = '';
    
    for (let i = 1; i <= paymentsPerMonth; i++) {
        html += `
            <div class="card mb-3">
                <div class="card-header">
                    <h6 class="mb-0">Выплата ${i}</h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <label class="form-label">День месяца</label>
                            <input type="number" id="payment_day_${i}" class="form-control" 
                                   min="1" max="31" value="${i === 1 ? 15 : 30}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Период с (день месяца)</label>
                            <input type="number" id="period_start_${i}" class="form-control" 
                                   min="1" max="31" value="${i === 1 ? 1 : 16}">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Период по (день месяца)</label>
                            <input type="number" id="period_end_${i}" class="form-control" 
                                   min="1" max="31" value="${i === 1 ? 15 : 31}">
                        </div>
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

