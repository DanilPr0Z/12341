"""
Утилиты для модуля бронирования
"""
from datetime import datetime, timedelta


def create_error_message(title="Ошибка", message="Произошла ошибка"):
    """Создает текстовое сообщение об ошибке для toast-уведомления."""
    if title and title != "Ошибка":
        return f"{title}: {message}"
    return message


def create_success_message(title="Успешно", message="Операция выполнена успешно"):
    """Создает текстовое сообщение об успехе для toast-уведомления."""
    if title and title != "Успешно":
        return f"{title}: {message}"
    return message


def validate_booking_times(booking_date, start_time, end_time, today, current_time):
    """
    Валидация времени бронирования

    Args:
        booking_date: Дата бронирования
        start_time: Время начала
        end_time: Время окончания
        today: Сегодняшняя дата
        current_time: Текущее время

    Returns:
        (is_valid, error_message) - кортеж с результатом валидации и сообщением об ошибке
    """
    # Проверка даты
    if booking_date < today:
        return False, "Нельзя бронировать корт на прошедшую дату"

    # Проверка времени для сегодняшнего дня
    if booking_date == today and start_time < current_time:
        return False, "Нельзя бронировать корт на прошедшее время сегодня"

    # Проверка логики времени
    if end_time <= start_time:
        return False, "Время окончания должно быть позже времени начала"

    return True, None


def validate_booking_duration(start_time, end_time, booking_date, min_hours=1, max_hours=3):
    """
    Проверка продолжительности бронирования

    Args:
        start_time: Время начала
        end_time: Время окончания
        booking_date: Дата бронирования
        min_hours: Минимальная продолжительность в часах
        max_hours: Максимальная продолжительность в часах

    Returns:
        (is_valid, duration_hours, error_message)
    """
    start_dt = datetime.combine(booking_date, start_time)
    end_dt = datetime.combine(booking_date, end_time)

    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    duration_hours = (end_dt - start_dt).total_seconds() / 3600

    if duration_hours < min_hours:
        return False, duration_hours, f"Минимальная продолжительность бронирования - {min_hours} час"

    if duration_hours > max_hours:
        return False, duration_hours, f"Максимальная продолжительность бронирования - {max_hours} часа"

    return True, duration_hours, None


def validate_working_hours(start_time, end_time, working_start=8, working_end=22):
    """
    Проверка рабочих часов

    Args:
        start_time: Время начала
        end_time: Время окончания
        working_start: Начало рабочего дня (час)
        working_end: Конец рабочего дня (час)

    Returns:
        (is_valid, error_message)
    """
    from datetime import time

    working_hours_start = time(hour=working_start, minute=0)
    working_hours_end = time(hour=working_end, minute=0)

    if start_time < working_hours_start or end_time > working_hours_end:
        return False, f"Бронирование доступно с {working_start:02d}:00 до {working_end:02d}:00"

    return True, None


def check_time_conflicts(court, booking_date, start_time, end_time, exclude_booking_id=None):
    """
    Проверка конфликтов времени с существующими бронированиями

    Args:
        court: Объект корта
        booking_date: Дата бронирования
        start_time: Время начала
        end_time: Время окончания
        exclude_booking_id: ID бронирования для исключения (при редактировании)

    Returns:
        (has_conflict, conflicting_booking) - кортеж с результатом и конфликтующим бронированием
    """
    from .models import Booking

    existing_bookings = Booking.objects.filter(
        court=court,
        date=booking_date,
        status__in=['pending', 'confirmed']
    ).select_for_update()

    if exclude_booking_id:
        existing_bookings = existing_bookings.exclude(id=exclude_booking_id)

    for booking in existing_bookings:
        # Проверка пересечения времени
        if (booking.start_time <= start_time < booking.end_time or
                booking.start_time < end_time <= booking.end_time or
                (start_time <= booking.start_time and end_time >= booking.end_time)):
            return True, booking

    return False, None


def pluralize_hours(hours):
    """
    Правильное склонение слова "час"

    Args:
        hours: Количество часов (int или float)

    Returns:
        Строка с правильным склонением (например: "1 час", "2 часа", "5 часов")
    """
    try:
        value = float(hours)
    except (TypeError, ValueError):
        value = 1.0

    # Поддержка 0.5 шага (1.5, 2.5 и т.п.)
    if abs(value - round(value)) > 1e-9:
        # Для дробных значений в русском обычно говорят "1.5 часа", "2.5 часа"
        formatted = f"{value:g}".replace('.', ',')
        return f"{formatted} часа"

    hours_int = int(round(value))
    if hours_int == 1:
        return "1 час"
    if 2 <= hours_int <= 4:
        return f"{hours_int} часа"
    return f"{hours_int} часов"
