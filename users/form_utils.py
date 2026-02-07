"""
Утилиты для работы с формами Django
"""
import logging

logger = logging.getLogger(__name__)


def get_form_errors(form):
    """
    Извлекает ошибки из формы Django в удобный формат

    Args:
        form: Django Form instance

    Returns:
        dict: {'field_name': ['error1', 'error2'], ...}
    """
    errors = {}
    for field, error_list in form.errors.items():
        errors[field] = [str(error) for error in error_list]
    return errors


def get_first_form_error(form):
    """
    Получает первую ошибку из формы Django

    Args:
        form: Django Form instance

    Returns:
        str: Текст первой ошибки или пустая строка
    """
    errors = get_form_errors(form)

    if errors:
        first_field = list(errors.keys())[0]
        if errors[first_field]:
            return errors[first_field][0]

    return ''


def prepare_form_error_response(form, custom_message=None):
    """
    Подготавливает полный ответ об ошибке формы для JSON API

    Args:
        form: Django Form instance
        custom_message: Кастомное сообщение вместо первой ошибки (optional)

    Returns:
        dict: {'success': False, 'errors': {...}, 'message': '...'}
    """
    errors = get_form_errors(form)
    first_error = custom_message or get_first_form_error(form)

    logger.warning(f"Form validation failed: {errors}")

    return {
        'success': False,
        'errors': errors,
        'message': first_error
    }
