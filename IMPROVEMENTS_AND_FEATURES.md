# Улучшения и новые функции для Paddle Booking System

**Дата:** 2026-01-29
**Версия проекта:** v3.5+
**Статус:** Идеи для разработки

---

## 🔥 Критические улучшения (исправлено)

### ✅ Исправленные проблемы
1. **Критическая ошибка в manager/views.py:1579** - `user.objects` → `User.objects` ✅
2. **База данных переименована** - `db.sqlite3` → `db.db` ✅
3. **Удален отладочный print** - из paddle_booking/views.py ✅

---

## 💎 Быстрые улучшения (Quick Wins - 1-2 дня)

### 1. Улучшения UI/UX

#### 1.1 Поиск и фильтрация
```python
# Добавить глобальный поиск по всем страницам админ-панели
- Поиск по бронированиям (дата, пользователь, корт)
- Поиск по пользователям (имя, email, телефон)
- Поиск по платежам (transaction_id, сумма)
- Горячая клавиша: Ctrl+K или Cmd+K
```

**Техническая реализация:**
- Добавить endpoint `/manager/api/search/`
- JavaScript обработчик с debounce (300ms)
- Modal окно с результатами поиска
- Highlight совпадений

#### 1.2 Сортировка таблиц
```python
# Кликабельные заголовки колонок
- Сортировка по любому полю
- Индикатор направления (↑↓)
- Сохранение в localStorage
```

#### 1.3 Экспорт данных
```python
# Расширенный экспорт
- CSV (уже есть) ✅
- Excel (.xlsx) с форматированием
- PDF отчеты
- JSON для API
```

**Реализация для Excel:**
```python
# requirements.txt
openpyxl==3.1.2

# views.py
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

def export_to_excel(queryset, filename):
    wb = Workbook()
    ws = wb.active
    # Заголовки с форматированием
    # Данные
    # Автоширина колонок
    return response
```

### 2. Уведомления и алерты

#### 2.1 Real-time уведомления
```python
# Использовать Django Channels + WebSocket
- Новое бронирование → уведомление менеджеру
- Изменение статуса → уведомление клиенту
- Новый платеж → уведомление в админку
- Отмена бронирования → всем участникам
```

**Стэк:**
- `channels` + `daphne` для WebSocket
- Redis для channel layer
- Toast notifications на фронтенде

#### 2.2 Email уведомления
```python
# Интеграция с SendGrid или Mailgun
TEMPLATES = {
    'booking_confirmed': 'Бронирование подтверждено',
    'booking_reminder': 'Напоминание о бронировании (за 24ч)',
    'payment_received': 'Платеж получен',
    'booking_cancelled': 'Бронирование отменено',
    'invoice': 'Счет на оплату',
}
```

#### 2.3 SMS уведомления
```python
# Интеграция с SMS.ru или Twilio
from smsaero import SmsAero

def send_booking_reminder(booking):
    """Отправка SMS напоминания за 24 часа"""
    api = SmsAero(email=settings.SMS_EMAIL, api_key=settings.SMS_API_KEY)
    message = f"Напоминание: завтра в {booking.start_time} у вас бронирование корта {booking.court.name}"
    api.send(booking.user.profile.phone, message)
```

### 3. Аналитика и отчеты

#### 3.1 Dashboard widgets
```javascript
// Добавить виджеты с метриками
- Доход за сегодня/неделю/месяц (с процентом роста)
- Количество новых пользователей
- Загруженность кортов (в процентах)
- Топ-5 клиентов по расходам
- Средний чек
- Конверсия: визиты → бронирования
```

#### 3.2 Графики и визуализация
```javascript
// Дополнительные графики Chart.js
- Heatmap загруженности (по дням недели и часам)
- Funnel chart (воронка конверсии)
- Pie chart распределения бронирований по типам
- Area chart прогноз дохода
```

#### 3.3 Отчеты по расписанию
```python
# Celery задачи для автоматических отчетов
@shared_task
def send_weekly_report():
    """Отправка еженедельного отчета владельцу"""
    stats = calculate_weekly_stats()
    send_email_report(stats)

# Настройка в celery beat
CELERY_BEAT_SCHEDULE = {
    'weekly-report': {
        'task': 'manager.tasks.send_weekly_report',
        'schedule': crontab(day_of_week=1, hour=9, minute=0),
    },
}
```

---

## 🚀 Средние улучшения (1-2 недели)

### 4. Система платежей

#### 4.1 Интеграция ЮKassa
```python
# yookassa_integration.py
from yookassa import Configuration, Payment

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

def create_payment(booking):
    """Создание платежа через ЮKassa"""
    payment = Payment.create({
        "amount": {
            "value": str(booking.total_price),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"{settings.SITE_URL}/bookings/{booking.id}/success"
        },
        "capture": True,
        "description": f"Бронирование корта {booking.court.name}"
    })
    return payment.confirmation.confirmation_url
```

#### 4.2 Автоматическая обработка платежей
```python
# Webhook endpoint для ЮKassa
@csrf_exempt
def yookassa_webhook(request):
    """Обработка уведомлений от ЮKassa"""
    data = json.loads(request.body)

    if data['event'] == 'payment.succeeded':
        payment_id = data['object']['id']
        # Найти бронирование и подтвердить
        booking = Booking.objects.get(payment__transaction_id=payment_id)
        booking.status = 'confirmed'
        booking.payment.status = 'paid'
        booking.payment.save()
        booking.save()

        # Отправить уведомление
        send_payment_confirmation(booking)

    return JsonResponse({'status': 'ok'})
```

#### 4.3 Возвраты и частичная оплата
```python
# Возврат средств через API
def refund_payment(payment, amount=None):
    """Возврат платежа (полный или частичный)"""
    refund_amount = amount or payment.amount

    refund = Refund.create({
        "payment_id": payment.transaction_id,
        "amount": {
            "value": str(refund_amount),
            "currency": "RUB"
        }
    })

    payment.status = 'refunded' if amount is None else 'partial_refund'
    payment.refunded_amount = refund_amount
    payment.save()
```

### 5. CRM функционал

#### 5.1 Профили клиентов с историей
```python
# users/models.py
class CustomerProfile(models.Model):
    """Расширенный профиль клиента для CRM"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Сегментация
    segment = models.CharField(max_length=20, choices=[
        ('vip', 'VIP клиент'),
        ('regular', 'Постоянный'),
        ('new', 'Новый'),
        ('churned', 'Ушедший'),
    ])

    # Метрики
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_bookings = models.IntegerField(default=0)
    last_booking_date = models.DateField(null=True)

    # Предпочтения
    favorite_court = models.ForeignKey(Court, null=True, on_delete=SET_NULL)
    preferred_time = models.TimeField(null=True)
    preferred_day = models.CharField(max_length=10, null=True)

    # LTV (Lifetime Value)
    ltv = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Заметки менеджера
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list)  # ['постоянный', 'турнир', 'vip']
```

#### 5.2 Автоматическая сегментация
```python
@receiver(post_save, sender=Booking)
def update_customer_segment(sender, instance, **kwargs):
    """Автоматическое обновление сегмента клиента"""
    profile = instance.user.customer_profile

    # Пересчитываем метрики
    profile.total_bookings = Booking.objects.filter(user=instance.user).count()
    profile.total_spent = Booking.objects.filter(
        user=instance.user,
        status='confirmed'
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0

    # Определяем сегмент
    if profile.total_spent > 50000:
        profile.segment = 'vip'
    elif profile.total_bookings > 10:
        profile.segment = 'regular'
    else:
        profile.segment = 'new'

    profile.save()
```

#### 5.3 Email кампании
```python
# manager/campaigns.py
class EmailCampaign:
    """Целевые email рассылки"""

    @staticmethod
    def send_winback_campaign():
        """Вернуть ушедших клиентов (не было бронирований 30+ дней)"""
        inactive_users = User.objects.filter(
            customer_profile__last_booking_date__lt=timezone.now() - timedelta(days=30)
        )

        for user in inactive_users:
            send_email(
                to=user.email,
                subject="Скучаем по вам! Специальная скидка 20%",
                template='winback_20_discount.html',
                context={'user': user, 'discount_code': generate_promo_code()}
            )

    @staticmethod
    def send_vip_promotion():
        """Специальные предложения для VIP клиентов"""
        vip_users = User.objects.filter(customer_profile__segment='vip')

        for user in vip_users:
            send_email(
                to=user.email,
                subject="Эксклюзивно для VIP: Ранее бронирование на турнир",
                template='vip_tournament_early_access.html',
                context={'user': user}
            )
```

### 6. Расписание и календарь

#### 6.1 Повторяющиеся бронирования
```python
# booking/models.py
class RecurringBooking(models.Model):
    """Повторяющееся бронирование (для регулярных тренировок)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    court = models.ForeignKey(Court, on_delete=CASCADE)

    # Расписание
    start_time = models.TimeField()
    end_time = models.TimeField()
    recurrence_rule = models.CharField(max_length=20, choices=[
        ('weekly', 'Еженедельно'),
        ('biweekly', 'Раз в 2 недели'),
        ('monthly', 'Ежемесячно'),
    ])
    weekday = models.IntegerField()  # 0=Monday, 6=Sunday

    # Период действия
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    def generate_bookings(self):
        """Автоматическое создание бронирований по расписанию"""
        current_date = self.start_date
        while current_date <= (self.end_date or current_date + timedelta(days=365)):
            if current_date.weekday() == self.weekday:
                Booking.objects.create(
                    user=self.user,
                    court=self.court,
                    date=current_date,
                    start_time=self.start_time,
                    end_time=self.end_time,
                    booking_type='training',
                    recurring_booking=self
                )

            # Следующая дата по правилу
            if self.recurrence_rule == 'weekly':
                current_date += timedelta(days=7)
            elif self.recurrence_rule == 'biweekly':
                current_date += timedelta(days=14)
            elif self.recurrence_rule == 'monthly':
                current_date = add_months(current_date, 1)
```

#### 6.2 Листы ожидания
```python
# booking/models.py
class WaitingList(models.Model):
    """Лист ожидания для занятых слотов"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    court = models.ForeignKey(Court, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    @staticmethod
    def notify_when_available(booking):
        """Уведомить людей из листа ожидания при отмене"""
        if booking.status == 'cancelled':
            waitlist = WaitingList.objects.filter(
                court=booking.court,
                date=booking.date,
                start_time=booking.start_time
            )

            for wait_entry in waitlist:
                send_notification(
                    wait_entry.user,
                    f"Освободился слот {booking.date} {booking.start_time}!",
                    notification_type='waitlist_available'
                )
```

#### 6.3 Умное расписание тренера
```python
# users/models.py
class CoachAvailability(models.Model):
    """Доступность тренера"""
    coach = models.ForeignKey(User, on_delete=models.CASCADE)

    # Регулярное расписание
    weekday = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Исключения
    is_available = models.BooleanField(default=True)

    # Буферное время между сессиями
    buffer_minutes = models.IntegerField(default=15)

class CoachTimeOff(models.Model):
    """Отпуска и выходные тренера"""
    coach = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=200)
```

---

## 🎯 Большие фичи (1+ месяц)

### 7. Турниры и соревнования

#### 7.1 Система турниров
```python
# tournament/models.py
class Tournament(models.Model):
    """Турнир"""
    name = models.CharField(max_length=200)
    description = models.TextField()

    # Даты
    start_date = models.DateField()
    end_date = models.DateField()
    registration_deadline = models.DateField()

    # Настройки
    max_participants = models.IntegerField()
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2)
    prize_pool = models.DecimalField(max_digits=10, decimal_places=2)

    # Формат
    format = models.CharField(max_length=20, choices=[
        ('single_elimination', 'Олимпийская система'),
        ('double_elimination', 'Двойная олимпийская'),
        ('round_robin', 'Круговая'),
        ('swiss', 'Швейцарская'),
    ])

    # Ограничения по рейтингу
    min_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    max_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True)

    # Статус
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Черновик'),
        ('registration_open', 'Регистрация открыта'),
        ('registration_closed', 'Регистрация закрыта'),
        ('in_progress', 'Идет турнир'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ])

class TournamentParticipant(models.Model):
    """Участник турнира"""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seed = models.IntegerField(null=True)  # Посев
    payment_status = models.CharField(max_length=20)

class TournamentMatch(models.Model):
    """Матч в турнире"""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    round = models.IntegerField()
    match_number = models.IntegerField()

    player1 = models.ForeignKey(User, on_delete=CASCADE, related_name='matches_as_p1')
    player2 = models.ForeignKey(User, on_delete=CASCADE, related_name='matches_as_p2')

    # Результат
    winner = models.ForeignKey(User, null=True, on_delete=SET_NULL, related_name='won_matches')
    score = models.JSONField(default=dict)  # {"sets": ["6-4", "7-5"]}

    # Расписание
    scheduled_date = models.DateField(null=True)
    scheduled_time = models.TimeField(null=True)
    court = models.ForeignKey(Court, null=True, on_delete=SET_NULL)

    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Запланирован'),
        ('in_progress', 'Идет'),
        ('completed', 'Завершен'),
        ('walkover', 'Walkover'),
    ])
```

#### 7.2 Автоматическая генерация сетки
```python
# tournament/bracket_generator.py
def generate_single_elimination_bracket(tournament):
    """Генерация олимпийской сетки"""
    participants = list(tournament.participants.all().order_by('seed'))

    # Определяем количество раундов
    num_participants = len(participants)
    num_rounds = math.ceil(math.log2(num_participants))

    # Генерируем первый раунд
    matches = []
    for i in range(0, len(participants), 2):
        if i + 1 < len(participants):
            match = TournamentMatch.objects.create(
                tournament=tournament,
                round=1,
                match_number=i//2 + 1,
                player1=participants[i].user,
                player2=participants[i+1].user,
                status='scheduled'
            )
            matches.append(match)
        else:
            # Bye (нечетное количество участников)
            pass

    return matches

def generate_round_robin_schedule(tournament):
    """Генерация круговой системы"""
    participants = list(tournament.participants.all())
    n = len(participants)

    # Алгоритм круговой системы
    matches = []
    for round_num in range(n - 1):
        for i in range(n // 2):
            p1 = participants[i]
            p2 = participants[n - 1 - i]

            match = TournamentMatch.objects.create(
                tournament=tournament,
                round=round_num + 1,
                match_number=i + 1,
                player1=p1.user,
                player2=p2.user,
                status='scheduled'
            )
            matches.append(match)

        # Ротация (кроме первого элемента)
        participants = [participants[0]] + [participants[-1]] + participants[1:-1]

    return matches
```

### 8. Мобильное приложение (React Native)

#### 8.1 REST API для мобильного приложения
```python
# api/v1/serializers.py
from rest_framework import serializers

class CourtSerializer(serializers.ModelSerializer):
    class Meta:
        model = Court
        fields = ['id', 'name', 'price_per_hour', 'is_available']

class BookingSerializer(serializers.ModelSerializer):
    court = CourtSerializer(read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'court', 'user_name', 'date',
            'start_time', 'end_time', 'status', 'total_price'
        ]

# api/v1/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        booking.status = 'confirmed'
        booking.save()
        return Response({'status': 'confirmed'})

# api/v1/urls.py
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'courts', CourtViewSet, basename='court')

urlpatterns = router.urls
```

#### 8.2 Push notifications
```python
# notifications/push.py
from firebase_admin import messaging

def send_push_notification(user, title, body, data=None):
    """Отправка push уведомления через Firebase"""

    # Получаем FCM token пользователя
    device = user.devices.filter(is_active=True).first()
    if not device:
        return

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        token=device.fcm_token,
    )

    response = messaging.send(message)
    return response

# Использование
@receiver(post_save, sender=Booking)
def notify_booking_confirmed(sender, instance, **kwargs):
    if instance.status == 'confirmed':
        send_push_notification(
            instance.user,
            title="Бронирование подтверждено!",
            body=f"Корт {instance.court.name} на {instance.date}",
            data={'booking_id': str(instance.id)}
        )
```

### 9. Loyalty программа и бонусы

#### 9.1 Система баллов
```python
# loyalty/models.py
class LoyaltyAccount(models.Model):
    """Бонусный счет"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    tier = models.CharField(max_length=20, choices=[
        ('bronze', 'Бронза'),
        ('silver', 'Серебро'),
        ('gold', 'Золото'),
        ('platinum', 'Платина'),
    ], default='bronze')

    def add_points(self, amount, description):
        """Начислить баллы"""
        self.points += amount
        self.save()

        PointsTransaction.objects.create(
            account=self,
            amount=amount,
            type='earned',
            description=description
        )

        # Проверяем повышение уровня
        self.check_tier_upgrade()

    def spend_points(self, amount, description):
        """Потратить баллы"""
        if self.points < amount:
            raise ValueError("Недостаточно баллов")

        self.points -= amount
        self.save()

        PointsTransaction.objects.create(
            account=self,
            amount=-amount,
            type='spent',
            description=description
        )

    def check_tier_upgrade(self):
        """Проверка повышения уровня"""
        total_spent = self.user.customer_profile.total_spent

        if total_spent >= 100000:
            self.tier = 'platinum'
        elif total_spent >= 50000:
            self.tier = 'gold'
        elif total_spent >= 20000:
            self.tier = 'silver'
        else:
            self.tier = 'bronze'

        self.save()

class PointsTransaction(models.Model):
    """История начислений/списаний баллов"""
    account = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE)
    amount = models.IntegerField()
    type = models.CharField(max_length=20, choices=[
        ('earned', 'Начислено'),
        ('spent', 'Потрачено'),
        ('expired', 'Сгорело'),
    ])
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

class Reward(models.Model):
    """Награды за баллы"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    points_cost = models.IntegerField()

    # Тип награды
    type = models.CharField(max_length=20, choices=[
        ('discount', 'Скидка'),
        ('free_booking', 'Бесплатное бронирование'),
        ('upgrade', 'Upgrade корта'),
        ('merch', 'Мерч'),
    ])

    # Параметры
    discount_percent = models.IntegerField(null=True)
    free_hours = models.IntegerField(null=True)

    is_active = models.BooleanField(default=True)
```

#### 9.2 Автоматическое начисление баллов
```python
@receiver(post_save, sender=Booking)
def award_loyalty_points(sender, instance, **kwargs):
    """Начисление баллов за бронирование"""
    if instance.status == 'confirmed':
        account, created = LoyaltyAccount.objects.get_or_create(user=instance.user)

        # 1 балл за каждые 100 рублей
        points = int(instance.total_price / 100)

        # Бонус за уровень
        multiplier = {
            'bronze': 1,
            'silver': 1.5,
            'gold': 2,
            'platinum': 3,
        }[account.tier]

        points = int(points * multiplier)

        account.add_points(
            points,
            f"Бронирование #{instance.id} - {instance.court.name}"
        )
```

#### 9.3 Реферальная программа
```python
# loyalty/models.py
class ReferralProgram(models.Model):
    """Реферальная программа"""
    referrer = models.ForeignKey(User, on_delete=CASCADE, related_name='referrals_sent')
    referred = models.ForeignKey(User, on_delete=CASCADE, related_name='referred_by')

    # Награды
    referrer_bonus = models.IntegerField(default=500)  # баллов
    referred_bonus = models.IntegerField(default=300)  # баллов

    # Статус
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Ожидает'),
        ('completed', 'Выполнено'),
    ])

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

    @staticmethod
    def complete_referral(referred_user):
        """Завершить реферал после первого бронирования"""
        try:
            referral = ReferralProgram.objects.get(
                referred=referred_user,
                status='pending'
            )

            # Награждаем обоих
            referrer_account = LoyaltyAccount.objects.get(user=referral.referrer)
            referred_account, _ = LoyaltyAccount.objects.get_or_create(user=referred_user)

            referrer_account.add_points(
                referral.referrer_bonus,
                f"Реферал: {referred_user.get_full_name()}"
            )

            referred_account.add_points(
                referral.referred_bonus,
                "Бонус за регистрацию по реферальной ссылке"
            )

            referral.status = 'completed'
            referral.completed_at = timezone.now()
            referral.save()

        except ReferralProgram.DoesNotExist:
            pass
```

---

## 🤖 AI и Machine Learning фичи

### 10. Умные рекомендации

#### 10.1 Рекомендация партнеров по игре
```python
# ml/partner_matching.py
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class PartnerRecommender:
    """ML модель для подбора партнеров"""

    def get_user_features(self, user):
        """Извлечь признаки пользователя"""
        profile = user.customer_profile
        rating = user.rating

        return np.array([
            rating.numeric_rating,  # Уровень игры
            profile.total_bookings,  # Активность
            self.get_time_preference(user),  # Предпочитаемое время
            self.get_day_preference(user),  # Предпочитаемый день
        ])

    def recommend_partners(self, user, n=5):
        """Рекомендовать N лучших партнеров"""
        user_features = self.get_user_features(user)

        # Получаем всех пользователей кроме текущего
        all_users = User.objects.exclude(id=user.id)

        similarities = []
        for other_user in all_users:
            other_features = self.get_user_features(other_user)
            similarity = cosine_similarity(
                user_features.reshape(1, -1),
                other_features.reshape(1, -1)
            )[0][0]
            similarities.append((other_user, similarity))

        # Сортируем по схожести
        similarities.sort(key=lambda x: x[1], reverse=True)

        return [user for user, _ in similarities[:n]]
```

#### 10.2 Прогноз загруженности
```python
# ml/demand_forecasting.py
from sklearn.ensemble import RandomForestRegressor
import pandas as pd

class DemandForecaster:
    """Прогноз спроса на корты"""

    def train(self):
        """Обучить модель на исторических данных"""
        # Получаем исторические бронирования
        bookings = Booking.objects.filter(
            status='confirmed',
            date__gte=timezone.now() - timedelta(days=365)
        )

        # Подготавливаем данные
        data = []
        for booking in bookings:
            data.append({
                'weekday': booking.date.weekday(),
                'hour': booking.start_time.hour,
                'month': booking.date.month,
                'is_weekend': booking.date.weekday() >= 5,
                'court_id': booking.court.id,
                'bookings_count': 1,
            })

        df = pd.DataFrame(data)

        # Группируем и считаем
        features = df.groupby(['weekday', 'hour', 'month', 'is_weekend', 'court_id']).size()

        # Обучаем модель
        X = features.index.to_frame()
        y = features.values

        self.model = RandomForestRegressor(n_estimators=100)
        self.model.fit(X, y)

    def predict_demand(self, date, hour, court_id):
        """Предсказать количество бронирований"""
        features = pd.DataFrame([{
            'weekday': date.weekday(),
            'hour': hour,
            'month': date.month,
            'is_weekend': date.weekday() >= 5,
            'court_id': court_id,
        }])

        prediction = self.model.predict(features)[0]
        return max(0, int(prediction))
```

#### 10.3 Динамическое ценообразование
```python
# pricing/dynamic_pricing.py
class DynamicPricer:
    """Динамические цены на основе спроса"""

    def calculate_price(self, court, date, start_time):
        """Рассчитать цену с учетом спроса"""
        base_price = court.price_per_hour

        # Множители
        multipliers = []

        # 1. Время суток
        hour = start_time.hour
        if 18 <= hour <= 21:  # Пик
            multipliers.append(1.3)
        elif 6 <= hour <= 9 or 22 <= hour <= 23:  # Непопулярное время
            multipliers.append(0.8)

        # 2. День недели
        if date.weekday() >= 5:  # Выходные
            multipliers.append(1.2)

        # 3. Прогноз спроса
        forecaster = DemandForecaster()
        predicted_demand = forecaster.predict_demand(date, hour, court.id)
        if predicted_demand > 3:
            multipliers.append(1.4)
        elif predicted_demand < 1:
            multipliers.append(0.9)

        # 4. Заполненность на дату
        bookings_on_date = Booking.objects.filter(
            court=court,
            date=date,
            status='confirmed'
        ).count()

        if bookings_on_date >= 8:  # Высокая заполненность
            multipliers.append(1.25)

        # Применяем множители
        final_price = base_price
        for multiplier in multipliers:
            final_price *= multiplier

        return round(final_price, 2)
```

---

## 📱 Интеграции

### 11. Социальные сети и мессенджеры

#### 11.1 Telegram бот
```python
# telegram_bot/bot.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

async def start(update: Update, context):
    """Приветствие"""
    keyboard = [
        [InlineKeyboardButton("📅 Мои бронирования", callback_data='my_bookings')],
        [InlineKeyboardButton("➕ Новое бронирование", callback_data='new_booking')],
        [InlineKeyboardButton("💰 Баланс и баллы", callback_data='balance')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        'Привет! Я бот для бронирования кортов.',
        reply_markup=reply_markup
    )

async def my_bookings(update: Update, context):
    """Показать мои бронирования"""
    query = update.callback_query
    user = get_user_by_telegram_id(query.from_user.id)

    bookings = Booking.objects.filter(
        user=user,
        date__gte=timezone.now().date()
    )

    text = "Ваши бронирования:\n\n"
    for booking in bookings:
        text += f"📅 {booking.date} {booking.start_time}\n"
        text += f"🏟 {booking.court.name}\n"
        text += f"💵 {booking.total_price}₽\n\n"

    await query.message.reply_text(text)

# Запуск бота
application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(my_bookings, pattern='^my_bookings$'))
application.run_polling()
```

#### 11.2 WhatsApp интеграция (Twilio)
```python
# whatsapp/notifications.py
from twilio.rest import Client

def send_whatsapp_notification(phone, message):
    """Отправить WhatsApp сообщение"""
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    message = client.messages.create(
        from_=f'whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}',
        body=message,
        to=f'whatsapp:{phone}'
    )

    return message.sid

# Использование
def notify_booking_reminder(booking):
    """Напоминание за 2 часа до бронирования"""
    message = f"""
🏸 Напоминание о бронировании!

📅 {booking.date.strftime('%d.%m.%Y')}
⏰ {booking.start_time.strftime('%H:%M')}
🏟 Корт: {booking.court.name}

Ждем вас!
    """

    send_whatsapp_notification(
        booking.user.profile.phone,
        message.strip()
    )
```

### 12. Внешние сервисы

#### 12.1 Интеграция с Google Calendar
```python
# integrations/google_calendar.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def create_calendar_event(booking, user_credentials):
    """Создать событие в Google Calendar"""
    creds = Credentials(**user_credentials)
    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': f'Падл - {booking.court.name}',
        'description': f'Бронирование #{booking.id}',
        'start': {
            'dateTime': f'{booking.date}T{booking.start_time}',
            'timeZone': 'Europe/Moscow',
        },
        'end': {
            'dateTime': f'{booking.date}T{booking.end_time}',
            'timeZone': 'Europe/Moscow',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 120},
                {'method': 'email', 'minutes': 60},
            ],
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    return event['htmlLink']
```

#### 12.2 Экспорт в QuickBooks (бухгалтерия)
```python
# integrations/quickbooks.py
from intuitlib.client import AuthClient
from quickbooks import QuickBooks

def sync_payments_to_quickbooks():
    """Синхронизация платежей с QuickBooks"""
    auth_client = AuthClient(
        client_id=settings.QUICKBOOKS_CLIENT_ID,
        client_secret=settings.QUICKBOOKS_CLIENT_SECRET,
        redirect_uri=settings.QUICKBOOKS_REDIRECT_URI,
        environment='production'
    )

    client = QuickBooks(
        auth_client=auth_client,
        refresh_token=get_refresh_token(),
        company_id=settings.QUICKBOOKS_COMPANY_ID
    )

    # Получаем неэкспортированные платежи
    payments = Payment.objects.filter(
        status='paid',
        exported_to_quickbooks=False
    )

    for payment in payments:
        # Создаем Invoice в QuickBooks
        invoice = Invoice()
        invoice.CustomerRef = get_or_create_customer(client, payment.user)

        line = SalesItemLine()
        line.Amount = float(payment.amount)
        line.Description = f"Бронирование #{payment.booking.id}"
        invoice.Line.append(line)

        invoice.save(qb=client)

        payment.exported_to_quickbooks = True
        payment.quickbooks_invoice_id = invoice.Id
        payment.save()
```

---

## 💡 Инновационные идеи

### 13. Геймификация

```python
# gamification/models.py
class Achievement(models.Model):
    """Достижения"""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    icon = models.CharField(max_length=50)  # emoji или URL
    points = models.IntegerField()

    # Условия получения
    condition_type = models.CharField(max_length=20, choices=[
        ('bookings_count', 'Количество бронирований'),
        ('total_spent', 'Потрачено денег'),
        ('streak_days', 'Дни подряд'),
        ('tournament_win', 'Победа в турнире'),
        ('referrals', 'Приглашено друзей'),
    ])
    condition_value = models.IntegerField()

class UserAchievement(models.Model):
    """Полученные достижения"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'achievement']

# Примеры достижений
ACHIEVEMENTS = [
    {
        'code': 'first_booking',
        'name': '🎾 Первый шаг',
        'description': 'Сделайте первое бронирование',
        'points': 50,
    },
    {
        'code': 'booking_master',
        'name': '👑 Мастер бронирований',
        'description': 'Сделайте 100 бронирований',
        'points': 1000,
    },
    {
        'code': 'vip_spender',
        'name': '💎 VIP Игрок',
        'description': 'Потратьте 100,000₽',
        'points': 5000,
    },
    {
        'code': 'night_owl',
        'name': '🦉 Ночной игрок',
        'description': 'Забронируйте корт после 22:00',
        'points': 100,
    },
    {
        'code': 'early_bird',
        'name': '🐦 Ранняя пташка',
        'description': 'Забронируйте корт до 8:00',
        'points': 100,
    },
]
```

### 14. Live streaming матчей

```python
# streaming/models.py
class LiveStream(models.Model):
    """Прямая трансляция матча"""
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)

    # YouTube / Twitch
    platform = models.CharField(max_length=20)
    stream_url = models.URLField()
    stream_key = models.CharField(max_length=200)

    # Статус
    is_live = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True)
    ended_at = models.DateTimeField(null=True)

    # Статистика
    peak_viewers = models.IntegerField(default=0)
    total_views = models.IntegerField(default=0)
    chat_messages = models.IntegerField(default=0)

# Интеграция с YouTube Live API
def start_youtube_stream(booking):
    """Начать трансляцию на YouTube"""
    youtube = build('youtube', 'v3', credentials=get_youtube_credentials())

    broadcast = youtube.liveBroadcasts().insert(
        part='snippet,status',
        body={
            'snippet': {
                'title': f'{booking.user.get_full_name()} - Падл матч',
                'scheduledStartTime': booking.booking_datetime.isoformat(),
            },
            'status': {
                'privacyStatus': 'public'
            }
        }
    ).execute()

    return broadcast
```

### 15. AR / VR опыт

```python
# Идея: Виртуальный тур по кортам в AR
# - Unity + ARCore/ARKit
# - 360° фото кортов
# - Виртуальная примерка игры на корте
# - Планирование позиций на корте в AR

# Концепт API endpoint
@api_view(['GET'])
def get_court_3d_model(request, court_id):
    """Получить 3D модель корта для AR"""
    court = Court.objects.get(id=court_id)

    return Response({
        'model_url': court.ar_model_url,
        'textures': court.ar_textures,
        'dimensions': {
            'length': 20,  # метров
            'width': 10,
            'height': 10,
        },
        '360_photos': court.panoramic_photos.all()
    })
```

---

## 📊 Аналитика и отчетность

### 16. Advanced Analytics Dashboard

```python
# analytics/dashboards.py
class AdvancedAnalytics:
    """Расширенная аналитика"""

    def cohort_analysis(self, start_date, end_date):
        """Когортный анализ удержания клиентов"""
        cohorts = {}

        # Группируем пользователей по месяцу регистрации
        users = User.objects.filter(
            date_joined__gte=start_date,
            date_joined__lte=end_date
        )

        for user in users:
            cohort_month = user.date_joined.strftime('%Y-%m')
            if cohort_month not in cohorts:
                cohorts[cohort_month] = []
            cohorts[cohort_month].append(user)

        # Анализируем активность по месяцам
        retention_data = {}
        for cohort_month, cohort_users in cohorts.items():
            retention = []
            for month_offset in range(12):
                active_count = 0
                for user in cohort_users:
                    # Проверяем были ли бронирования в этом месяце
                    target_month = timezone.datetime.strptime(cohort_month, '%Y-%m') + timedelta(days=30*month_offset)
                    had_booking = Booking.objects.filter(
                        user=user,
                        date__year=target_month.year,
                        date__month=target_month.month
                    ).exists()

                    if had_booking:
                        active_count += 1

                retention.append(active_count / len(cohort_users) * 100)

            retention_data[cohort_month] = retention

        return retention_data

    def churn_prediction(self, user):
        """Предсказание оттока клиента"""
        # Признаки риска оттока:
        last_booking = Booking.objects.filter(user=user).order_by('-date').first()
        if not last_booking:
            return {'risk': 'high', 'probability': 0.9}

        days_since_last = (timezone.now().date() - last_booking.date).days

        if days_since_last > 60:
            return {'risk': 'high', 'probability': 0.85}
        elif days_since_last > 30:
            return {'risk': 'medium', 'probability': 0.5}
        else:
            return {'risk': 'low', 'probability': 0.1}

    def ltv_calculation(self, user):
        """Расчет Lifetime Value клиента"""
        total_revenue = Booking.objects.filter(
            user=user,
            status='confirmed'
        ).aggregate(Sum('total_price'))['total_price__sum'] or 0

        # Прогноз будущей ценности
        avg_booking_value = total_revenue / max(1, user.bookings_created.count())
        booking_frequency = self.get_booking_frequency(user)
        expected_lifetime = 24  # месяцев

        predicted_ltv = avg_booking_value * booking_frequency * expected_lifetime

        return {
            'historical_value': total_revenue,
            'predicted_ltv': predicted_ltv,
            'total_ltv': total_revenue + predicted_ltv
        }
```

---

## 🔐 Безопасность и соответствие

### 17. GDPR и защита данных

```python
# privacy/gdpr.py
class GDPRCompliance:
    """Соответствие GDPR"""

    @staticmethod
    def export_user_data(user):
        """Экспорт всех данных пользователя (право на доступ)"""
        data = {
            'personal_info': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.profile.phone,
                'date_joined': user.date_joined,
            },
            'bookings': list(user.bookings_created.values()),
            'payments': list(Payment.objects.filter(user=user).values()),
            'loyalty_points': user.loyalty_account.points if hasattr(user, 'loyalty_account') else 0,
        }

        # Генерируем JSON файл
        import json
        filename = f'user_data_{user.id}_{timezone.now().strftime("%Y%m%d")}.json'

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        return filename

    @staticmethod
    def anonymize_user(user):
        """Анонимизация пользователя (право на забвение)"""
        # Анонимизируем личные данные
        user.username = f'deleted_{user.id}'
        user.email = f'deleted_{user.id}@deleted.local'
        user.first_name = 'Deleted'
        user.last_name = 'User'
        user.is_active = False
        user.save()

        # Анонимизируем профиль
        user.profile.phone = '+00000000000'
        user.profile.avatar = None
        user.profile.save()

        # Сохраняем историю бронирований для отчетности, но анонимно
        Booking.objects.filter(user=user).update(
            user=None  # Или специальный "анонимный" пользователь
        )
```

---

## ✅ Приоритезация внедрения

### Фаза 1: Быстрые победы (1-2 недели)
1. ✅ Исправление критических ошибок
2. 🔍 Глобальный поиск (Ctrl+K)
3. 📊 Сортировка таблиц
4. 📧 Email уведомления (SendGrid)
5. 📱 SMS уведомления (SMS.ru)

### Фаза 2: Платежи и CRM (2-4 недели)
6. 💳 Интеграция ЮKassa
7. 👥 CRM профили клиентов
8. 🎯 Сегментация и таргетинг
9. 📈 Расширенная аналитика

### Фаза 3: Автоматизация (4-6 недель)
10. 🔄 Повторяющиеся бронирования
11. ⏰ Автоматические напоминания
12. 📝 Листы ожидания
13. 🤖 Telegram бот

### Фаза 4: Продвинутые фичи (2-3 месяца)
14. 🏆 Турниры
15. 🎮 Геймификация
16. 💎 Loyalty программа
17. 📱 Мобильное приложение (React Native)

### Фаза 5: AI и инновации (3+ месяца)
18. 🤖 ML рекомендации партнеров
19. 📊 Прогноз спроса
20. 💰 Динамическое ценообразование

---

## 🎯 Метрики успеха

### Бизнес метрики
- **MRR (Monthly Recurring Revenue)** - месячный доход
- **CAC (Customer Acquisition Cost)** - стоимость привлечения клиента
- **LTV (Lifetime Value)** - ценность клиента за всё время
- **Churn rate** - отток клиентов
- **Court utilization rate** - загруженность кортов (цель: >70%)

### Продуктовые метрики
- **DAU/MAU** - активные пользователи
- **Booking conversion rate** - конверсия визитов в бронирования (цель: >15%)
- **Average booking value** - средний чек
- **Repeat booking rate** - процент повторных бронирований (цель: >60%)
- **Net Promoter Score (NPS)** - готовность рекомендовать (цель: >50)

---

**Следующий шаг:** Выбери что внедрять в первую очередь!
