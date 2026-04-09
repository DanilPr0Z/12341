# Аудит кодовой базы — Баги и проблемы
**Дата:** 2026-03-19
**Статус исправлений:** обновлён 2026-03-19 (✅ = исправлено, ⚠️ = требует ручных действий)
**Проект:** PythonProject27 (Paddle Booking Platform)

---

## КРИТИЧЕСКИЕ БАГИ (вызовут крэш в runtime)

### 1. Отсутствующие шаблоны — TemplateDoesNotExist

**Файл:** `booking/views.py`

- `booking_detail()` (строка ~1005) рендерит `booking/booking_detail.html` — шаблон не существует
- `my_invitations()` (строка ~865) рендерит `booking/my_invitations.html` — шаблон не существует
- `send_invitation()` (строка ~841) рендерит `booking/send_invitation.html` — шаблон не существует

---

### 2. URL `booking_detail` не зарегистрирован — NoReverseMatch

**Файл:** `booking/urls.py`

Маршрут `booking_detail` отсутствует в `urlpatterns`. `send_invitation()` делает `redirect('booking_detail', booking_id=booking_id)` — это вызовет `NoReverseMatch` в runtime.

Также не зарегистрированы views: `accept_invitation`, `decline_invitation`, `cancel_invitation`, `booking_detail` — они определены в views.py, но недоступны через HTTP.

---

### 3. Метод `mark_email_sent()` не существует в модели Notification — AttributeError

**Файл:** `users/services.py` (строки ~175, 196, 216, 236, 256, 276)

```python
notification.mark_email_sent()  # AttributeError!
```

Модель `Notification` в `users/models.py` определяет только `mark_as_read()`. Метода `mark_email_sent()` не существует. Любой вызов `NotificationService` упадёт.

**Фикс:** Добавить метод в модель или заменить вызов на обновление поля.

---

### 4. Метод `mark_as_refunded()` не существует в модели Payment — AttributeError

**Файл:** `booking/services.py` (строка ~81)

```python
payment.mark_as_refunded()  # AttributeError!
```

Модель `Payment` определяет метод `refund()`, но не `mark_as_refunded()`.

---

### 5. `Payment.mark_as_paid()` вызывается с несуществующим параметром — TypeError

**Файл:** `booking/services.py` (строка ~63)

```python
payment.mark_as_paid(transaction_id=transaction_id)  # TypeError!
```

Метод в `booking/models.py` (строка ~410): `def mark_as_paid(self):` — не принимает аргументов.

---

### 6. Обращение к несуществующему полю `placement` — FieldError

**Файл:** `users/analytics.py` (строка ~181)

```python
tournaments_won = tournament_participations.filter(placement=1)  # FieldError!
```

Модель `TournamentParticipant` не имеет поля `placement`. Правильное поле: `final_position`.

**Фикс:** Заменить `placement=1` на `final_position=1`.

---

### 7. `logger` не определён в `tournament/models.py` — NameError

**Файл:** `tournament/models.py` (строки ~639, 659)

```python
logger.warning(...)  # NameError: name 'logger' is not defined
```

`logger` используется, но нигде не импортирован и не инициализирован.

**Фикс:** Добавить в начало файла:
```python
import logging
logger = logging.getLogger(__name__)
```

---

### 8. `Booking.confirm()` возвращает bool, но вызывается как tuple — ValueError

**Файл:** `booking/admin.py` (строка ~124)

```python
success, message = booking.confirm()  # ValueError: not enough values to unpack!
```

Метод `Booking.confirm()` в `models.py` возвращает `True` или `False`, а не tuple `(success, message)`.

---

### 9. `unique_together` конфликтует с Mexicano — IntegrityError

**Файл:** `booking/models.py` (строка ~743)

```python
unique_together = [('booking', 'round_number')]
```

`BookingMexicanoGenerator` создаёт несколько `GameRound` с одинаковым `round_number=1` для одного booking (при >4 участниках). Это вызовет `IntegrityError` из-за unique constraint.

---

## СЕРЬЁЗНЫЕ ПРОБЛЕМЫ (сломанный функционал)

### 10. `django.contrib.admin` не в INSTALLED_APPS, но admin.py активно использует его

**Файл:** `paddle_booking/settings.py`, `booking/admin.py`, `users/admin.py`, `tournament/admin.py`

`django.contrib.admin` закомментирован из `INSTALLED_APPS`, но все `admin.py` файлы используют `@admin.register()`, `admin.ModelAdmin`, и `reverse('admin:...')`. Все эти `reverse()` вызовы упадут с `NoReverseMatch`.

---

### 11. CORS настроен, но пакет не установлен и не подключён

**Файл:** `paddle_booking/settings.py` (строки ~195-196)

```python
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [...]
```

- `corsheaders` отсутствует в `INSTALLED_APPS`
- `corsheaders.middleware.CorsMiddleware` отсутствует в `MIDDLEWARE`
- `django-cors-headers` отсутствует в `requirements.txt`

Эти настройки не имеют никакого эффекта.

---

### 12. EMAIL_BACKEND не настроен

**Файл:** `paddle_booking/settings.py`

Нет `EMAIL_BACKEND` и `DEFAULT_FROM_EMAIL`. `NotificationService` отправляет письма через `send_mail()`. Без настройки SMTP это упадёт в production.

---

### 13. `dateutil` не в requirements.txt

**Файл:** `booking/views.py` (строка ~1051)

```python
from dateutil import parser
```

`python-dateutil` отсутствует в `requirements.txt`. Есть ненадёжный fallback.

**Фикс:** Добавить `python-dateutil` в `requirements.txt`.

---

### 14. Режим Mexicano не поддержан полностью при создании бронирования

**Файл:** `booking/views.py` (строки ~433-436)

```python
is_public=is_public if game_mode in ['americano'] else False,
rounds_count=rounds_count if game_mode in ['americano'] else 3,
points_per_round=points_per_round if game_mode in ['americano'] else 24,
```

Режим `mexicano` определён в `GAME_MODE_CHOICES`, но его настройки игнорируются — проверяется только `'americano'`. Mexicano-специфичные параметры не применяются.

---

### 15. `select_for_update()` не работает с SQLite

**Файл:** `booking/utils.py` (строка ~125)

`select_for_update()` используется для защиты от race conditions при бронировании. SQLite не поддерживает `SELECT ... FOR UPDATE` — Django молча игнорирует это. Защита от двойного бронирования не работает.

---

## ПРОБЛЕМЫ БЕЗОПАСНОСТИ

### 16. Коды верификации записываются в лог в открытом виде

**Файл:** `users/models.py` (строки ~168, 190)

```python
logger.info(f"Generated verification code for user {self.user.username}, phone {self.phone}: {self.verification_code}")
```

SMS и email коды подтверждения логируются в plaintext. Любой с доступом к логам может перехватить коды.

**Фикс:** Убрать код из логов, оставить только `"Generated verification code for user {username}"`.

---

### 17. Секретный ключ по умолчанию в settings.py

**Файл:** `paddle_booking/settings.py` (строка ~11)

```python
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-your-secret-key-change-this-in-production')
```

Если переменная окружения не установлена — используется предсказуемый ключ. Критично в production.

---

### 18. Внутренние ошибки утекают в API-ответы

**Файл:** `tournament/views.py` (строки ~205, 370, 416, 433, 500, 571, 619 и др.)

```python
return JsonResponse({'success': False, 'error': str(e)}, status=500)
```

`str(e)` может содержать SQL-запросы, пути к файлам, внутренние детали. Нужно логировать `e` и возвращать клиенту только общее сообщение.

---

### 19. Bare `except:` подавляет системные исключения

**Файл:** `booking/views.py` (строка ~1492)

```python
except:
    rating_before = 1.00
```

Перехватывает `KeyboardInterrupt`, `SystemExit` и другие системные исключения.

**Фикс:** Заменить на `except Exception:`.

---

### 20. Регистрация и отмена в турнире принимают любой HTTP-метод

**Файл:** `tournament/views.py` (строки ~97-149)

`public_tournament_register` и `public_tournament_unregister` не ограничены методом POST — уязвимы к CSRF и GET-based attacks.

**Фикс:** Добавить декоратор `@require_POST`.

---

## ЛОГИЧЕСКИЕ ОШИБКИ

### 21. Пробелы в диапазонах уровней рейтинга

**Файл:** `users/models.py`, метод `calculate_level()`

| Уровень | Диапазон | Проблема |
|---------|----------|---------|
| D | 1.00–1.50 | OK |
| D+ | 1.60–2.50 | Диапазон 1.51–1.59 не покрыт |
| C- | 2.60–3.00 | Диапазон 2.51–2.59 не покрыт |

Значения в "пробелах" вернут `'D'` (default), что неправильно.

---

### 22. `cancel_booking` может упасть при invitee=None

**Файл:** `booking/views.py` (строки ~594-601)

Для приглашений со `status='pending'` создаётся уведомление для `inv.invitee`, но поле `invitee` в модели `BookingInvitation` — nullable. Если `invitee is None` — `Notification.objects.create(user=None)` упадёт.

---

## МЁРТВЫЙ КОД

### 23. Устаревшие файлы моделей и генераторов

- `tournament/models_old_tennis.py` — старая модель, полностью мёртвый код
- `tournament/bracket_generator_old.py` — устаревший генератор

---

### 24. Неиспользуемые views в `paddle_booking/views.py`

`news()` (строка ~11), `tournaments()` (строка ~27), `booking_page()` (строка ~14-23) — определены, но не подключены в `paddle_booking/urls.py` и дублируют функционал из app-уровневых views.

---

### 25. Дублирующий `UsersConfig` в `users/signals.py`

`/Users/danil/PycharmProjects/PythonProject27/users/signals.py` содержит определение класса `UsersConfig`, которое дублирует `users/apps.py`. Мёртвый код.

---

### 26. Неиспользуемые импорты в `booking/views.py`

- Строка ~20: `import traceback` на уровне модуля + повторный импорт внутри функций
- Строка ~23: `from users.views import profile` — "для обратной совместимости", нигде не используется

---

## ПРОБЛЕМЫ С КОНФИГУРАЦИЕЙ

### 27. SQLite в production

**Файл:** `paddle_booking/settings.py`

`db.db` (SQLite) используется без условия на окружение. SQLite не поддерживает concurrent writes — критично для booking-системы с одновременными запросами.

---

### 28. `requirements.txt` не пинит версии пакетов

```
Django
Pillow
python-dotenv
django-ratelimit
reportlab>=4.0.0
```

Только `reportlab` имеет ограничение версии. Остальные пакеты могут получить несовместимое обновление при `pip install`.

**Фикс:** Зафиксировать версии через `pip freeze > requirements.txt`.

---

## ПРИОРИТЕТ ИСПРАВЛЕНИЙ

| Приоритет | Пункты | Статус |
|-----------|--------|--------|
| 🔴 Критично (крэш) | 1–9 | Нужно исправить немедленно |
| 🟠 Серьёзно | 10–15 | Исправить в ближайший релиз |
| 🟡 Безопасность | 16–20 | Исправить до выхода в production |
| 🟢 Логика/качество | 21–28 | Исправить при наличии времени |

---

## СТАТИСТИКА

| Категория | Кол-во |
|-----------|--------|
| Критические (runtime crash) | 9 |
| Серьёзные (сломанный функционал) | 6 |
| Безопасность | 5 |
| Логические ошибки | 2 |
| Мёртвый код | 4 |
| Конфигурация | 2 |
| **ИТОГО** | **28** |
