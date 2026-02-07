# Система уведомлений с фильтрами

## Обзор

Полнофункциональная система уведомлений с фильтрацией, временными метками и AJAX-операциями. Вдохновлена дизайном Lunda Padel и адаптирована для веб-версии.

## Основные возможности

1. **Фильтрация уведомлений** - по типу, статусу прочтения
2. **Временные метки** - относительное время ("2 часа назад", "Вчера")
3. **Отметка как прочитанное** - одно уведомление или все сразу
4. **Визуальное различие** - непрочитанные уведомления выделяются
5. **Быстрые действия** - кнопки для принятия приглашений, просмотра броней
6. **Real-time обновления** - AJAX без перезагрузки страницы

## Файловая структура

```
paddle_booking/
├── static/
│   ├── css/
│   │   └── notifications.css           # Стили системы уведомлений
│   └── js/
│       └── notifications.js            # JavaScript для фильтрации и AJAX
├── templates/
│   └── users/
│       ├── notifications.html          # Главная страница уведомлений
│       └── partials/
│           └── notification_card.html  # Компонент карточки уведомления
└── users/
    ├── views.py                        # Вью для уведомлений
    └── models.py                       # Модель Notification
```

## Типы уведомлений

Система поддерживает следующие типы уведомлений (определены в `users/models.py`):

### Общие
- `registration` - Регистрация
- `phone_verification` - Подтверждение телефона

### Бронирования
- `booking_created` - Бронирование создано
- `booking_confirmed` - Бронирование подтверждено
- `booking_cancelled` - Бронирование отменено
- `booking_reminder_24h` - Напоминание за 24 часа
- `booking_reminder_1h` - Напоминание за 1 час

### Платежи
- `payment_success` - Оплата успешна
- `payment_failed` - Ошибка оплаты
- `payment_pending` - Ожидает оплаты

### Социальные
- `booking_invitation` - Приглашение в бронирование
- `invitation_accepted` - Приглашение принято
- `invitation_declined` - Приглашение отклонено
- `partner_joined` - Партнёр присоединился

### Рейтинг
- `rating_updated` - Рейтинг обновлен

## Модель Notification

Основные поля:

```python
class Notification(models.Model):
    user = ForeignKey(User)              # Пользователь
    type = CharField(choices=...)        # Тип уведомления
    title = CharField()                  # Заголовок
    message = TextField()                # Сообщение
    is_read = BooleanField()            # Прочитано
    created_at = DateTimeField()        # Дата создания
    read_at = DateTimeField()           # Дата прочтения
    metadata = JSONField()              # Дополнительные данные
```

## URL-маршруты

```python
# users/urls.py
path('notifications/', views.notifications_list, name='notifications_list')
path('ajax/notifications/count/', views.get_unread_notifications_count, name='ajax_notifications_count')
path('ajax/notifications/mark-read/', views.mark_notification_read, name='ajax_mark_notification_read')
path('ajax/notifications/mark-all-read/', views.mark_all_notifications_read, name='ajax_mark_all_notifications_read')
```

## Использование

### Создание уведомления

```python
from users.models import Notification
from django.contrib.auth.models import User

user = User.objects.get(username='john')

notification = Notification.objects.create(
    user=user,
    type='booking_confirmed',
    title='Бронирование подтверждено',
    message='Ваше бронирование на 15:00 подтверждено',
    metadata={
        'booking_id': 123,
        'court_name': 'Корт 1',
        'date': '2025-02-10',
        'time': '15:00'
    }
)
```

### Получение непрочитанных уведомлений

```python
from users.models import Notification

unread = Notification.objects.filter(
    user=request.user,
    is_read=False
).order_by('-created_at')

count = unread.count()
```

### Отметка как прочитанное

```python
notification = Notification.objects.get(id=notification_id)
notification.mark_as_read()  # Автоматически устанавливает is_read=True и read_at
```

## Фильтры

### Основные фильтры

1. **Все** - показывает все уведомления
2. **Непрочитанные** - только непрочитанные (is_read=False)
3. **Прочитанные** - только прочитанные (is_read=True)

### Фильтры по типу

1. **Бронирования** - все уведомления с "booking" в типе
2. **Платежи** - все уведомления с "payment" в типе
3. **Приглашения** - все уведомления с "invitation" или "partner" в типе
4. **Рейтинг** - все уведомления с "rating" в типе

### JavaScript API

```javascript
// Применить фильтр
notificationsManager.applyFilter('unread');

// Отметить все как прочитанные
notificationsManager.markAllAsRead();

// Отметить одно как прочитанное
notificationsManager.markAsRead(notificationId, cardElement);

// Обновить счетчики
notificationsManager.updateFilterCounts();
```

## Временные метки

Система использует относительное время:

- **Только что** - < 1 минуты
- **X мин назад** - < 60 минут
- **X ч назад** - < 24 часов
- **Вчера** - 1 день
- **X дн назад** - < 7 дней
- **X нед назад** - < 30 дней
- **X мес назад** - < 365 дней
- **X г назад** - >= 365 дней

Временные метки автоматически обновляются каждую минуту.

## Визуальные индикаторы

### Непрочитанные уведомления

- Зеленоватый градиентный фон
- Зеленая левая граница
- Зеленая точка слева
- Более яркое выделение

### Типы иконок

Каждый тип уведомления имеет уникальную иконку и цветовую схему:

- **Бронирования** - фиолетовый градиент, иконка календаря
- **Отмены** - розовый градиент, иконка календаря
- **Напоминания** - оранжевый градиент, иконка календаря
- **Платежи (успех)** - зеленый градиент, иконка карты
- **Платежи (ошибка)** - красно-желтый градиент, иконка карты
- **Рейтинг** - сине-фиолетовый градиент, иконка звезды
- **Социальные** - голубой градиент, иконка пользователя

## Быстрые действия

Некоторые типы уведомлений имеют кнопки действий:

### Приглашение в бронирование
```html
<button onclick="handleInvitationAccept(invitationId)">Принять</button>
<button onclick="handleInvitationDecline(invitationId)">Отклонить</button>
```

### Напоминание о бронировании
```html
<button onclick="window.location.href='/profile?tab=bookings'">Просмотреть бронь</button>
```

### Обновление рейтинга
```html
<button onclick="window.location.href='/profile#rating'">Посмотреть рейтинг</button>
```

## AJAX-операции

### Отметить уведомление как прочитанное

**Endpoint:** `POST /users/ajax/notifications/mark-read/`

**Параметры:**
```javascript
{
    notification_id: 123
}
```

**Ответ:**
```json
{
    "success": true,
    "message": "Уведомление отмечено как прочитанное"
}
```

### Отметить все как прочитанные

**Endpoint:** `POST /users/ajax/notifications/mark-all-read/`

**Ответ:**
```json
{
    "success": true,
    "message": "Отмечено как прочитанные: 5",
    "marked_count": 5
}
```

### Получить количество непрочитанных

**Endpoint:** `GET /users/ajax/notifications/count/`

**Ответ:**
```json
{
    "success": true,
    "count": 3
}
```

## Адаптивный дизайн

### Десктоп (> 768px)
- Полноразмерные карточки
- Горизонтальное расположение иконки и контента
- Все фильтры в одну строку

### Планшет (480-768px)
- Вертикальное расположение иконки и контента
- Фильтры с переносом строк
- Компактные кнопки

### Мобильные (< 480px)
- Мобильно-оптимизированные карточки
- Фильтры в 2 колонки
- Кнопка "Отметить все" на всю ширину

## Анимации

### Появление карточек
- Анимация slideIn с задержкой для каждой карточки (0.05s, 0.1s, 0.15s...)

### Отметка как прочитанное
- Анимация fadeOut при клике

### Фильтрация
- Плавное появление/исчезновение карточек

## Интеграция с другими компонентами

### Навбар

Можно добавить счетчик непрочитанных в навбар:

```django
{% load static %}

<div class="notifications-bell">
    <a href="{% url 'notifications_list' %}">
        <i class="fas fa-bell"></i>
        {% if unread_count > 0 %}
            <span class="badge">{{ unread_count }}</span>
        {% endif %}
    </a>
</div>
```

### Автоматическое обновление счетчика

```javascript
// Обновлять каждые 30 секунд
setInterval(async () => {
    const response = await fetch('/users/ajax/notifications/count/');
    const data = await response.json();

    if (data.success) {
        const badge = document.querySelector('.notifications-bell .badge');
        if (data.count > 0) {
            if (!badge) {
                // Создать badge
            } else {
                badge.textContent = data.count;
            }
        } else if (badge) {
            badge.remove();
        }
    }
}, 30000);
```

## Создание уведомлений программно

### При создании бронирования

```python
# booking/views.py

def create_booking(request):
    # ... создание бронирования ...

    # Уведомление создателю
    Notification.objects.create(
        user=request.user,
        type='booking_created',
        title='Бронирование создано',
        message=f'Вы забронировали {court.name} на {booking.date} в {booking.start_time}',
        metadata={
            'booking_id': booking.id,
            'court_name': court.name,
            'date': str(booking.date),
            'time': str(booking.start_time)
        }
    )

    # Уведомления партнерам
    for partner in booking.partners.all():
        Notification.objects.create(
            user=partner,
            type='booking_invitation',
            title='Приглашение в игру',
            message=f'{request.user.username} приглашает вас на игру',
            metadata={
                'booking_id': booking.id,
                'invitation_id': invitation.id
            }
        )
```

### При обновлении рейтинга

```python
# users/views.py

def update_player_rating(request, user_id):
    # ... обновление рейтинга ...

    Notification.objects.create(
        user=player,
        type='rating_updated',
        title='Рейтинг обновлен',
        message=f'Ваш рейтинг изменился: {old_rating.level} → {new_rating.level}',
        metadata={
            'old_rating': str(old_rating.numeric_rating),
            'new_rating': str(new_rating.numeric_rating),
            'old_level': old_rating.level,
            'new_level': new_rating.level
        }
    )
```

### Напоминания (через Celery)

```python
# tasks.py

@celery_task
def send_booking_reminders():
    """Отправка напоминаний за 24 часа и 1 час"""
    now = timezone.now()
    tomorrow = now + timedelta(hours=24)
    in_one_hour = now + timedelta(hours=1)

    # Напоминания за 24 часа
    bookings_24h = Booking.objects.filter(
        date=tomorrow.date(),
        start_time__hour=tomorrow.hour,
        status='confirmed'
    )

    for booking in bookings_24h:
        Notification.objects.create(
            user=booking.user,
            type='booking_reminder_24h',
            title='Напоминание о бронировании',
            message=f'Завтра в {booking.start_time} у вас игра на {booking.court.name}',
            metadata={
                'booking_id': booking.id,
                'court_name': booking.court.name
            }
        )

    # Аналогично для 1 часа...
```

## Производительность

### Оптимизация запросов

```python
# Используем select_related для оптимизации
notifications = Notification.objects.filter(
    user=request.user
).select_related('user').order_by('-created_at')[:50]
```

### Пагинация

Для большого количества уведомлений:

```python
from django.core.paginator import Paginator

notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
paginator = Paginator(notifications, 20)  # 20 на страницу
page = request.GET.get('page')
notifications_page = paginator.get_page(page)
```

### Кэширование счетчика

```python
from django.core.cache import cache

def get_unread_count(user):
    cache_key = f'unread_notifications_{user.id}'
    count = cache.get(cache_key)

    if count is None:
        count = Notification.objects.filter(user=user, is_read=False).count()
        cache.set(cache_key, count, 300)  # 5 минут

    return count

# Инвалидация при создании/чтении
def invalidate_count_cache(user):
    cache_key = f'unread_notifications_{user.id}'
    cache.delete(cache_key)
```

## Расширение системы

### Добавление нового типа уведомления

1. **Добавить в NOTIFICATION_TYPES:**

```python
# users/models.py
NOTIFICATION_TYPES = [
    # ...
    ('tournament_invite', 'Приглашение в турнир'),
]
```

2. **Добавить иконку и цвет:**

```css
/* static/css/notifications.css */
.notification-icon.tournament_invite {
    background: linear-gradient(135deg, #ff6b6b 0%, #c92a2a 100%);
    color: white;
}
```

3. **Обновить партиал:**

```django
<!-- templates/users/partials/notification_card.html -->
{% elif 'tournament' in notification.type %}
    <i class="fas fa-trophy"></i>
```

4. **Создать уведомление:**

```python
Notification.objects.create(
    user=player,
    type='tournament_invite',
    title='Приглашение в турнир',
    message=f'Вас пригласили в турнир "{tournament.name}"',
    metadata={'tournament_id': tournament.id}
)
```

## Тестирование

### Создание тестовых уведомлений

```python
# management/commands/create_test_notifications.py

from django.core.management.base import BaseCommand
from users.models import Notification
from django.contrib.auth.models import User

class Command(BaseCommand):
    def handle(self, *args, **options):
        user = User.objects.first()

        # Создаем разные типы уведомлений
        types = [
            ('booking_created', 'Бронирование создано'),
            ('payment_success', 'Оплата прошла успешно'),
            ('rating_updated', 'Ваш рейтинг обновлен'),
        ]

        for ntype, message in types:
            Notification.objects.create(
                user=user,
                type=ntype,
                title=message,
                message='Тестовое уведомление',
                is_read=False
            )
```

Запуск: `python manage.py create_test_notifications`

## Безопасность

### CSRF защита

Все AJAX-запросы защищены CSRF-токеном:

```javascript
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

fetch('/users/ajax/notifications/mark-read/', {
    headers: {
        'X-CSRFToken': csrfToken
    }
})
```

### Проверка прав доступа

```python
# views.py
@login_required
def mark_notification_read(request):
    notification = Notification.objects.get(
        id=notification_id,
        user=request.user  # Убеждаемся что уведомление принадлежит пользователю
    )
```

## Зависимости

- Django 4.x+
- django.contrib.humanize (для naturaltime)
- Font Awesome 6.4.0 (иконки)
- JavaScript ES6+ (async/await)

## Дополнительные улучшения

### Real-time с WebSockets

Для мгновенного получения уведомлений:

```python
# consumers.py (Django Channels)
class NotificationConsumer(WebsocketConsumer):
    def receive(self, text_data):
        # Отправка уведомлений в real-time
        pass
```

### Push-уведомления

Интеграция с браузерными push-уведомлениями:

```javascript
// Запрос разрешения
Notification.requestPermission().then(permission => {
    if (permission === 'granted') {
        // Подписка на push-уведомления
    }
});
```

### Email/SMS уведомления

Расширение модели для отправки через разные каналы:

```python
class Notification(models.Model):
    # ...
    send_email = BooleanField(default=False)
    send_sms = BooleanField(default=False)
    send_push = BooleanField(default=False)
```
