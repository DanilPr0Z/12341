/**
 * Notifications Management System
 * Handles loading, displaying, and interacting with user notifications
 */

// Load notifications for profile page
function loadProfileNotifications() {
    const container = document.getElementById('notificationsListProfile');
    const accordionBadge = document.getElementById('accordionNotificationBadge');

    if (!container) return;

    fetch('/booking/api/notifications/')
        .then(response => response.json())
        .then(data => {
            console.log('📬 Уведомления загружены для профиля:', data);

            if (data.success && data.notifications && data.notifications.length > 0) {
                // Обновляем badge в аккордеоне
                if (accordionBadge) {
                    accordionBadge.textContent = data.count;
                    accordionBadge.style.display = 'inline-flex';
                }

                // Рендерим уведомления
                container.innerHTML = data.notifications.map(notification => `
                    <div class="notification-card invitation" data-invitation-id="${notification.id}">
                        <div class="notification-card-header">
                            <div class="notification-icon">
                                <i class="fas fa-user-plus"></i>
                            </div>
                            <div class="notification-time">
                                <i class="fas fa-clock"></i>
                                Только что
                            </div>
                        </div>

                        <div class="notification-content">
                            <h3 class="notification-title">${notification.title}</h3>
                            <p class="notification-text">${notification.message}</p>

                            ${notification.details ? `
                                <div class="notification-details">
                                    ${notification.details.map(detail => `
                                        <div class="notification-detail-item">
                                            <i class="${detail.icon}"></i>
                                            <span>${detail.text}</span>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : ''}

                            <div class="notification-actions">
                                <button class="btn-accept" data-invitation-id="${notification.id}">
                                    <i class="fas fa-check"></i>
                                    Принять
                                </button>
                                <button class="btn-decline" data-invitation-id="${notification.id}">
                                    <i class="fas fa-times"></i>
                                    Отклонить
                                </button>
                            </div>
                        </div>
                    </div>
                `).join('');

                // Добавляем обработчики
                attachNotificationHandlers();
            } else {
                // Нет уведомлений
                if (accordionBadge) {
                    accordionBadge.style.display = 'none';
                }

                container.innerHTML = `
                    <div class="notifications-empty">
                        <div class="notifications-empty-icon">
                            <i class="fas fa-bell-slash"></i>
                        </div>
                        <h3>Нет новых уведомлений</h3>
                        <p>Когда появятся новые приглашения в игры, они отобразятся здесь</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('❌ Ошибка загрузки уведомлений:', error);
            container.innerHTML = `
                <div class="notifications-empty">
                    <div class="notifications-empty-icon" style="color: #ef4444;">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <h3>Ошибка загрузки</h3>
                    <p>Не удалось загрузить уведомления. Попробуйте обновить страницу.</p>
                </div>
            `;
        });
}

// Attach event handlers to notification buttons
function attachNotificationHandlers() {
    // Accept invitation buttons
    document.querySelectorAll('.btn-accept').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const invitationId = this.dataset.invitationId;
            acceptInvitation(invitationId);
        });
    });

    // Decline invitation buttons
    document.querySelectorAll('.btn-decline').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const invitationId = this.dataset.invitationId;
            declineInvitation(invitationId);
        });
    });
}

// Accept invitation
function acceptInvitation(invitationId) {
    const button = document.querySelector(`.btn-accept[data-invitation-id="${invitationId}"]`);

    if (button) {
        button.classList.add('loading');
        button.textContent = 'Принимаю...';
    }

    fetch(`/booking/api/invitation/${invitationId}/accept/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (window.toast) {
                window.toast.success(data.message || 'Приглашение принято!');
            }
            // Перезагружаем уведомления
            setTimeout(() => {
                loadProfileNotifications();
                // Обновляем badge в navbar
                if (window.loadNotifications) {
                    window.loadNotifications();
                }
            }, 500);
        } else {
            if (window.toast) {
                window.toast.error(data.message || 'Ошибка при принятии приглашения');
            }
            if (button) {
                button.classList.remove('loading');
                button.innerHTML = '<i class="fas fa-check"></i> Принять';
            }
        }
    })
    .catch(error => {
        console.error('❌ Ошибка принятия приглашения:', error);
        if (window.toast) {
            window.toast.error('Ошибка при принятии приглашения');
        }
        if (button) {
            button.classList.remove('loading');
            button.innerHTML = '<i class="fas fa-check"></i> Принять';
        }
    });
}

// Decline invitation
function declineInvitation(invitationId) {
    const button = document.querySelector(`.btn-decline[data-invitation-id="${invitationId}"]`);

    if (button) {
        button.classList.add('loading');
        button.textContent = 'Отклоняю...';
    }

    fetch(`/booking/api/invitation/${invitationId}/decline/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (window.toast) {
                window.toast.info(data.message || 'Приглашение отклонено');
            }
            // Перезагружаем уведомления
            setTimeout(() => {
                loadProfileNotifications();
                // Обновляем badge в navbar
                if (window.loadNotifications) {
                    window.loadNotifications();
                }
            }, 500);
        } else {
            if (window.toast) {
                window.toast.error(data.message || 'Ошибка при отклонении приглашения');
            }
            if (button) {
                button.classList.remove('loading');
                button.innerHTML = '<i class="fas fa-times"></i> Отклонить';
            }
        }
    })
    .catch(error => {
        console.error('❌ Ошибка отклонения приглашения:', error);
        if (window.toast) {
            window.toast.error('Ошибка при отклонении приглашения');
        }
        if (button) {
            button.classList.remove('loading');
            button.innerHTML = '<i class="fas fa-times"></i> Отклонить';
        }
    });
}

// Get CSRF token
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

// Initialize notifications on profile page
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on profile page
    if (document.getElementById('notificationsListProfile')) {
        loadProfileNotifications();

        // Auto-refresh every 30 seconds
        setInterval(loadProfileNotifications, 30000);
    }
});
