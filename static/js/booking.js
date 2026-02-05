   // booking.js - ПОЛНЫЙ КОД С ВСЕМ ФУНКЦИОНАЛОМ
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Booking JS loaded - полная версия');

    // ==================== ПЕРЕМЕННЫЕ ====================
    const weekNav = document.getElementById('week-nav');
    const prevWeekBtn = document.getElementById('prev-week');
    const nextWeekBtn = document.getElementById('next-week');
    const monthHeader = document.querySelector('.month-header');

    // Определяем тип layout'а
    let isNewLayout = false;
    let courtsList = document.getElementById('courts-horizontal-list');
    if (courtsList) {
        isNewLayout = true;
        console.log('📱 Используем НОВЫЙ layout с горизонтальными кортами');
    } else {
        courtsList = document.getElementById('courts-list');
        console.log('📱 Используем СТАРЫЙ layout с вертикальными кортами');
    }

    const timeSlots = document.getElementById('time-slots');
    const selectedTimeInfo = document.getElementById('selected-time-info');
    const confirmBookingBtn = document.getElementById('confirm-booking-btn');

    // Состояние
    let selectedDate = new Date();
    let selectedCourt = null;
    let selectedCourtPrice = null;
    let selectedCourtName = null;
    let currentWeekStart = null;
    let currentWeekIndex = 0;
    let selectedTimeSlot = null;
    let selectedDuration = 1;

    // Проверяем авторизацию
    let isUserAuthenticated = false;
    if (document.body.classList.contains('user-authenticated')) {
        isUserAuthenticated = true;
        console.log('✅ Пользователь авторизован');
    }

    // Получаем CSRF токен
    function getCsrfToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    // ==================== ИНИЦИАЛИЗАЦИЯ ====================

    if (weekNav && prevWeekBtn && nextWeekBtn && monthHeader) {
        console.log('📅 Инициализируем календарь...');
        initCalendar();

        // Hover эффекты для кнопок
        [prevWeekBtn, nextWeekBtn].forEach(btn => {
            if (!btn) return;

            btn.addEventListener('mouseenter', function() {
                if (!this.disabled) {
                    this.style.background = 'linear-gradient(135deg, #9ef01a 0%, #bff167 100%)';
                    this.style.borderColor = '#9ef01a';
                    this.style.color = 'white';
                    this.style.transform = 'translateY(-3px)';
                    this.style.boxShadow = '0 5px 15px rgba(158, 240, 26, 0.3)';
                }
            });

            btn.addEventListener('mouseleave', function() {
                if (!this.disabled) {
                    this.style.background = 'white';
                    this.style.borderColor = '#bff167';
                    this.style.color = '#38b000';
                    this.style.transform = 'translateY(0)';
                    this.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
                }
            });
        });
    }

    // Переключение недель
    if (prevWeekBtn) {
        prevWeekBtn.addEventListener('click', function() {
            if (this.disabled) return;
            navigateWeek(-1);
        });
    }

    if (nextWeekBtn) {
        nextWeekBtn.addEventListener('click', function() {
            navigateWeek(1);
        });
    }

    // ВЫБОР КОРТА
    if (courtsList) {
        console.log('🎾 Настройка выбора корта...');
        initCourtsSelection();
    }

    // Инициализация секций времени (только для нового layout'а)
    if (isNewLayout) {
        initTimeSections();
    }

    // Инициализация кнопки подтверждения
    if (confirmBookingBtn) {
        confirmBookingBtn.addEventListener('click', handleBookingConfirmation);
    }

    // ==================== ФУНКЦИИ ====================

    // Инициализация календаря
    function initCalendar() {
        console.log('📅 Инициализация календаря...');
        const today = new Date();
        currentWeekStart = getWeekStartDate(today);
        console.log('📅 Начало текущей недели:', currentWeekStart.toLocaleDateString('ru-RU'));
        currentWeekIndex = 0;
        renderWeek(currentWeekStart);

        // Выбираем текущий день по умолчанию
        selectedDate = new Date(today);
        highlightSelectedDate();

        console.log('✅ Календарь инициализирован успешно');
    }

    // Получение даты начала недели (понедельник)
    function getWeekStartDate(date) {
        const day = date.getDay();
        const diff = date.getDate() - day + (day === 0 ? -6 : 1);
        const result = new Date(date);
        result.setDate(diff);
        return result;
    }

    // Обновление состояния кнопки "Назад"
    function updatePrevButtonState() {
        if (!prevWeekBtn) return;

        const today = new Date();
        const currentWeekStartDate = getWeekStartDate(today);

        if (currentWeekStart.getTime() <= currentWeekStartDate.getTime()) {
            prevWeekBtn.disabled = true;
            prevWeekBtn.style.opacity = '0.4';
            prevWeekBtn.style.cursor = 'not-allowed';
            prevWeekBtn.style.background = '#f0f0f0';
            prevWeekBtn.style.borderColor = '#d0d0d0';
            prevWeekBtn.style.color = '#888';
            prevWeekBtn.title = 'Доступны только текущая и будущие недели';
        } else {
            prevWeekBtn.disabled = false;
            prevWeekBtn.style.opacity = '1';
            prevWeekBtn.style.cursor = 'pointer';
            prevWeekBtn.style.background = 'white';
            prevWeekBtn.style.borderColor = '#bff167';
            prevWeekBtn.style.color = '#38b000';
            prevWeekBtn.title = 'Предыдущая неделя';
        }
    }

    // Отрисовка недели
    function renderWeek(startDate) {
        if (!weekNav) return;

        console.log('🎨 Отрисовка недели начиная с:', startDate.toLocaleDateString('ru-RU'));

        weekNav.innerHTML = '';

        for (let i = 0; i < 7; i++) {
            const currentDate = new Date(startDate);
            currentDate.setDate(startDate.getDate() + i);

            const dayElement = document.createElement('div');
            dayElement.className = 'week-day';
            dayElement.dataset.date = formatDate(currentDate);
            dayElement.title = formatDisplayDate(currentDate);
            dayElement.style.cursor = 'pointer';

            const weekdayElement = document.createElement('div');
            weekdayElement.className = 'weekday';
            weekdayElement.textContent = formatWeekday(currentDate);

            const dayNumElement = document.createElement('div');
            dayNumElement.className = 'daynum';
            dayNumElement.textContent = currentDate.getDate();

            // Проверяем, является ли этот день сегодняшним
            const today = new Date();
            if (currentDate.toDateString() === today.toDateString()) {
                dayElement.classList.add('today');
            }

            // Обработчик клика
            dayElement.addEventListener('click', function() {
                console.log('📅 Дата выбрана:', currentDate.toLocaleDateString('ru-RU'));

                document.querySelectorAll('.week-day').forEach(day => {
                    day.classList.remove('selected');
                });

                dayElement.classList.add('selected');
                selectedDate = new Date(currentDate);

                if (selectedCourt) {
                    loadTimeSlots(selectedCourt, formatDate(selectedDate));
                } else {
                    if (isNewLayout) {
                        showTimeSlotsMessage('Выберите корт, чтобы увидеть доступное время');
                    } else if (timeSlots) {
                        timeSlots.innerHTML = `
                            <div class="select-court-date">
                                <i class="fas fa-calendar-check"></i>
                                <p>Выберите корт, чтобы увидеть доступное время</p>
                            </div>
                        `;
                    }
                }
            });

            dayElement.appendChild(weekdayElement);
            dayElement.appendChild(dayNumElement);
            weekNav.appendChild(dayElement);
        }

        updateMonthHeader(startDate);
        updatePrevButtonState();

        // Выделяем текущий день по умолчанию
        const today = new Date();
        const todayElement = document.querySelector(`.week-day[data-date="${formatDate(today)}"]`);
        if (todayElement) {
            console.log('🎯 Автовыбор сегодняшнего дня');
            todayElement.click();
        }

        console.log('✅ Неделя отрисована');
    }

    // Обновление заголовка месяца
    function updateMonthHeader(startDate) {
        if (!monthHeader) return;

        const monthsInWeek = [];
        const monthsNames = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ];

        for (let i = 0; i < 7; i++) {
            const currentDate = new Date(startDate);
            currentDate.setDate(startDate.getDate() + i);
            const monthName = monthsNames[currentDate.getMonth()];

            if (!monthsInWeek.includes(monthName)) {
                monthsInWeek.push(monthName);
            }
        }

        let monthTitle = monthsInWeek.join(' / ');

        const today = new Date();
        const firstDayOfWeek = new Date(startDate);

        if (firstDayOfWeek.getFullYear() !== today.getFullYear()) {
            monthTitle += ` ${firstDayOfWeek.getFullYear()}`;
        }

        monthHeader.textContent = monthTitle;
    }

    // Выделение выбранной даты
    function highlightSelectedDate() {
        if (!weekNav) return;

        document.querySelectorAll('.week-day').forEach(day => {
            day.classList.remove('selected');
        });

        const selectedDay = document.querySelector(`.week-day[data-date="${formatDate(selectedDate)}"]`);
        if (selectedDay) {
            selectedDay.classList.add('selected');
        }
    }

    // Навигация по неделям
    function navigateWeek(direction) {
        if (!currentWeekStart) return;

        currentWeekIndex += direction;

        if (currentWeekIndex < 0) {
            currentWeekIndex = 0;
            return;
        }

        const MAX_WEEKS_AHEAD = 12;
        if (currentWeekIndex > MAX_WEEKS_AHEAD) {
            currentWeekIndex = MAX_WEEKS_AHEAD;
            return;
        }

        const newWeekStart = new Date(currentWeekStart);
        newWeekStart.setDate(currentWeekStart.getDate() + (direction * 7));

        currentWeekStart = newWeekStart;
        renderWeek(currentWeekStart);
    }

    // Форматирование даты в строку YYYY-MM-DD
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // Форматирование дня недели
    function formatWeekday(date) {
        const day = date.getDay();
        const weekdays = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'];
        return weekdays[day];
    }

    // Форматирование для отображения
    function formatDisplayDate(date) {
        const day = date.getDate();
        const month = date.getMonth() + 1;
        const year = date.getFullYear();
        return `${day}.${month}.${year}`;
    }

    // Инициализация выбора кортов
    function initCourtsSelection() {
        console.log('🎾 Настройка выбора корта...');

        const courtSelector = isNewLayout ? '.court-horizontal-item' : '.court-item';
        const courtElements = document.querySelectorAll(courtSelector);

        if (!courtElements.length) return;

        courtElements.forEach(item => {
            // Устанавливаем курсор и делаем кликабельным
            item.style.cursor = 'pointer';
            item.style.pointerEvents = 'auto';

            // Убираем pointer-events у всех дочерних элементов
            item.querySelectorAll('*').forEach(child => {
                child.style.pointerEvents = 'none';
            });

            // Обработчик клика
            item.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('🎯 Клик на корт:', this.dataset.courtId);

                // Убираем активный класс у всех кортов
                courtElements.forEach(i => {
                    i.classList.remove('active');
                });

                // Добавляем активный класс выбранному корту
                this.classList.add('active');
                selectedCourt = this.dataset.courtId;
                selectedCourtPrice = this.dataset.courtPrice;
                selectedCourtName = this.querySelector('h4').textContent;

                // Обновляем глобальные данные о выбранном корте
                window.selectedCourtData = {
                    id: selectedCourt,
                    name: selectedCourtName,
                    price: selectedCourtPrice
                };

                console.log('✅ Корт выбран - ID:', selectedCourt, 'Цена:', selectedCourtPrice, 'Название:', selectedCourtName);

                // Загружаем доступные временные слоты
                if (selectedDate) {
                    loadTimeSlots(selectedCourt, formatDate(selectedDate));
                }

                // Сбрасываем выбранное время
                resetTimeSelection();
            });

            // Визуальная обратная связь
            item.addEventListener('mouseenter', function() {
                if (!this.classList.contains('active')) {
                    this.style.transform = 'translateY(-5px)';
                }
            });

            item.addEventListener('mouseleave', function() {
                if (!this.classList.contains('active')) {
                    this.style.transform = 'translateY(0)';
                }
            });
        });
    }

    // Инициализация секций времени - ИСПРАВЛЕННАЯ ВЕРСИЯ
    function initTimeSections() {
        console.log('⏰ Инициализация секций времени...');

        const sectionHeaders = document.querySelectorAll('.section-header');
        if (!sectionHeaders.length) return;

        // ДОБАВЛЯЕМ ОБРАБОТЧИКИ КЛИКА НА ЗАГОЛОВКИ
        sectionHeaders.forEach(header => {
            // Делаем заголовок явно кликабельным
            header.style.cursor = 'pointer';
            header.style.userSelect = 'none';

            // ОБРАБОТЧИК КЛИКА
            header.addEventListener('click', function() {
                console.log('Клик на заголовке секции:', this.dataset.section);

                const section = this.dataset.section;
                const content = document.getElementById(`${section}-slots`);

                if (!content) return;

                // Переключаем видимость
                if (content.style.display === 'none') {
                    // ОТКРЫВАЕМ
                    content.style.display = 'block';

                    // Меняем иконку
                    const arrow = this.querySelector('.toggle-arrow i');
                    if (arrow) {
                        arrow.className = 'fas fa-chevron-down';
                    }

                    console.log(`✅ Секция "${section}" открыта`);
                } else {
                    // ЗАКРЫВАЕМ
                    content.style.display = 'none';

                    // Меняем иконку
                    const arrow = this.querySelector('.toggle-arrow i');
                    if (arrow) {
                        arrow.className = 'fas fa-chevron-right';
                    }

                    console.log(`✅ Секция "${section}" закрыта`);
                }

                // Визуальная обратная связь
                this.style.transform = 'scale(0.98)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 150);
            });

            // Визуальная обратная связь при наведении
            header.addEventListener('mouseenter', function() {
                this.style.opacity = '0.9';
            });

            header.addEventListener('mouseleave', function() {
                this.style.opacity = '1';
            });
        });

        // ОТКРЫВАЕМ ВСЕ СЕКЦИИ ПО УМОЛЧАНИЮ - ИСПРАВЛЕНО
        sectionHeaders.forEach(header => {
            const section = header.dataset.section;
            const content = document.getElementById(`${section}-slots`);

            if (content) {
                // Открываем по умолчанию
                content.style.display = 'block';

                // Устанавливаем правильную иконку
                const arrow = header.querySelector('.toggle-arrow i');
                if (arrow) {
                    arrow.className = 'fas fa-chevron-down';
                }
            }
        });

        console.log('✅ Секции времени инициализированы');
    }

    // Загрузка временных слотов
    function loadTimeSlots(courtId, dateStr) {
        console.log('🕐 Current client time:', new Date().toLocaleTimeString());
        console.log('📅 Selected date:', dateStr);
        console.log('🏟️ Selected court:', courtId);
        console.log('📡 Загрузка слотов для корта:', courtId, 'дата:', dateStr);

        // Показываем индикатор загрузки
        if (isNewLayout) {
            document.querySelectorAll('.section-content').forEach(content => {
                content.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;"><i class="fas fa-spinner fa-spin"></i> Загрузка доступного времени...</div>';
            });
        }

        const url = `/booking/available-slots/?court=${courtId}&date=${dateStr}`;
        console.log('📡 Fetch URL:', url);

        fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            console.log('📡 Response status:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return response.json();
        })
        .then(data => {
            console.log('✅ API response received:', data);

            if (data.success) {
                console.log('🎯 Rendering slots...');
                // Новый формат: data.items вместо data.slots
                renderTimeSlotsBySections(data.items || data.slots, data.court_price, data.court_name);

                if (data.available_count === 0) {
                    console.log('⚠️ No available slots');
                }
            } else {
                console.error('❌ API returned error:', data.message);
                showMessage(data.message || 'Ошибка загрузки слотов', 'error');
            }
        })
        .catch(error => {
            console.error('❌ Error fetching time slots:', error);
            showMessage('Ошибка загрузки. Пожалуйста, попробуйте позже.', 'error');
        });
    }

    // Отрисовка временных слотов по секциям
    function renderTimeSlotsBySections(items, courtPrice, courtName) {
        console.log('🎨 Отрисовка слотов по секциям:', items ? items.length : 0, 'шт.');
        console.log('🎨 Полученные items:', items);

        if (!items || !Array.isArray(items) || items.length === 0) {
            console.error('❌ No items or items is not an array:', items);
            showTimeSlotsMessage('Нет доступных слотов на выбранную дату');
            return;
        }

        // Распределяем items по секциям - НОВАЯ ЛОГИКА С ПОДДЕРЖКОЙ ТИПОВ
        const morningItems = items.filter(item => {
            const hour = item.hour;
            return hour >= 8 && hour < 12;
        });

        const dayItems = items.filter(item => {
            const hour = item.hour;
            return hour >= 12 && hour < 17;
        });

        const eveningItems = items.filter(item => {
            const hour = item.hour;
            return hour >= 17 && hour < 22;
        });

        console.log('📊 Morning items:', morningItems.length, morningItems);
        console.log('📊 Day items:', dayItems.length, dayItems);
        console.log('📊 Evening items:', eveningItems.length, eveningItems);

        // Отрисовываем каждую секцию
        renderTimeSection('morning', morningItems, courtPrice, courtName);
        renderTimeSection('day', dayItems, courtPrice, courtName);
        renderTimeSection('evening', eveningItems, courtPrice, courtName);

        console.log('✅ Слоты отрисованы по секциям');
    }

    // Отрисовка одной секции времени
    function renderTimeSection(sectionName, items, courtPrice, courtName) {
        const sectionContent = document.getElementById(`${sectionName}-slots`);
        if (!sectionContent) {
            console.error(`❌ Section content not found: ${sectionName}-slots`);
            return;
        }

        console.log(`🎯 Rendering section: ${sectionName} with ${items.length} items`);

        if (!items || items.length === 0) {
            console.log(`⚠️ No items for section: ${sectionName}`);
            sectionContent.innerHTML = `
                <div class="select-court-date" style="text-align: center; padding: 40px; color: #777;">
                    <i class="fas fa-calendar-times" style="font-size: 48px; margin-bottom: 15px;"></i>
                    <p style="margin: 0; font-size: 16px;">Нет доступных слотов в это время</p>
                </div>
            `;
            return;
        }

        // Создаем сетку слотов
        const grid = document.createElement('div');
        grid.className = 'time-slots-grid';
        grid.style.cssText = `
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 15px;
            margin-top: 10px;
        `;

        items.forEach(item => {
            console.log(`🎯 Item for ${sectionName}:`, item);
            const itemElement = createTimeSlotElement(item, courtPrice, courtName);
            grid.appendChild(itemElement);
        });

        sectionContent.innerHTML = '';
        sectionContent.appendChild(grid);

        console.log(`✅ Section ${sectionName} rendered with ${items.length} items`);
    }

    // Отрисовка временных слотов (старый layout)
    function renderTimeSlotsOldLayout(slots, courtPrice, courtName) {
        if (!timeSlots) return;

        console.log('🎨 Отрисовка слотов (старый layout):', slots.length, 'шт.');

        timeSlots.innerHTML = '';

        if (!slots || slots.length === 0) {
            timeSlots.innerHTML = '<div class="error-message"><i class="fas fa-calendar-times"></i> Нет доступных слотов на выбранную дату</div>';
            return;
        }

        // Добавляем заголовок с информацией
        const header = document.createElement('div');
        header.className = 'slots-header';
        header.innerHTML = `
            <h4><i class="fas fa-clock"></i> Доступное время (по 1 часу)</h4>
            <p class="slots-info">Выберите начальное время, затем укажите продолжительность (1-3 часа)</p>
        `;
        timeSlots.appendChild(header);

        // Создаем контейнер для слотов
        const slotsContainer = document.createElement('div');
        slotsContainer.className = 'slots-grid';

        // Отображаем каждый слот
        slots.forEach(slot => {
            const slotElement = createTimeSlotElement(slot, courtPrice, courtName);
            slotsContainer.appendChild(slotElement);
        });

        timeSlots.appendChild(slotsContainer);
        console.log('✅ Слоты отрисованы (старый layout)');
    }

    // Создание элемента временного слота
    function createTimeSlotElement(item, courtPrice, courtName) {
        console.log(`🎯 Creating element:`, item);

        // Проверяем тип элемента
        if (item.type === 'partner_booking') {
            return createPartnerBookingElement(item);
        } else {
            return createFreeSlotElement(item, courtPrice, courtName);
        }
    }

    // Создание элемента свободного слота
    function createFreeSlotElement(slot, courtPrice, courtName) {
        let slotElement;

        if (isNewLayout) {
            slotElement = document.createElement('div');
            slotElement.className = 'time-slot-card available';
            slotElement.style.cssText = `
                background: white;
                border-radius: 12px;
                padding: 20px;
                cursor: pointer;
                transition: all 0.3s ease;
                border: 3px solid #bff167;
                text-align: center;
                opacity: 1;
            `;

            slotElement.innerHTML = `
                <div class="slot-time" style="display: block; font-weight: 700; color: #333; font-size: 18px; margin-bottom: 8px;">${slot.start_time}</div>
                <div class="slot-price" style="display: block; font-size: 16px; color: #38b000; font-weight: 600; margin-bottom: 5px;">${courtPrice} ₽</div>
                <div class="slot-status" style="font-size: 12px; color: #38b000; text-transform: uppercase; letter-spacing: 0.5px;">
                    <i class="fas fa-check-circle"></i>
                    <span>Доступно</span>
                </div>
                <div class="slot-hint" style="font-size: 11px; color: #666; margin-top: 5px;">Нажмите для выбора</div>
            `;
        } else {
            slotElement = document.createElement('div');
            slotElement.className = 'time-slot available';

            slotElement.innerHTML = `
                <div class="slot-content">
                    <div class="slot-time">${slot.start_time} - ${slot.end_time}</div>
                    <div class="slot-status">
                        <i class="fas fa-check-circle"></i>
                        <span>Доступно</span>
                    </div>
                    <div class="slot-price">${courtPrice} ₽/час</div>
                    <div class="slot-hint">Нажмите для выбора</div>
                </div>
            `;
        }

        slotElement.dataset.startTime = slot.start_time;
        slotElement.dataset.endTime = slot.end_time;
        slotElement.dataset.hour = slot.hour;
        slotElement.dataset.isAvailable = true;

        slotElement.style.cursor = 'pointer';
        slotElement.title = `Нажмите для бронирования ${slot.start_time}`;

        slotElement.addEventListener('click', function() {
            handleTimeSlotSelection(this, courtPrice, courtName);
        });

        // Hover эффекты
        slotElement.addEventListener('mouseenter', function() {
            if (!this.classList.contains('selected')) {
                if (isNewLayout) {
                    this.style.transform = 'translateY(-5px)';
                    this.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.1)';
                } else {
                    this.style.transform = 'translateX(5px)';
                }
            }
        });

        slotElement.addEventListener('mouseleave', function() {
            if (!this.classList.contains('selected')) {
                if (isNewLayout) {
                    this.style.transform = 'translateY(0)';
                    this.style.boxShadow = 'none';
                } else {
                    this.style.transform = 'translateX(0)';
                }
            }
        });

        return slotElement;
    }

    // Создание элемента бронирования с поиском партнёра
    function createPartnerBookingElement(booking) {
        const bookingElement = document.createElement('div');
        bookingElement.className = 'partner-booking-card';

        const canJoin = booking.can_join;
        const borderColor = canJoin ? '#9ef01a' : '#ff6b6b';
        const bgColor = canJoin ? '#f0ffe0' : '#fff5f5';

        bookingElement.style.cssText = `
            background: ${bgColor};
            border-radius: 12px;
            padding: 15px;
            cursor: ${canJoin ? 'pointer' : 'not-allowed'};
            transition: all 0.3s ease;
            border: 3px solid ${borderColor};
            opacity: ${canJoin ? '1' : '0.7'};
        `;

        const joinButtonHtml = canJoin ?
            `<button style="
                width: 100%;
                padding: 10px;
                background: linear-gradient(135deg, #9ef01a 0%, #bff167 100%);
                color: #333;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                cursor: pointer;
                margin-top: 10px;
                transition: all 0.3s;
            " class="join-partner-btn">
                <i class="fas fa-user-plus"></i> Присоединиться
            </button>` :
            `<div style="
                width: 100%;
                padding: 8px;
                background: #ffebee;
                color: #c62828;
                border-radius: 6px;
                font-size: 11px;
                text-align: center;
                margin-top: 10px;
            ">
                <i class="fas fa-exclamation-circle"></i> ${booking.join_message || 'Недоступно'}
            </div>`;

        bookingElement.innerHTML = `
            <div style="text-align: center;">
                <div style="font-weight: 700; color: #333; font-size: 16px; margin-bottom: 5px;">
                    <i class="fas fa-clock"></i> ${booking.start_time}
                </div>
                <div style="font-size: 13px; color: #666; margin-bottom: 8px;">
                    <i class="fas fa-users"></i> Найти партнёра
                </div>
                <div style="font-size: 14px; color: #333; margin-bottom: 5px;">
                    <strong>${booking.creator_name}</strong>
                </div>
                <div style="font-size: 12px; color: #38b000; margin-bottom: 5px;">
                    Рейтинг: ${booking.creator_rating || 'Не указан'}
                </div>
                <div style="font-size: 13px; color: #333; margin-bottom: 5px;">
                    Игроков: ${booking.current_players}/${booking.max_players}
                </div>
                <div style="font-size: 15px; color: #38b000; font-weight: bold; margin-bottom: 5px;">
                    ${Math.round(booking.price_per_person)} ₽/чел
                </div>
                ${booking.required_rating ?
                    `<div style="font-size: 11px; color: #666; margin-bottom: 5px;">
                        Требуемый уровень: ${booking.required_rating}
                    </div>` : ''
                }
                ${joinButtonHtml}
            </div>
        `;

        bookingElement.dataset.bookingId = booking.booking_id;
        bookingElement.dataset.startTime = booking.start_time;
        bookingElement.dataset.endTime = booking.end_time;
        bookingElement.dataset.hour = booking.hour;

        if (canJoin) {
            const joinBtn = bookingElement.querySelector('.join-partner-btn');
            if (joinBtn) {
                joinBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    handleJoinPartnerBooking(booking.booking_id);
                });

                joinBtn.addEventListener('mouseenter', function() {
                    this.style.transform = 'scale(1.05)';
                    this.style.boxShadow = '0 5px 15px rgba(158, 240, 26, 0.3)';
                });

                joinBtn.addEventListener('mouseleave', function() {
                    this.style.transform = 'scale(1)';
                    this.style.boxShadow = 'none';
                });
            }

            bookingElement.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-5px)';
                this.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.15)';
            });

            bookingElement.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = 'none';
            });
        }

        return bookingElement;
    }

    // Обработчик присоединения к бронированию
    function handleJoinPartnerBooking(bookingId) {
        if (!isUserAuthenticated) {
            showMessage('Пожалуйста, войдите в систему для присоединения к бронированию', 'error');
            window.location.href = '/users/login/';
            return;
        }

        console.log('🎯 Присоединение к бронированию:', bookingId);

        // Подтверждение
        if (confirm('Вы уверены, что хотите присоединиться к этому бронированию?')) {
            fetch(`/booking/join/${bookingId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showMessage('Вы успешно присоединились к бронированию!', 'success');
                    // Перенаправляем на страницу деталей бронирования
                    window.location.href = `/booking/detail/${bookingId}/`;
                } else {
                    showMessage(data.message || 'Ошибка при присоединении', 'error');
                }
            })
            .catch(error => {
                console.error('Error joining booking:', error);
                showMessage('Ошибка при присоединении. Попробуйте позже.', 'error');
            });
        }
    }

    // Выбор временного слота
    function handleTimeSlotSelection(slotElement, courtPrice, courtName) {
        console.log('⏰ Выбран слот:', slotElement.dataset.startTime);

        // Сбрасываем предыдущий выбор
        resetTimeSelection();

        // Помечаем выбранный слот
        slotElement.classList.add('selected');
        selectedTimeSlot = {
            startTime: slotElement.dataset.startTime,
            endTime: slotElement.dataset.endTime,
            hour: parseInt(slotElement.dataset.hour)
        };

        // Для нового layout'а показываем блок с выбранным временем
        if (isNewLayout) {
            showSelectedTimeInfo(courtName, courtPrice);
        } else {
            // Для старого layout'а показываем выбор продолжительности
            showDurationSelector(
                selectedTimeSlot.startTime,
                selectedTimeSlot.endTime,
                courtPrice,
                courtName,
                selectedTimeSlot.hour
            );
        }
    }

    // Показать выбранное время (новый layout)
    function showSelectedTimeInfo(courtName, courtPrice) {
        if (!selectedTimeInfo) return;

        // Заполняем информацию
        document.getElementById('selected-court').textContent = courtName;
        document.getElementById('selected-date').textContent = formatDisplayDate(selectedDate);
        document.getElementById('selected-time').textContent = `${selectedTimeSlot.startTime} - ${selectedTimeSlot.endTime}`;
        document.getElementById('selected-price').textContent = `${courtPrice} ₽`;

        // Показываем блок
        selectedTimeInfo.style.display = 'block';

        // Прокручиваем к блоку
        selectedTimeInfo.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Сброс выбранного времени
    function resetTimeSelection() {
        // Сбрасываем выделение слотов
        const selector = isNewLayout ? '.time-slot-card' : '.time-slot';
        document.querySelectorAll(selector).forEach(card => {
            card.classList.remove('selected');
        });

        selectedTimeSlot = null;

        // Скрываем блок с выбранным временем
        if (selectedTimeInfo) {
            selectedTimeInfo.style.display = 'none';
        }
    }

    // Показать сообщение в секциях времени
    function showTimeSlotsMessage(message) {
        console.log('📢 Showing time slots message:', message);

        if (isNewLayout) {
            document.querySelectorAll('.section-content').forEach(content => {
                content.innerHTML = `<div class="error-message" style="text-align: center; padding: 40px; color: #dc3545;"><i class="fas fa-exclamation-circle"></i> ${message}</div>`;
            });
        } else if (timeSlots) {
            timeSlots.innerHTML = `<div class="error-message"><i class="fas fa-exclamation-circle"></i> ${message}</div>`;
        }
    }

    // ==================== ВЫБОР ПРОДОЛЖИТЕЛЬНОСТИ (старый layout) ====================

    function showDurationSelector(startTime, endTime, courtPrice, courtName, hour) {
        console.log('🕒 Выбор продолжительности для', startTime);

        // Удаляем старые модальные окна
        document.querySelectorAll('.duration-modal').forEach(modal => modal.remove());

        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.className = 'duration-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1001;
        `;

        modal.innerHTML = `
            <div class="duration-modal-content" style="
                background: white;
                border-radius: 15px;
                padding: 30px;
                width: 90%;
                max-width: 500px;
                position: relative;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                animation: slideIn 0.3s;
            ">
                <span class="close-duration" style="
                    position: absolute;
                    right: 20px;
                    top: 15px;
                    font-size: 28px;
                    cursor: pointer;
                    color: #666;
                ">&times;</span>

                <h2 style="color: #38b000; margin-bottom: 20px; text-align: center;">Выберите продолжительность</h2>

                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="font-size: 1.2rem; color: #333; margin-bottom: 10px;">
                        <i class="fas fa-calendar-day"></i> ${formatDisplayDate(selectedDate)}
                    </div>
                    <div style="font-size: 1.4rem; font-weight: bold; color: #333; margin-bottom: 5px;">
                        ${courtName}
                    </div>
                    <div style="font-size: 1.1rem; color: #666;">
                        Начало: <strong>${startTime}</strong>
                    </div>
                </div>

                <div class="duration-options" style="
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 15px;
                    margin-bottom: 30px;
                ">
                    <button class="duration-option" data-hours="1" style="
                        padding: 20px 10px;
                        border: 2px solid #eee;
                        border-radius: 10px;
                        background: white;
                        cursor: pointer;
                        transition: all 0.3s;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        gap: 10px;
                    ">
                        <div style="font-size: 1.5rem; font-weight: bold; color: #333;">1 час</div>
                        <div style="font-size: 1.1rem; color: #38b000; font-weight: bold;">${courtPrice} ₽</div>
                        <div style="font-size: 0.9rem; color: #666;">${startTime} - ${calculateEndTime(startTime, 1)}</div>
                    </button>

                    <button class="duration-option" data-hours="2" style="
                        padding: 20px 10px;
                        border: 2px solid #eee;
                        border-radius: 10px;
                        background: white;
                        cursor: pointer;
                        transition: all 0.3s;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        gap: 10px;
                    ">
                        <div style="font-size: 1.5rem; font-weight: bold; color: #333;">2 часа</div>
                        <div style="font-size: 1.1rem; color: #38b000; font-weight: bold;">${courtPrice * 2} ₽</div>
                        <div style="font-size: 0.9rem; color: #666;">${startTime} - ${calculateEndTime(startTime, 2)}</div>
                    </button>

                    <button class="duration-option" data-hours="3" style="
                        padding: 20px 10px;
                        border: 2px solid #eee;
                        border-radius: 10px;
                        background: white;
                        cursor: pointer;
                        transition: all 0.3s;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        gap: 10px;
                    ">
                        <div style="font-size: 1.5rem; font-weight: bold; color: #333;">3 часа</div>
                        <div style="font-size: 1.1rem; color: #38b000; font-weight: bold;">${courtPrice * 3} ₽</div>
                        <div style="font-size: 0.9rem; color: #666;">${startTime} - ${calculateEndTime(startTime, 3)}</div>
                    </button>
                </div>

                <div style="text-align: center; color: #666; font-size: 0.9rem; margin-bottom: 20px;">
                    <i class="fas fa-info-circle"></i> Вы можете забронировать от 1 до 3 часов подряд
                </div>

                <div style="display: flex; justify-content: space-between; gap: 15px;">
                    <button class="btn-secondary cancel-duration" style="
                        flex: 1;
                        padding: 15px;
                        background: #6c757d;
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: all 0.3s;
                    ">Отмена</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Обработчики для выбора продолжительности
        modal.querySelectorAll('.duration-option').forEach(option => {
            option.addEventListener('click', function() {
                const hours = parseInt(this.dataset.hours);
                selectedDuration = hours;

                const endTime = calculateEndTime(startTime, hours);

                // Проверяем доступность выбранной продолжительности
                checkExtendedAvailability(startTime, endTime, hours, courtPrice, courtName);

                modal.remove();
            });

            // Hover эффекты
            option.addEventListener('mouseenter', function() {
                this.style.borderColor = '#9ef01a';
                this.style.transform = 'translateY(-5px)';
                this.style.boxShadow = '0 5px 15px rgba(0,0,0,0.1)';
            });

            option.addEventListener('mouseleave', function() {
                this.style.borderColor = '#eee';
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = 'none';
            });
        });

        // Закрытие модального окна
        modal.querySelector('.close-duration').addEventListener('click', () => {
            modal.remove();
        });

        modal.querySelector('.cancel-duration').addEventListener('click', () => {
            modal.remove();
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    // Расчет времени окончания
    function calculateEndTime(startTime, hours) {
        const [startHour] = startTime.split(':').map(Number);
        const endHour = startHour + hours;
        return `${endHour.toString().padStart(2, '0')}:00`;
    }

    // Проверка доступности расширенного слота
    function checkExtendedAvailability(startTime, endTime, duration, courtPrice, courtName) {
        console.log('🔍 Проверка доступности:', startTime, '-', endTime, `(${duration}ч)`);

        // Показываем индикатор загрузки
        if (timeSlots) {
            timeSlots.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Проверка доступности...</div>';
        }

        // Отправляем запрос на проверку
        fetch('/booking/check-availability/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: new URLSearchParams({
                'court_id': selectedCourt,
                'date': formatDate(selectedDate),
                'start_time': startTime,
                'duration': duration.toString()
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.available) {
                // Доступно, показываем подтверждение
                showBookingConfirmation(
                    startTime,
                    endTime,
                    duration,
                    courtPrice,
                    courtName
                );
            } else {
                // Недоступно
                showErrorMessage(data.message || 'Выбранное время уже занято');

                // Перезагружаем слоты
                if (selectedCourt) {
                    loadTimeSlots(selectedCourt, formatDate(selectedDate));
                }
            }
        })
        .catch(error => {
            console.error('Error checking availability:', error);
            showErrorMessage('Ошибка при проверке доступности');
        });
    }

    // ==================== ПОДТВЕРЖДЕНИЕ БРОНИРОВАНИЯ ====================

    function handleBookingConfirmation() {
        if (!selectedCourt || !selectedTimeSlot) {
            showMessage('Пожалуйста, выберите корт и время', 'error');
            return;
        }

        // Для нового layout'а продолжительность всегда 1 час
        const duration = isNewLayout ? 1 : selectedDuration;

        // Получаем информацию о корте
        const courtElement = document.querySelector(isNewLayout ? '.court-horizontal-item.active' : '.court-item.active');
        if (!courtElement) {
            console.error('❌ Элемент корта не найден');
            return;
        }

        const courtNameDisplay = courtElement.querySelector('h4').textContent;
        const formattedDate = formatDisplayDate(selectedDate);
        const courtPrice = parseFloat(courtElement.dataset.courtPrice);
        const totalPrice = courtPrice * duration;
        const endTime = isNewLayout ? selectedTimeSlot.endTime : calculateEndTime(selectedTimeSlot.startTime, duration);

        // Показываем модальное окно подтверждения
        showBookingConfirmationModal(
            courtNameDisplay,
            formattedDate,
            selectedTimeSlot.startTime,
            endTime,
            totalPrice,
            duration
        );
    }

    // Показать подтверждение бронирования
    function showBookingConfirmation(startTime, endTime, duration, courtPrice, courtName) {
        console.log('✅ Подтверждение бронирования');

        // Получаем информацию о корте
        const courtElement = document.querySelector(isNewLayout ? '.court-horizontal-item.active' : '.court-item.active');
        if (!courtElement) {
            console.error('❌ Элемент корта не найден');
            return;
        }

        const courtNameDisplay = courtElement.querySelector('h4').textContent;
        const formattedDate = formatDisplayDate(selectedDate);
        const totalPrice = courtPrice * duration;

        // Используем существующее модальное окно
        const existingModal = document.getElementById('bookingConfirmModal');
        if (existingModal) {
            console.log('✅ Используем существующее модальное окно');

            // Заполняем данные
            document.getElementById('modal-court-name').textContent = courtNameDisplay;
            document.getElementById('modal-date').textContent = formattedDate;
            document.getElementById('modal-time').textContent = `${startTime} - ${endTime}`;
            document.getElementById('modal-price').textContent = `${totalPrice} ₽`;

            // Заполняем форму
            document.getElementById('form-court-id').value = selectedCourt;
            document.getElementById('form-date').value = formatDate(selectedDate);
            document.getElementById('form-start-time').value = startTime;
            document.getElementById('form-end-time').value = endTime;

            // Добавляем поле duration
            let durationInput = document.getElementById('form-duration');
            if (!durationInput) {
                durationInput = document.createElement('input');
                durationInput.type = 'hidden';
                durationInput.name = 'duration';
                durationInput.id = 'form-duration';
                document.getElementById('booking-form').appendChild(durationInput);
            }
            durationInput.value = duration;

            // Показываем модальное окно
            existingModal.style.display = 'block';

            // Обработчики закрытия
            const closeBtn = existingModal.querySelector('.close-modal');
            const cancelBtn = existingModal.querySelector('.cancel-booking');

            const closeModal = function() {
                existingModal.style.display = 'none';
            };

            closeBtn.onclick = closeModal;
            cancelBtn.onclick = closeModal;

            // Клик вне модального окна
            window.onclick = function(e) {
                if (e.target === existingModal) {
                    closeModal();
                }
            };

            return;
        }

        // Если статического модального окна нет, создаем динамическое
        createDynamicBookingModal(
            courtNameDisplay,
            formattedDate,
            startTime,
            endTime,
            totalPrice,
            duration
        );
    }

    // Создание динамического модального окна
    function createDynamicBookingModal(courtName, date, startTime, endTime, totalPrice, duration) {
        console.log('⚠️ Создаем динамическое модальное окно');

        const modalHTML = `
            <div id="bookingConfirmModal" class="modal" style="
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                animation: fadeIn 0.3s;
            ">
                <div class="modal-content" style="
                    background: white;
                    border-radius: 15px;
                    max-width: 500px;
                    width: 90%;
                    padding: 30px;
                    position: relative;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    animation: slideIn 0.3s;
                ">
                    <span class="close-modal" style="
                        position: absolute;
                        right: 20px;
                        top: 15px;
                        font-size: 28px;
                        cursor: pointer;
                        color: #666;
                        transition: color 0.3s;
                    ">&times;</span>
                    <h2 style="color: #38b000; margin-bottom: 20px; text-align: center; font-size: 24px;">Подтверждение бронирования</h2>
                    <div class="booking-details" style="
                        background: #f9f9f9;
                        border-radius: 10px;
                        padding: 20px;
                        margin: 20px 0;
                        border: 1px solid #eee;
                    ">
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e8e8e8;">
                            <span style="font-weight: 600; color: #555;">Корт:</span>
                            <span style="font-weight: 700; color: #333;">${courtName}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e8e8e8;">
                            <span style="font-weight: 600; color: #555;">Дата:</span>
                            <span style="font-weight: 700; color: #333;">${date}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e8e8e8;">
                            <span style="font-weight: 600; color: #555;">Время:</span>
                            <span style="font-weight: 700; color: #333;">${startTime} - ${endTime} (${duration} ч)</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 10px 0;">
                            <span style="font-weight: 600; color: #555;">Стоимость:</span>
                            <span style="font-weight: 700; color: #333;">${totalPrice} ₽</span>
                        </div>
                    </div>
                    <form id="booking-form" method="post" action="/booking/create/" style="margin-top: 20px;">
                        <input type="hidden" name="court_id" value="${selectedCourt}">
                        <input type="hidden" name="date" value="${formatDate(selectedDate)}">
                        <input type="hidden" name="start_time" value="${startTime}">
                        <input type="hidden" name="end_time" value="${endTime}">
                        <input type="hidden" name="duration" value="${duration}">
                        <input type="hidden" name="csrfmiddlewaretoken" value="${getCsrfToken()}">

                        <div style="display: flex; gap: 15px; margin-top: 30px;">
                            <button type="button" class="btn-secondary cancel-booking" style="
                                flex: 1;
                                padding: 15px;
                                background: #6c757d;
                                color: white;
                                border: none;
                                border-radius: 8px;
                                font-weight: bold;
                                cursor: pointer;
                                transition: all 0.3s;
                                font-size: 16px;
                            ">Отмена</button>
                            <button type="submit" class="btn-primary confirm-booking" style="
                                flex: 1;
                                padding: 15px;
                                background: linear-gradient(135deg, #9ef01a 0%, #bff167 100%);
                                color: #333;
                                border: none;
                                border-radius: 8px;
                                font-weight: bold;
                                cursor: pointer;
                                transition: all 0.3s;
                                font-size: 16px;
                            ">Подтвердить бронирование</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHTML;
        document.body.appendChild(modalContainer.firstElementChild);

        const modal = document.getElementById('bookingConfirmModal');
        const closeBtn = modal.querySelector('.close-modal');
        const cancelBtn = modal.querySelector('.cancel-booking');
        const confirmBtn = modal.querySelector('.confirm-booking');

        // Закрытие модального окна
        const closeModal = function() {
            modal.style.animation = 'fadeOut 0.3s';
            setTimeout(() => {
                modal.remove();
            }, 300);
        };

        closeBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);

        // Подтверждение бронирования
        confirmBtn.addEventListener('click', function(e) {
            e.preventDefault();

            console.log('✅ Подтверждение бронирования нажато');

            confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Бронирование...';
            confirmBtn.disabled = true;
            cancelBtn.disabled = true;

            // Отправляем форму
            const form = modal.querySelector('#booking-form');
            form.submit();
        });

        // Закрытие при клике вне модального окна
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
    }

    function showBookingConfirmationModal(courtName, date, startTime, endTime, totalPrice, duration) {
        const modal = document.getElementById('bookingConfirmModal');
        if (!modal) return;

        // Заполняем данные
        document.getElementById('modal-court-name').textContent = courtName;
        document.getElementById('modal-date').textContent = date;
        document.getElementById('modal-time').textContent = `${startTime} - ${endTime}`;
        document.getElementById('modal-price').textContent = `${totalPrice} ₽`;

        // Заполняем форму
        document.getElementById('form-court-id').value = selectedCourt;
        document.getElementById('form-date').value = formatDate(selectedDate);
        document.getElementById('form-start-time').value = startTime;
        document.getElementById('form-end-time').value = endTime;

        let durationInput = document.getElementById('form-duration');
        if (!durationInput) {
            durationInput = document.createElement('input');
            durationInput.type = 'hidden';
            durationInput.name = 'duration';
            durationInput.id = 'form-duration';
            document.getElementById('booking-form').appendChild(durationInput);
        }
        durationInput.value = duration;

        // Показываем модальное окно
        if (window.openModal) {
            window.openModal(modal);
        } else {
            modal.style.display = 'block';
        }

        // Обработчики закрытия
        const closeBtn = modal.querySelector('.close-modal');
        const cancelBtn = modal.querySelector('.cancel-booking');

        const closeThisModal = function() {
            if (window.closeModal) {
                window.closeModal(modal);
            } else {
                modal.style.display = 'none';
            }
        };

        closeBtn.onclick = closeThisModal;
        cancelBtn.onclick = closeThisModal;

        window.onclick = function(e) {
            if (e.target === modal) {
                closeThisModal();
            }
        };
    }

    // ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

    function showMessage(message, type) {
        // Используем функцию из main.js если она есть
        if (typeof showMessage !== 'undefined') {
            showMessage(type, message);
        } else {
            // Или показываем alert
            if (type === 'error') {
                alert(`Ошибка: ${message}`);
            } else if (type === 'warning') {
                alert(`Внимание: ${message}`);
            } else {
                console.log(message);
            }
        }
    }

    function showErrorMessage(message) {
        // Используем функцию из main.js если она есть
        if (typeof showMessage !== 'undefined') {
            showMessage('error', message);
        } else {
            // Или показываем alert
            alert(`Ошибка: ${message}`);
        }
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Добавляем CSS анимации
    if (!document.querySelector('#booking-animations')) {
        const style = document.createElement('style');
        style.id = 'booking-animations';
        style.textContent = `
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            @keyframes fadeOut { from { opacity: 1; } to { opacity: 0; } }
            @keyframes slideIn { from { opacity: 0; transform: translateY(-50px) scale(0.9); } to { opacity: 1; transform: translateY(0) scale(1); } }
            .fa-spinner { animation: fa-spin 1s infinite linear; }
            @keyframes fa-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        `;
        document.head.appendChild(style);
    }

    // Экспортируем необходимые функции и переменные в глобальную область
    window.bookingState = {
        get selectedDate() { return selectedDate; },
        set selectedDate(val) { selectedDate = val; },
        get selectedCourt() { return selectedCourt; },
        set selectedCourt(val) { selectedCourt = val; }
    };

    window.loadTimeSlots = loadTimeSlots;
    window.showTimeSlotsMessage = showTimeSlotsMessage;
    window.formatDate = formatDate;
    window.selectedCourtData = { id: null, name: null, price: null };

    console.log('✅ Booking JS загружен - ПОЛНАЯ ВЕРСИЯ');
});