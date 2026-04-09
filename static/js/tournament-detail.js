/**
 * ============================================
 * TOURNAMENT DETAIL
 * ============================================
 *
 * Детальная страница турнира
 */

let selectedPartner = null;

// Загрузка таблицы лидеров (публичный API)
async function loadLeaderboard() {
    const container = document.getElementById('leaderboardTable');
    if (!container) return;

    try {
        const response = await fetch(`/tournaments/ajax/tournament/${TOURNAMENT_ID}/leaderboard/`);
        const data = await response.json();

        if (data.success) {
            renderLeaderboard(data.leaderboard);
        } else {
            container.innerHTML = '<p style="text-align:center;color:#999;">Не удалось загрузить таблицу лидеров</p>';
        }
    } catch (error) {
        console.error('Error loading leaderboard:', error);
        container.innerHTML = '<p style="text-align:center;color:#999;">Ошибка загрузки таблицы лидеров</p>';
    }
}

function renderLeaderboard(leaderboard) {
    const container = document.getElementById('leaderboardTable');

    if (!leaderboard || leaderboard.length === 0) {
        container.innerHTML = '<p style="text-align:center;color:#999;">Нет данных для таблицы лидеров</p>';
        return;
    }

    let html = `
        <table class="leaderboard-responsive-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Игрок</th>
                    <th>Очки</th>
                    <th>Матчи</th>
                    <th>Победы</th>
                    <th>% побед</th>
                </tr>
            </thead>
            <tbody>
    `;

    leaderboard.forEach(p => {
        const rankClass = p.rank <= 3 ? `rank-${p.rank}` : '';
        html += `
            <tr class="${rankClass}">
                <td class="rank-cell">
                    ${p.rank <= 3 ? `<span class="rank-medal">${['', '&#129351;', '&#129352;', '&#129353;'][p.rank]}</span>` : p.rank}
                </td>
                <td class="player-cell">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <div class="participant-avatar-small">
                            ${p.avatar ? `<img src="${p.avatar}" alt="${p.name}">` : (p.name ? p.name[0].toUpperCase() : '?')}
                        </div>
                        <span>${p.name}</span>
                    </div>
                </td>
                <td><strong>${p.total_points}</strong></td>
                <td>${p.matches_played}</td>
                <td>${p.matches_won}</td>
                <td>${p.win_rate}%</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// Загрузка сетки турнира
async function loadBracket() {
    const bracketContainer = document.getElementById('tournamentBracket');
    if (!bracketContainer) return;

    try {
        const response = await fetch(`/tournaments/api/${TOURNAMENT_ID}/bracket/`);
        const data = await response.json();

        if (data.success) {
            renderBracket(data.bracket);
        }
    } catch (error) {
        console.error('Error loading bracket:', error);
    }
}

function renderBracket(bracket) {
    const container = document.getElementById('tournamentBracket');

    if (!bracket || bracket.length === 0) {
        container.innerHTML = `
            <div class="bracket-info">
                <i class="fas fa-info-circle"></i>
                <p>Сетка турнира будет доступна после начала</p>
            </div>
        `;
        return;
    }

    // Создаём контейнер для сетки
    let html = '<div class="tournament-bracket">';

    // Проходимся по каждому раунду
    bracket.forEach((round, roundIndex) => {
        html += `
            <div class="bracket-round" data-round="${round.round_number}">
                <h3 class="round-title">${round.round_name || `Раунд ${round.round_number}`}</h3>
                <div class="round-matches">
        `;

        // Отображаем матчи в раунде
        round.matches.forEach(match => {
            const team1Won = match.winning_team_id === match.team1.id;
            const team2Won = match.winning_team_id === match.team2.id;
            const isCompleted = match.status === 'completed';
            const isInProgress = match.status === 'in_progress';

            html += `
                <div class="bracket-match ${isCompleted ? 'completed' : ''} ${isInProgress ? 'in-progress' : ''}" data-match-id="${match.id}">
                    <!-- Команда 1 -->
                    <div class="match-team ${team1Won ? 'winner' : ''} ${team2Won ? 'loser' : ''}">
                        <div class="team-info">
                            <div class="team-name">${match.team1.name}</div>
                            ${match.team1.player1 ? `
                                <div class="team-players">
                                    ${match.team1.player1}
                                    ${match.team1.player2 ? ` & ${match.team1.player2}` : ''}
                                </div>
                            ` : ''}
                        </div>
                        ${isCompleted || isInProgress ? `
                            <div class="team-score ${team1Won ? 'winning-score' : ''}">${match.score_team1 || 0}</div>
                        ` : ''}
                    </div>

                    <!-- Разделитель -->
                    <div class="match-divider">
                        ${isInProgress ? '<i class="fas fa-circle pulse"></i>' : 'vs'}
                    </div>

                    <!-- Команда 2 -->
                    <div class="match-team ${team2Won ? 'winner' : ''} ${team1Won ? 'loser' : ''}">
                        <div class="team-info">
                            <div class="team-name">${match.team2.name}</div>
                            ${match.team2.player1 ? `
                                <div class="team-players">
                                    ${match.team2.player1}
                                    ${match.team2.player2 ? ` & ${match.team2.player2}` : ''}
                                </div>
                            ` : ''}
                        </div>
                        ${isCompleted || isInProgress ? `
                            <div class="team-score ${team2Won ? 'winning-score' : ''}">${match.score_team2 || 0}</div>
                        ` : ''}
                    </div>

                    <!-- Статус матча -->
                    ${isCompleted ? `
                        <div class="match-status completed">
                            <i class="fas fa-check-circle"></i> Завершён
                        </div>
                    ` : isInProgress ? `
                        <div class="match-status in-progress">
                            <i class="fas fa-play-circle"></i> В процессе
                        </div>
                    ` : `
                        <div class="match-status pending">
                            <i class="fas fa-clock"></i> Ожидается
                        </div>
                    `}
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}

// Поиск партнера
let partnerSearchTimeout;
const partnerSearchInput = document.getElementById('partnerSearch');
const partnerSearchResults = document.getElementById('partnerSearchResults');

if (partnerSearchInput) {
    partnerSearchInput.addEventListener('input', (e) => {
        clearTimeout(partnerSearchTimeout);

        const query = e.target.value.trim();

        if (query.length < 2) {
            partnerSearchResults.classList.remove('active');
            partnerSearchResults.innerHTML = '';
            return;
        }

        partnerSearchTimeout = setTimeout(() => {
            searchPartners(query);
        }, 300);
    });
}

async function searchPartners(query) {
    try {
        const response = await fetch(`/booking/api/search-users/?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.success) {
            renderPartnerSearchResults(data.users);
        }
    } catch (error) {
        console.error('Error searching partners:', error);
    }
}

function renderPartnerSearchResults(users) {
    if (users.length === 0) {
        partnerSearchResults.classList.add('active');
        partnerSearchResults.innerHTML = `
            <div class="partner-result-item">
                <p style="color: #999; margin: 0;">Ничего не найдено</p>
            </div>
        `;
        return;
    }

    partnerSearchResults.classList.add('active');
    partnerSearchResults.innerHTML = users.map(user => `
        <div class="partner-result-item" onclick="selectPartner(${user.id}, '${user.name}')">
            <strong>${user.name}</strong>
            ${user.rating ? `<span style="color: #999; margin-left: 8px;">${user.rating}</span>` : ''}
        </div>
    `).join('');
}

function selectPartner(userId, userName) {
    selectedPartner = userId;
    partnerSearchInput.value = userName;
    partnerSearchResults.classList.remove('active');
    partnerSearchResults.innerHTML = '';
}

// Регистрация на турнир
async function registerForTournament(tournamentId) {
    const button = document.querySelector('.btn-register');
    const originalText = button.textContent;

    try {
        button.disabled = true;
        button.textContent = 'Регистрация...';

        const formData = {
            tournament_id: tournamentId
        };

        // Для командных турниров добавляем партнера
        if (IS_TEAM_TOURNAMENT) {
            if (!selectedPartner) {
                alert('Пожалуйста, выберите партнера');
                button.disabled = false;
                button.textContent = originalText;
                return;
            }

            formData.partner_id = selectedPartner;

            const teamNameInput = document.getElementById('teamName');
            if (teamNameInput && teamNameInput.value.trim()) {
                formData.team_name = teamNameInput.value.trim();
            }
        }

        const response = await fetch(`/tournaments/public/${tournamentId}/register/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.success) {
            if (window.toast) {
                toast.success(data.message || 'Вы успешно зарегистрированы!');
            } else {
                alert(data.message || 'Вы успешно зарегистрированы!');
            }

            // Перезагружаем страницу через 1 секунду
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            if (window.toast) {
                toast.error(data.error || 'Ошибка регистрации');
            } else {
                alert(data.error || 'Ошибка регистрации');
            }

            button.disabled = false;
            button.textContent = originalText;
        }
    } catch (error) {
        console.error('Error registering:', error);

        if (window.toast) {
            toast.error('Ошибка соединения с сервером');
        } else {
            alert('Ошибка соединения с сервером');
        }

        button.disabled = false;
        button.textContent = originalText;
    }
}

// Отмена регистрации
async function unregisterFromTournament(tournamentId) {
    if (!confirm('Вы уверены, что хотите отменить регистрацию?')) {
        return;
    }

    try {
        const response = await fetch(`/tournaments/public/${tournamentId}/unregister/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        const data = await response.json();

        if (data.success) {
            if (window.toast) {
                toast.success(data.message || 'Регистрация отменена');
            } else {
                alert(data.message || 'Регистрация отменена');
            }

            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            if (window.toast) {
                toast.error(data.error || 'Ошибка отмены регистрации');
            } else {
                alert(data.error || 'Ошибка отмены регистрации');
            }
        }
    } catch (error) {
        console.error('Error unregistering:', error);

        if (window.toast) {
            toast.error('Ошибка соединения с сервером');
        } else {
            alert('Ошибка соединения с сервером');
        }
    }
}

// Вспомогательная функция для получения CSRF токена
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

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    if (typeof TOURNAMENT_ID !== 'undefined') {
        // Загружаем таблицу лидеров
        loadLeaderboard();

        // Загружаем сетку если турнир начался
        const bracketContainer = document.getElementById('tournamentBracket');
        if (bracketContainer) {
            loadBracket();
        }
    }
});
