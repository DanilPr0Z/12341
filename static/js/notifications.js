/**
 * ============================================
 * NOTIFICATIONS SYSTEM
 * ============================================
 *
 * Управление уведомлениями с фильтрацией и AJAX-операциями
 */

class NotificationsManager {
    constructor() {
        this.currentFilter = 'all';
        this.init();
    }

    init() {
        this.setupFilterButtons();
        this.setupMarkAllReadButton();
        this.setupNotificationClicks();
        console.log('✅ Notifications Manager инициализирован');
    }

    // ==================== ФИЛЬТРЫ ====================

    setupFilterButtons() {
        const filterButtons = document.querySelectorAll('.filter-chip');

        filterButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const filter = button.dataset.filter;
                this.applyFilter(filter);

                // Обновляем активное состояние кнопок
                filterButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                this.currentFilter = filter;
            });
        });
    }

    applyFilter(filter) {
        const allCards = document.querySelectorAll('.notification-card');
        const sections = document.querySelectorAll('.notifications-section');

        allCards.forEach(card => {
            const cardType = card.dataset.notificationType;
            const isRead = card.dataset.isRead === 'true';
            let shouldShow = false;

            // Применяем фильтр
            switch (filter) {
                case 'all':
                    shouldShow = true;
                    break;
                case 'unread':
                    shouldShow = !isRead;
                    break;
                case 'read':
                    shouldShow = isRead;
                    break;
                case 'booking':
                    shouldShow = cardType.includes('booking');
                    break;
                case 'payment':
                    shouldShow = cardType.includes('payment');
                    break;
                case 'invitation':
                    shouldShow = cardType.includes('invitation') || cardType.includes('partner');
                    break;
                case 'rating':
                    shouldShow = cardType.includes('rating');
                    break;
                default:
                    shouldShow = true;
            }

            // Показываем/скрываем карточку
            if (shouldShow) {
                card.style.display = '';
                card.style.animation = 'slideIn 0.3s ease-out';
            } else {
                card.style.display = 'none';
            }
        });

        // Скрываем пустые секции
        sections.forEach(section => {
            const visibleCards = section.querySelectorAll('.notification-card[style=""], .notification-card:not([style*="display: none"])');
            if (visibleCards.length === 0) {
                section.style.display = 'none';
            } else {
                section.style.display = '';
            }
        });

        // Проверяем, есть ли видимые уведомления
        const hasVisibleCards = Array.from(allCards).some(card => card.style.display !== 'none');
        const emptyState = document.querySelector('.notifications-empty');
        const notificationsList = document.getElementById('notificationsList');

        if (!hasVisibleCards && emptyState) {
            emptyState.style.display = 'block';
        } else if (emptyState) {
            emptyState.style.display = 'none';
        }
    }

    // ==================== ОТМЕТИТЬ ВСЕ КАК ПРОЧИТАННЫЕ ====================

    setupMarkAllReadButton() {
        const markAllBtn = document.getElementById('markAllReadBtn');

        if (markAllBtn) {
            markAllBtn.addEventListener('click', () => {
                this.markAllAsRead();
            });
        }
    }

    async markAllAsRead() {
        const markAllBtn = document.getElementById('markAllReadBtn');
        const originalText = markAllBtn.innerHTML;

        try {
            // Показываем загрузку
            markAllBtn.disabled = true;
            markAllBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Отмечаем...';

            // Получаем CSRF токен
            const csrfToken = this.getCSRFToken();

            // Отправляем запрос
            const response = await fetch('/users/ajax/notifications/mark-all-read/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            });

            const data = await response.json();

            if (data.success) {
                // Обновляем все непрочитанные карточки
                const unreadCards = document.querySelectorAll('.notification-card.unread');
                unreadCards.forEach(card => {
                    card.classList.remove('unread');
                    card.dataset.isRead = 'true';
                });

                // Перемещаем карточки из секции "Новые" в "Ранее"
                const unreadSection = document.querySelector('.notifications-section[data-section="unread"]');
                const readSection = document.querySelector('.notifications-section[data-section="read"]');

                if (unreadSection && readSection) {
                    const unreadList = unreadSection.querySelector('.notifications-list');
                    const readList = readSection.querySelector('.notifications-list');

                    // Перемещаем все карточки
                    while (unreadList.firstChild) {
                        readList.insertBefore(unreadList.firstChild, readList.firstChild);
                    }

                    // Скрываем пустую секцию "Новые"
                    unreadSection.style.display = 'none';
                }

                // Обновляем счетчик
                const unreadBadge = document.querySelector('.unread-count-badge');
                if (unreadBadge) {
                    unreadBadge.remove();
                }

                // Обновляем счетчики в фильтрах
                this.updateFilterCounts();

                // Показываем уведомление
                if (window.toast) {
                    toast.success(`Отмечено как прочитанные: ${data.marked_count}`);
                }

                // Отключаем кнопку
                markAllBtn.disabled = true;
                markAllBtn.innerHTML = '<i class="fas fa-check-double"></i> Все прочитано';
            } else {
                throw new Error(data.message || 'Ошибка при отметке уведомлений');
            }

        } catch (error) {
            console.error('Error marking all as read:', error);

            if (window.toast) {
                toast.error('Ошибка при отметке уведомлений');
            }

            // Восстанавливаем кнопку
            markAllBtn.disabled = false;
            markAllBtn.innerHTML = originalText;
        }
    }

    // ==================== ОТМЕТИТЬ ОДНО КАК ПРОЧИТАННОЕ ====================

    setupNotificationClicks() {
        const cards = document.querySelectorAll('.notification-card');

        cards.forEach(card => {
            card.addEventListener('click', (e) => {
                // Если клик по кнопке действия - не отмечаем как прочитанное
                if (e.target.closest('.notification-action-btn')) {
                    return;
                }

                const notificationId = card.dataset.notificationId;
                const isRead = card.dataset.isRead === 'true';

                // Если уже прочитано - ничего не делаем
                if (isRead) {
                    return;
                }

                // Отмечаем как прочитанное
                this.markAsRead(notificationId, card);
            });
        });
    }

    async markAsRead(notificationId, card) {
        try {
            // Получаем CSRF токен
            const csrfToken = this.getCSRFToken();

            // Визуально отмечаем как прочитанное сразу
            card.classList.add('marking-read');

            // Отправляем запрос
            const response = await fetch('/users/ajax/notifications/mark-read/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: `notification_id=${notificationId}`
            });

            const data = await response.json();

            if (data.success) {
                // Обновляем состояние карточки
                setTimeout(() => {
                    card.classList.remove('unread', 'marking-read');
                    card.dataset.isRead = 'true';

                    // Обновляем счетчики
                    this.updateFilterCounts();

                    // Проверяем, нужно ли отключить кнопку "Отметить все"
                    const unreadCards = document.querySelectorAll('.notification-card.unread');
                    const markAllBtn = document.getElementById('markAllReadBtn');
                    if (unreadCards.length === 0 && markAllBtn) {
                        markAllBtn.disabled = true;
                    }

                    // Обновляем badge в header
                    const unreadBadge = document.querySelector('.unread-count-badge');
                    if (unreadBadge) {
                        const currentCount = parseInt(unreadBadge.textContent);
                        if (currentCount <= 1) {
                            unreadBadge.remove();
                        } else {
                            unreadBadge.textContent = currentCount - 1;
                        }
                    }
                }, 300);
            } else {
                // Если ошибка - возвращаем состояние
                card.classList.remove('marking-read');
                console.error('Error marking as read:', data.message);
            }

        } catch (error) {
            console.error('Error marking notification as read:', error);
            card.classList.remove('marking-read');
        }
    }

    // ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.querySelector('meta[name="csrf-token"]')?.content ||
               '';
    }

    updateFilterCounts() {
        const allCards = document.querySelectorAll('.notification-card');
        const unreadCards = document.querySelectorAll('.notification-card[data-is-read="false"]');
        const readCards = document.querySelectorAll('.notification-card[data-is-read="true"]');

        // Обновляем счетчик "Все"
        const allFilterCount = document.querySelector('.filter-chip[data-filter="all"] .filter-chip-count');
        if (allFilterCount) {
            allFilterCount.textContent = allCards.length;
        }

        // Обновляем счетчик "Непрочитанные"
        const unreadFilter = document.querySelector('.filter-chip[data-filter="unread"]');
        if (unreadFilter) {
            const unreadFilterCount = unreadFilter.querySelector('.filter-chip-count');
            if (unreadFilterCount) {
                unreadFilterCount.textContent = unreadCards.length;
            }

            // Скрываем фильтр если нет непрочитанных
            if (unreadCards.length === 0) {
                unreadFilter.style.display = 'none';
            }
        }

        // Обновляем счетчик "Прочитанные"
        const readFilterCount = document.querySelector('.filter-chip[data-filter="read"] .filter-chip-count');
        if (readFilterCount) {
            readFilterCount.textContent = readCards.length;
        }
    }
}

// ==================== ОБРАБОТЧИКИ ДЕЙСТВИЙ ====================

function handleInvitationAccept(invitationId) {
    console.log('Accepting invitation:', invitationId);
    // TODO: Реализовать принятие приглашения
    if (window.toast) {
        toast.info('Функция принятия приглашения в разработке');
    }
}

function handleInvitationDecline(invitationId) {
    console.log('Declining invitation:', invitationId);
    // TODO: Реализовать отклонение приглашения
    if (window.toast) {
        toast.info('Функция отклонения приглашения в разработке');
    }
}

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

let notificationsManager;

document.addEventListener('DOMContentLoaded', () => {
    notificationsManager = new NotificationsManager();
});

// Экспорт для использования
window.NotificationsManager = NotificationsManager;
window.notificationsManager = notificationsManager;
