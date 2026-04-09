/**
 * Notifications page JS
 */

// ===== CSRF =====
function getCsrfToken() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
}

// ===== MARK SINGLE AS READ =====
function markNotificationRead(notificationId, callback) {
    fetch('/users/ajax/notifications/mark-read/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': getCsrfToken() },
        body: new URLSearchParams({ notification_id: notificationId })
    })
    .then(r => r.json())
    .then(data => { if (callback) callback(data); })
    .catch(() => {});
}

// ===== MARK ALL READ =====
function markAllNotificationsRead() {
    fetch('/users/ajax/notifications/mark-all-read/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // Убираем визуальные признаки непрочитанных
            document.querySelectorAll('.notification-card.unread').forEach(c => c.classList.remove('unread'));
            const badge = document.querySelector('h1 .unread-count-badge');
            if (badge) badge.remove();
            const btn = document.getElementById('markAllReadBtn');
            if (btn) btn.disabled = true;
            // Обновляем navbar badge
            if (window.loadNotifications) window.loadNotifications();
            if (window.toast) window.toast.success('Все уведомления прочитаны');
        }
    })
    .catch(() => {});
}

// ===== ACCEPT INVITATION =====
function replaceActionsWithStatus(btn, statusHtml) {
    const actionsDiv = btn.closest('.notification-actions');
    if (actionsDiv) {
        actionsDiv.outerHTML = statusHtml;
    }
}

function handleInvitationAccept(invitationId, btn) {
    if (!invitationId) return;

    fetch(`/booking/api/invitation/${invitationId}/accept/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            if (window.toast) window.toast.success(data.message || 'Приглашение принято!');
            if (btn) {
                replaceActionsWithStatus(btn,
                    '<div class="notification-status-label" style="color:#10b981;font-weight:600;font-size:13px;margin-top:8px;"><i class="fas fa-check-circle"></i> Принято</div>');
            }
        } else {
            if (window.toast) window.toast.error(data.message || 'Ошибка');
        }
    })
    .catch(() => { if (window.toast) window.toast.error('Ошибка соединения'); });
}

// ===== DECLINE INVITATION =====
function handleInvitationDecline(invitationId, btn) {
    if (!invitationId) return;

    fetch(`/booking/api/invitation/${invitationId}/decline/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            if (window.toast) window.toast.info(data.message || 'Приглашение отклонено');
            if (btn) {
                replaceActionsWithStatus(btn,
                    '<div class="notification-status-label" style="color:#ef4444;font-weight:600;font-size:13px;margin-top:8px;"><i class="fas fa-times-circle"></i> Отклонено</div>');
            }
        } else {
            if (window.toast) window.toast.error(data.message || 'Ошибка');
        }
    })
    .catch(() => { if (window.toast) window.toast.error('Ошибка соединения'); });
}

// ===== FILTERS =====
function initFilters() {
    const chips = document.querySelectorAll('.filter-chip');
    const cards = document.querySelectorAll('.notification-card');
    const sections = document.querySelectorAll('.notifications-section');

    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            chips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            const filter = chip.dataset.filter;

            sections.forEach(s => {
                const sectionFilter = s.dataset.section;
                if (filter === 'all') {
                    s.style.display = '';
                } else if (filter === 'unread') {
                    s.style.display = sectionFilter === 'unread' ? '' : 'none';
                } else if (filter === 'read') {
                    s.style.display = sectionFilter === 'read' ? '' : 'none';
                } else {
                    s.style.display = '';
                }
            });

            cards.forEach(card => {
                const type = card.dataset.notificationType || '';
                if (filter === 'all' || filter === 'unread' || filter === 'read') return;
                const match =
                    (filter === 'booking'    && (type.includes('booking') || type.includes('partner'))) ||
                    (filter === 'invitation' && (type.includes('invitation') || type.includes('partner'))) ||
                    (filter === 'payment'    && type.includes('payment')) ||
                    (filter === 'rating'     && type.includes('rating'));
                card.style.display = match ? '' : 'none';
            });
        });
    });
}

// ===== AUTO MARK READ ON HOVER =====
function initAutoMarkRead() {
    document.querySelectorAll('.notification-card.unread').forEach(card => {
        card.addEventListener('mouseenter', function() {
            const id = this.dataset.notificationId;
            if (!id || this.dataset.markedRead) return;
            this.dataset.markedRead = '1';
            markNotificationRead(id, () => {
                this.classList.remove('unread');
                if (window.loadNotifications) window.loadNotifications();
                // Обновляем счётчик в заголовке
                const badge = document.querySelector('h1 .unread-count-badge');
                if (badge) {
                    const n = parseInt(badge.textContent) - 1;
                    if (n <= 0) badge.remove();
                    else badge.textContent = n;
                }
            });
        }, { once: true });
    });
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', function() {
    initFilters();
    initAutoMarkRead();

    const markAllBtn = document.getElementById('markAllReadBtn');
    if (markAllBtn) {
        markAllBtn.addEventListener('click', markAllNotificationsRead);
    }
});
