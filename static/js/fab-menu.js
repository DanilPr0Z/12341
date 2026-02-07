/**
 * ============================================
 * FAB MENU CONTROLLER
 * ============================================
 *
 * Управление Floating Action Button меню
 */

class FABMenu {
    constructor(options = {}) {
        this.options = {
            fabSelector: '.fab-main',
            backdropSelector: '.fab-backdrop',
            optionsSelector: '.fab-options',
            ...options
        };

        this.fab = document.querySelector(this.options.fabSelector);
        this.backdrop = document.querySelector(this.options.backdropSelector);
        this.optionsContainer = document.querySelector(this.options.optionsSelector);
        this.isOpen = false;

        if (this.fab) {
            this.init();
        }
    }

    init() {
        // Клик по основной кнопке
        this.fab.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });

        // Клик по backdrop - закрываем меню
        if (this.backdrop) {
            this.backdrop.addEventListener('click', () => {
                this.close();
            });
        }

        // Клик по опциям
        if (this.optionsContainer) {
            const options = this.optionsContainer.querySelectorAll('.fab-option');
            options.forEach(option => {
                option.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.handleOptionClick(option);
                });
            });
        }

        // ESC для закрытия
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        this.isOpen = true;
        this.fab.classList.add('active');

        if (this.backdrop) {
            this.backdrop.classList.add('active');
        }

        if (this.optionsContainer) {
            this.optionsContainer.classList.add('active');
        }

        // Событие открытия
        this.fab.dispatchEvent(new CustomEvent('fab:opened', {
            bubbles: true
        }));
    }

    close() {
        this.isOpen = false;
        this.fab.classList.remove('active');

        if (this.backdrop) {
            this.backdrop.classList.remove('active');
        }

        if (this.optionsContainer) {
            this.optionsContainer.classList.remove('active');
        }

        // Событие закрытия
        this.fab.dispatchEvent(new CustomEvent('fab:closed', {
            bubbles: true
        }));
    }

    handleOptionClick(option) {
        const action = option.dataset.action;

        // Получаем URL из data-url или href
        const url = option.dataset.url || option.getAttribute('href');

        console.log(`FAB опция нажата: ${action}`);

        // Закрываем меню
        this.close();

        // Если есть URL, переходим
        if (url && url !== '#') {
            // Небольшая задержка для анимации
            setTimeout(() => {
                window.location.href = url;
            }, 150);
        }

        // Событие клика по опции
        option.dispatchEvent(new CustomEvent('fab:option-clicked', {
            bubbles: true,
            detail: { action, url }
        }));
    }

    // Обновление badge
    updateBadge(count) {
        let badge = this.fab.querySelector('.fab-badge');

        if (count > 0) {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'fab-badge';
                this.fab.appendChild(badge);
            }
            badge.textContent = count > 99 ? '99+' : count;
        } else {
            if (badge) {
                badge.remove();
            }
        }
    }
}

// Auto-init
let fabMenu;
document.addEventListener('DOMContentLoaded', () => {
    fabMenu = new FABMenu();
    console.log('✅ FAB Menu инициализировано');
});

// Экспорт для использования
window.FABMenu = FABMenu;
window.fabMenu = fabMenu;

/**
 * ПРИМЕР ИСПОЛЬЗОВАНИЯ:
 *
 * HTML:
 * <div class="fab-backdrop"></div>
 * <div class="fab-container">
 *     <button class="fab-main">
 *         <i class="fas fa-plus fab-main-icon"></i>
 *     </button>
 *     <div class="fab-options">
 *         <button class="fab-option primary" data-action="game" data-url="/booking/games/create/">
 *             <i class="fas fa-tennis-ball fab-option-icon"></i>
 *             <span class="fab-option-text">Игра</span>
 *         </button>
 *         <button class="fab-option secondary" data-action="subscription" data-url="/subscription/">
 *             <i class="fas fa-bell fab-option-icon"></i>
 *             <span class="fab-option-text">Подписка</span>
 *         </button>
 *         <button class="fab-option info" data-action="booking" data-url="/booking/">
 *             <i class="fas fa-calendar fab-option-icon"></i>
 *             <span class="fab-option-text">Бронь</span>
 *         </button>
 *     </div>
 * </div>
 *
 * JavaScript (обновление badge):
 * fabMenu.updateBadge(3); // Показать badge с цифрой 3
 * fabMenu.updateBadge(0); // Скрыть badge
 *
 * События:
 * document.addEventListener('fab:opened', () => console.log('FAB открыто'));
 * document.addEventListener('fab:closed', () => console.log('FAB закрыто'));
 * document.addEventListener('fab:option-clicked', (e) => {
 *     console.log('Опция:', e.detail.action);
 * });
 */
