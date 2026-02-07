/**
 * ============================================
 * TOURNAMENT DETAIL
 * ============================================
 *
 * Детальная страница турнира
 */

let selectedPartner = null;

// Загрузка участников
async function loadParticipants() {
    try {
        const response = await fetch(`/tournament/api/${TOURNAMENT_ID}/`);
        const data = await response.json();

        if (data.success) {
            renderParticipants(data.tournament.participants);
        }
    } catch (error) {
        console.error('Error loading participants:', error);
    }
}

function renderParticipants(participants) {
    const container = document.getElementById('participantsList');

    if (!participants || participants.length === 0) {
        container.innerHTML = `
            <div class="empty-state-small">
                <p>Пока нет участников</p>
            </div>
        `;
        return;
    }

    container.innerHTML = participants.map(p => `
        <div class="participant-item">
            <div class="participant-avatar">
                ${p.avatar ? `<img src="${p.avatar}" alt="${p.name}">` : p.name[0].toUpperCase()}
            </div>
            <div class="participant-info">
                <p class="participant-name">${p.name}${p.partner ? ` + ${p.partner_name}` : ''}</p>
                <p class="participant-rating">${p.rating || 'Без рейтинга'}</p>
            </div>
        </div>
    `).join('');
}

// Загрузка сетки турнира
async function loadBracket() {
    const bracketContainer = document.getElementById('tournamentBracket');
    if (!bracketContainer) return;

    try {
        const response = await fetch(`/tournament/api/${TOURNAMENT_ID}/bracket/`);
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

    // TODO: Реализовать визуализацию сетки турнира
    // Пока просто показываем сообщение
    container.innerHTML = `
        <div class="bracket-info">
            <i class="fas fa-info-circle"></i>
            <p>Сетка турнира будет доступна после начала</p>
        </div>
    `;
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

        const response = await fetch(`/tournament/public/${tournamentId}/register/`, {
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
        const response = await fetch(`/tournament/public/${tournamentId}/unregister/`, {
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
    // Загружаем участников
    loadParticipants();

    // Загружаем сетку если турнир начался
    if (typeof TOURNAMENT_ID !== 'undefined') {
        const bracketContainer = document.getElementById('tournamentBracket');
        if (bracketContainer) {
            loadBracket();
        }
    }
});
