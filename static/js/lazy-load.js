/**
 * ============================================
 * LAZY LOADING ИЗОБРАЖЕНИЙ
 * ============================================
 *
 * Функционал:
 * - Отложенная загрузка изображений
 * - Intersection Observer API
 * - Плавное появление загруженных изображений
 * - Placeholder эффект
 * - Поддержка responsive images
 */

class LazyLoader {
    constructor(options = {}) {
        this.options = {
            rootMargin: '50px', // Начинаем загрузку за 50px до появления в viewport
            threshold: 0.01,
            className: 'lazy-load',
            loadedClassName: 'lazy-loaded',
            errorClassName: 'lazy-error',
            ...options
        };

        this.observer = null;
        this.images = [];
        this.init();
    }

    init() {
        // Проверяем поддержку IntersectionObserver
        if (!('IntersectionObserver' in window)) {
            console.warn('IntersectionObserver не поддерживается, загружаем все изображения сразу');
            this.loadAllImages();
            return;
        }

        // Создаем observer
        this.observer = new IntersectionObserver(
            this.handleIntersection.bind(this),
            {
                rootMargin: this.options.rootMargin,
                threshold: this.options.threshold
            }
        );

        // Находим все изображения для lazy loading
        this.findImages();

        // Наблюдаем за каждым изображением
        this.images.forEach(img => {
            this.observer.observe(img);
        });
    }

    /**
     * Находим все изображения для lazy loading
     */
    findImages() {
        // Изображения с атрибутом data-src
        const dataSrcImages = document.querySelectorAll(`img[data-src]`);

        // Изображения с классом lazy-load
        const classImages = document.querySelectorAll(`.${this.options.className}`);

        // Объединяем и убираем дубликаты
        const allImages = [...new Set([...dataSrcImages, ...classImages])];

        this.images = Array.from(allImages);

        console.log(`LazyLoader: Найдено ${this.images.length} изображений для lazy loading`);
    }

    /**
     * Обработчик пересечения с viewport
     */
    handleIntersection(entries, observer) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                this.loadImage(img);
                observer.unobserve(img); // Прекращаем наблюдение после загрузки
            }
        });
    }

    /**
     * Загрузка одного изображения
     */
    loadImage(img) {
        const src = img.dataset.src;
        const srcset = img.dataset.srcset;

        if (!src && !srcset) {
            console.warn('LazyLoader: Изображение не имеет data-src или data-srcset', img);
            return;
        }

        // Показываем placeholder во время загрузки
        this.showPlaceholder(img);

        // Создаем новое изображение для предзагрузки
        const tempImg = new Image();

        tempImg.onload = () => {
            this.onImageLoad(img, src, srcset);
        };

        tempImg.onerror = () => {
            this.onImageError(img);
        };

        // Начинаем загрузку
        if (srcset) {
            tempImg.srcset = srcset;
        }
        if (src) {
            tempImg.src = src;
        }
    }

    /**
     * Успешная загрузка изображения
     */
    onImageLoad(img, src, srcset) {
        // Устанавливаем src и srcset
        if (src) {
            img.src = src;
        }
        if (srcset) {
            img.srcset = srcset;
        }

        // Удаляем data-атрибуты
        delete img.dataset.src;
        delete img.dataset.srcset;

        // Добавляем класс загруженного
        img.classList.add(this.options.loadedClassName);
        img.classList.remove(this.options.className);

        // Плавное появление
        this.fadeIn(img);

        // Удаляем placeholder
        this.removePlaceholder(img);

        // Событие для отслеживания
        img.dispatchEvent(new CustomEvent('lazyloaded', {
            bubbles: true,
            detail: { src, srcset }
        }));
    }

    /**
     * Ошибка загрузки изображения
     */
    onImageError(img) {
        img.classList.add(this.options.errorClassName);
        img.classList.remove(this.options.className);

        // Показываем fallback изображение если есть
        if (img.dataset.fallback) {
            img.src = img.dataset.fallback;
        }

        console.error('LazyLoader: Ошибка загрузки изображения', img);

        img.dispatchEvent(new CustomEvent('lazyerror', {
            bubbles: true
        }));
    }

    /**
     * Показ placeholder'а
     */
    showPlaceholder(img) {
        // Добавляем класс для стилизации
        img.classList.add('lazy-loading');

        // Если есть низкокачественное превью
        if (img.dataset.placeholder) {
            const tempSrc = img.src;
            img.src = img.dataset.placeholder;
            img.dataset.originalSrc = tempSrc;
        }
    }

    /**
     * Удаление placeholder'а
     */
    removePlaceholder(img) {
        img.classList.remove('lazy-loading');
    }

    /**
     * Плавное появление
     */
    fadeIn(img) {
        img.style.opacity = '0';
        img.style.transition = 'opacity 0.4s ease-in';

        // Принудительный reflow
        img.offsetHeight;

        img.style.opacity = '1';

        // Очищаем inline стили после анимации
        setTimeout(() => {
            img.style.opacity = '';
            img.style.transition = '';
        }, 400);
    }

    /**
     * Загрузка всех изображений сразу (fallback)
     */
    loadAllImages() {
        this.findImages();
        this.images.forEach(img => {
            if (img.dataset.src) {
                img.src = img.dataset.src;
                delete img.dataset.src;
            }
            if (img.dataset.srcset) {
                img.srcset = img.dataset.srcset;
                delete img.dataset.srcset;
            }
            img.classList.add(this.options.loadedClassName);
            img.classList.remove(this.options.className);
        });
    }

    /**
     * Обновление списка изображений (для динамически добавленных)
     */
    update() {
        if (!this.observer) {
            this.loadAllImages();
            return;
        }

        // Находим новые изображения
        this.findImages();

        // Наблюдаем за новыми изображениями
        this.images.forEach(img => {
            if (!img.classList.contains(this.options.loadedClassName) &&
                !img.classList.contains(this.options.errorClassName)) {
                this.observer.observe(img);
            }
        });
    }

    /**
     * Уничтожение observer'а
     */
    destroy() {
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
        this.images = [];
    }
}

/**
 * BACKGROUND IMAGES LAZY LOADING
 */
class BackgroundLazyLoader {
    constructor(options = {}) {
        this.options = {
            rootMargin: '50px',
            threshold: 0.01,
            selector: '[data-bg]',
            ...options
        };

        this.observer = null;
        this.elements = [];
        this.init();
    }

    init() {
        if (!('IntersectionObserver' in window)) {
            this.loadAllBackgrounds();
            return;
        }

        this.observer = new IntersectionObserver(
            this.handleIntersection.bind(this),
            {
                rootMargin: this.options.rootMargin,
                threshold: this.options.threshold
            }
        );

        this.findElements();
        this.elements.forEach(el => this.observer.observe(el));
    }

    findElements() {
        this.elements = Array.from(document.querySelectorAll(this.options.selector));
        console.log(`BackgroundLazyLoader: Найдено ${this.elements.length} элементов с фоновыми изображениями`);
    }

    handleIntersection(entries, observer) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                this.loadBackground(el);
                observer.unobserve(el);
            }
        });
    }

    loadBackground(el) {
        const bg = el.dataset.bg;
        if (!bg) return;

        el.style.backgroundImage = `url(${bg})`;
        delete el.dataset.bg;
        el.classList.add('bg-loaded');

        el.dispatchEvent(new CustomEvent('bgloaded', {
            bubbles: true,
            detail: { bg }
        }));
    }

    loadAllBackgrounds() {
        this.findElements();
        this.elements.forEach(el => {
            if (el.dataset.bg) {
                el.style.backgroundImage = `url(${el.dataset.bg})`;
                delete el.dataset.bg;
                el.classList.add('bg-loaded');
            }
        });
    }

    update() {
        if (!this.observer) {
            this.loadAllBackgrounds();
            return;
        }

        this.findElements();
        this.elements.forEach(el => {
            if (!el.classList.contains('bg-loaded')) {
                this.observer.observe(el);
            }
        });
    }

    destroy() {
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
        this.elements = [];
    }
}

/**
 * AUTO-INIT
 */
let imageLazyLoader = null;
let backgroundLazyLoader = null;

document.addEventListener('DOMContentLoaded', () => {
    // Инициализируем lazy loading для изображений
    imageLazyLoader = new LazyLoader({
        rootMargin: '100px',
        threshold: 0.01
    });

    // Инициализируем lazy loading для фоновых изображений
    backgroundLazyLoader = new BackgroundLazyLoader({
        rootMargin: '100px',
        threshold: 0.01
    });

    console.log('LazyLoading инициализирован');
});

/**
 * Функция для обновления lazy loader'ов после добавления нового контента
 */
function updateLazyLoaders() {
    if (imageLazyLoader) {
        imageLazyLoader.update();
    }
    if (backgroundLazyLoader) {
        backgroundLazyLoader.update();
    }
}

// Экспорт для использования
window.LazyLoader = LazyLoader;
window.BackgroundLazyLoader = BackgroundLazyLoader;
window.updateLazyLoaders = updateLazyLoaders;

/**
 * ПРИМЕР ИСПОЛЬЗОВАНИЯ:
 *
 * HTML:
 * <img data-src="/path/to/image.jpg"
 *      data-srcset="/path/to/image-small.jpg 480w, /path/to/image-large.jpg 1200w"
 *      data-placeholder="/path/to/tiny-preview.jpg"
 *      class="lazy-load"
 *      alt="Description">
 *
 * <div data-bg="/path/to/background.jpg" class="hero-section"></div>
 *
 * JavaScript (после добавления нового контента):
 * updateLazyLoaders();
 */
