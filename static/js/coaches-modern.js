/**
 * ============================================
 * MODERN COACHES PAGE - JAVASCRIPT
 * ============================================
 *
 * Фильтры, поиск тренеров, двойной слайдер
 */

class CoachesFilter {
    constructor() {
        this.filters = {
            search: '',
            ratingRange: 'all',
            specialization: 'all',
            priceRange: 'all'
        };

        this.coaches = [];
        this.filteredCoaches = [];

        this.init();
    }

    init() {
        this.setupSearchFilter();
        this.setupRatingFilter();
        this.setupSpecFilter();
        this.setupPriceFilter();
        this.loadCoaches();
    }

    // ==================== SEARCH FILTER ====================
    setupSearchFilter() {
        const searchInput = document.getElementById('coachSearch');

        searchInput.addEventListener('input', (e) => {
            this.filters.search = e.target.value.toLowerCase().trim();
            this.applyFilters();
        });
    }

    // ==================== RATING FILTER ====================
    setupRatingFilter() {
        const ratingSelect = document.getElementById('ratingFilter');

        ratingSelect.addEventListener('change', (e) => {
            this.filters.ratingRange = e.target.value;
            this.applyFilters();
        });
    }

    // ==================== SPECIALIZATION FILTER ====================
    setupSpecFilter() {
        const specSelect = document.getElementById('specFilter');

        specSelect.addEventListener('change', (e) => {
            this.filters.specialization = e.target.value;
            this.applyFilters();
        });
    }

    // ==================== PRICE FILTER ====================
    setupPriceFilter() {
        const priceSelect = document.getElementById('priceFilter');

        priceSelect.addEventListener('change', (e) => {
            this.filters.priceRange = e.target.value;
            this.applyFilters();
        });
    }

    // ==================== LOAD COACHES ====================
    async loadCoaches() {
        try {
            // Проверяем, есть ли данные от Django
            if (typeof COACHES_DATA !== 'undefined' && COACHES_DATA.length > 0) {
                this.coaches = COACHES_DATA;
            } else {
                // Fallback на mock data для разработки
                this.coaches = this.getMockCoaches();
            }

            this.applyFilters();
        } catch (error) {
            console.error('Error loading coaches:', error);
            this.showError();
        }
    }

    // ==================== APPLY FILTERS ====================
    applyFilters() {
        this.filteredCoaches = this.coaches.filter(coach => {
            // Фильтр по поиску (имя или специализация)
            if (this.filters.search) {
                const searchMatch =
                    coach.name.toLowerCase().includes(this.filters.search) ||
                    (coach.spec && coach.spec.toLowerCase().includes(this.filters.search)) ||
                    (coach.specialization && coach.specialization.toLowerCase().includes(this.filters.search));

                if (!searchMatch) return false;
            }

            // Фильтр по рейтингу
            if (this.filters.ratingRange !== 'all') {
                const [min, max] = this.filters.ratingRange.split('-').map(parseFloat);
                if (coach.rating < min || coach.rating > max) {
                    return false;
                }
            }

            // Фильтр по специализации
            if (this.filters.specialization !== 'all') {
                if (coach.specialization !== this.filters.specialization) {
                    return false;
                }
            }

            // Фильтр по цене
            if (this.filters.priceRange !== 'all') {
                const price = coach.hourlyRate;
                const [min, max] = this.filters.priceRange.split('-').map(Number);

                if (max) {
                    if (price < min || price > max) return false;
                } else {
                    if (price < min) return false;
                }
            }

            return true;
        });

        this.renderCoaches();
        this.updateCount();
    }

    // ==================== RENDER COACHES ====================
    renderCoaches() {
        const grid = document.getElementById('coachesGrid');
        const emptyState = document.getElementById('emptyState');

        if (this.filteredCoaches.length === 0) {
            grid.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }

        grid.style.display = 'grid';
        emptyState.style.display = 'none';

        grid.innerHTML = this.filteredCoaches.map(coach => this.createCoachCard(coach)).join('');
    }

    createCoachCard(coach) {
        return `
            <div class="coach-card" onclick="window.location.href='/users/coaches/${coach.id}/'">
                <!-- Header с аватаром и рейтингом -->
                <div class="coach-card-header">
                    <div class="coach-avatar">
                        ${coach.avatar ? `<img src="${coach.avatar}" alt="${coach.name}">` : coach.name[0]}
                    </div>
                    <div class="coach-rating-badge">
                        <i class="fas fa-star"></i>
                        ${coach.rating.toFixed(1)}
                    </div>
                </div>

                <!-- Body с информацией -->
                <div class="coach-card-body">
                    <h3 class="coach-name">${coach.name}</h3>
                    ${coach.spec ? `
                    <div class="coach-specialization">
                        <i class="fas fa-certificate"></i>
                        <span>${coach.spec}</span>
                    </div>
                    ` : ''}

                    <!-- Мини-статистика -->
                    <div class="coach-stats-mini">
                        <div class="coach-stat-item">
                            <div class="coach-stat-value">${coach.experience}</div>
                            <div class="coach-stat-label">${this.pluralize(coach.experience, 'год', 'года', 'лет')}</div>
                        </div>
                        <div class="coach-stat-item">
                            <div class="coach-stat-value">${coach.studentsCount || 0}</div>
                            <div class="coach-stat-label">${this.pluralize(coach.studentsCount || 0, 'ученик', 'ученика', 'учеников')}</div>
                        </div>
                        <div class="coach-stat-item">
                            <div class="coach-stat-value">${coach.rating.toFixed(1)}</div>
                            <div class="coach-stat-label">оценка</div>
                        </div>
                    </div>

                    ${coach.bio ? `<p class="coach-bio-preview">${coach.bio}</p>` : ''}
                </div>

                <!-- Footer с ценой и кнопкой -->
                <div class="coach-card-footer">
                    <div class="coach-price">
                        <span class="coach-price-label">За час</span>
                        <span class="coach-price-value">${coach.hourlyRate}₽</span>
                    </div>
                    <button class="btn-contact-coach" onclick="event.stopPropagation(); bookCoach(${coach.id})">
                        <i class="fas fa-envelope"></i>
                        Связаться
                    </button>
                </div>
            </div>
        `;
    }

    // ==================== UPDATE COUNT ====================
    updateCount() {
        const countEl = document.getElementById('coachesCount');
        if (countEl) {
            countEl.textContent = this.filteredCoaches.length;
        }
    }

    // ==================== HELPERS ====================
    pluralize(number, one, two, five) {
        let n = Math.abs(number);
        n %= 100;
        if (n >= 5 && n <= 20) {
            return five;
        }
        n %= 10;
        if (n === 1) {
            return one;
        }
        if (n >= 2 && n <= 4) {
            return two;
        }
        return five;
    }

    showError() {
        const grid = document.getElementById('coachesGrid');
        grid.innerHTML = `
            <div class="error-state" style="grid-column: 1 / -1; text-align: center; padding: 60px 20px;">
                <i class="fas fa-exclamation-circle" style="font-size: 64px; color: #f44336; margin-bottom: 20px;"></i>
                <h3 style="font-size: 24px; color: #666; margin: 0 0 10px 0;">Ошибка загрузки</h3>
                <p style="font-size: 16px; color: #999; margin: 0 0 24px 0;">Не удалось загрузить список тренеров</p>
                <button class="btn-primary" onclick="location.reload()">Попробовать снова</button>
            </div>
        `;
    }

    // ==================== MOCK DATA ====================
    getMockCoaches() {
        return [
            {
                id: 1,
                name: 'Иван Петров',
                rating: 6.5,
                experience: 8,
                hourlyRate: 2500,
                specialization: 'advanced',
                spec: 'Продвинутые игроки',
                studentsCount: 24,
                avatar: null,
                bio: 'Мастер спорта по падел-теннису. Специализируюсь на подготовке продвинутых игроков к турнирам высокого уровня.'
            },
            {
                id: 2,
                name: 'Мария Иванова',
                rating: 5.0,
                experience: 5,
                hourlyRate: 1800,
                specialization: 'intermediate',
                spec: 'Средний уровень',
                studentsCount: 18,
                avatar: null,
                bio: 'Помогаю игрокам среднего уровня улучшить технику и тактику игры. Индивидуальный подход к каждому.'
            },
            {
                id: 3,
                name: 'Сергей Козлов',
                rating: 4.5,
                experience: 3,
                hourlyRate: 1200,
                specialization: 'beginner',
                spec: 'Начинающие',
                studentsCount: 12,
                avatar: null,
                bio: 'Обучаю основам падел-тенниса с нуля. Доступные объяснения и практические упражнения.'
            },
            {
                id: 4,
                name: 'Елена Смирнова',
                rating: 5.5,
                experience: 6,
                hourlyRate: 2000,
                specialization: 'kids',
                spec: 'Детские группы',
                studentsCount: 30,
                avatar: null,
                bio: 'Работаю с детьми от 6 до 14 лет. Игровой подход к обучению, развитие координации и командной работы.'
            }
        ];
    }
}

// ==================== GLOBAL FUNCTIONS ====================
function resetFilters() {
    location.reload();
}

async function bookCoach(coachId) {
    // Получаем информацию о тренере
    const coach = await fetchCoachInfo(coachId);
    if (!coach) {
        toast.error('Не удалось загрузить информацию о тренере');
        return;
    }

    // Показываем модальное окно бронирования
    showCoachBookingModal(coach);
}

async function fetchCoachInfo(coachId) {
    try {
        const response = await fetch(`/booking/api/coaches/${coachId}/`);
        const data = await response.json();
        return data.success ? data.coach : null;
    } catch (error) {
        console.error('Error fetching coach info:', error);
        return null;
    }
}

function showCoachBookingModal(coach) {
    // Создаём модальное окно
    const modal = document.createElement('div');
    modal.className = 'modal show';
    modal.id = 'coachBookingModal';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h3>
                    <i class="fas fa-chalkboard-teacher"></i>
                    Бронирование тренировки
                </h3>
                <button class="modal-close" onclick="closeCoachBookingModal()">×</button>
            </div>

            <div class="modal-body">
                <!-- Информация о тренере -->
                <div class="coach-booking-info">
                    <div class="coach-avatar-large">
                        ${coach.full_name.charAt(0).toUpperCase()}
                    </div>
                    <div class="coach-details">
                        <h4>${coach.full_name}</h4>
                        ${coach.specialization ? `<p class="text-muted">${coach.specialization}</p>` : ''}
                        ${coach.price_per_hour ? `<p class="price-info"><i class="fas fa-ruble-sign"></i> ${coach.price_per_hour} / час</p>` : ''}
                    </div>
                </div>

                <hr style="margin: 20px 0;">

                <!-- Форма бронирования -->
                <form id="coachBookingForm">
                    <input type="hidden" name="coach_id" value="${coach.id}">
                    <input type="hidden" name="booking_type" value="training">

                    <!-- Корт -->
                    <div class="form-group">
                        <label for="court_select">
                            <i class="fas fa-map-marker-alt"></i> Корт
                        </label>
                        <select id="court_select" name="court_id" class="form-control" required>
                            <option value="">Выберите корт</option>
                            <!-- Будет заполнено динамически -->
                        </select>
                    </div>

                    <!-- Дата -->
                    <div class="form-group">
                        <label for="booking_date">
                            <i class="fas fa-calendar"></i> Дата
                        </label>
                        <input type="date" id="booking_date" name="date" class="form-control"
                               min="${new Date().toISOString().split('T')[0]}" required>
                    </div>

                    <!-- Время начала -->
                    <div class="form-group">
                        <label for="start_time">
                            <i class="fas fa-clock"></i> Время начала
                        </label>
                        <select id="start_time" name="start_time" class="form-control" required>
                            <option value="">Выберите время</option>
                            <!-- Будет заполнено динамически -->
                        </select>
                    </div>

                    <!-- Длительность -->
                    <div class="form-group">
                        <label for="duration">
                            <i class="fas fa-hourglass-half"></i> Длительность
                        </label>
                        <select id="duration" name="duration" class="form-control" required>
                            <option value="1">1 час</option>
                            <option value="1.5">1.5 часа</option>
                            <option value="2" selected>2 часа</option>
                        </select>
                    </div>

                    <!-- Комментарий -->
                    <div class="form-group">
                        <label for="comment">
                            <i class="fas fa-comment"></i> Комментарий (необязательно)
                        </label>
                        <textarea id="comment" name="comment" class="form-control" rows="3"
                                  placeholder="Например: хочу улучшить подачу"></textarea>
                    </div>
                </form>
            </div>

            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeCoachBookingModal()">
                    Отмена
                </button>
                <button class="btn btn-primary" onclick="submitCoachBooking()" id="submitBookingBtn">
                    <i class="fas fa-check"></i> Забронировать
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Блокируем прокрутку body
    document.body.classList.add('modal-open');

    // Загружаем список кортов
    loadCourtsForBooking();

    // Генерируем временные слоты
    generateTimeSlots();
}

async function loadCourtsForBooking() {
    try {
        const response = await fetch('/booking/api/courts/');
        const data = await response.json();

        const select = document.getElementById('court_select');
        if (data.courts && data.courts.length > 0) {
            data.courts.forEach(court => {
                const option = document.createElement('option');
                option.value = court.id;
                option.textContent = `${court.name} (${court.price_per_hour} ₽/час)`;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading courts:', error);
    }
}

function generateTimeSlots() {
    const select = document.getElementById('start_time');
    const start = 8; // Начало работы - 8:00
    const end = 22; // Конец работы - 22:00

    for (let hour = start; hour < end; hour++) {
        for (let minute of [0, 30]) {
            const timeStr = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
            const option = document.createElement('option');
            option.value = timeStr;
            option.textContent = timeStr;
            select.appendChild(option);
        }
    }
}

async function submitCoachBooking() {
    const form = document.getElementById('coachBookingForm');
    const formData = new FormData(form);

    // Валидация
    if (!form.checkValidity()) {
        toast.warning('Заполните все обязательные поля');
        return;
    }

    // Отключаем кнопку
    const submitBtn = document.getElementById('submitBookingBtn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Бронирование...';

    try {
        const response = await fetch('/booking/create/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            toast.success('Тренировка успешно забронирована!');
            closeCoachBookingModal();

            // Перенаправляем на страницу бронирований через 1.5 секунд
            setTimeout(() => {
                window.location.href = '/users/profile/#bookings';
            }, 1500);
        } else {
            toast.error(data.message || 'Ошибка при бронировании');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-check"></i> Забронировать';
        }
    } catch (error) {
        console.error('Error creating booking:', error);
        toast.error('Ошибка при бронировании тренировки');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-check"></i> Забронировать';
    }
}

function closeCoachBookingModal() {
    const modal = document.getElementById('coachBookingModal');
    if (modal) {
        modal.remove();
    }
    document.body.classList.remove('modal-open');
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

// ==================== INIT ====================
let coachesFilter;

document.addEventListener('DOMContentLoaded', () => {
    coachesFilter = new CoachesFilter();
});
