/**
 * ============================================
 * LOADING STATES ДЛЯ КНОПОК
 * ============================================
 *
 * Утилита для управления loading состояниями кнопок
 */

class ButtonLoading {
    constructor() {
        this.loadingButtons = new Map();
        this.init();
    }

    init() {
        // Добавляем CSS для loading состояния
        this.injectStyles();

        // Автоматически обрабатываем кнопки с data-loading атрибутом
        this.setupAutoLoading();
    }

    /**
     * Инъекция стилей для loading
     */
    injectStyles() {
        if (document.getElementById('button-loading-styles')) return;

        const style = document.createElement('style');
        style.id = 'button-loading-styles';
        style.textContent = `
            .btn-loading {
                position: relative;
                pointer-events: none;
                opacity: 0.7;
            }

            .btn-loading .btn-text {
                opacity: 0;
            }

            .btn-loading::after {
                content: '';
                position: absolute;
                width: 16px;
                height: 16px;
                top: 50%;
                left: 50%;
                margin-left: -8px;
                margin-top: -8px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                border-top-color: white;
                animation: btn-spin 0.6s linear infinite;
            }

            @keyframes btn-spin {
                to { transform: rotate(360deg); }
            }

            /* Вариант с темной темой */
            .btn-loading.btn-secondary::after,
            .btn-loading.btn-light::after {
                border: 2px solid rgba(0, 0, 0, 0.1);
                border-top-color: #666;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Установка loading состояния для кнопки
     */
    start(button, loadingText = null) {
        if (typeof button === 'string') {
            button = document.querySelector(button);
        }

        if (!button) {
            logger.warn('ButtonLoading: кнопка не найдена');
            return;
        }

        // Сохраняем оригинальный текст
        if (!this.loadingButtons.has(button)) {
            this.loadingButtons.set(button, {
                originalText: button.innerHTML,
                originalDisabled: button.disabled
            });
        }

        // Оборачиваем текст в span если нужно
        if (!button.querySelector('.btn-text')) {
            button.innerHTML = `<span class="btn-text">${button.innerHTML}</span>`;
        }

        // Устанавливаем loading текст если передан
        if (loadingText) {
            button.querySelector('.btn-text').textContent = loadingText;
        }

        // Добавляем класс и отключаем кнопку
        button.classList.add('btn-loading');
        button.disabled = true;
    }

    /**
     * Снятие loading состояния
     */
    stop(button) {
        if (typeof button === 'string') {
            button = document.querySelector(button);
        }

        if (!button) {
            logger.warn('ButtonLoading: кнопка не найдена');
            return;
        }

        const originalState = this.loadingButtons.get(button);

        if (originalState) {
            // Восстанавливаем оригинальный текст
            button.innerHTML = originalState.originalText;
            button.disabled = originalState.originalDisabled;

            // Удаляем из Map
            this.loadingButtons.delete(button);
        }

        // Удаляем класс
        button.classList.remove('btn-loading');
    }

    /**
     * Автоматическая обработка форм с data-loading
     */
    setupAutoLoading() {
        document.addEventListener('submit', (e) => {
            const form = e.target;
            const submitButton = form.querySelector('[type="submit"]');

            if (submitButton && submitButton.dataset.loading !== 'false') {
                const loadingText = submitButton.dataset.loadingText || null;
                this.start(submitButton, loadingText);

                // Останавливаем loading если форма invalid
                setTimeout(() => {
                    if (!form.checkValidity()) {
                        this.stop(submitButton);
                    }
                }, 100);
            }
        });
    }

    /**
     * Wrapper для async функций с автоматическим loading
     */
    async wrap(button, asyncFunction, loadingText = null) {
        try {
            this.start(button, loadingText);
            const result = await asyncFunction();
            this.stop(button);
            return result;
        } catch (error) {
            this.stop(button);
            throw error;
        }
    }
}

// Создаем глобальный экземпляр
const buttonLoading = new ButtonLoading();
window.buttonLoading = buttonLoading;

/**
 * ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ:
 *
 * 1. Простое использование:
 * const btn = document.querySelector('#myButton');
 * buttonLoading.start(btn);
 * // ... выполняем операцию ...
 * buttonLoading.stop(btn);
 *
 * 2. С custom текстом:
 * buttonLoading.start(btn, 'Загрузка...');
 *
 * 3. С async/await:
 * await buttonLoading.wrap(btn, async () => {
 *     const response = await fetch('/api/data');
 *     return response.json();
 * }, 'Загрузка данных...');
 *
 * 4. Автоматически для форм (добавить data-loading-text атрибут):
 * <button type="submit" data-loading-text="Отправка...">Отправить</button>
 *
 * 5. Отключить автоматический loading для кнопки:
 * <button type="submit" data-loading="false">Отправить</button>
 */

logger.info('ButtonLoading инициализирован');
