/**
 * Управление листом ожидания и чатом игры
 * @version 1.0.0
 */

class GameWaitingList {
    constructor(bookingId) {
        this.bookingId = bookingId;
        this.isOwner = false;
        this.pollInterval = null;
        this.init();
    }

    init() {
        logger.info('Initializing GameWaitingList', { bookingId: this.bookingId });

        // Определяем является ли пользователь владельцем
        this.checkOwnership();

        // Привязываем обработчики событий
        this.bindEvents();

        // Загружаем лист ожидания если владелец
        if (this.isOwner) {
            this.loadWaitingList();
            this.startPolling();
        }
    }

    checkOwnership() {
        // Проверяем data-атрибут на странице
        const gameContainer = document.querySelector(`[data-booking-id="${this.bookingId}"]`);
        if (gameContainer) {
            this.isOwner = gameContainer.dataset.isOwner === 'true';
        }
    }

    bindEvents() {
        // Кнопка "Присоединиться к игре"
        const joinBtn = document.querySelector(`#join-game-btn-${this.bookingId}`);
        if (joinBtn) {
            joinBtn.addEventListener('click', () => this.joinGame());
        }

        // Делегирование для кнопок одобрения/отклонения
        document.addEventListener('click', (e) => {
            // Одобрить запрос
            if (e.target.closest('.approve-waiting-btn')) {
                const waitingId = e.target.closest('.approve-waiting-btn').dataset.waitingId;
                this.approveRequest(waitingId);
            }

            // Отклонить запрос
            if (e.target.closest('.reject-waiting-btn')) {
                const waitingId = e.target.closest('.reject-waiting-btn').dataset.waitingId;
                this.rejectRequest(waitingId);
            }
        });
    }

    async joinGame() {
        const joinBtn = document.querySelector(`#join-game-btn-${this.bookingId}`);
        if (joinBtn) {
            joinBtn.disabled = true;
            joinBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отправка...';
        }

        try {
            const response = await fetch(`/booking/waiting-list/${this.bookingId}/join/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: new URLSearchParams({ message: '' })
            });

            const data = await response.json();

            if (data.success) {
                toast.success(data.message);
                if (joinBtn) {
                    joinBtn.innerHTML = '<i class="fas fa-check"></i> Запрос отправлен';
                }
            } else {
                toast.error(data.message);
                if (joinBtn) {
                    joinBtn.disabled = false;
                    joinBtn.innerHTML = '<i class="fas fa-user-plus"></i> Отправить запрос';
                }
            }
        } catch (error) {
            logger.error('Error joining game', { error });
            toast.error('Ошибка при отправке запроса');
            if (joinBtn) {
                joinBtn.disabled = false;
                joinBtn.innerHTML = '<i class="fas fa-user-plus"></i> Отправить запрос';
            }
        }
    }

    async loadWaitingList() {
        try {
            const response = await fetch(`/booking/waiting-list/${this.bookingId}/`);
            const data = await response.json();

            if (data.success) {
                this.renderWaitingList(data.waiting_list);
                logger.debug('Waiting list loaded', { count: data.count });
            }
        } catch (error) {
            logger.error('Error loading waiting list', { error });
        }
    }

    renderWaitingList(waitingList) {
        const container = document.querySelector('#waiting-list-container');
        if (!container) return;

        if (waitingList.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-users fa-3x" style="color: #ccc;"></i>
                    <p style="color: #999; margin-top: 16px;">Нет запросов на присоединение</p>
                </div>
            `;
            return;
        }

        container.innerHTML = waitingList.map(waiting => `
            <div class="waiting-list-item" data-waiting-id="${waiting.id}">
                <div class="waiting-user">
                    <div class="user-avatar">
                        ${waiting.user.full_name.charAt(0).toUpperCase()}
                    </div>
                    <div class="user-info">
                        <div class="user-name">${waiting.user.full_name}</div>
                        ${waiting.user.rating ? `
                            <div class="user-rating">
                                <i class="fas fa-star"></i>
                                ${waiting.user.rating.level} (${waiting.user.rating.numeric.toFixed(2)})
                            </div>
                        ` : ''}
                    </div>
                </div>
                ${waiting.message ? `
                    <div class="waiting-message">
                        <i class="fas fa-comment"></i> ${waiting.message}
                    </div>
                ` : ''}
                <div class="waiting-actions">
                    <button class="btn btn-success btn-sm approve-waiting-btn" data-waiting-id="${waiting.id}">
                        <i class="fas fa-check"></i> Принять
                    </button>
                    <button class="btn btn-danger btn-sm reject-waiting-btn" data-waiting-id="${waiting.id}">
                        <i class="fas fa-times"></i> Отклонить
                    </button>
                </div>
                <div class="waiting-time">
                    ${this.formatTime(waiting.created_at)}
                </div>
            </div>
        `).join('');
    }

    async approveRequest(waitingId) {
        try {
            showLoading('Одобрение запроса...');

            const response = await fetch(`/booking/waiting-list/${waitingId}/approve/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });

            const data = await response.json();
            hideLoading();

            if (data.success) {
                toast.success(data.message);

                // Удаляем элемент из списка
                const item = document.querySelector(`[data-waiting-id="${waitingId}"]`);
                if (item) {
                    item.style.animation = 'fadeOut 0.3s';
                    setTimeout(() => item.remove(), 300);
                }

                // Перезагружаем список
                this.loadWaitingList();

                logger.info('Request approved', { waitingId });
            } else {
                toast.error(data.message);
            }
        } catch (error) {
            hideLoading();
            logger.error('Error approving request', { error });
            toast.error('Ошибка при одобрении запроса');
        }
    }

    async rejectRequest(waitingId) {
        try {
            // Опционально: спросить причину отклонения
            const reason = prompt('Причина отклонения (необязательно):');
            if (reason === null) return; // Пользователь отменил

            showLoading('Отклонение запроса...');

            const response = await fetch(`/booking/waiting-list/${waitingId}/reject/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: new URLSearchParams({ reason })
            });

            const data = await response.json();
            hideLoading();

            if (data.success) {
                toast.success(data.message);

                // Удаляем элемент из списка
                const item = document.querySelector(`[data-waiting-id="${waitingId}"]`);
                if (item) {
                    item.style.animation = 'fadeOut 0.3s';
                    setTimeout(() => item.remove(), 300);
                }

                // Перезагружаем список
                this.loadWaitingList();

                logger.info('Request rejected', { waitingId });
            } else {
                toast.error(data.message);
            }
        } catch (error) {
            hideLoading();
            logger.error('Error rejecting request', { error });
            toast.error('Ошибка при отклонении запроса');
        }
    }

    showMessageModal() {
        return new Promise((resolve) => {
            // Создаём простую модалку
            const modal = document.createElement('div');
            modal.className = 'modal show';
            modal.innerHTML = `
                <div class="modal-content" style="max-width: 400px;">
                    <div class="modal-header">
                        <h3>Присоединиться к игре</h3>
                        <button class="modal-close" type="button" data-action="close">×</button>
                    </div>
                    <div class="modal-body">
                        <p>Отправьте запрос владельцу игры на присоединение</p>
                        <textarea id="join-message" class="form-control" rows="3"
                            placeholder="Напишите сообщение владельцу (необязательно)"></textarea>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" type="button" data-action="cancel">
                            Отмена
                        </button>
                        <button class="btn btn-primary" id="confirm-join-btn">
                            Отправить запрос
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            const closeWith = (value) => {
                modal.remove();
                resolve(value);
            };

            const closeBtn = modal.querySelector('[data-action="close"]');
            if (closeBtn) closeBtn.addEventListener('click', () => closeWith(null));

            const cancelBtn = modal.querySelector('[data-action="cancel"]');
            if (cancelBtn) cancelBtn.addEventListener('click', () => closeWith(null));

            // Обработчик кнопки подтверждения
            document.getElementById('confirm-join-btn').addEventListener('click', () => {
                const message = document.getElementById('join-message').value.trim();
                closeWith(message);
            });

            // Закрытие по клику по фону
            modal.addEventListener('click', (e) => {
                if (e.target === modal) closeWith(null);
            });

            // Закрытие по Esc
            document.addEventListener('keydown', function escHandler(e) {
                if (e.key === 'Escape') {
                    document.removeEventListener('keydown', escHandler);
                    closeWith(null);
                }
            });
        });
    }

    startPolling() {
        // Обновляем лист ожидания каждые 10 секунд
        this.pollInterval = setInterval(() => {
            this.loadWaitingList();
        }, 10000);
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    formatTime(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000); // секунды

        if (diff < 60) return 'только что';
        if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`;
        if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`;
        return date.toLocaleDateString('ru-RU');
    }

    destroy() {
        this.stopPolling();
    }
}

// Вспомогательные функции
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

function showLoading(message = 'Загрузка...') {
    // Реализация показа индикатора загрузки
    if (window.toast) {
        toast.info(message);
    }
}

function hideLoading() {
    // Реализация скрытия индикатора загрузки
}

// Экспортируем класс
window.GameWaitingList = GameWaitingList;
