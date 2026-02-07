/**
 * ============================================
 * СИСТЕМА REAL-TIME ВАЛИДАЦИИ ФОРМ
 * ============================================
 *
 * Функционал:
 * - Валидация полей в реальном времени
 * - Визуальная обратная связь (иконки ✓ и ✗)
 * - Анимации при ошибках (shake)
 * - Проверка паролей, email, телефонов
 * - Strength meter для паролей
 * - Дебаунс для оптимизации
 */

class FormValidator {
    constructor(formSelector, options = {}) {
        this.form = document.querySelector(formSelector);
        if (!this.form) return;

        this.options = {
            validateOnInput: true,
            validateOnBlur: true,
            showPasswordStrength: true,
            debounceTime: 300,
            ...options
        };

        this.validators = {
            required: this.validateRequired.bind(this),
            email: this.validateEmail.bind(this),
            phone: this.validatePhone.bind(this),
            minLength: this.validateMinLength.bind(this),
            maxLength: this.validateMaxLength.bind(this),
            password: this.validatePassword.bind(this),
            match: this.validateMatch.bind(this),
            username: this.validateUsername.bind(this)
        };

        this.init();
    }

    init() {
        // Находим все поля для валидации
        this.fields = this.form.querySelectorAll('input[data-validate], textarea[data-validate]');

        // Добавляем обработчики событий
        this.fields.forEach(field => {
            this.enhanceField(field);

            if (this.options.validateOnInput) {
                field.addEventListener('input', this.debounce((e) => {
                    this.validateField(e.target);
                }, this.options.debounceTime));
            }

            if (this.options.validateOnBlur) {
                field.addEventListener('blur', (e) => {
                    this.validateField(e.target);
                });
            }

            // Очищаем ошибку при фокусе
            field.addEventListener('focus', (e) => {
                this.clearFieldError(e.target);
            });
        });

        // Валидация при отправке формы
        this.form.addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
                this.showFormError('Пожалуйста, исправьте ошибки в форме');
            } else {
                // Добавляем loading state на кнопку
                const submitBtn = this.form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    this.setButtonLoading(submitBtn, true);
                }
            }
        });
    }

    /**
     * Улучшаем поле: добавляем обертки для иконок и сообщений
     */
    enhanceField(field) {
        const parent = field.parentElement;

        // Добавляем wrapper для иконки валидации
        if (!parent.querySelector('.validation-icon')) {
            const iconWrapper = document.createElement('div');
            iconWrapper.className = 'validation-icon';
            parent.style.position = 'relative';
            parent.appendChild(iconWrapper);
        }

        // Добавляем контейнер для ошибок если его нет
        if (!parent.querySelector('.field-error')) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'field-error';
            parent.appendChild(errorDiv);
        }

        // Добавляем password strength meter для паролей
        if (field.type === 'password' && field.dataset.validate.includes('password') && this.options.showPasswordStrength) {
            this.addPasswordStrengthMeter(field);
        }
    }

    /**
     * Валидация одного поля
     */
    validateField(field) {
        const rules = field.dataset.validate.split('|');
        let isValid = true;
        let errorMessage = '';

        for (const rule of rules) {
            const [validatorName, ...params] = rule.split(':');
            const validator = this.validators[validatorName];

            if (validator) {
                const result = validator(field, ...params);
                if (!result.valid) {
                    isValid = false;
                    errorMessage = result.message;
                    break;
                }
            }
        }

        if (isValid) {
            this.showFieldSuccess(field);
        } else {
            this.showFieldError(field, errorMessage);
        }

        return isValid;
    }

    /**
     * Валидация всей формы
     */
    validateForm() {
        let isValid = true;

        this.fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    /**
     * ВАЛИДАТОРЫ
     */

    validateRequired(field) {
        const value = field.value.trim();
        return {
            valid: value.length > 0,
            message: 'Это поле обязательно для заполнения'
        };
    }

    validateEmail(field) {
        const value = field.value.trim();
        if (!value) return { valid: true }; // Required проверит

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return {
            valid: emailRegex.test(value),
            message: 'Введите корректный email адрес'
        };
    }

    validatePhone(field) {
        const value = field.value.trim();
        if (!value) return { valid: true };

        // Поддержка российских номеров
        const phoneRegex = /^(\+7|8)?[\s-]?\(?[0-9]{3}\)?[\s-]?[0-9]{3}[\s-]?[0-9]{2}[\s-]?[0-9]{2}$/;
        return {
            valid: phoneRegex.test(value),
            message: 'Введите корректный номер телефона'
        };
    }

    validateMinLength(field, minLength) {
        const value = field.value.trim();
        if (!value) return { valid: true };

        return {
            valid: value.length >= parseInt(minLength),
            message: `Минимальная длина: ${minLength} символов`
        };
    }

    validateMaxLength(field, maxLength) {
        const value = field.value.trim();
        return {
            valid: value.length <= parseInt(maxLength),
            message: `Максимальная длина: ${maxLength} символов`
        };
    }

    validatePassword(field) {
        const value = field.value;
        if (!value) return { valid: true };

        // Минимум 8 символов, одна буква и одна цифра
        const hasMinLength = value.length >= 8;
        const hasLetter = /[a-zA-Zа-яА-Я]/.test(value);
        const hasNumber = /[0-9]/.test(value);

        const strength = this.calculatePasswordStrength(value);

        if (this.options.showPasswordStrength) {
            this.updatePasswordStrengthMeter(field, strength);
        }

        return {
            valid: hasMinLength && hasLetter && hasNumber,
            message: 'Пароль должен содержать минимум 8 символов, буквы и цифры'
        };
    }

    validateMatch(field, targetFieldName) {
        const targetField = this.form.querySelector(`[name="${targetFieldName}"]`);
        if (!targetField) return { valid: true };

        return {
            valid: field.value === targetField.value,
            message: 'Пароли не совпадают'
        };
    }

    validateUsername(field) {
        const value = field.value.trim();
        if (!value) return { valid: true };

        // Только латиница, цифры, подчеркивание, минимум 3 символа
        const usernameRegex = /^[a-zA-Z0-9_]{3,}$/;
        return {
            valid: usernameRegex.test(value),
            message: 'Только латиница, цифры и подчеркивание (минимум 3 символа)'
        };
    }

    /**
     * ВИЗУАЛЬНАЯ ОБРАТНАЯ СВЯЗЬ
     */

    showFieldSuccess(field) {
        const parent = field.parentElement;
        const icon = parent.querySelector('.validation-icon');
        const errorDiv = parent.querySelector('.field-error');

        // Убираем класс ошибки
        field.classList.remove('field-invalid');
        field.classList.add('field-valid');
        parent.classList.remove('has-error');

        // Показываем иконку успеха
        if (icon) {
            icon.innerHTML = '<i class="fas fa-check-circle"></i>';
            icon.classList.remove('error');
            icon.classList.add('success', 'zoom-in');
            setTimeout(() => icon.classList.remove('zoom-in'), 300);
        }

        // Скрываем сообщение об ошибке
        if (errorDiv) {
            errorDiv.textContent = '';
            errorDiv.style.display = 'none';
        }
    }

    showFieldError(field, message) {
        const parent = field.parentElement;
        const icon = parent.querySelector('.validation-icon');
        const errorDiv = parent.querySelector('.field-error');

        // Добавляем класс ошибки
        field.classList.remove('field-valid');
        field.classList.add('field-invalid', 'shake');
        parent.classList.add('has-error');

        // Убираем анимацию shake через 500ms
        setTimeout(() => field.classList.remove('shake'), 500);

        // Показываем иконку ошибки
        if (icon) {
            icon.innerHTML = '<i class="fas fa-times-circle"></i>';
            icon.classList.remove('success');
            icon.classList.add('error', 'wiggle');
            setTimeout(() => icon.classList.remove('wiggle'), 500);
        }

        // Показываем сообщение об ошибке
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            errorDiv.classList.add('fade-in-up');
            setTimeout(() => errorDiv.classList.remove('fade-in-up'), 500);
        }
    }

    clearFieldError(field) {
        const parent = field.parentElement;
        const icon = parent.querySelector('.validation-icon');

        field.classList.remove('field-invalid', 'shake');
        parent.classList.remove('has-error');

        if (icon) {
            icon.innerHTML = '';
            icon.classList.remove('error', 'success');
        }
    }

    showFormError(message) {
        // Показываем toast с ошибкой
        if (window.showToast) {
            window.showToast(message, 'error');
        } else {
            alert(message);
        }
    }

    /**
     * PASSWORD STRENGTH METER
     */

    addPasswordStrengthMeter(field) {
        const parent = field.parentElement;

        const meterHTML = `
            <div class="password-strength-meter">
                <div class="strength-bar">
                    <div class="strength-fill" data-strength="0"></div>
                </div>
                <div class="strength-label">Сила пароля: <span class="strength-text">Слабый</span></div>
            </div>
        `;

        parent.insertAdjacentHTML('beforeend', meterHTML);
    }

    calculatePasswordStrength(password) {
        let strength = 0;

        if (password.length >= 8) strength += 25;
        if (password.length >= 12) strength += 15;
        if (/[a-z]/.test(password)) strength += 15;
        if (/[A-Z]/.test(password)) strength += 15;
        if (/[0-9]/.test(password)) strength += 15;
        if (/[^a-zA-Z0-9]/.test(password)) strength += 15;

        return strength;
    }

    updatePasswordStrengthMeter(field, strength) {
        const parent = field.parentElement;
        const meter = parent.querySelector('.password-strength-meter');
        if (!meter) return;

        const fill = meter.querySelector('.strength-fill');
        const text = meter.querySelector('.strength-text');

        fill.style.width = strength + '%';
        fill.dataset.strength = strength;

        // Определяем уровень и цвет
        let level, color;
        if (strength < 40) {
            level = 'Слабый';
            color = '#f44336';
        } else if (strength < 70) {
            level = 'Средний';
            color = '#ff9800';
        } else if (strength < 90) {
            level = 'Хороший';
            color = '#4caf50';
        } else {
            level = 'Отличный';
            color = '#2196f3';
        }

        text.textContent = level;
        fill.style.background = `linear-gradient(90deg, ${color}, ${color}dd)`;
    }

    /**
     * LOADING STATE ДЛЯ КНОПОК
     */

    setButtonLoading(button, isLoading) {
        if (isLoading) {
            button.dataset.originalText = button.innerHTML;
            button.disabled = true;
            button.classList.add('btn-loading');
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Загрузка...';
        } else {
            button.disabled = false;
            button.classList.remove('btn-loading');
            button.innerHTML = button.dataset.originalText || button.innerHTML;
        }
    }

    /**
     * УТИЛИТЫ
     */

    debounce(func, wait) {
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
}

/**
 * AUTO-INIT для форм с классом .validate-form
 */
document.addEventListener('DOMContentLoaded', () => {
    const forms = document.querySelectorAll('.validate-form');
    forms.forEach(form => {
        new FormValidator(`#${form.id}`, {
            validateOnInput: true,
            validateOnBlur: true,
            showPasswordStrength: true
        });
    });
});

// Экспортируем для использования
window.FormValidator = FormValidator;
