/**
 * BOOKING ACCORDION CONTROLLER
 * Управление аккордеон-интерфейсом страницы бронирования
 */

// Состояние бронирования
const bookingState = {
    currentStep: 1,
    selectedDate: null,
    selectedTime: null,
    selectedDuration: 1,
    selectedCourt: null,
    selectedCourtPrice: 0,
    configuration: {},
    manualOverride: false
};

/**
 * Инициализация аккордеона
 */
function initBookingAccordion() {
    console.log('[Accordion] Initializing booking accordion...');

    // Добавить обработчики клика на заголовки аккордеона
    document.querySelectorAll('.booking-accordion-header').forEach(header => {
        header.addEventListener('click', handleAccordionHeaderClick);
    });

    // Инициализировать duration selector
    initDurationSelector();

    // Инициализировать time period filters
    initTimePeriodFilters();

    // Открыть первую секцию по умолчанию
    openAccordionSection(1);

    console.log('[Accordion] Initialized successfully');
}

/**
 * Обработчик клика на заголовок аккордеона
 */
function handleAccordionHeaderClick(event) {
    const header = event.currentTarget;
    const item = header.closest('.booking-accordion-item');
    const stepNumber = parseInt(item.dataset.step);

    // Если секция заблокирована, ничего не делать
    if (item.classList.contains('locked')) {
        toast.warning('Заполните предыдущие шаги');
        return;
    }

    // Переключить состояние секции
    if (item.classList.contains('active')) {
        // Если это не текущий обязательный шаг, разрешить закрыть
        if (bookingState.currentStep !== stepNumber) {
            closeAccordionSection(stepNumber);
        }
    } else {
        openAccordionSection(stepNumber);
    }
}

/**
 * Открыть секцию аккордеона
 */
function openAccordionSection(stepNumber) {
    console.log(`[Accordion] Opening section ${stepNumber}`);

    const section = document.querySelector(`.booking-accordion-item[data-step="${stepNumber}"]`);
    if (!section) return;

    // Если не manual override, закрыть другие секции
    if (!bookingState.manualOverride) {
        document.querySelectorAll('.booking-accordion-item.active').forEach(item => {
            const itemStep = parseInt(item.dataset.step);
            if (itemStep !== stepNumber) {
                // Не закрывать шаг 3 пока пользователь выбирает длительность
                if (itemStep === 3 && bookingState.selectedTime && bookingState.currentStep === 3) {
                    return;
                }
                item.classList.remove('active');
            }
        });
    }

    // Открыть текущую секцию
    section.classList.add('active');
    section.classList.remove('locked');

    // Прокрутить к секции только если она вне зоны видимости
    setTimeout(() => {
        const rect = section.getBoundingClientRect();
        const isVisible = rect.top >= 0 && rect.top <= window.innerHeight * 0.4;
        if (!isVisible) {
            section.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest'
            });
        }
    }, 100);
}

/**
 * Закрыть секцию аккордеона
 */
function closeAccordionSection(stepNumber) {
    console.log(`[Accordion] Closing section ${stepNumber}`);

    const section = document.querySelector(`.booking-accordion-item[data-step="${stepNumber}"]`);
    if (!section) return;

    section.classList.remove('active');

    // Если закрывается секция выбора времени, скрыть селектор длительности
    if (stepNumber === 3) {
        const durationContainer = document.getElementById('duration-selector-container');
        if (durationContainer) {
            durationContainer.style.display = 'none';
        }
    }
}

/**
 * Переход к следующей секции
 */
function moveToNextSection(currentStep) {
    const nextStep = currentStep + 1;
    const nextSection = document.querySelector(`.booking-accordion-item[data-step="${nextStep}"]`);

    if (!nextSection) return;

    // Отметить текущую секцию как завершённую
    const currentSection = document.querySelector(`.booking-accordion-item[data-step="${currentStep}"]`);
    if (currentSection) {
        currentSection.classList.add('completed');
    }

    // Обновить текущий шаг
    bookingState.currentStep = nextStep;

    // Разблокировать и открыть следующую секцию
    nextSection.classList.remove('locked');

    setTimeout(() => {
        closeAccordionSection(currentStep);
        openAccordionSection(nextStep);
    }, 300);
}

/**
 * Проверка возможности перехода к следующему шагу
 */
function canProceedToStep(stepNumber) {
    switch(stepNumber) {
        case 1:
            return true; // Календарь всегда доступен
        case 2:
            return bookingState.selectedDate !== null;
        case 3:
            // Для выбора времени нужно выбрать дату и корт
            return bookingState.selectedDate !== null && bookingState.selectedCourt !== null;
        case 4:
            // Для настроек нужно выбрать время
            return bookingState.selectedTime !== null;
        default:
            return false;
    }
}

/**
 * Обработчик выбора даты в календаре
 */
function handleDateSelect(dateInfo) {
    console.log('[Accordion] Date selected:', dateInfo.dateStr);

    bookingState.selectedDate = dateInfo.dateStr;

    // Обновить статус секции
    updateSectionStatus(1, `Выбрано: ${formatDate(dateInfo.dateStr)}`);

    // Если корт уже выбран, загрузить временные слоты
    if (bookingState.selectedCourt) {
        loadTimeSlots(dateInfo.dateStr, bookingState.selectedCourt);
        // Если корт был выбран, перейти к шагу 3 (время)
        moveToNextSection(2);
    } else {
        // Корт не выбран, перейти к шагу 2 (выбор корта)
        moveToNextSection(1);
    }
}

/**
 * Обработчик выбора времени
 */
function handleTimeSelect(timeSlot) {
    console.log('[Accordion] Time selected:', timeSlot);

    bookingState.selectedTime = timeSlot;

    const startTime = timeSlot.split(' - ')[0];
    const endTime = calculateEndTime(startTime, bookingState.selectedDuration);

    // Обновить статус секции 3 (время)
    const durationText = String(bookingState.selectedDuration).replace('.', ',');
    updateSectionStatus(3, `${startTime} — ${endTime} (${durationText} ч)`);

    // Обновить скрытые поля формы
    document.getElementById('form-date').value = bookingState.selectedDate;
    document.getElementById('form-start-time').value = startTime;
    document.getElementById('form-end-time').value = endTime;
    document.getElementById('form-duration').value = bookingState.selectedDuration;
    document.getElementById('form-court-id').value = bookingState.selectedCourt;

    // Показать селектор длительности
    const durationContainer = document.getElementById('duration-selector-container');
    if (durationContainer) {
        durationContainer.style.display = 'block';
        // Прокрутить к селектору длительности
        durationContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Обновить отображение времени в селекторе длительности и summary
    updateDurationDisplay();
    updateBookingSummary();

    // НЕ переходим автоматически — пользователь должен выбрать длительность и нажать кнопку
}

/**
 * Обработчик выбора корта
 */
function handleCourtSelect(courtId, courtName, courtPrice) {
    console.log('[Accordion] Court selected:', courtId);

    bookingState.selectedCourt = courtId;
    bookingState.selectedCourtPrice = courtPrice;

    // Обновить статус секции
    updateSectionStatus(3, `${courtName} (${courtPrice}₽/час)`);

    // Обновить summary
    updateBookingSummary();

    // Перейти к настройке бронирования
    moveToNextSection(3);
}

/**
 * Обновить статус секции
 */
function updateSectionStatus(stepNumber, statusText) {
    const section = document.querySelector(`.booking-accordion-item[data-step="${stepNumber}"]`);
    if (!section) return;

    const subtitle = section.querySelector('.accordion-subtitle');
    if (subtitle) {
        subtitle.textContent = statusText;
    }
}

/**
 * Обновить сводку бронирования
 */
function updateBookingSummary() {
    const summary = document.getElementById('booking-summary');
    if (!summary) return;

    // Получить название корта из выбранного элемента
    const selectedCourtCard = document.querySelector('.compact-court-card.active');
    const courtName = selectedCourtCard ? selectedCourtCard.dataset.courtName : `Корт ${bookingState.selectedCourt}`;

    const totalPrice = bookingState.selectedCourtPrice * bookingState.selectedDuration;

    // Обновить все поля summary
    const summaryDate = document.getElementById('summary-date');
    const summaryTime = document.getElementById('summary-time');
    const summaryCourt = document.getElementById('summary-court');
    const summaryDuration = document.getElementById('summary-duration');
    const summaryPrice = document.getElementById('summary-price');

    if (summaryDate) summaryDate.textContent = bookingState.selectedDate ? formatDate(bookingState.selectedDate) : '-';
    if (summaryTime) summaryTime.textContent = bookingState.selectedTime || '-';
    if (summaryCourt) summaryCourt.textContent = courtName || '-';
    if (summaryDuration) summaryDuration.textContent = bookingState.selectedDuration ? `${String(bookingState.selectedDuration).replace('.', ',')} час${getDurationSuffix(bookingState.selectedDuration)}` : '-';
    if (summaryPrice) summaryPrice.textContent = totalPrice > 0 ? `${totalPrice}₽` : '-';

    // Всегда показывать summary, чтобы видеть прогресс
    summary.style.display = 'block';

    console.log('[Accordion] Summary updated:', {
        date: bookingState.selectedDate,
        time: bookingState.selectedTime,
        court: bookingState.selectedCourt,
        duration: bookingState.selectedDuration
    });
}

/**
 * Инициализация селектора длительности
 */
function initDurationSelector() {
    const minusBtn = document.getElementById('duration-minus');
    const plusBtn = document.getElementById('duration-plus');
    const durationValue = document.getElementById('duration-value');

    // Обработчик кнопки минус
    if (minusBtn) {
        minusBtn.addEventListener('click', function() {
            if (bookingState.selectedDuration > 1) {
                bookingState.selectedDuration -= 0.5;
                updateDurationDisplay();
                reloadTimeSlotsForDuration();
            }
        });
    }

    // Обработчик кнопки плюс
    if (plusBtn) {
        plusBtn.addEventListener('click', function() {
            if (bookingState.selectedDuration < 3) {
                bookingState.selectedDuration += 0.5;
                updateDurationDisplay();
                reloadTimeSlotsForDuration();
            }
        });
    }

    // Обновить кнопки при инициализации
    updateDurationDisplay();
}

/**
 * Обновить отображение длительности
 */
function updateDurationDisplay() {
    const durationValue = document.getElementById('duration-value');
    const durationLabel = document.getElementById('duration-label');
    const minusBtn = document.getElementById('duration-minus');
    const plusBtn = document.getElementById('duration-plus');
    const timeRange = document.getElementById('duration-time-range');

    if (durationValue) {
        // Формат с запятой для русской локали: 1,5 вместо 1.5
        durationValue.textContent = String(bookingState.selectedDuration).replace('.', ',');
    }

    if (durationLabel) {
        durationLabel.textContent = formatDurationLabel(bookingState.selectedDuration);
    }

    // Показать диапазон времени если время выбрано, иначе очистить
    if (timeRange) {
        if (bookingState.selectedTime) {
            const startTime = bookingState.selectedTime.split(' - ')[0];
            const endTime = calculateEndTime(startTime, bookingState.selectedDuration);
            timeRange.textContent = `${startTime} — ${endTime}`;
        } else {
            timeRange.textContent = '';
        }
    }

    // Обновить состояние кнопок
    if (minusBtn) {
        minusBtn.disabled = bookingState.selectedDuration <= 1;
    }
    if (plusBtn) {
        plusBtn.disabled = bookingState.selectedDuration >= 3;
    }

    // Обновить скрытые поля формы
    const formDuration = document.getElementById('form-duration');
    if (formDuration) {
        formDuration.value = bookingState.selectedDuration;
    }

    if (bookingState.selectedTime) {
        const startTime = bookingState.selectedTime.split(' - ')[0];
        const endTime = calculateEndTime(startTime, bookingState.selectedDuration);
        const formEndTime = document.getElementById('form-end-time');
        if (formEndTime) {
            formEndTime.value = endTime;
        }
    }

    // Обновить сводку
    updateBookingSummary();

    console.log('[Accordion] Duration changed:', bookingState.selectedDuration);
}

/**
 * Форматировать подпись длительности (час/часа/часов)
 */
function formatDurationLabel(duration) {
    // Дробные всегда "часа": 1,5 часа, 2,5 часа
    if (duration % 1 !== 0) return 'часа';
    if (duration === 1) return 'час';
    if (duration >= 2 && duration <= 4) return 'часа';
    return 'часов';
}

/**
 * Перезагрузить временные слоты при изменении длительности
 */
function reloadTimeSlotsForDuration() {
    if (bookingState.selectedDate && bookingState.selectedCourt) {
        // Сбросить выбранное время, так как слоты изменились
        bookingState.selectedTime = null;
        loadTimeSlots(bookingState.selectedDate, bookingState.selectedCourt);
    }
}

/**
 * Инициализация фильтров периодов времени
 */
function initTimePeriodFilters() {
    const filterButtons = document.querySelectorAll('.time-period-btn');

    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Убрать активный класс со всех
            filterButtons.forEach(b => b.classList.remove('active'));

            // Добавить активный класс к выбранному
            this.classList.add('active');

            // Применить фильтр
            const filter = this.dataset.filter;
            applyTimePeriodFilter(filter);
        });
    });
}

/**
 * Применить фильтр периода времени
 */
function applyTimePeriodFilter(filter) {
    console.log('[Accordion] Applying time filter:', filter);

    const timeSlots = document.querySelectorAll('.compact-time-slot');

    timeSlots.forEach(slot => {
        const timeText = slot.querySelector('.time-slot-time').textContent;
        const hour = parseInt(timeText.split(':')[0]);

        let show = true;

        switch(filter) {
            case 'morning':
                show = hour >= 8 && hour < 12;
                break;
            case 'afternoon':
                show = hour >= 12 && hour < 17;
                break;
            case 'evening':
                show = hour >= 17 && hour < 22;
                break;
            case 'all':
            default:
                show = true;
        }

        slot.style.display = show ? 'flex' : 'none';
    });
}

/**
 * Загрузить доступные временные слоты
 */
function loadTimeSlots(date, courtId) {
    if (!courtId) {
        console.log('[Accordion] No court selected yet');
        return;
    }

    console.log('[Accordion] Loading time slots for', date, 'court', courtId, 'duration', bookingState.selectedDuration);

    const timeSlotsContainer = document.getElementById('time-slots-grid');
    if (!timeSlotsContainer) return;

    // Плавное затемнение вместо полной замены — нет моргания
    timeSlotsContainer.style.opacity = '0.4';
    timeSlotsContainer.style.pointerEvents = 'none';

    // AJAX запрос для получения слотов
    fetch(`/booking/available-slots/?date=${encodeURIComponent(date)}&court=${encodeURIComponent(courtId)}&duration=${encodeURIComponent(bookingState.selectedDuration)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Поддержка обоих форматов ответа (новый: slots, старый: items)
                const slots = data.slots || [];
                renderTimeSlots(slots);
            } else {
                timeSlotsContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;"><i class="fas fa-calendar-times" style="font-size: 32px; margin-bottom: 16px;"></i><p>Нет доступных слотов на выбранную дату</p></div>';
            }
        })
        .catch(error => {
            console.error('[Accordion] Error loading time slots:', error);
            timeSlotsContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #dc3545;"><i class="fas fa-exclamation-triangle" style="font-size: 32px; margin-bottom: 16px;"></i><p>Ошибка загрузки временных слотов</p></div>';
        });
}

/**
 * Отрисовать временные слоты
 */
function renderTimeSlots(slots) {
    const timeSlotsContainer = document.getElementById('time-slots-grid');
    if (!timeSlotsContainer) return;

    if (!slots || slots.length === 0) {
        timeSlotsContainer.style.opacity = '1';
        timeSlotsContainer.style.pointerEvents = '';
        timeSlotsContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;"><i class="fas fa-calendar-times" style="font-size: 32px; margin-bottom: 16px;"></i><p>Нет доступных слотов</p></div>';
        return;
    }

    timeSlotsContainer.innerHTML = '';
    timeSlotsContainer.style.opacity = '1';
    timeSlotsContainer.style.pointerEvents = '';

    slots.forEach(slot => {
        const slotElement = document.createElement('div');
        slotElement.className = 'compact-time-slot';
        if (slot.booked) {
            slotElement.classList.add('booked');
        }

        const slotEndTime = calculateEndTime(slot.start_time, bookingState.selectedDuration);
        const durationText = String(bookingState.selectedDuration).replace('.', ',');
        slotElement.innerHTML = `
            <div class="time-slot-time">${slot.start_time} — ${slotEndTime}</div>
            <div class="time-slot-duration">${durationText} ч</div>
        `;

        if (!slot.booked) {
            slotElement.addEventListener('click', function() {
                // Убрать активный класс со всех
                document.querySelectorAll('.compact-time-slot').forEach(s => s.classList.remove('active'));

                // Добавить активный класс к выбранному
                this.classList.add('active');

                // Обработать выбор времени
                const endTime = calculateEndTime(slot.start_time, bookingState.selectedDuration);
                handleTimeSelect(`${slot.start_time} - ${endTime}`);
            });
        }

        timeSlotsContainer.appendChild(slotElement);
    });

    // Применить текущий фильтр
    const activeFilter = document.querySelector('.time-period-btn.active');
    if (activeFilter) {
        applyTimePeriodFilter(activeFilter.dataset.filter);
    }
}

/**
 * Рассчитать время окончания
 */
function calculateEndTime(startTime, duration) {
    const [hours, minutes] = startTime.split(':').map(Number);
    const totalMinutes = hours * 60 + minutes + duration * 60;
    const endHours = Math.floor(totalMinutes / 60);
    const endMinutes = totalMinutes % 60;

    return `${String(endHours).padStart(2, '0')}:${String(endMinutes).padStart(2, '0')}`;
}

/**
 * Форматировать дату
 */
function formatDate(dateStr) {
    const date = new Date(dateStr);
    const options = { day: 'numeric', month: 'long', year: 'numeric' };
    return date.toLocaleDateString('ru-RU', options);
}

/**
 * Получить суффикс для длительности
 */
function getDurationSuffix(duration) {
    // Дробные: 1,5 часа, 2,5 часа
    if (duration % 1 !== 0) return 'а';
    if (duration === 1) return '';
    if (duration >= 2 && duration <= 4) return 'а';
    return 'ов';
}

/**
 * Обработчик выбора корта (вызывается из HTML)
 */
window.selectCourtAccordion = function(element, courtId, courtName, courtPrice) {
    console.log('[Accordion] Court selected via onclick:', courtId);

    // Убрать активный класс со всех кортов
    document.querySelectorAll('.compact-court-card').forEach(card => {
        card.classList.remove('active');
    });

    // Добавить активный класс к выбранному
    element.classList.add('active');

    // Сохранить выбор в состояние
    bookingState.selectedCourt = courtId;
    bookingState.selectedCourtPrice = courtPrice;

    // Обновить статус секции 2
    updateSectionStatus(2, `${courtName} (${courtPrice}₽/час)`);

    // Загрузить временные слоты для этого корта, если дата уже выбрана
    if (bookingState.selectedDate) {
        loadTimeSlots(bookingState.selectedDate, courtId);
        // Перейти к выбору времени
        moveToNextSection(2);
    } else {
        // Корт выбран, но дата нет - не переходить дальше
        toast.info('Теперь выберите дату в календаре');
    }
};

// Alias для совместимости
window.selectAccordionCourt = window.selectCourtAccordion;

// Инициализировать при загрузке DOM
document.addEventListener('DOMContentLoaded', function() {
    initBookingAccordion();
});
