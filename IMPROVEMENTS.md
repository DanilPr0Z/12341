# Предложения по улучшению существующего функционала
**Дата:** 2026-03-19

Только улучшение того, что уже есть — без новых фич.

---

## ПРОИЗВОДИТЕЛЬНОСТЬ

### 1. N+1 запросы в шаблонах

**Где:** `booking/views.py` — `booking_page`, `find_partners`, `games_list`

Почти везде при выводе списков бронирований или игр выполняются дополнительные SQL-запросы внутри цикла (доступ к `booking.court`, `booking.user.profile`, `booking.partners`).

**Как улучшить:**
```python
# Сейчас
Booking.objects.filter(...)

# Нужно
Booking.objects.filter(...).select_related(
    'court', 'user', 'user__profile'
).prefetch_related('partners', 'partners__profile')
```
Это даст 5-10x ускорение на страницах со списками.

---

### 2. Кэш не используется на страницах с тяжёлой аналитикой

**Где:** `users/analytics.py` — `get_player_stats()`

Функция выполняет 15+ SQL-запросов при каждом открытии профиля. В settings.py уже настроен `LocMemCache`.

**Как улучшить:**
```python
from django.core.cache import cache

def get_player_stats(user):
    cache_key = f'player_stats_{user.id}'
    result = cache.get(cache_key)
    if result is None:
        result = _calculate_player_stats(user)
        cache.set(cache_key, result, timeout=300)  # 5 минут
    return result
```
Сбрасывать кэш при изменении бронирования (уже есть `clear_slots_cache` — добавить аналогичный для профиля).

---

### 3. `get_available_slots()` вызывается дважды при создании бронирования

**Где:** `booking/views.py` строки ~440-444

Сначала проверяется конфликт, затем после создания — ещё раз. Оба запроса одинаковые. Сохранить результат первой проверки.

---

## НАДЁЖНОСТЬ И ЦЕЛОСТНОСТЬ ДАННЫХ

### 4. `Booking.confirm()` не отправляет уведомление

**Где:** `booking/models.py` метод `confirm()`

Метод меняет статус и сохраняет, но не вызывает `NotificationService.notify_booking_confirmed()`. Уведомление вручную вызывается только в admin, но не в `booking/views.py confirm_booking()`.

**Как улучшить:** Вызвать `NotificationService.notify_booking_confirmed(self)` внутри `confirm()`, или хотя бы добавить `django.db.models.signals.post_save` который отследит смену статуса.

---

### 5. `Payment.refund()` не обновляет статус бронирования

**Где:** `booking/models.py` метод `refund()`

После возврата платежа бронирование остаётся в статусе `confirmed`. Пользователь видит актуальный платёж, но статус брони вводит в заблуждение.

**Как улучшить:**
```python
def refund(self):
    if self.status == 'paid':
        self.status = 'refunded'
        self.refunded_at = timezone.now()
        self.save()
        # Обновить статус брони если нужно
        if self.booking.status == 'confirmed':
            self.booking.status = 'cancelled'
            self.booking.save()
        return True
    return False
```

---

### 6. Нет валидации времени бронирования (прошедшая дата)

**Где:** `booking/views.py` — `create_booking()`

Можно создать бронирование на вчера. Отсутствует проверка:
```python
if booking_date < today:
    return JsonResponse({'success': False, 'message': 'Нельзя бронировать прошедшие даты'})
if booking_date == today and start_time < timezone.now().time():
    return JsonResponse({'success': False, 'message': 'Нельзя бронировать прошедшее время'})
```

---

### 7. `join_booking()` не проверяет, не является ли пользователь уже партнёром

**Где:** `booking/views.py` — `join_booking()`

Вызывается `booking.can_join(user)` → `booking.add_partner(user)`, но `can_join()` должна проверять и список ожидания тоже. Если пользователь уже в `WaitingList`, его попытка снова присоединиться создаёт дублирующую запись.

---

### 8. `TournamentParticipant.mark_as_paid()` не обновляет Tournament.participants_paid_count

**Где:** `tournament/models.py`

Метод помечает участника как оплатившего, но нет счётчика оплативших на уровне турнира — менеджеру приходится считать вручную каждый раз запросом.

---

## UX И ИНТЕРФЕЙС

### 9. Форма создания бронирования не сохраняет введённые данные при ошибке

**Где:** `templates/booking.html`, `booking/views.py`

Если создание провалилось (конфликт слотов, ошибка валидации), форма очищается. Пользователь вынужден вводить всё заново.

**Как улучшить:** При ошибке возвращать заполненные данные в JSON и восстанавливать их через JS, или использовать Django forms с сохранением состояния.

---

### 10. Уведомления не группируются

**Где:** `users/models.py` — модель `Notification`, `templates/users/partials/notification_card.html`

Если пользователь получил 5 уведомлений "Игра отменена" — они показываются отдельно. Можно группировать по типу за один день.

---

### 11. Нет пагинации в `find_partners`

**Где:** `booking/views.py` — `find_partners()`, `templates/booking/find_partners.html`

При большом числе публичных бронирований страница загружает их все. Нужна пагинация или бесконечная прокрутка (JS + API endpoint уже есть в виде `/api/available-slots/`).

---

### 12. Профиль не обновляет рейтинг автоматически после игры

**Где:** `users/models.py` — `PlayerRating`, `booking/views.py`

Рейтинг обновляется только вручную через тренировочные сессии. Americano и Mexicano игры завершаются, но рейтинг не пересчитывается. Формула уже есть в `PlayerRating`, нет только вызова.

---

## БЕЗОПАСНОСТЬ

### 13. Верификационные коды в логах (убрать)

**Где:** `users/models.py` строки ~168, 190

```python
# Сейчас (небезопасно):
logger.info(f"...verification_code}: {self.verification_code}")

# Нужно:
logger.info(f"Generated verification code for user {self.user.username}")
```

---

### 14. Ошибки сервера утекают клиенту в API

**Где:** `tournament/views.py` — везде где `'error': str(e)` в ответах со статусом 500

```python
# Сейчас:
return JsonResponse({'success': False, 'error': str(e)}, status=500)

# Нужно:
logger.exception(f"Tournament API error: {e}")
return JsonResponse({'success': False, 'error': 'Внутренняя ошибка сервера'}, status=500)
```

---

### 15. `@require_POST` отсутствует на мутирующих tournament views

**Где:** `tournament/views.py` — `public_tournament_register`, `public_tournament_unregister`

Добавить декоратор `@require_POST` — это одна строка, но критично для защиты от CSRF через GET.

---

## КОД И СОПРОВОЖДАЕМОСТЬ

### 16. Email-бэкенд не настроен через переменные окружения

**Где:** `paddle_booking/settings.py`

Добавить в settings.py:
```python
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@paddlebooking.com')
```
Это позволит локально видеть письма в консоли, а в production — использовать реальный SMTP.

---

### 17. `requirements.txt` — зафиксировать версии

**Где:** `requirements.txt`

```bash
pip freeze > requirements.txt
```
Без фиксации `pip install` может в любой момент установить несовместимую версию Django или Pillow.

---

### 18. SQLite → PostgreSQL для production

**Где:** `paddle_booking/settings.py`

```python
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', BASE_DIR / 'db.db'),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
```
SQLite не поддерживает `SELECT FOR UPDATE` и concurrent writes — критично для системы бронирования.

---

### 19. Убрать устаревшие файлы

Удалить или перенести в `/archive/`:
- `tournament/models_old_tennis.py`
- `tournament/bracket_generator_old.py`
- Неиспользуемые views в `paddle_booking/views.py` (`news`, `tournaments`, `booking_page`)

---

### 20. Унифицировать обработку ошибок в views

**Где:** `booking/views.py`, `tournament/views.py`

Сейчас каждый view обрабатывает ошибки по-своему. Создать декоратор:
```python
def api_view(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except ValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
            logger.exception(f"API error in {func.__name__}: {e}")
            return JsonResponse({'success': False, 'error': 'Внутренняя ошибка'}, status=500)
    return wrapper
```

---

## ИТОГОВЫЕ ПРИОРИТЕТЫ

| Приоритет | Пункт | Трудозатраты |
|-----------|-------|--------------|
| 🔴 Высокий | 13, 14, 15 (безопасность) | 1-2 часа |
| 🔴 Высокий | 16 (email backend) | 30 минут |
| 🟠 Средний | 1, 2, 3 (производительность) | 3-5 часов |
| 🟠 Средний | 4, 5, 6, 7 (надёжность данных) | 3-4 часа |
| 🟡 Низкий | 9, 10, 11, 12 (UX) | 4-6 часов |
| 🟢 Техдолг | 17, 18, 19, 20 (инфраструктура) | 2-3 часа |
