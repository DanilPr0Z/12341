# 🚀 РУКОВОДСТВО ПО ОПТИМИЗАЦИИ ПРОИЗВОДИТЕЛЬНОСТИ

## 📋 СОДЕРЖАНИЕ
1. [Оптимизация запросов к БД](#оптимизация-запросов-к-бд)
2. [Использование кеширования](#использование-кеширования)
3. [Lazy Loading изображений](#lazy-loading-изображений)
4. [Рекомендации по улучшению](#рекомендации-по-улучшению)

---

## ⚡ ОПТИМИЗАЦИЯ ЗАПРОСОВ К БД

### 🔴 Проблемные места в `booking/views.py`:

#### 1. **booking_page** (строка 48)
```python
# ❌ БЫЛО:
courts = Court.objects.filter(is_available=True).order_by('name')

# ✅ ДОЛЖНО БЫТЬ:
courts = Court.objects.filter(
    is_available=True
).select_related(
    'location'  # Если есть связь с Location
).prefetch_related(
    'bookings'  # Если нужна информация о бронированиях
).order_by('name')
```

#### 2. **get_available_slots** (строка 106)
```python
# ❌ БЫЛО:
existing_bookings = Booking.objects.filter(
    court=court,
    date=booking_date,
    status__in=['pending', 'confirmed', 'completed']
)

# ✅ ДОЛЖНО БЫТЬ:
existing_bookings = Booking.objects.filter(
    court=court,
    date=booking_date,
    status__in=['pending', 'confirmed', 'completed']
).select_related(
    'user',
    'user__profile',
    'court'
).only(  # Выбираем только нужные поля
    'id', 'start_time', 'end_time', 'status'
)
```

#### 3. **find_partners** (строка 638)
```python
# ✅ УЖЕ ОПТИМИЗИРОВАНО:
available_bookings = Booking.objects.filter(
    looking_for_partner=True,
    status__in=['pending', 'confirmed'],
    date__gte=today
).select_related(
    'user', 'user__profile', 'user__rating', 'court'
).prefetch_related(
    Prefetch('partners', queryset=User.objects.all(), to_attr='partners_list')
).order_by('date', 'start_time')
```

#### 4. **search_partners** (строки 1128-1135)
```python
# ❌ БЫЛО (ДВА ОТДЕЛЬНЫХ ЗАПРОСА):
users_by_name = User.objects.filter(
    Q(first_name__icontains=query) |
    Q(last_name__icontains=query)
)
users_by_phone = User.objects.filter(
    profile__phone__icontains=query
)

# ✅ ДОЛЖНО БЫТЬ (ОДИН ЗАПРОС):
from django.db.models import Q

users = User.objects.filter(
    Q(first_name__icontains=query) |
    Q(last_name__icontains=query) |
    Q(profile__phone__icontains=query)
).select_related(
    'profile',
    'rating'
).distinct()[:10]  # Ограничиваем количество результатов
```

#### 5. **social_games_list** (строки 1331-1351)
```python
# ❌ БЫЛО:
public_games = Booking.objects.filter(
    is_public=True,
    game_mode__in=['americano', 'mexicano'],
    status__in=['pending', 'confirmed'],
    date__gte=today
).select_related('court', 'user', 'user__profile')

# ✅ ДОЛЖНО БЫТЬ:
public_games = Booking.objects.filter(
    is_public=True,
    game_mode__in=['americano', 'mexicano'],
    status__in=['pending', 'confirmed'],
    date__gte=today
).select_related(
    'court',
    'user',
    'user__profile',
    'user__rating'  # Если есть связь
).prefetch_related(
    Prefetch(
        'game_participants',
        queryset=GameParticipant.objects.select_related('user', 'user__profile'),
        to_attr='participants_list'
    )
).order_by('date', 'start_time')
```

---

## 💾 ИСПОЛЬЗОВАНИЕ КЕШИРОВАНИЯ

### Установка
Кеширование уже настроено в `settings.py`:
- `default` - основной кеш (5 минут)
- `static_data` - статические данные (1 час)
- `sessions` - сессии пользователей (30 минут)

### Примеры использования

#### 1. Кеширование дорогих запросов
```python
from booking.cache_utils import cached_query, CacheManager

@cached_query(timeout=600, cache_alias='static_data', key_prefix='courts')
def get_available_courts_optimized(date):
    """Получить доступные корты с кешированием"""
    return Court.objects.filter(
        is_available=True
    ).select_related('location').prefetch_related('bookings')
```

#### 2. Кеширование view для конкретного пользователя
```python
from booking.cache_utils import cache_view_for_user

@login_required
@cache_view_for_user(timeout=300)
def my_bookings(request):
    """Страница бронирований с кешированием"""
    bookings = Booking.objects.filter(user=request.user)
    return render(request, 'my_bookings.html', {'bookings': bookings})
```

#### 3. Инвалидация кеша после изменений
```python
from booking.cache_utils import CacheManager

@require_POST
@login_required
def create_booking(request):
    # ... создание бронирования ...

    # Инвалидируем кеш после создания
    CacheManager.invalidate_user_cache(request.user.id)
    CacheManager.invalidate_courts_cache()

    return JsonResponse({'success': True})
```

#### 4. Использование get_or_set
```python
from booking.cache_utils import get_or_set_cache

def get_active_tournaments():
    """Получить активные турниры с кешированием"""
    return get_or_set_cache(
        'active_tournaments',
        lambda: Tournament.objects.filter(status='active').select_related('location'),
        timeout=1800  # 30 минут
    )
```

---

## 🖼️ LAZY LOADING ИЗОБРАЖЕНИЙ

### HTML разметка

#### Обычные изображения
```html
<!-- ❌ Обычная загрузка -->
<img src="/media/avatars/user.jpg" alt="User">

<!-- ✅ Lazy loading -->
<img data-src="/media/avatars/user.jpg"
     data-placeholder="/media/avatars/user-tiny.jpg"
     class="lazy-load"
     alt="User">
```

#### Responsive изображения
```html
<img data-src="/media/images/court.jpg"
     data-srcset="/media/images/court-480.jpg 480w,
                  /media/images/court-800.jpg 800w,
                  /media/images/court-1200.jpg 1200w"
     class="lazy-load"
     alt="Court">
```

#### Фоновые изображения
```html
<div data-bg="/media/images/hero-bg.jpg"
     class="hero-section">
    <h1>Заголовок</h1>
</div>
```

### JavaScript
Lazy loading уже автоматически инициализируется! Просто добавьте:
```html
<script src="{% static 'js/lazy-load.js' %}"></script>
```

Обновление после динамического добавления контента:
```javascript
// После добавления нового контента через AJAX
updateLazyLoaders();
```

---

## 📊 РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ

### 1. **Используйте select_related для ForeignKey**
```python
# Для каждого ForeignKey используйте select_related
booking = Booking.objects.select_related(
    'user',           # ForeignKey
    'court',          # ForeignKey
    'user__profile'   # ForeignKey через ForeignKey
).get(id=booking_id)
```

### 2. **Используйте prefetch_related для ManyToMany**
```python
# Для каждого ManyToMany используйте prefetch_related
booking = Booking.objects.prefetch_related(
    'partners',              # ManyToMany
    'game_participants',     # Reverse ForeignKey
    'game_participants__user'  # ForeignKey внутри prefetch
).get(id=booking_id)
```

### 3. **Используйте only() для выборки конкретных полей**
```python
# Если нужны только определенные поля
users = User.objects.only(
    'id', 'username', 'first_name', 'last_name'
).all()
```

### 4. **Используйте defer() чтобы исключить тяжелые поля**
```python
# Исключаем большие текстовые поля
bookings = Booking.objects.defer(
    'description',  # Большое текстовое поле
    'notes'
).all()
```

### 5. **Используйте values() для получения словарей**
```python
# Если не нужны объекты модели, используйте values()
court_data = Court.objects.values(
    'id', 'name', 'price_per_hour'
).filter(is_available=True)
```

### 6. **Используйте count() вместо len()**
```python
# ❌ ПЛОХО:
total = len(Booking.objects.all())  # Загружает все объекты

# ✅ ХОРОШО:
total = Booking.objects.count()  # Только COUNT(*) запрос
```

### 7. **Используйте exists() вместо if queryset**
```python
# ❌ ПЛОХО:
if Booking.objects.filter(user=user):
    ...

# ✅ ХОРОШО:
if Booking.objects.filter(user=user).exists():
    ...
```

### 8. **Используйте bulk_create() для множественной вставки**
```python
# ❌ ПЛОХО:
for i in range(100):
    Booking.objects.create(...)  # 100 запросов

# ✅ ХОРОШО:
bookings = [Booking(...) for i in range(100)]
Booking.objects.bulk_create(bookings)  # 1 запрос
```

---

## 🎯 ПРИОРИТЕТЫ ОПТИМИЗАЦИИ

### Высокий приоритет
1. ✅ **booking_page** - главная страница, много трафика
2. ✅ **get_available_slots** - вызывается при каждом выборе даты
3. ✅ **find_partners** - уже оптимизировано
4. ✅ **search_partners** - частые AJAX запросы

### Средний приоритет
5. **social_games_list** - используется реже
6. **my_games** - личный кабинет
7. **invitations_list** - уведомления

### Низкий приоритет
8. Административные страницы (используются редко)
9. Статические страницы

---

## 📈 ИЗМЕРЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ

### Django Debug Toolbar (для разработки)
```python
# В settings.py (только для DEBUG=True)
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']
```

### Логирование медленных запросов
```python
# В settings.py
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',  # Включить для просмотра SQL запросов
            'handlers': ['console'],
        },
    },
}
```

### Использование django-silk (профилирование)
```bash
pip install django-silk
```

---

## ✅ ЧЕКЛИСТ ОПТИМИЗАЦИИ

- [ ] Добавить select_related для всех ForeignKey
- [ ] Добавить prefetch_related для всех ManyToMany
- [ ] Использовать only()/defer() где возможно
- [ ] Заменить len() на count()
- [ ] Заменить if queryset на exists()
- [ ] Добавить кеширование для часто используемых данных
- [ ] Использовать lazy loading для всех изображений
- [ ] Добавить индексы для часто фильтруемых полей (уже сделано в моделях)
- [ ] Оптимизировать AJAX endpoints
- [ ] Протестировать производительность с Django Debug Toolbar

---

## 📚 ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ

- [Django Database Optimization](https://docs.djangoproject.com/en/stable/topics/db/optimization/)
- [Django Caching Framework](https://docs.djangoproject.com/en/stable/topics/cache/)
- [Select Related и Prefetch Related](https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related)
