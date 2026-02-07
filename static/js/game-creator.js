/**
 * ============================================
 * GAME CREATOR
 * ============================================
 *
 * Управление формой создания игры с модальными окнами
 */

class GameCreator {
    constructor() {
        this.gameData = {
            type: 'game',
            location: null,
            date: null,
            time: null,
            duration: 1.5,
            playerCount: 4,
            ratingRange: { min: 'D', max: 'D+' },
            isPlayer: true,
            isRated: true,
            isPrivate: false,
            hasCourtBooked: false,
            settings: {
                anyoneCanInvite: false,
                anyoneCanSubmitScore: false,
                noConfirmation: false
            },
            comment: ''
        };

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeDefaults();
        console.log('✅ Game Creator инициализирован');
    }

    setupEventListeners() {
        // Клики по настройкам
        document.querySelectorAll('.game-setting-row').forEach(row => {
            row.addEventListener('click', (e) => {
                // Если клик по toggle - не открываем модалку
                if (e.target.closest('.toggle-switch')) {
                    return;
                }

                const action = row.dataset.action;
                if (action) {
                    this.handleSettingClick(action);
                }
            });
        });

        // Toggles
        document.querySelectorAll('.toggle-switch input').forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                const setting = e.target.dataset.setting;
                this.handleToggleChange(setting, e.target.checked);
            });
        });

        // Комментарий
        const commentField = document.querySelector('.game-comment-field');
        if (commentField) {
            commentField.addEventListener('click', () => {
                this.openCommentModal();
            });
        }

        // Кнопка создания
        const createButton = document.querySelector('.game-create-button');
        if (createButton) {
            createButton.addEventListener('click', () => {
                this.createGame();
            });
        }
    }

    initializeDefaults() {
        // Установка текущей даты
        const today = new Date();
        this.gameData.date = today;

        // Установка следующего доступного времени
        const currentHour = today.getHours();
        const nextSlot = Math.ceil((currentHour + 1) / 0.5) * 0.5;
        this.gameData.time = `${Math.floor(nextSlot)}:${nextSlot % 1 === 0.5 ? '30' : '00'}`;
    }

    // ==================== ОБРАБОТЧИКИ ====================

    handleSettingClick(action) {
        switch (action) {
            case 'type':
                this.openTypeModal();
                break;
            case 'location':
                this.openLocationModal();
                break;
            case 'datetime':
                this.openDateTimeModal();
                break;
            case 'players':
                this.openPlayersModal();
                break;
            case 'rating':
                this.openRatingModal();
                break;
            default:
                console.log('Unknown action:', action);
        }
    }

    handleToggleChange(setting, value) {
        switch (setting) {
            case 'isPlayer':
                this.gameData.isPlayer = value;
                break;
            case 'isRated':
                this.gameData.isRated = value;
                break;
            case 'isPrivate':
                this.gameData.isPrivate = value;
                break;
            case 'hasCourtBooked':
                this.gameData.hasCourtBooked = value;
                break;
            case 'anyoneCanInvite':
                this.gameData.settings.anyoneCanInvite = value;
                break;
            case 'anyoneCanSubmitScore':
                this.gameData.settings.anyoneCanSubmitScore = value;
                break;
            case 'noConfirmation':
                this.gameData.settings.noConfirmation = value;
                break;
        }

        console.log('Setting changed:', setting, value);
        this.updateUI();
    }

    // ==================== МОДАЛЬНЫЕ ОКНА ====================

    openTypeModal() {
        const modal = this.createModal('Тип игры', `
            <div class="game-modal-body">
                <p style="color: #666; margin-bottom: 16px;">Выберите тип игры</p>
                <div class="game-type-selector">
                    <button class="game-type-button ${this.gameData.type === 'game' ? 'active' : ''}" data-type="game">
                        Игра
                    </button>
                    <button class="game-type-button ${this.gameData.type === 'tournament' ? 'active' : ''}" data-type="tournament">
                        Турнир
                    </button>
                </div>
            </div>
        `);

        // Обработчики для кнопок типа
        modal.querySelectorAll('.game-type-button').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.querySelectorAll('.game-type-button').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });

        this.showModal(modal, () => {
            const activeBtn = modal.querySelector('.game-type-button.active');
            if (activeBtn) {
                this.gameData.type = activeBtn.dataset.type;
                this.updateUI();
            }
        });
    }

    openDateTimeModal() {
        // Генерация дат (7 дней вперед)
        const dates = [];
        const today = new Date();
        for (let i = 0; i < 7; i++) {
            const date = new Date(today);
            date.setDate(today.getDate() + i);
            dates.push(date);
        }

        const datesHTML = dates.map((date, i) => {
            const dayNames = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
            const monthNames = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];

            return `
                <div class="game-date-card ${i === 0 ? 'active' : ''}" data-date="${date.toISOString()}">
                    <p class="game-date-day">${dayNames[date.getDay()]}</p>
                    <p class="game-date-number">${date.getDate()}</p>
                    <p class="game-date-month">${monthNames[date.getMonth()]}</p>
                </div>
            `;
        }).join('');

        // Генерация временных слотов
        const timeSlots = [];
        for (let hour = 8; hour <= 22; hour++) {
            timeSlots.push(`${hour}:00`);
            if (hour < 22) {
                timeSlots.push(`${hour}:30`);
            }
        }

        const timeSlotsHTML = timeSlots.map(time => `
            <button class="game-time-slot" data-time="${time}">${time}</button>
        `).join('');

        const modal = this.createModal('Дата и время', `
            <div class="game-modal-body">
                <div class="game-date-picker">
                    <p class="game-date-label">Дата</p>
                    <div class="game-date-scroll">
                        ${datesHTML}
                    </div>
                </div>

                <div class="game-duration-picker">
                    <p class="game-duration-label">Продолжительность (в часах)</p>
                    <div class="game-duration-control">
                        <button class="game-duration-button" data-action="decrease">− 0,5</button>
                        <div class="game-duration-value">${this.gameData.duration}</div>
                        <button class="game-duration-button" data-action="increase">+ 0,5</button>
                    </div>
                </div>

                <div class="game-time-of-day">
                    <p class="game-time-of-day-label">Выберите время начала</p>
                    <div class="game-time-of-day-buttons">
                        <button class="game-time-of-day-button" data-period="morning">Утро</button>
                        <button class="game-time-of-day-button active" data-period="day">День</button>
                        <button class="game-time-of-day-button" data-period="evening">Вечер</button>
                        <button class="game-time-of-day-button" data-period="night">Ночь</button>
                    </div>
                </div>

                <div class="game-time-slots">
                    <div class="game-time-slots-grid">
                        ${timeSlotsHTML}
                    </div>
                </div>
            </div>
        `);

        // Обработчики
        this.setupDateTimeHandlers(modal);

        this.showModal(modal, () => {
            const activeDate = modal.querySelector('.game-date-card.active');
            const activeTime = modal.querySelector('.game-time-slot.active');

            if (activeDate) {
                this.gameData.date = new Date(activeDate.dataset.date);
            }
            if (activeTime) {
                this.gameData.time = activeTime.dataset.time;
            }

            this.updateUI();
        });
    }

    setupDateTimeHandlers(modal) {
        // Выбор даты
        modal.querySelectorAll('.game-date-card').forEach(card => {
            card.addEventListener('click', () => {
                modal.querySelectorAll('.game-date-card').forEach(c => c.classList.remove('active'));
                card.classList.add('active');
            });
        });

        // Продолжительность
        modal.querySelectorAll('.game-duration-button').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                const valueEl = modal.querySelector('.game-duration-value');
                let current = parseFloat(valueEl.textContent);

                if (action === 'increase' && current < 4) {
                    current += 0.5;
                } else if (action === 'decrease' && current > 0.5) {
                    current -= 0.5;
                }

                valueEl.textContent = current;
                this.gameData.duration = current;
            });
        });

        // Время дня
        modal.querySelectorAll('.game-time-of-day-button').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.querySelectorAll('.game-time-of-day-button').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Фильтр временных слотов
                const period = btn.dataset.period;
                this.filterTimeSlots(modal, period);
            });
        });

        // Выбор времени
        modal.querySelectorAll('.game-time-slot').forEach(slot => {
            slot.addEventListener('click', () => {
                modal.querySelectorAll('.game-time-slot').forEach(s => s.classList.remove('active'));
                slot.classList.add('active');
            });
        });
    }

    filterTimeSlots(modal, period) {
        const timeRanges = {
            morning: { start: 6, end: 12 },
            day: { start: 12, end: 18 },
            evening: { start: 18, end: 22 },
            night: { start: 22, end: 24 }
        };

        const range = timeRanges[period];
        modal.querySelectorAll('.game-time-slot').forEach(slot => {
            const time = slot.dataset.time;
            const hour = parseInt(time.split(':')[0]);

            if (hour >= range.start && hour < range.end) {
                slot.style.display = '';
            } else {
                slot.style.display = 'none';
            }
        });
    }

    openPlayersModal() {
        const modal = this.createModal('Количество игроков', `
            <div class="game-modal-body">
                <p style="color: #666; margin-bottom: 16px;">Количество игроков</p>
                <div class="game-player-count-selector">
                    ${[4, 5, 6, 7, 8].map(count => `
                        <button class="game-player-count-button ${count === this.gameData.playerCount ? 'active' : ''}" data-count="${count}">
                            ${count}
                        </button>
                    `).join('')}
                </div>
            </div>
        `);

        modal.querySelectorAll('.game-player-count-button').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.querySelectorAll('.game-player-count-button').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });

        this.showModal(modal, () => {
            const activeBtn = modal.querySelector('.game-player-count-button.active');
            if (activeBtn) {
                this.gameData.playerCount = parseInt(activeBtn.dataset.count);
                this.updateUI();
            }
        });
    }

    openRatingModal() {
        // TODO: Реализовать выбор диапазона рейтинга
        if (window.toast) {
            toast.info('Выбор диапазона рейтинга в разработке');
        }
    }

    openLocationModal() {
        // TODO: Реализовать выбор локации
        if (window.toast) {
            toast.info('Выбор локации в разработке');
        }
    }

    openCommentModal() {
        // TODO: Реализовать ввод комментария
        if (window.toast) {
            toast.info('Добавление комментария в разработке');
        }
    }

    // ==================== УТИЛИТЫ МОДАЛОК ====================

    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'game-modal';
        modal.innerHTML = `
            <div class="game-modal-content">
                <div class="game-modal-header">
                    <h3 class="game-modal-title">${title}</h3>
                    <button class="game-modal-close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                ${content}
                <div class="game-modal-footer">
                    <button class="game-modal-button primary">Готово</button>
                </div>
            </div>
        `;

        return modal;
    }

    showModal(modal, onConfirm) {
        document.body.appendChild(modal);

        // Анимация появления
        setTimeout(() => modal.classList.add('active'), 10);

        // Закрытие
        const closeBtn = modal.querySelector('.game-modal-close');
        const confirmBtn = modal.querySelector('.game-modal-button.primary');
        const backdrop = modal;

        const close = () => {
            modal.classList.remove('active');
            setTimeout(() => modal.remove(), 300);
        };

        closeBtn.addEventListener('click', close);
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) close();
        });

        confirmBtn.addEventListener('click', () => {
            if (onConfirm) onConfirm();
            close();
        });
    }

    // ==================== UPDATE UI ====================

    updateUI() {
        // Обновление отображаемых значений
        this.updateTypeDisplay();
        this.updateDateTimeDisplay();
        this.updatePlayersDisplay();
        this.updateRatingDisplay();
    }

    updateTypeDisplay() {
        const typeValue = document.querySelector('[data-display="type-value"]');
        if (typeValue) {
            typeValue.textContent = this.gameData.type === 'game' ? 'Игра' : 'Турнир';
        }
    }

    updateDateTimeDisplay() {
        const dateValue = document.querySelector('[data-display="datetime-value"]');
        if (dateValue && this.gameData.date && this.gameData.time) {
            const date = this.gameData.date;
            const dayNames = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
            const monthNames = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

            const formatted = `${dayNames[date.getDay()]} ${date.getDate()} ${monthNames[date.getMonth()]}, ${this.gameData.time}`;
            dateValue.textContent = formatted;
        }
    }

    updatePlayersDisplay() {
        const playersValue = document.querySelector('[data-display="players-value"]');
        if (playersValue) {
            playersValue.textContent = this.gameData.playerCount;
        }
    }

    updateRatingDisplay() {
        const ratingValue = document.querySelector('[data-display="rating-value"]');
        if (ratingValue) {
            ratingValue.textContent = `${this.gameData.ratingRange.min}...${this.gameData.ratingRange.max}`;
        }
    }

    // ==================== CREATE GAME ====================

    async createGame() {
        console.log('Creating game with data:', this.gameData);

        // TODO: Отправка данных на сервер
        if (window.toast) {
            toast.info('Создание игры в разработке');
        }

        // Временно - показываем данные
        console.log(JSON.stringify(this.gameData, null, 2));
    }
}

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

let gameCreator;

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.game-creator-container')) {
        gameCreator = new GameCreator();
    }
});

// Экспорт
window.GameCreator = GameCreator;
window.gameCreator = gameCreator;
