/**
 * ============================================
 * TOURNAMENTS LIST
 * ============================================
 *
 * Управление списком турниров
 */

class TournamentsList {
    constructor() {
        this.tournaments = [];
        this.currentFilter = 'all';
        this.init();
    }

    init() {
        this.setupFilters();
        this.loadTournaments();
    }

    setupFilters() {
        const filterBtns = document.querySelectorAll('.tournament-filter-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // Убираем active у всех кнопок
                filterBtns.forEach(b => b.classList.remove('active'));
                // Добавляем active к нажатой
                btn.classList.add('active');

                // Применяем фильтр
                this.currentFilter = btn.dataset.filter;
                this.filterTournaments();
            });
        });
    }

    async loadTournaments() {
        try {
            this.showLoading();

            const response = await fetch('/tournament/api/list/');
            const data = await response.json();

            if (data.success) {
                this.tournaments = data.tournaments;
                this.renderTournaments();
            } else {
                this.showError(data.error || 'Ошибка загрузки турниров');
            }
        } catch (error) {
            console.error('Error loading tournaments:', error);
            this.showError('Ошибка соединения с сервером');
        }
    }

    filterTournaments() {
        if (this.currentFilter === 'all') {
            this.renderTournaments();
            return;
        }

        const filtered = this.tournaments.filter(t => t.status === this.currentFilter);
        this.renderTournaments(filtered);
    }

    renderTournaments(tournaments = null) {
        const grid = document.getElementById('tournamentsGrid');
        const emptyState = document.getElementById('emptyState');
        const loadingState = document.getElementById('loadingState');

        loadingState.style.display = 'none';

        const items = tournaments || this.tournaments;

        if (items.length === 0) {
            grid.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';
        grid.innerHTML = items.map(tournament => this.createTournamentCard(tournament)).join('');

        // Добавляем обработчики клика
        grid.querySelectorAll('.tournament-card').forEach((card, index) => {
            card.addEventListener('click', () => {
                window.location.href = `/tournament/public/${items[index].id}/`;
            });
        });
    }

    createTournamentCard(tournament) {
        const fillPercentage = (tournament.participants_count / tournament.max_participants) * 100;
        const isFull = tournament.participants_count >= tournament.max_participants;

        // Определяем градиент для хедера в зависимости от формата
        const headerGradients = {
            'americano': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'mexicano': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            'mixed_americano': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            'team_americano': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
            'team_mexicano': 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
            'doubles_elimination': 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
            'doubles_round_robin': 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
        };

        const gradient = headerGradients[tournament.format] || 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';

        // Статус текст
        const statusText = {
            'registration_open': 'Регистрация',
            'registration_closed': 'Закрыта',
            'in_progress': 'Идет',
            'completed': 'Завершен',
            'cancelled': 'Отменен',
            'draft': 'Черновик'
        };

        // Кнопка действия
        let buttonText = 'Подробнее';
        let buttonClass = '';

        if (tournament.status === 'registration_open' && !isFull) {
            buttonText = 'Зарегистрироваться';
        } else if (isFull) {
            buttonText = 'Мест нет';
            buttonClass = 'disabled';
        } else if (tournament.status === 'in_progress') {
            buttonText = 'Смотреть сетку';
        } else if (tournament.status === 'completed') {
            buttonText = 'Результаты';
        }

        return `
            <div class="tournament-card" data-id="${tournament.id}">
                <!-- Хедер -->
                <div class="tournament-card-header" style="background: ${gradient}; ${tournament.image ? `background-image: linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0.6)), url('${tournament.image}'); background-size: cover;` : ''}">
                    <div class="tournament-card-status status-${tournament.status}">
                        ${statusText[tournament.status] || tournament.status}
                    </div>
                    <h3 class="tournament-card-title">${tournament.name}</h3>
                    <div class="tournament-card-format">
                        <i class="fas fa-trophy"></i>
                        ${this.formatTypeShort(tournament.format)}
                    </div>
                </div>

                <!-- Тело -->
                <div class="tournament-card-body">
                    <!-- Даты -->
                    <div class="tournament-card-dates">
                        <i class="fas fa-calendar"></i>
                        <span>${tournament.start_date_formatted}${tournament.start_date !== tournament.end_date ? ' - ' + tournament.end_date_formatted : ''}</span>
                    </div>

                    <!-- Статистика -->
                    <div class="tournament-card-stats">
                        <div class="tournament-card-stat">
                            <p class="tournament-card-stat-value">${tournament.entry_fee}₽</p>
                            <p class="tournament-card-stat-label">Взнос</p>
                        </div>
                        <div class="tournament-card-stat">
                            <p class="tournament-card-stat-value">${tournament.prize_pool}₽</p>
                            <p class="tournament-card-stat-label">Призовые</p>
                        </div>
                        <div class="tournament-card-stat">
                            <p class="tournament-card-stat-value">${tournament.participants_count}/${tournament.max_participants}</p>
                            <p class="tournament-card-stat-label">Участники</p>
                        </div>
                    </div>

                    <!-- Прогресс -->
                    <div class="tournament-card-progress">
                        <div class="tournament-card-progress-label">
                            <span>Заполнено</span>
                            <span>${Math.round(fillPercentage)}%</span>
                        </div>
                        <div class="tournament-card-progress-bar">
                            <div class="tournament-card-progress-fill" style="width: ${fillPercentage}%"></div>
                        </div>
                    </div>

                    <!-- Кнопка -->
                    <button class="tournament-card-button ${buttonClass}">
                        ${buttonText}
                    </button>
                </div>
            </div>
        `;
    }

    formatTypeShort(format) {
        const types = {
            'americano': 'Americano',
            'mexicano': 'Mexicano',
            'mixed_americano': 'Mixed',
            'team_americano': 'Team Americano',
            'team_mexicano': 'Team Mexicano',
            'doubles_elimination': 'Плей-офф',
            'doubles_round_robin': 'Круговая',
        };
        return types[format] || format;
    }

    showLoading() {
        document.getElementById('tournamentsGrid').innerHTML = '';
        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('loadingState').style.display = 'block';
    }

    showError(message) {
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('tournamentsGrid').innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-circle"></i>
                <p>${message}</p>
                <button onclick="tournamentsList.loadTournaments()" class="btn-primary">
                    Попробовать снова
                </button>
            </div>
        `;
    }
}

// Инициализация
let tournamentsList;
document.addEventListener('DOMContentLoaded', () => {
    tournamentsList = new TournamentsList();
});
