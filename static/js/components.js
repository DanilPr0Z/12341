/**
 * Библиотека переиспользуемых UI компонентов
 */

// ==================== TOAST NOTIFICATIONS ====================
class ToastNotification {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // Создаем контейнер для toast-ов если его нет
        if (!document.querySelector('.toast-container')) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.querySelector('.toast-container');
        }
    }

    show(message, type = 'success', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast-notification ${type}`;

        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };

        const titles = {
            success: 'Успешно!',
            error: 'Ошибка!',
            warning: 'Внимание!',
            info: 'Информация'
        };

        toast.innerHTML = `
            <i class="fas ${icons[type]}"></i>
            <div class="toast-content">
                <strong>${titles[type]}</strong>
                <p>${message}</p>
            </div>
            <button class="toast-close">&times;</button>
            <div class="toast-progress"></div>
        `;

        this.container.appendChild(toast);

        // Закрытие по клику на крестик
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => this.remove(toast));

        // Автоматическое удаление
        if (duration > 0) {
            setTimeout(() => this.remove(toast), duration);
        }

        return toast;
    }

    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }

    remove(toast) {
        // Плавное исчезновение
        toast.style.animation = 'slideOutRight 0.4s cubic-bezier(0.6, -0.28, 0.74, 0.05)';
        toast.style.opacity = '0';
        toast.style.marginBottom = '-20px'; // Плавное сжатие пространства

        // Удаляем элемент после анимации
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 400);
    }
}

// Глобальный экземпляр
const toast = new ToastNotification();

// Добавляем анимацию выхода
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ==================== АНИМИРОВАННЫЙ СЧЕТЧИК ====================
function animateCounter(element, target, duration = 2000) {
    const start = parseInt(element.textContent) || 0;
    const increment = (target - start) / (duration / 16);
    let current = start;

    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= target) || (increment < 0 && current <= target)) {
            element.textContent = Math.round(target);
            clearInterval(timer);
        } else {
            element.textContent = Math.round(current);
        }
    }, 16);
}

// Автоматически анимируем все счетчики при скролле в видимость
function initCounters() {
    const counters = document.querySelectorAll('.animated-counter');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.dataset.animated) {
                const target = parseInt(entry.target.dataset.target) || 0;
                animateCounter(entry.target, target);
                entry.target.dataset.animated = 'true';
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(counter => observer.observe(counter));
}

// ==================== RIPPLE EFFECT ====================
function createRipple(event) {
    const button = event.currentTarget;

    // Удаляем старый ripple если есть
    const existingRipple = button.querySelector('.ripple');
    if (existingRipple) {
        existingRipple.remove();
    }

    const circle = document.createElement('span');
    const diameter = Math.max(button.clientWidth, button.clientHeight);
    const radius = diameter / 2;

    circle.style.width = circle.style.height = `${diameter}px`;
    circle.style.left = `${event.clientX - button.offsetLeft - radius}px`;
    circle.style.top = `${event.clientY - button.offsetTop - radius}px`;
    circle.classList.add('ripple');

    button.appendChild(circle);

    setTimeout(() => circle.remove(), 600);
}

// Добавляем ripple effect ко всем кнопкам с классом .btn-ripple
document.addEventListener('DOMContentLoaded', function() {
    const rippleButtons = document.querySelectorAll('.btn-ripple');
    rippleButtons.forEach(button => {
        button.addEventListener('click', createRipple);
    });

    // Инициализируем счетчики
    initCounters();
});

// Стили для ripple
const rippleStyle = document.createElement('style');
rippleStyle.textContent = `
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple-animation 0.6s ease-out;
        pointer-events: none;
    }

    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
`;
document.head.appendChild(rippleStyle);

// ==================== SKELETON LOADER ====================
function showSkeleton(element) {
    element.classList.add('skeleton-loading');
    element.innerHTML = `
        <div class="skeleton-loader">
            <div class="skeleton-line"></div>
            <div class="skeleton-line medium"></div>
            <div class="skeleton-line short"></div>
        </div>
    `;
}

function hideSkeleton(element, content) {
    element.classList.remove('skeleton-loading');
    element.innerHTML = content;
}

// Skeleton для списка кортов
function showCourtsSkeleton(container, count = 3) {
    container.innerHTML = '';
    for (let i = 0; i < count; i++) {
        const skeleton = document.createElement('div');
        skeleton.className = 'skeleton-court';
        skeleton.innerHTML = `
            <div class="skeleton-court-header">
                <div class="skeleton-court-title"></div>
                <div class="skeleton-court-price"></div>
            </div>
            <div class="skeleton-court-desc"></div>
            <div class="skeleton-court-desc short"></div>
        `;
        container.appendChild(skeleton);
    }
}

// Skeleton для временных слотов
function showSlotsSkeleton(container, count = 8) {
    container.innerHTML = '';
    for (let i = 0; i < count; i++) {
        const skeleton = document.createElement('div');
        skeleton.className = 'skeleton-slot';
        container.appendChild(skeleton);
    }
}

// ==================== КОНФИРМ ДИАЛОГ ====================
function showConfirmDialog(options = {}) {
    const defaults = {
        title: 'Подтверждение',
        message: 'Вы уверены?',
        confirmText: 'Да',
        cancelText: 'Отмена',
        onConfirm: () => {},
        onCancel: () => {},
        type: 'warning'
    };

    const settings = { ...defaults, ...options };

    const modal = document.createElement('div');
    modal.className = 'modal modal-modern';
    modal.style.display = 'flex';

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    const colors = {
        success: '#4caf50',
        error: '#f44336',
        warning: '#ff9800',
        info: '#2196f3'
    };

    modal.innerHTML = `
        <div class="modal-backdrop" style="backdrop-filter: blur(8px); background: rgba(0, 0, 0, 0.5);"></div>
        <div class="modal-content" style="
            background: white;
            padding: 30px;
            border-radius: 15px;
            max-width: 450px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            position: relative;
            z-index: 1;
            text-align: center;
        ">
            <i class="fas ${icons[settings.type]}" style="
                font-size: 64px;
                color: ${colors[settings.type]};
                margin-bottom: 20px;
            "></i>
            <h2 style="margin-bottom: 15px; color: #333;">${settings.title}</h2>
            <p style="margin-bottom: 30px; color: #666; font-size: 16px;">${settings.message}</p>
            <div style="display: flex; gap: 15px; justify-content: center;">
                <button class="btn-cancel" style="
                    flex: 1;
                    padding: 12px 30px;
                    border-radius: 8px;
                    border: 2px solid #ddd;
                    background: white;
                    color: #666;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s;
                ">${settings.cancelText}</button>
                <button class="btn-confirm" style="
                    flex: 1;
                    padding: 12px 30px;
                    border-radius: 8px;
                    border: none;
                    background: linear-gradient(135deg, ${colors[settings.type]}, ${colors[settings.type]}dd);
                    color: white;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s;
                ">${settings.confirmText}</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    const btnConfirm = modal.querySelector('.btn-confirm');
    const btnCancel = modal.querySelector('.btn-cancel');
    const backdrop = modal.querySelector('.modal-backdrop');

    btnConfirm.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
        this.style.boxShadow = `0 5px 15px ${colors[settings.type]}50`;
    });

    btnConfirm.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = 'none';
    });

    btnCancel.addEventListener('mouseenter', function() {
        this.style.borderColor = '#999';
        this.style.background = '#f5f5f5';
    });

    btnCancel.addEventListener('mouseleave', function() {
        this.style.borderColor = '#ddd';
        this.style.background = 'white';
    });

    btnConfirm.addEventListener('click', () => {
        settings.onConfirm();
        modal.remove();
    });

    btnCancel.addEventListener('click', () => {
        settings.onCancel();
        modal.remove();
    });

    backdrop.addEventListener('click', () => {
        settings.onCancel();
        modal.remove();
    });

    return modal;
}

// ==================== PROGRESS BAR ====================
function updateProgressBar(element, value, animated = true) {
    const fill = element.querySelector('.progress-fill');
    const label = element.querySelector('.progress-label');

    if (animated) {
        setTimeout(() => {
            fill.style.width = `${value}%`;
            if (label) {
                let current = 0;
                const increment = value / 50;
                const timer = setInterval(() => {
                    current += increment;
                    if (current >= value) {
                        label.textContent = `${Math.round(value)}%`;
                        clearInterval(timer);
                    } else {
                        label.textContent = `${Math.round(current)}%`;
                    }
                }, 20);
            }
        }, 100);
    } else {
        fill.style.width = `${value}%`;
        if (label) label.textContent = `${Math.round(value)}%`;
    }
}

// ==================== LOADING OVERLAY ====================
let loadingOverlay = null;

function showLoading(message = 'Загрузка...') {
    if (!loadingOverlay) {
        loadingOverlay = document.createElement('div');
        loadingOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(5px);
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        loadingOverlay.innerHTML = `
            <div style="
                background: white;
                padding: 30px 40px;
                border-radius: 15px;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            ">
                <i class="fas fa-spinner fa-spin" style="
                    font-size: 48px;
                    color: var(--primary-color, #9ef01a);
                    margin-bottom: 15px;
                "></i>
                <p class="loading-message" style="
                    margin: 0;
                    font-size: 16px;
                    font-weight: 600;
                    color: #333;
                ">${message}</p>
            </div>
        `;

        document.body.appendChild(loadingOverlay);
    } else {
        loadingOverlay.querySelector('.loading-message').textContent = message;
        loadingOverlay.style.display = 'flex';
    }
}

function hideLoading() {
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

// ==================== MODAL HELPERS ====================
/**
 * Открыть модальное окно с блокировкой прокрутки
 * @param {HTMLElement|string} modal - элемент модального окна или его ID
 */
function openModal(modal) {
    const modalEl = typeof modal === 'string' ? document.getElementById(modal) : modal;

    if (!modalEl) {
        console.error('Modal element not found:', modal);
        return;
    }

    // Показываем модальное окно
    modalEl.style.display = 'flex';

    // Блокируем прокрутку body
    document.body.classList.add('modal-open');

    // Добавляем обработчик закрытия по клику на фон
    modalEl.addEventListener('click', function(e) {
        if (e.target === modalEl) {
            closeModal(modalEl);
        }
    });

    // Добавляем обработчик закрытия по Escape
    const escapeHandler = function(e) {
        if (e.key === 'Escape') {
            closeModal(modalEl);
            document.removeEventListener('keydown', escapeHandler);
        }
    };
    document.addEventListener('keydown', escapeHandler);
    modalEl._escapeHandler = escapeHandler;
}

/**
 * Закрыть модальное окно и восстановить прокрутку
 * @param {HTMLElement|string} modal - элемент модального окна или его ID
 */
function closeModal(modal) {
    const modalEl = typeof modal === 'string' ? document.getElementById(modal) : modal;

    if (!modalEl) {
        console.error('Modal element not found:', modal);
        return;
    }

    // Скрываем модальное окно
    modalEl.style.display = 'none';

    // Проверяем, есть ли другие открытые модальные окна
    const openModals = document.querySelectorAll('.modal[style*="display: flex"], .modal[style*="display: block"]');
    const hasOpenModals = Array.from(openModals).some(m => m !== modalEl && m.style.display !== 'none');

    // Разблокируем прокрутку только если нет других открытых модалок
    if (!hasOpenModals) {
        document.body.classList.remove('modal-open');
    }

    // Удаляем обработчик Escape
    if (modalEl._escapeHandler) {
        document.removeEventListener('keydown', modalEl._escapeHandler);
        delete modalEl._escapeHandler;
    }
}

/**
 * Закрыть все открытые модальные окна
 */
function closeAllModals() {
    const modals = document.querySelectorAll('.modal, .profile-modal');
    modals.forEach(modal => {
        if (modal.style.display !== 'none') {
            closeModal(modal);
        }
    });
}

// ==================== DEBOUNCE UTILITY ====================
/**
 * Debounce функция - откладывает выполнение функции до тех пор,
 * пока не пройдет указанное время с момента последнего вызова
 *
 * @param {Function} func - Функция для выполнения
 * @param {Number} wait - Время ожидания в миллисекундах
 * @returns {Function} Debounced функция
 *
 * @example
 * const debouncedSearch = debounce((query) => {
 *     fetch(`/api/search?q=${query}`)
 *         .then(response => response.json())
 *         .then(data => console.log(data));
 * }, 300);
 *
 * searchInput.addEventListener('input', (e) => {
 *     debouncedSearch(e.target.value);
 * });
 */
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle функция - ограничивает частоту вызовов функции
 *
 * @param {Function} func - Функция для выполнения
 * @param {Number} limit - Минимальный интервал между вызовами в миллисекундах
 * @returns {Function} Throttled функция
 */
function throttle(func, limit = 300) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ==================== RESPONSIVE TABLES ====================
/**
 * Автоматически добавляет data-label атрибуты для адаптивных таблиц
 * Находит все таблицы с классом .responsive-table или .history-table и добавляет data-label
 */
function initResponsiveTables() {
    const tables = document.querySelectorAll('table.responsive-table, table.history-table, table');

    tables.forEach(table => {
        const headers = table.querySelectorAll('thead th');
        const rows = table.querySelectorAll('tbody tr');

        // Если нет заголовков, пропускаем
        if (headers.length === 0) return;

        // Для каждой строки добавляем data-label к ячейкам
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                // Пропускаем, если уже есть data-label
                if (cell.hasAttribute('data-label')) return;

                // Получаем текст заголовка
                if (headers[index]) {
                    const headerText = headers[index].textContent.trim();
                    cell.setAttribute('data-label', headerText);
                }
            });
        });

        // Добавляем класс responsive-table если его нет
        if (!table.classList.contains('responsive-table') &&
            !table.classList.contains('history-table')) {
            // Оборачиваем таблицу в wrapper для overflow-x scroll
            if (!table.parentElement.classList.contains('responsive-table-wrapper')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'responsive-table-wrapper';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            }
        }
    });
}

// ==================== AUTO-APPLY DEBOUNCE TO SEARCH INPUTS ====================
/**
 * Автоматически применяет debounce ко всем поисковым полям при загрузке страницы
 */
document.addEventListener('DOMContentLoaded', function() {
    // Находим все search input поля
    const searchInputs = document.querySelectorAll(
        'input[type="search"], input[id*="search" i], input[id*="Search"], input.search-input'
    );

    searchInputs.forEach(input => {
        // Получаем функцию из onkeyup атрибута
        const onkeyupAttr = input.getAttribute('onkeyup');

        if (onkeyupAttr) {
            // Удаляем старый onkeyup обработчик
            input.removeAttribute('onkeyup');

            // Создаем функцию из строки атрибута
            const filterFunction = new Function(onkeyupAttr);

            // Оборачиваем в debounce и применяем как input обработчик
            const debouncedFilter = debounce(filterFunction, 300);

            input.addEventListener('input', debouncedFilter);
        }
    });

    // Инициализируем адаптивные таблицы
    initResponsiveTables();

    // Инициализируем lazy loading для изображений
    initLazyLoading();
});

// ==================== LAZY LOADING FOR IMAGES ====================
/**
 * Инициализирует lazy loading для изображений
 * Поддерживает современный атрибут loading="lazy" и data-src для старых браузеров
 */
function initLazyLoading() {
    // Проверяем поддержку нативного loading="lazy"
    const supportsNativeLazyLoading = 'loading' in HTMLImageElement.prototype;

    if (supportsNativeLazyLoading) {
        // Браузер поддерживает нативный lazy loading
        // Добавляем loading="lazy" ко всем изображениям без этого атрибута
        document.querySelectorAll('img:not([loading])').forEach(img => {
            // Пропускаем маленькие изображения (иконки, аватары < 100px)
            if (img.width > 100 || img.height > 100 || (!img.width && !img.height)) {
                img.setAttribute('loading', 'lazy');
            }
        });
    } else {
        // Используем Intersection Observer для старых браузеров
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;

                    // Загружаем изображение
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }

                    // Добавляем класс для CSS анимации появления
                    img.classList.add('lazy-loaded');

                    // Перестаем наблюдать за этим изображением
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px 0px', // Начинаем загрузку за 50px до появления в viewport
            threshold: 0.01
        });

        // Находим все изображения с data-src или без src
        document.querySelectorAll('img[data-src], img[loading="lazy"]:not([src])').forEach(img => {
            imageObserver.observe(img);
        });
    }
}

/**
 * Добавить изображение в очередь lazy loading (для динамически добавляемых изображений)
 * @param {HTMLImageElement} img - элемент изображения
 */
function addToLazyLoad(img) {
    if ('loading' in HTMLImageElement.prototype) {
        img.setAttribute('loading', 'lazy');
    } else {
        // Создаём observer если его ещё нет
        if (!window._lazyImageObserver) {
            window._lazyImageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                        }
                        img.classList.add('lazy-loaded');
                        window._lazyImageObserver.unobserve(img);
                    }
                });
            }, { rootMargin: '50px 0px', threshold: 0.01 });
        }
        window._lazyImageObserver.observe(img);
    }
}

// Экспортируем в глобальную область
window.toast = toast;
window.animateCounter = animateCounter;
window.showSkeleton = showSkeleton;
window.hideSkeleton = hideSkeleton;
window.showCourtsSkeleton = showCourtsSkeleton;
window.showSlotsSkeleton = showSlotsSkeleton;
window.showConfirmDialog = showConfirmDialog;
window.updateProgressBar = updateProgressBar;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.openModal = openModal;
window.closeModal = closeModal;
window.closeAllModals = closeAllModals;
window.debounce = debounce;
window.throttle = throttle;
window.addToLazyLoad = addToLazyLoad;
window.initLazyLoading = initLazyLoading;
window.initResponsiveTables = initResponsiveTables;
