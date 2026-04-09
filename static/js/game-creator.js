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
            locationAddress: null,
            date: null,
            time: null,
            duration: 1.5,
            playerCount: 4,
            ratingRange: [], // Массив допустимых рейтингов, например: ['C', 'C+', 'B-']
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
        // Рейтинговая система: D, D+, C-, C, C+, B-, B, B+, A-, A, A+
        const ratings = ['D', 'D+', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+'];

        const content = `
            <div class="rating-selector">
                <p style="color: #666; margin-bottom: 20px;">Выберите допустимые уровни игроков для вашей игры</p>
                <div class="rating-grid">
                    ${ratings.map(rating => `
                        <button class="rating-button ${this.gameData.ratingRange.includes(rating) ? 'active' : ''}"
                                data-rating="${rating}">
                            <i class="fas fa-star"></i>
                            ${rating}
                        </button>
                    `).join('')}
                </div>
                <div class="rating-presets" style="margin-top: 20px;">
                    <p style="color: #999; font-size: 13px; margin-bottom: 10px;">Быстрый выбор:</p>
                    <button class="btn btn-sm btn-secondary" onclick="selectRatingPreset('all')">
                        Все уровни
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="selectRatingPreset('beginners')">
                        Новички (D-C)
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="selectRatingPreset('intermediate')">
                        Средний (C-B)
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="selectRatingPreset('advanced')">
                        Продвинутые (B-A+)
                    </button>
                </div>
            </div>
        `;

        const modal = this.createModal('Выбор уровня игроков', content);
        document.body.appendChild(modal);

        // Сохраняем ссылку на gameCreator для использования в preset функциях
        window.currentGameCreator = this;

        // Обработчик клика на рейтинг
        modal.querySelectorAll('.rating-button').forEach(btn => {
            btn.addEventListener('click', () => {
                const rating = btn.dataset.rating;
                btn.classList.toggle('active');

                if (btn.classList.contains('active')) {
                    if (!this.gameData.ratingRange.includes(rating)) {
                        this.gameData.ratingRange.push(rating);
                    }
                } else {
                    this.gameData.ratingRange = this.gameData.ratingRange.filter(r => r !== rating);
                }

                this.updateUI();
            });
        });

        // Закрытие модалки
        modal.querySelector('.game-modal-close').addEventListener('click', () => {
            modal.remove();
            window.currentGameCreator = null;
        });
    }

    openLocationModal() {
        const content = `
            <div class="location-selector">
                <p style="color: #666; margin-bottom: 20px;">Укажите площадку для игры</p>
                <div class="form-group">
                    <label>Название площадки</label>
                    <input type="text" class="form-control" id="locationInput"
                           placeholder="Например: Спорт Сити, Корт 3"
                           value="${this.gameData.location || ''}">
                </div>
                <div class="form-group">
                    <label>Адрес (необязательно)</label>
                    <input type="text" class="form-control" id="locationAddressInput"
                           placeholder="Например: ул. Ленина, 123"
                           value="${this.gameData.locationAddress || ''}">
                </div>
                <button class="btn btn-primary btn-block" id="saveLocationBtn">
                    <i class="fas fa-check"></i> Сохранить
                </button>
            </div>
        `;

        const modal = this.createModal('Локация игры', content);
        document.body.appendChild(modal);

        // Обработчик сохранения
        modal.querySelector('#saveLocationBtn').addEventListener('click', () => {
            const location = modal.querySelector('#locationInput').value.trim();
            const address = modal.querySelector('#locationAddressInput').value.trim();

            if (location) {
                this.gameData.location = location;
                this.gameData.locationAddress = address;
                this.updateUI();
                modal.remove();

                if (window.toast) {
                    toast.success('Локация сохранена');
                }
            } else {
                if (window.toast) {
                    toast.warning('Введите название площадки');
                }
            }
        });

        // Закрытие модалки
        modal.querySelector('.game-modal-close').addEventListener('click', () => {
            modal.remove();
        });
    }

    openCommentModal() {
        const content = `
            <div class="comment-input">
                <p style="color: #666; margin-bottom: 20px;">Добавьте заметку или пожелания к игре</p>
                <div class="form-group">
                    <textarea class="form-control" id="commentInput" rows="5"
                              placeholder="Например: Ищу партнёров для дружеской игры, уровень средний">${this.gameData.comment || ''}</textarea>
                    <div style="color: #999; font-size: 12px; margin-top: 8px;">
                        ${(this.gameData.comment || '').length}/500 символов
                    </div>
                </div>
                <button class="btn btn-primary btn-block" id="saveCommentBtn">
                    <i class="fas fa-check"></i> Сохранить
                </button>
            </div>
        `;

        const modal = this.createModal('Комментарий к игре', content);
        document.body.appendChild(modal);

        // Счетчик символов
        const textarea = modal.querySelector('#commentInput');
        const counter = modal.querySelector('div[style*="font-size: 12px"]');
        textarea.addEventListener('input', () => {
            const length = textarea.value.length;
            counter.textContent = `${length}/500 символов`;

            if (length > 500) {
                counter.style.color = '#ef4444';
            } else {
                counter.style.color = '#999';
            }
        });

        // Обработчик сохранения
        modal.querySelector('#saveCommentBtn').addEventListener('click', () => {
            const comment = textarea.value.trim();

            if (comment.length > 500) {
                if (window.toast) {
                    toast.error('Комментарий слишком длинный (максимум 500 символов)');
                }
                return;
            }

            this.gameData.comment = comment;
            this.updateUI();
            modal.remove();

            if (window.toast) {
                toast.success('Комментарий сохранён');
            }
        });

        // Закрытие модалки
        modal.querySelector('.game-modal-close').addEventListener('click', () => {
            modal.remove();
        });
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
        // Validate required fields
        if (!this.gameData.date || !this.gameData.time) {
            if (window.toast) toast.error('Укажите дату и время игры');
            return;
        }

        const btn = document.querySelector('.game-create-button');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Создание...';
        }

        try {
            const date = this.gameData.date;
            const dateStr = `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;

            const formData = new URLSearchParams({
                'date': dateStr,
                'start_time': this.gameData.time,
                'duration': this.gameData.duration.toString(),
                'game_mode': this.gameData.type === 'tournament' ? 'americano' : 'americano',
                'max_players': this.gameData.playerCount.toString(),
                'looking_for_partner': this.gameData.isPrivate ? '0' : '1',
                'is_public': this.gameData.isPrivate ? '0' : '1',
                'rounds_count': '3',
                'points_per_round': '24',
                'booking_type': 'game',
                'comment': this.gameData.comment || ''
            });

            // Add rating levels
            if (this.gameData.ratingRange && this.gameData.ratingRange.length > 0) {
                this.gameData.ratingRange.forEach(r => formData.append('required_rating_levels', r));
            }

            // Need court_id - for now use first available or check if location set
            // We need to get court from location or select first available
            const courtsResponse = await fetch('/booking/api/courts/');
            const courtsData = await courtsResponse.json();

            if (!courtsData.courts || courtsData.courts.length === 0) {
                if (window.toast) toast.error('Нет доступных кортов');
                return;
            }

            formData.append('court_id', courtsData.courts[0].id.toString());

            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                || document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1];

            const response = await fetch('/booking/create/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData.toString()
            });

            if (response.redirected) {
                window.location.href = response.url;
                return;
            }

            const data = await response.json();
            if (data.success) {
                if (window.toast) toast.success('Игра создана!');
                if (data.booking_id) {
                    window.location.href = `/booking/games/${data.booking_id}/`;
                } else {
                    window.location.href = '/booking/games/';
                }
            } else {
                if (window.toast) toast.error(data.message || 'Ошибка создания игры');
            }
        } catch (error) {
            console.error('Error creating game:', error);
            if (window.toast) toast.error('Ошибка при создании игры');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-plus"></i> Создать игру';
            }
        }
    }
}

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

let gameCreator;

document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.game-creator-container')) {
        gameCreator = new GameCreator();
    }
});

// ==================== GLOBAL HELPERS ====================

/**
 * Функция для быстрого выбора пресетов рейтинга
 */
window.selectRatingPreset = function(preset) {
    if (!window.currentGameCreator) return;

    const ratings = {
        all: ['D', 'D+', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+'],
        beginners: ['D', 'D+', 'C-', 'C', 'C+'],
        intermediate: ['C-', 'C', 'C+', 'B-', 'B', 'B+'],
        advanced: ['B-', 'B', 'B+', 'A-', 'A', 'A+']
    };

    window.currentGameCreator.gameData.ratingRange = ratings[preset] || [];
    window.currentGameCreator.updateUI();

    // Обновляем активные кнопки в модалке
    const modal = document.querySelector('.game-modal');
    if (modal) {
        modal.querySelectorAll('.rating-button').forEach(btn => {
            const rating = btn.dataset.rating;
            if (ratings[preset].includes(rating)) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    if (window.toast) {
        toast.success('Рейтинги выбраны');
    }
};

// Экспорт
window.GameCreator = GameCreator;
window.gameCreator = gameCreator;
