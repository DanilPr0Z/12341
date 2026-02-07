/**
 * ============================================
 * БЕЗОПАСНОЕ ЛОГИРОВАНИЕ
 * ============================================
 *
 * Утилита для логирования, которая автоматически
 * отключается в production режиме
 */

class Logger {
    constructor() {
        // Определяем, находимся ли мы в dev режиме
        this.isDevelopment = window.location.hostname === 'localhost' ||
                            window.location.hostname === '127.0.0.1' ||
                            window.location.hostname.includes('dev');

        // Уровни логирования
        this.levels = {
            ERROR: 'error',
            WARN: 'warn',
            INFO: 'info',
            DEBUG: 'debug'
        };

        // Текущий уровень (можно изменить через localStorage)
        const savedLevel = localStorage.getItem('logLevel');
        this.currentLevel = savedLevel || this.levels.INFO;
    }

    /**
     * Проверка, нужно ли выводить лог
     */
    shouldLog(level) {
        if (!this.isDevelopment && level !== this.levels.ERROR) {
            return false;
        }

        const levelOrder = [this.levels.ERROR, this.levels.WARN, this.levels.INFO, this.levels.DEBUG];
        return levelOrder.indexOf(level) <= levelOrder.indexOf(this.currentLevel);
    }

    /**
     * Форматирование сообщения с эмодзи и временем
     */
    format(emoji, level, ...args) {
        const time = new Date().toLocaleTimeString('ru-RU');
        return [`${emoji} [${time}] [${level}]`, ...args];
    }

    /**
     * Ошибки (всегда выводятся, даже в production)
     */
    error(...args) {
        console.error(...this.format('🔴', 'ERROR', ...args));

        // Отправка ошибок в систему мониторинга (если настроена)
        if (window.errorTracking) {
            window.errorTracking.captureException(args[0]);
        }
    }

    /**
     * Предупреждения
     */
    warn(...args) {
        if (this.shouldLog(this.levels.WARN)) {
            console.warn(...this.format('⚠️', 'WARN', ...args));
        }
    }

    /**
     * Информационные сообщения
     */
    info(...args) {
        if (this.shouldLog(this.levels.INFO)) {
            console.log(...this.format('ℹ️', 'INFO', ...args));
        }
    }

    /**
     * Отладочные сообщения
     */
    debug(...args) {
        if (this.shouldLog(this.levels.DEBUG)) {
            console.log(...this.format('🐛', 'DEBUG', ...args));
        }
    }

    /**
     * Успешные операции
     */
    success(...args) {
        if (this.shouldLog(this.levels.INFO)) {
            console.log(...this.format('✅', 'SUCCESS', ...args));
        }
    }

    /**
     * Начало операции
     */
    start(...args) {
        if (this.shouldLog(this.levels.INFO)) {
            console.log(...this.format('🎯', 'START', ...args));
        }
    }

    /**
     * API запросы
     */
    api(method, url, data = null) {
        if (this.shouldLog(this.levels.DEBUG)) {
            console.log(...this.format('🌐', 'API', `${method} ${url}`, data));
        }
    }

    /**
     * Таблица данных
     */
    table(label, data) {
        if (this.shouldLog(this.levels.DEBUG)) {
            console.log(`📊 ${label}:`);
            console.table(data);
        }
    }

    /**
     * Группировка логов
     */
    group(label, collapsed = false) {
        if (this.shouldLog(this.levels.DEBUG)) {
            if (collapsed) {
                console.groupCollapsed(label);
            } else {
                console.group(label);
            }
        }
    }

    groupEnd() {
        if (this.shouldLog(this.levels.DEBUG)) {
            console.groupEnd();
        }
    }

    /**
     * Измерение времени выполнения
     */
    time(label) {
        if (this.shouldLog(this.levels.DEBUG)) {
            console.time(label);
        }
    }

    timeEnd(label) {
        if (this.shouldLog(this.levels.DEBUG)) {
            console.timeEnd(label);
        }
    }

    /**
     * Установка уровня логирования
     */
    setLevel(level) {
        this.currentLevel = level;
        localStorage.setItem('logLevel', level);
        this.info(`Уровень логирования установлен: ${level}`);
    }
}

// Создаем глобальный экземпляр
const logger = new Logger();

// Экспортируем для использования
window.logger = logger;

/**
 * ИСПОЛЬЗОВАНИЕ:
 *
 * logger.error('Критическая ошибка!', errorObject);
 * logger.warn('Предупреждение');
 * logger.info('Информация');
 * logger.debug('Отладочная информация');
 * logger.success('Операция выполнена успешно');
 * logger.api('GET', '/api/users');
 *
 * // Измерение времени
 * logger.time('loadData');
 * // ... код ...
 * logger.timeEnd('loadData');
 *
 * // Группировка
 * logger.group('User Data');
 * logger.info('Name:', name);
 * logger.info('Email:', email);
 * logger.groupEnd();
 *
 * // Изменение уровня (в консоли браузера)
 * logger.setLevel('debug'); // Показать все логи
 * logger.setLevel('error'); // Только ошибки
 */

// Перехват необработанных ошибок
window.addEventListener('error', (event) => {
    logger.error('Необработанная ошибка:', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error
    });
});

// Перехват необработанных промисов
window.addEventListener('unhandledrejection', (event) => {
    logger.error('Необработанный промис:', {
        reason: event.reason,
        promise: event.promise
    });
});

console.log('📝 Logger инициализирован (режим: ' + (logger.isDevelopment ? 'разработка' : 'production') + ')');
