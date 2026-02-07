"""
============================================
УТИЛИТЫ ДЛЯ КЕШИРОВАНИЯ
============================================

Функционал:
- Декораторы для кеширования view функций
- Функции для работы с кешем
- Инвалидация кеша
- Кеширование дорогих запросов
"""

from django.core.cache import cache, caches
from django.views.decorators.cache import cache_page
from functools import wraps
import hashlib
import json
from typing import Any, Callable, Optional


def make_cache_key(*args, **kwargs) -> str:
    """
    Создание уникального ключа кеша из аргументов

    Usage:
        key = make_cache_key('courts', 'list', user_id=123)
    """
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_string = ':'.join(key_parts)

    # Хешируем если строка слишком длинная
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"hash:{key_hash}"

    return key_string


def cached_query(timeout: int = 300, cache_alias: str = 'default', key_prefix: str = ''):
    """
    Декоратор для кеширования результатов функций/методов

    Usage:
        @cached_query(timeout=600, key_prefix='courts')
        def get_available_courts(date):
            return Court.objects.filter(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем уникальный ключ кеша
            cache_key = make_cache_key(
                key_prefix or func.__name__,
                *args,
                **kwargs
            )

            # Пытаемся получить из кеша
            cached_result = caches[cache_alias].get(cache_key)
            if cached_result is not None:
                print(f"✅ Cache HIT: {cache_key}")
                return cached_result

            # Выполняем функцию и кешируем результат
            print(f"❌ Cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            caches[cache_alias].set(cache_key, result, timeout)

            return result

        return wrapper
    return decorator


def cache_view_for_user(timeout: int = 300):
    """
    Декоратор для кеширования view с учетом пользователя

    Usage:
        @cache_view_for_user(timeout=600)
        def my_profile_view(request):
            ...
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Создаем ключ с ID пользователя
            user_id = request.user.id if request.user.is_authenticated else 'anonymous'
            cache_key = make_cache_key(
                'view',
                view_func.__name__,
                user_id,
                *args,
                **kwargs
            )

            # Пытаемся получить из кеша
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                print(f"✅ View Cache HIT: {cache_key}")
                return cached_response

            # Выполняем view и кешируем ответ
            print(f"❌ View Cache MISS: {cache_key}")
            response = view_func(request, *args, **kwargs)
            cache.set(cache_key, response, timeout)

            return response

        return wrapper
    return decorator


class CacheManager:
    """
    Менеджер кеша для организованной работы с кешированием
    """

    @staticmethod
    def get_courts_cache_key(date: str = None) -> str:
        """Ключ для списка кортов"""
        if date:
            return f"courts:list:date:{date}"
        return "courts:list:all"

    @staticmethod
    def get_court_detail_key(court_id: int) -> str:
        """Ключ для детальной информации о корте"""
        return f"court:detail:{court_id}"

    @staticmethod
    def get_user_bookings_key(user_id: int) -> str:
        """Ключ для списка бронирований пользователя"""
        return f"user:bookings:{user_id}"

    @staticmethod
    def get_tournament_list_key() -> str:
        """Ключ для списка турниров"""
        return "tournaments:list"

    @staticmethod
    def get_tournament_detail_key(tournament_id: int) -> str:
        """Ключ для детальной информации о турнире"""
        return f"tournament:detail:{tournament_id}"

    @staticmethod
    def invalidate_courts_cache():
        """Инвалидация кеша кортов"""
        cache.delete("courts:list:all")
        # Удаляем все ключи с датами (pattern matching не поддерживается в locmem)
        print("🗑️  Инвалидирован кеш кортов")

    @staticmethod
    def invalidate_user_cache(user_id: int):
        """Инвалидация кеша пользователя"""
        cache.delete(CacheManager.get_user_bookings_key(user_id))
        print(f"🗑️  Инвалидирован кеш пользователя {user_id}")

    @staticmethod
    def invalidate_tournament_cache(tournament_id: int = None):
        """Инвалидация кеша турниров"""
        cache.delete(CacheManager.get_tournament_list_key())
        if tournament_id:
            cache.delete(CacheManager.get_tournament_detail_key(tournament_id))
        print(f"🗑️  Инвалидирован кеш турниров")

    @staticmethod
    def clear_all_cache():
        """Полная очистка кеша"""
        cache.clear()
        caches['static_data'].clear()
        print("🗑️  Полная очистка всех кешей")


def cache_queryset(queryset, timeout: int = 300, cache_alias: str = 'default', key: str = None):
    """
    Кеширование QuerySet

    Usage:
        courts = cache_queryset(
            Court.objects.select_related('location').all(),
            timeout=600,
            key='courts_with_location'
        )
    """
    if key is None:
        # Генерируем ключ из запроса
        query_str = str(queryset.query)
        key = hashlib.md5(query_str.encode()).hexdigest()

    cache_key = f"queryset:{key}"

    # Пытаемся получить из кеша
    cached_result = caches[cache_alias].get(cache_key)
    if cached_result is not None:
        print(f"✅ QuerySet Cache HIT: {cache_key}")
        return cached_result

    # Выполняем запрос и кешируем
    print(f"❌ QuerySet Cache MISS: {cache_key}")
    result = list(queryset)  # Принудительно выполняем запрос
    caches[cache_alias].set(cache_key, result, timeout)

    return result


def get_or_set_cache(key: str, callback: Callable, timeout: int = 300, cache_alias: str = 'default') -> Any:
    """
    Универсальная функция get_or_set для кеша

    Usage:
        courts = get_or_set_cache(
            'all_courts',
            lambda: Court.objects.all(),
            timeout=600
        )
    """
    cached_value = caches[cache_alias].get(key)
    if cached_value is not None:
        print(f"✅ Cache HIT: {key}")
        return cached_value

    print(f"❌ Cache MISS: {key}")
    value = callback()
    caches[cache_alias].set(key, value, timeout)

    return value


# ============================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ============================================

"""
# В views.py:

from booking.cache_utils import cached_query, cache_view_for_user, CacheManager

# 1. Кеширование дорогого запроса
@cached_query(timeout=600, cache_alias='static_data', key_prefix='courts')
def get_available_courts(date):
    return Court.objects.select_related('location').filter(
        bookings__start_time__date=date
    ).distinct()

# 2. Кеширование view для пользователя
@cache_view_for_user(timeout=300)
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user)
    return render(request, 'bookings.html', {'bookings': bookings})

# 3. Использование CacheManager
def create_booking(request):
    # ... создание бронирования ...

    # Инвалидируем кеш пользователя
    CacheManager.invalidate_user_cache(request.user.id)
    CacheManager.invalidate_courts_cache()

# 4. Кеширование QuerySet
courts = cache_queryset(
    Court.objects.select_related('location').prefetch_related('bookings'),
    timeout=600,
    key='courts_full'
)

# 5. Get or Set
tournaments = get_or_set_cache(
    'active_tournaments',
    lambda: Tournament.objects.filter(status='active').order_by('-start_date'),
    timeout=1800
)
"""
