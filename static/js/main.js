document.addEventListener('DOMContentLoaded', function() {
    // ==================== ОБЩИЕ ПЕРЕМЕННЫЕ ====================
    const loginModal = document.getElementById('loginModal');
    const registerModal = document.getElementById('registerModal');
    const logoutModal = document.getElementById('logoutModal');
    const openLoginBtn = document.getElementById('openLoginModal');
    const openRegisterBtn = document.getElementById('openRegisterModal');
    const openLogoutBtn = document.getElementById('openLogoutModal');
    const closeButtons = document.querySelectorAll('.close-modal');
    const cancelLogoutBtn = document.getElementById('cancelLogout');
    const confirmLogoutBtn = document.getElementById('confirmLogout');

    // ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

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

    function showMessage(type, text) {
        // Создаем или получаем контейнер для toast уведомлений
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }

        // Создаем элемент сообщения
        const messageDiv = document.createElement('div');
        messageDiv.className = `custom-message ${type}-message`;
        messageDiv.textContent = text;
        messageDiv.style.cssText = `
            padding: 15px 20px;
            border-radius: 8px;
            max-width: 300px;
            animation: slideIn 0.3s ease;
            color: white;
            font-weight: bold;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            margin-bottom: 12px;
            position: relative;
        `;

        if (type === 'success') {
            messageDiv.style.backgroundColor = '#28a745';
            messageDiv.style.borderLeft = '4px solid #1e7e34';
        } else {
            messageDiv.style.backgroundColor = '#dc3545';
            messageDiv.style.borderLeft = '4px solid #bd2130';
        }

        // Добавляем в контейнер (новые сообщения сверху)
        toastContainer.insertBefore(messageDiv, toastContainer.firstChild);

        // Удаляем сообщение через 5 секунд
        setTimeout(() => {
            messageDiv.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.parentNode.removeChild(messageDiv);
                }
                // Удаляем контейнер если он пустой
                if (toastContainer.children.length === 0) {
                    toastContainer.remove();
                }
            }, 300);
        }, 5000);
    }

    // ==================== УПРАВЛЕНИЕ МОДАЛЬНЫМИ ОКНАМИ ====================

    // Открытие модальных окон
    if (openLoginBtn) {
        openLoginBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.closeAllModals();
            if (loginModal) window.openModal(loginModal);
        });
    }

    if (openRegisterBtn) {
        openRegisterBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.closeAllModals();
            if (registerModal) window.openModal(registerModal);
        });
    }

    if (openLogoutBtn) {
        openLogoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.closeAllModals();
            if (logoutModal) window.openModal(logoutModal);
        });
    }

    // Закрытие
    closeButtons.forEach(button => {
        button.addEventListener('click', closeAllModals);
    });

    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            window.closeAllModals();
        }
    });

    if (cancelLogoutBtn) {
        cancelLogoutBtn.addEventListener('click', closeAllModals);
    }

    // Переключение между формами
    document.querySelectorAll('.switch-to-register').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            window.closeAllModals();
            if (registerModal) window.openModal(registerModal);
        });
    });

    document.querySelectorAll('.switch-to-login').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            window.closeAllModals();
            if (loginModal) window.openModal(loginModal);
        });
    });

    // ==================== AJAX ФОРМЫ ====================

    // Вход
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const submitBtn = loginForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Вход...';

            // Очищаем старые ошибки
            document.querySelectorAll('.error-message').forEach(error => error.remove());
            document.querySelectorAll('.form-input').forEach(input => {
                input.style.borderColor = '';
                input.style.boxShadow = '';
            });

            fetch('/users/ajax/login/', {
                method: 'POST',
                body: new FormData(loginForm),
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                console.log('Ответ сервера при входе:', data);

                if (data.success) {
                    showMessage('success', data.message);
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    // Отображаем ошибки полей
                    if (data.errors) {
                        for (const field in data.errors) {
                            const input = document.querySelector(`[name="${field}"]`);
                            if (input) {
                                const fieldErrors = data.errors[field];
                                if (Array.isArray(fieldErrors) && fieldErrors.length > 0) {
                                    const errorText = fieldErrors[0];

                                    const errorDiv = document.createElement('div');
                                    errorDiv.className = 'error-message';
                                    errorDiv.style.cssText = `
                                        color: #dc3545;
                                        font-size: 14px;
                                        margin-top: 5px;
                                        padding: 5px 10px;
                                        background-color: #f8d7da;
                                        border-radius: 4px;
                                        border-left: 3px solid #dc3545;
                                    `;
                                    errorDiv.textContent = errorText;

                                    // Добавляем после поля
                                    const parent = input.parentNode;
                                    if (parent.querySelector('.error-message')) {
                                        parent.querySelector('.error-message').remove();
                                    }
                                    parent.appendChild(errorDiv);

                                    // Добавляем красную рамку полю с ошибкой
                                    input.style.borderColor = '#dc3545';
                                    input.style.boxShadow = '0 0 0 0.2rem rgba(220,53,69,.25)';

                                    // Убираем красную рамку при исправлении
                                    const cleanup = function() {
                                        this.style.borderColor = '';
                                        this.style.boxShadow = '';
                                        const errorMsg = this.parentNode.querySelector('.error-message');
                                        if (errorMsg) errorMsg.remove();
                                        this.removeEventListener('input', cleanup);
                                    };
                                    input.addEventListener('input', cleanup);
                                }
                            }
                        }
                    }

                    // Показываем общее сообщение об ошибке
                    if (data.message) {
                        showMessage('error', data.message);
                    }

                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                    submitBtn.classList.remove('btn-loading');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('error', 'Ошибка при входе');
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
                submitBtn.classList.remove('btn-loading');
            });
        });
    }

    // ==================== AJAX РЕГИСТРАЦИЯ ====================
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(registerForm);
            const submitBtn = registerForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;

            // Показываем индикатор загрузки
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Регистрация...';

            // Очищаем старые ошибки
            document.querySelectorAll('.error-message').forEach(error => error.remove());
            document.querySelectorAll('.form-input').forEach(input => {
                input.style.borderColor = '';
                input.style.boxShadow = '';
            });

            fetch('/users/ajax/register/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                console.log('Ответ сервера:', data);

                if (data.success) {
                    showMessage('success', data.message);
                    window.closeAllModals();

                    // Обновляем страницу через 1.5 секунды
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    // Отображаем ошибки полей
                    if (data.errors) {
                        for (const field in data.errors) {
                            const input = document.querySelector(`[name="${field}"]`);
                            if (input) {
                                const fieldErrors = data.errors[field];
                                if (Array.isArray(fieldErrors) && fieldErrors.length > 0) {
                                    const errorText = fieldErrors[0];

                                    const errorDiv = document.createElement('div');
                                    errorDiv.className = 'error-message';
                                    errorDiv.style.cssText = `
                                        color: #dc3545;
                                        font-size: 14px;
                                        margin-top: 5px;
                                        padding: 5px 10px;
                                        background-color: #f8d7da;
                                        border-radius: 4px;
                                        border-left: 3px solid #dc3545;
                                    `;
                                    errorDiv.textContent = errorText;

                                    // Добавляем после поля
                                    const parent = input.parentNode;
                                    if (parent.querySelector('.error-message')) {
                                        parent.querySelector('.error-message').remove();
                                    }
                                    parent.appendChild(errorDiv);

                                    // Добавляем красную рамку полю с ошибкой
                                    input.style.borderColor = '#dc3545';
                                    input.style.boxShadow = '0 0 0 0.2rem rgba(220,53,69,.25)';

                                    // Убираем красную рамку при исправлении
                                    const cleanup = function() {
                                        this.style.borderColor = '';
                                        this.style.boxShadow = '';
                                        const errorMsg = this.parentNode.querySelector('.error-message');
                                        if (errorMsg) errorMsg.remove();
                                        this.removeEventListener('input', cleanup);
                                    };
                                    input.addEventListener('input', cleanup);
                                }
                            }
                        }
                    }

                    // Показываем общее сообщение об ошибке
                    if (data.message) {
                        showMessage('error', data.message);
                    }

                    // Восстанавливаем кнопку
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                    submitBtn.classList.remove('btn-loading');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('error', 'Произошла ошибка при регистрации');
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
                submitBtn.classList.remove('btn-loading');
            });
        });
    }

    // ==================== ВЫХОД ИЗ АККАУНТА ====================
    if (confirmLogoutBtn) {
        confirmLogoutBtn.addEventListener('click', function() {
            const originalText = confirmLogoutBtn.textContent;
            confirmLogoutBtn.disabled = true;
            confirmLogoutBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Выход...';

            // Создаем форму для POST запроса
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/users/logout/';
            form.style.display = 'none';

            // CSRF токен
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = getCookie('csrftoken');
            form.appendChild(csrfInput);

            document.body.appendChild(form);
            form.submit();
        });
    }

    // ==================== ВАЛИДАЦИЯ ФОРМ В РЕАЛЬНОМ ВРЕМЕНИ ====================

    /**
     * Валидация email
     */
    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    /**
     * Валидация пароля
     */
    function validatePassword(password) {
        return password.length >= 8;
    }

    /**
     * Валидация имени пользователя
     */
    function validateUsername(username) {
        return username.length >= 3 && /^[a-zA-Z0-9_]+$/.test(username);
    }

    /**
     * Показать ошибку поля
     */
    function showFieldError(input, message) {
        // Удаляем старую ошибку
        const parent = input.parentNode;
        const oldError = parent.querySelector('.error-message');
        if (oldError) oldError.remove();

        // Создаем новую ошибку
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.cssText = `
            color: #dc3545;
            font-size: 14px;
            margin-top: 5px;
            padding: 5px 10px;
            background-color: #f8d7da;
            border-radius: 4px;
            border-left: 3px solid #dc3545;
        `;
        errorDiv.textContent = message;
        parent.appendChild(errorDiv);

        // Красная рамка
        input.style.borderColor = '#dc3545';
        input.style.boxShadow = '0 0 0 0.2rem rgba(220,53,69,.25)';
    }

    /**
     * Очистить ошибку поля
     */
    function clearFieldError(input) {
        const parent = input.parentNode;
        const errorMsg = parent.querySelector('.error-message');
        if (errorMsg) errorMsg.remove();

        input.style.borderColor = '';
        input.style.boxShadow = '';
    }

    /**
     * Показать успешную валидацию
     */
    function showFieldSuccess(input) {
        clearFieldError(input);
        input.style.borderColor = '#28a745';
        input.style.boxShadow = '0 0 0 0.2rem rgba(40,167,69,.25)';
    }

    // Валидация полей логина
    if (loginForm) {
        const emailInput = loginForm.querySelector('input[name="email"]');
        const passwordInput = loginForm.querySelector('input[name="password"]');

        if (emailInput) {
            emailInput.addEventListener('blur', function() {
                const value = this.value.trim();
                if (!value) {
                    showFieldError(this, 'Email обязателен');
                } else if (!validateEmail(value)) {
                    showFieldError(this, 'Некорректный email адрес');
                } else {
                    showFieldSuccess(this);
                }
            });

            emailInput.addEventListener('input', function() {
                if (this.value.trim() && validateEmail(this.value.trim())) {
                    showFieldSuccess(this);
                }
            });
        }

        if (passwordInput) {
            passwordInput.addEventListener('blur', function() {
                const value = this.value;
                if (!value) {
                    showFieldError(this, 'Пароль обязателен');
                } else if (!validatePassword(value)) {
                    showFieldError(this, 'Пароль должен быть минимум 8 символов');
                } else {
                    showFieldSuccess(this);
                }
            });

            passwordInput.addEventListener('input', function() {
                if (this.value && validatePassword(this.value)) {
                    showFieldSuccess(this);
                }
            });
        }
    }

    // Валидация полей регистрации
    if (registerForm) {
        const usernameInput = registerForm.querySelector('input[name="username"]');
        const emailInput = registerForm.querySelector('input[name="email"]');
        const password1Input = registerForm.querySelector('input[name="password1"]');
        const password2Input = registerForm.querySelector('input[name="password2"]');

        if (usernameInput) {
            usernameInput.addEventListener('blur', function() {
                const value = this.value.trim();
                if (!value) {
                    showFieldError(this, 'Имя пользователя обязательно');
                } else if (!validateUsername(value)) {
                    showFieldError(this, 'Минимум 3 символа. Только буквы, цифры и _');
                } else {
                    showFieldSuccess(this);
                }
            });

            usernameInput.addEventListener('input', function() {
                if (this.value.trim() && validateUsername(this.value.trim())) {
                    showFieldSuccess(this);
                }
            });
        }

        if (emailInput) {
            emailInput.addEventListener('blur', function() {
                const value = this.value.trim();
                if (!value) {
                    showFieldError(this, 'Email обязателен');
                } else if (!validateEmail(value)) {
                    showFieldError(this, 'Некорректный email адрес');
                } else {
                    showFieldSuccess(this);
                }
            });

            emailInput.addEventListener('input', function() {
                if (this.value.trim() && validateEmail(this.value.trim())) {
                    showFieldSuccess(this);
                }
            });
        }

        if (password1Input) {
            password1Input.addEventListener('blur', function() {
                const value = this.value;
                if (!value) {
                    showFieldError(this, 'Пароль обязателен');
                } else if (!validatePassword(value)) {
                    showFieldError(this, 'Пароль должен быть минимум 8 символов');
                } else {
                    showFieldSuccess(this);
                }
            });

            password1Input.addEventListener('input', function() {
                if (this.value && validatePassword(this.value)) {
                    showFieldSuccess(this);
                }
                // Проверяем совпадение паролей если второй пароль уже введен
                if (password2Input && password2Input.value) {
                    if (this.value === password2Input.value) {
                        showFieldSuccess(password2Input);
                    } else {
                        showFieldError(password2Input, 'Пароли не совпадают');
                    }
                }
            });
        }

        if (password2Input) {
            password2Input.addEventListener('blur', function() {
                const value = this.value;
                if (!value) {
                    showFieldError(this, 'Подтвердите пароль');
                } else if (password1Input && value !== password1Input.value) {
                    showFieldError(this, 'Пароли не совпадают');
                } else {
                    showFieldSuccess(this);
                }
            });

            password2Input.addEventListener('input', function() {
                if (password1Input && this.value === password1Input.value) {
                    showFieldSuccess(this);
                } else if (this.value) {
                    showFieldError(this, 'Пароли не совпадают');
                }
            });
        }
    }

    // ==================== ВЫПАДАЮЩЕЕ МЕНЮ ====================
    const userDropdowns = document.querySelectorAll('.user-dropdown');

    userDropdowns.forEach(dropdown => {
        const button = dropdown.querySelector('.user-btn');
        const menu = dropdown.querySelector('.dropdown-content');

        if (button && menu) {
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
            });
        }
    });

    document.addEventListener('click', function() {
        document.querySelectorAll('.dropdown-content').forEach(menu => {
            menu.style.display = 'none';
        });
    });

    // ==================== HAMBURGER МОБИЛЬНОЕ МЕНЮ ====================

    const navHamburger = document.getElementById('navHamburger');
    const navMenu = document.getElementById('navMenu');

    if (navHamburger && navMenu) {
        // Создаем backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'nav-mobile-backdrop';
        document.body.appendChild(backdrop);

        function openMobileMenu() {
            navMenu.classList.add('mobile-open');
            navHamburger.classList.add('is-open');
            backdrop.classList.add('show');
            navHamburger.setAttribute('aria-expanded', 'true');
            document.body.style.overflow = 'hidden'; // Предотвращаем скролл под меню
        }

        function closeMobileMenu() {
            navMenu.classList.remove('mobile-open');
            navHamburger.classList.remove('is-open');
            backdrop.classList.remove('show');
            navHamburger.setAttribute('aria-expanded', 'false');
            document.body.style.overflow = '';
        }

        navHamburger.addEventListener('click', function(e) {
            e.stopPropagation();
            if (navMenu.classList.contains('mobile-open')) {
                closeMobileMenu();
            } else {
                openMobileMenu();
            }
        });

        // Закрытие по клику на backdrop
        backdrop.addEventListener('click', closeMobileMenu);

        // Закрытие при клике на ссылку в меню
        navMenu.querySelectorAll('.nav-item').forEach(link => {
            link.addEventListener('click', closeMobileMenu);
        });

        // Закрытие при изменении размера окна (если вернулись на десктоп)
        window.addEventListener('resize', function() {
            if (window.innerWidth > 992) {
                closeMobileMenu();
            }
        });

        // Закрытие на Escape
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && navMenu.classList.contains('mobile-open')) {
                closeMobileMenu();
                navHamburger.focus();
            }
        });
    }

    // ==================== CSS АНИМАЦИИ ====================
    if (!document.querySelector('#custom-styles')) {
        const style = document.createElement('style');
        style.id = 'custom-styles';
        style.textContent = `
            @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
            @keyframes slideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(100%); opacity: 0; } }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(-20px); } to { opacity: 1; transform: translateY(0); } }
            .modal-content { animation: fadeIn 0.3s ease; }
            .fa-spinner { margin-right: 8px; animation: fa-spin 1s infinite linear; }
            @keyframes fa-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        `;
        document.head.appendChild(style);
    }

    console.log('Paddle Booking JS loaded');
});