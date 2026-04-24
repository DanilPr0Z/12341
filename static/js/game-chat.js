/**
 * Чат игры
 * @version 1.0.0
 */

class GameChat {
    constructor(bookingId) {
        this.bookingId = bookingId;
        this.messages = [];
        this.pollInterval = null;
        this.lastMessageId = 0;
        this.init();
    }

    init() {
        logger.info('Initializing GameChat', { bookingId: this.bookingId });

        // Привязываем обработчики событий
        this.bindEvents();

        // Загружаем сообщения
        this.loadMessages();

        // Запускаем опрос новых сообщений
        this.startPolling();
    }

    bindEvents() {
        const sendBtn = document.querySelector('#send-chat-message-btn');
        const messageInput = document.querySelector('#chat-message-input');

        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }

        if (messageInput) {
            // Отправка по Enter (но не Shift+Enter)
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
    }

    async loadMessages() {
        try {
            const response = await fetch(`/booking/chat/${this.bookingId}/`);
            const data = await response.json();

            if (data.success) {
                this.messages = data.messages;
                this.renderMessages();

                // Запоминаем ID последнего сообщения
                if (this.messages.length > 0) {
                    this.lastMessageId = this.messages[this.messages.length - 1].id;
                }

                logger.debug('Chat messages loaded', { count: data.count });
            }
        } catch (error) {
            logger.error('Error loading chat messages', { error });
        }
    }

    renderMessages() {
        const container = document.querySelector('#chat-messages-container');
        if (!container) return;

        if (this.messages.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="text-align: center; padding: 40px 20px;">
                    <i class="fas fa-comments fa-3x" style="color: #ccc;"></i>
                    <p style="color: #999; margin-top: 16px;">Начните общение с участниками игры</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.messages.map(msg => this.renderMessage(msg)).join('');

        // Прокручиваем вниз
        container.scrollTop = container.scrollHeight;
    }

    renderMessage(msg) {
        const messageClass = msg.is_own ? 'chat-message-own' : 'chat-message-other';
        const systemClass = msg.is_system ? 'chat-message-system' : '';

        if (msg.is_system) {
            return `
                <div class="chat-message ${systemClass}" data-message-id="${msg.id}">
                    <div class="system-message-content">
                        <i class="fas fa-info-circle"></i>
                        ${msg.message}
                    </div>
                    <div class="message-time">${this.formatTime(msg.created_at)}</div>
                </div>
            `;
        }

        return `
            <div class="chat-message ${messageClass}" data-message-id="${msg.id}">
                <div class="message-header">
                    <span class="message-author">${msg.user.full_name}</span>
                    <span class="message-time">${this.formatTime(msg.created_at)}</span>
                </div>
                <div class="message-content">${this.escapeHtml(msg.message)}</div>
            </div>
        `;
    }

    async sendMessage() {
        const input = document.querySelector('#chat-message-input');
        if (!input) return;

        const message = input.value.trim();
        if (!message) {
            toast.warning('Введите сообщение');
            return;
        }

        if (message.length > 1000) {
            toast.error('Сообщение слишком длинное (максимум 1000 символов)');
            return;
        }

        try {
            const response = await fetch(`/booking/chat/${this.bookingId}/send/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: new URLSearchParams({ message })
            });

            const data = await response.json();

            if (data.success) {
                // Очищаем поле ввода
                input.value = '';

                // Добавляем сообщение в список
                this.messages.push(data.chat_message);
                this.lastMessageId = data.chat_message.id;

                // Перерисовываем
                this.renderMessages();

                logger.info('Chat message sent', { bookingId: this.bookingId });
            } else {
                toast.error(data.message);
            }
        } catch (error) {
            logger.error('Error sending chat message', { error });
            toast.error('Ошибка при отправке сообщения');
        }
    }

    async checkNewMessages() {
        try {
            const response = await fetch(`/booking/chat/${this.bookingId}/`);
            const data = await response.json();

            if (data.success && data.messages.length > 0) {
                const lastServerMessageId = data.messages[data.messages.length - 1].id;

                // Если есть новые сообщения
                if (lastServerMessageId > this.lastMessageId) {
                    // Добавляем только новые сообщения
                    const newMessages = data.messages.filter(msg => msg.id > this.lastMessageId);

                    newMessages.forEach(msg => {
                        this.messages.push(msg);

                        // Добавляем новое сообщение в DOM
                        const container = document.querySelector('#chat-messages-container');
                        if (container) {
                            const messageEl = document.createElement('div');
                            messageEl.innerHTML = this.renderMessage(msg);
                            container.appendChild(messageEl.firstElementChild);

                            // Прокручиваем вниз
                            container.scrollTop = container.scrollHeight;
                        }
                    });

                    this.lastMessageId = lastServerMessageId;

                    // Показываем уведомление о новых сообщениях (если не свои)
                    const hasOtherMessages = newMessages.some(msg => !msg.is_own);
                    if (hasOtherMessages && document.hidden) {
                        this.showNotification('Новое сообщение в чате игры');
                    }

                    logger.debug('New chat messages received', { count: newMessages.length });
                }
            }
        } catch (error) {
            logger.error('Error checking new messages', { error });
        }
    }

    startPolling() {
        // Проверяем новые сообщения каждые 3 секунды
        this.pollInterval = setInterval(() => {
            this.checkNewMessages();
        }, 3000);
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    showNotification(message) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Paddle Booking', {
                body: message,
                icon: '/static/img/icon.png'
            });
        }
    }

    formatTime(isoString) {
        const date = new Date(isoString);
        const opts = { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Samara' };
        const dateOpts = { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'Europe/Samara' };

        const now = new Date();
        const todayStr = now.toLocaleDateString('ru-RU', dateOpts);
        const msgDateStr = date.toLocaleDateString('ru-RU', dateOpts);

        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayStr = yesterday.toLocaleDateString('ru-RU', dateOpts);

        const time = date.toLocaleTimeString('ru-RU', opts);

        if (msgDateStr === todayStr) return time;
        if (msgDateStr === yesterdayStr) return 'вчера ' + time;
        return msgDateStr + ' ' + time;
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
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

// Экспортируем класс
window.GameChat = GameChat;
