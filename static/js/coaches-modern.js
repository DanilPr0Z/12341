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
            minRating: 1.0,
            maxRating: 7.0,
            timeOfDay: 'all',
            specialization: 'all',
            priceRange: 'all'
        };

        this.coaches = [];
        this.filteredCoaches = [];

        this.init();
    }

    init() {
        this.setupRangeSlider();
        this.setupTimeFilters();
        this.setupSpecFilters();
        this.setupPriceFilters();
        this.loadCoaches();
    }

    // ==================== RANGE SLIDER ====================
    setupRangeSlider() {
        const minSlider = document.getElementById('minRating');
        const maxSlider = document.getElementById('maxRating');
        const minLabel = document.getElementById('minRatingLabel');
        const maxLabel = document.getElementById('maxRatingLabel');
        const sliderRange = document.getElementById('sliderRange');

        const updateSlider = () => {
            let min = parseFloat(minSlider.value);
            let max = parseFloat(maxSlider.value);

            // Не даём слайдерам пересекаться
            if (min > max - 0.5) {
                min = max - 0.5;
                minSlider.value = min;
            }

            if (max < min + 0.5) {
                max = min + 0.5;
                maxSlider.value = max;
            }

            // Обновляем labels
            minLabel.textContent = min.toFixed(1);
            maxLabel.textContent = max.toFixed(1);

            // Обновляем визуальный range
            const minPercent = ((min - 1) / 6) * 100;
            const maxPercent = ((max - 1) / 6) * 100;

            sliderRange.style.left = minPercent + '%';
            sliderRange.style.width = (maxPercent - minPercent) + '%';

            // Сохраняем в фильтры
            this.filters.minRating = min;
            this.filters.maxRating = max;

            // Применяем фильтры
            this.applyFilters();
        };

        minSlider.addEventListener('input', updateSlider);
        maxSlider.addEventListener('input', updateSlider);

        // Инициализация
        updateSlider();
    }

    // ==================== TIME FILTERS ====================
    setupTimeFilters() {
        const timeBtns = document.querySelectorAll('.time-btn');

        timeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // Убираем active у всех
                timeBtns.forEach(b => b.classList.remove('active'));
                // Добавляем active к нажатой
                btn.classList.add('active');

                // Сохраняем фильтр
                this.filters.timeOfDay = btn.dataset.time;

                // Применяем
                this.applyFilters();
            });
        });
    }

    // ==================== SPECIALIZATION FILTERS ====================
    setupSpecFilters() {
        const specBtns = document.querySelectorAll('.spec-btn');

        specBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // Убираем active у всех
                specBtns.forEach(b => b.classList.remove('active'));
                // Добавляем active к нажатой
                btn.classList.add('active');

                // Сохраняем фильтр
                this.filters.specialization = btn.dataset.spec;

                // Применяем
                this.applyFilters();
            });
        });
    }

    // ==================== PRICE FILTERS ====================
    setupPriceFilters() {
        const priceBtns = document.querySelectorAll('.price-btn');

        priceBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // Убираем active у всех
                priceBtns.forEach(b => b.classList.remove('active'));
                // Добавляем active к нажатой
                btn.classList.add('active');

                // Сохраняем фильтр
                this.filters.priceRange = btn.dataset.price;

                // Применяем
                this.applyFilters();
            });
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
            // Фильтр по рейтингу
            if (coach.rating < this.filters.minRating || coach.rating > this.filters.maxRating) {
                return false;
            }

            // Фильтр по времени
            if (this.filters.timeOfDay !== 'all') {
                if (!coach.availableTimes || !coach.availableTimes.includes(this.filters.timeOfDay)) {
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
                <div class="coach-card-header">
                    <div class="coach-avatar">
                        ${coach.avatar ? `<img src="${coach.avatar}" alt="${coach.name}">` : coach.name[0]}
                    </div>
                    <div class="coach-info">
                        <h3 class="coach-name">${coach.name}</h3>
                        <div class="coach-rating">
                            <i class="fas fa-star"></i>
                            <span>${coach.rating.toFixed(1)}</span>
                        </div>
                        ${coach.spec ? `
                        <div class="coach-specialization">
                            <i class="fas fa-certificate"></i>
                            <span>${coach.spec}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>

                <div class="coach-details">
                    <div class="coach-detail-item">
                        <i class="fas fa-clock"></i>
                        <span>Опыт: ${coach.experience} ${this.pluralize(coach.experience, 'год', 'года', 'лет')}</span>
                    </div>
                    <div class="coach-detail-item">
                        <i class="fas fa-users"></i>
                        <span>${coach.studentsCount || 0} ${this.pluralize(coach.studentsCount || 0, 'ученик', 'ученика', 'учеников')}</span>
                    </div>
                </div>

                <div class="coach-price">
                    <span class="coach-price-label">Стоимость часа</span>
                    <span class="coach-price-value">${coach.hourlyRate}₽</span>
                </div>

                <div class="coach-actions">
                    <button class="btn-book-coach" onclick="event.stopPropagation(); bookCoach(${coach.id})">
                        Забронировать
                    </button>
                    <button class="btn-view-coach" onclick="event.stopPropagation(); window.location.href='/users/coaches/${coach.id}/'">
                        <i class="fas fa-eye"></i>
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
                availableTimes: ['morning', 'day', 'evening']
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
                availableTimes: ['day', 'evening']
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
                availableTimes: ['all']
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
                availableTimes: ['morning', 'day']
            }
        ];
    }
}

// ==================== GLOBAL FUNCTIONS ====================
function resetFilters() {
    location.reload();
}

function bookCoach(coachId) {
    // TODO: Реализовать бронирование тренера
    alert(`Бронирование тренера ID: ${coachId}`);
}

// ==================== INIT ====================
let coachesFilter;

document.addEventListener('DOMContentLoaded', () => {
    coachesFilter = new CoachesFilter();
});
