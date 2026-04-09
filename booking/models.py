from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models.signals import pre_save
from django.dispatch import receiver


class Court(models.Model):
    name = models.CharField(max_length=100)
    # УДАЛЕНО: today_bookings_count - не использовалось в коде
    description = models.TextField()
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_available']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings_created', verbose_name='Создатель')
    court = models.ForeignKey(Court, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'В ожидании'),
        ('confirmed', 'Подтверждено'),
        ('cancelled', 'Отменено'),
    ], default='pending')
    confirmed_at = models.DateTimeField(null=True, blank=True)

    # Тип бронирования
    BOOKING_TYPE_CHOICES = [
        ('game', 'Игра'),
        ('training', 'Тренировка'),
    ]
    booking_type = models.CharField(
        max_length=20,
        choices=BOOKING_TYPE_CHOICES,
        default='game',
        verbose_name='Тип бронирования',
        help_text='Игра или тренировка',
        db_index=True
    )

    # Новые поля для партнёров и тренера
    partners = models.ManyToManyField(
        User,
        related_name='bookings_as_partner',
        blank=True,
        verbose_name='Партнёры'
    )
    coach = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings_as_coach',
        verbose_name='Тренер',
        limit_choices_to={'groups__name': 'Тренеры'}
    )

    # Функция "Найти партнёра"
    looking_for_partner = models.BooleanField(
        default=False,
        verbose_name='Ищет партнёра'
    )
    max_players = models.IntegerField(
        default=4,
        verbose_name='Макс. игроков',
        help_text='Максимальное количество игроков (включая создателя)'
    )
    required_rating_level = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name='Требуемый уровень игры (устаревшее)',
        help_text='DEPRECATED: используйте required_rating_levels'
    )
    required_rating_levels = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Требуемые уровни игры',
        help_text='Список буквенных рейтингов для поиска партнёров (например: ["C+", "B-", "B"])'
    )

    # Round-robin игры (все с каждым, пары меняются)
    GAME_MODE_CHOICES = [
        ('regular', 'Обычная игра'),
        ('americano', 'Americano - Каждый с каждым, пары меняются'),
        ('mexicano', 'Mexicano - Пары по рейтингу'),
        ('training', 'Тренировка'),
    ]
    game_mode = models.CharField(
        max_length=20,
        choices=GAME_MODE_CHOICES,
        default='regular',
        verbose_name='Режим игры',
        db_index=True
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name='Публичная игра',
        help_text='Игра видна другим пользователям во вкладке "Игры"'
    )
    rounds_count = models.IntegerField(
        default=3,
        verbose_name='Количество раундов',
        help_text='Для Americano/Mexicano режимов'
    )
    points_per_round = models.IntegerField(
        default=24,
        verbose_name='Очков в раунде',
        help_text='Количество очков для игры до окончания раунда'
    )

    GAME_STATUS_CHOICES = [
        ('pending', 'Ожидает игроков'),
        ('ready', 'Готова к началу'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]
    game_status = models.CharField(
        max_length=20,
        choices=GAME_STATUS_CHOICES,
        default='pending',
        verbose_name='Статус игры',
        db_index=True
    )
    current_round = models.IntegerField(
        default=0,
        verbose_name='Текущий раунд',
        help_text='Номер текущего раунда (0 = игра не началась)'
    )
    min_rating_required = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Минимальный рейтинг',
        help_text='Минимальный рейтинг для участия'
    )
    max_rating_required = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Максимальный рейтинг',
        help_text='Максимальный рейтинг для участия'
    )

    class Meta:
        ordering = ['-date', '-start_time']
        indexes = [
            models.Index(fields=['court', 'date', 'status']),
            models.Index(fields=['user']),
            models.Index(fields=['date', 'start_time']),
            models.Index(fields=['status']),
            models.Index(fields=['looking_for_partner', 'date']),
            # Новые индексы для оптимизации
            models.Index(fields=['user', 'date']),  # Поиск бронирований пользователя на дату
            models.Index(fields=['coach', 'date']),  # Поиск тренировок по тренеру
            models.Index(fields=['booking_type']),  # Фильтрация по типу бронирования
            models.Index(fields=['booking_type', 'date']),  # Поиск игр/тренировок по дате
        ]

    def __str__(self):
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        display_name = full_name if full_name else self.user.username
        return f"{display_name} - {self.court.name} - {self.date}"

    @property
    def total_price(self):
        """Рассчитывает общую стоимость бронирования"""
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)

        if end_dt <= start_dt:
            end_dt += timedelta(days=1)  # на случай если бронирование через полночь

        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        return round(float(self.court.price_per_hour) * duration_hours, 2)

    @property
    def price_per_person(self):
        """Рассчитывает стоимость на одного человека"""
        total = self.total_price
        # Для Americano/Mexicano считаем по GameParticipant
        if self.game_mode in ('americano', 'mexicano'):
            participants_count = self.game_participants.filter(status='accepted').count()
            if participants_count > 0:
                return round(total / participants_count, 2)
            return total
        # Для обычных игр: создатель + партнёры (без тренера)
        participants_count = 1 + self.partners.count()
        if participants_count > 1:
            return round(total / participants_count, 2)
        return total

    @property
    def available_slots(self):
        """Количество свободных мест для партнёров"""
        current_players = 1 + self.partners.count()  # создатель + партнёры
        return max(0, self.max_players - current_players)

    @property
    def is_full(self):
        """Проверка, заполнено ли бронирование"""
        return self.available_slots == 0

    def get_all_participants(self):
        """Возвращает список всех участников (создатель + партнёры)"""
        participants = [self.user]
        participants.extend(list(self.partners.all()))
        return participants

    def can_join(self, user, skip_rating_check=False, skip_partner_search_check=False):
        """Проверка, может ли пользователь присоединиться к бронированию

        Args:
            user: Пользователь, который хочет присоединиться
            skip_rating_check: Пропустить проверку рейтинга (для приглашенных)
            skip_partner_search_check: Пропустить проверку looking_for_partner (для приглашенных)
        """
        # Нельзя присоединиться если:
        # 1. Бронирование не ищет партнёров (пропускается для приглашений)
        if not skip_partner_search_check and not self.looking_for_partner:
            return False, "Бронирование не ищет партнёров"

        # 2. Бронирование уже заполнено
        if self.is_full:
            return False, "Нет свободных мест"

        # 3. Пользователь уже является участником
        if user == self.user or user in self.partners.all():
            return False, "Вы уже являетесь участником"

        # 4. Бронирование отменено
        if self.status == 'cancelled':
            return False, "Бронирование отменено"

        # 5. Проверка рейтинга (если указаны требуемые уровни и не пропускается проверка)
        if not skip_rating_check:
            required_levels = self.required_rating_levels or []
            if required_levels:
                try:
                    user_rating = user.rating.level
                    if user_rating not in required_levels:
                        levels_str = ", ".join(required_levels)
                        return False, f"Требуемые уровни: {levels_str}. Ваш уровень: {user_rating}"
                except (AttributeError, Exception):
                    return False, "У вас нет рейтинга или он не установлен"

        return True, "OK"

    def add_partner(self, user):
        """Добавить партнёра в бронирование"""
        can_join, message = self.can_join(user)
        if not can_join:
            return False, message

        self.partners.add(user)
        return True, "Вы успешно присоединились к бронированию"

    @property
    def can_confirm(self):
        """Можно ли подтвердить бронирование (за 24 часа до начала)"""
        from django.utils import timezone

        # Создаем aware datetime для booking_datetime
        booking_datetime = timezone.make_aware(
            datetime.combine(self.date, self.start_time)
        )
        current_time = timezone.now()
        time_diff = booking_datetime - current_time

        # Можно подтвердить если осталось от 0 до 24 часов
        return timedelta(hours=0) < time_diff <= timedelta(hours=24)

    @property
    def hours_until_confirmation(self):
        """Сколько часов осталось до возможности подтверждения"""
        from django.utils import timezone

        booking_datetime = timezone.make_aware(
            datetime.combine(self.date, self.start_time)
        )
        current_time = timezone.now()
        time_diff = booking_datetime - current_time

        # Если уже можно подтверждать
        if time_diff <= timedelta(hours=24):
            return 0

        # Сколько осталось до возможности подтверждения
        hours_until = (time_diff - timedelta(hours=24)).total_seconds() / 3600
        return max(0, int(hours_until))

    @property
    def booking_datetime(self):
        """Полная дата и время начала бронирования"""
        return timezone.make_aware(datetime.combine(self.date, self.start_time))

    def confirm(self):
        """Подтвердить бронирование"""
        if self.status == 'pending' and self.can_confirm:
            self.status = 'confirmed'
            self.confirmed_at = timezone.now()
            self.save()
            try:
                from users.services import NotificationService
                NotificationService.notify_booking_confirmed(self)
            except Exception:
                pass
            return True
        return False


class Payment(models.Model):
    """Модель платежа за бронирование"""

    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачено'),
        ('refunded', 'Возвращено'),
        ('failed', 'Ошибка оплаты'),
        ('cancelled', 'Отменено'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('card', 'Банковская карта'),
        ('bank_transfer', 'Банковский перевод'),
        ('cash', 'Наличные'),
        ('online', 'Онлайн оплата'),
    ]

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='payment',
        verbose_name='Бронирование'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name='Статус'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='online',
        verbose_name='Способ оплаты'
    )
    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        verbose_name='ID транзакции'
    )
    payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='ID платежного намерения',
        help_text='Используется для интеграции с платежными системами'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    paid_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Дата оплаты'
    )
    refunded_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Дата возврата'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Дополнительные данные',
        help_text='Для хранения данных платежной системы'
    )

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['created_at']),
            # Новый индекс для оптимизации
            models.Index(fields=['booking', 'status']),  # Проверка платежей по бронированию
        ]

    def __str__(self):
        return f"Платеж #{self.id} - {self.booking} - {self.amount}₽ ({self.get_status_display()})"

    def mark_as_paid(self):
        """Отметить платеж как оплаченный"""
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save()

    def mark_as_failed(self):
        """Отметить платеж как ошибочный"""
        self.status = 'failed'
        self.save()

    def refund(self):
        """Вернуть платеж и отменить бронирование"""
        if self.status == 'paid':
            self.status = 'refunded'
            self.refunded_at = timezone.now()
            self.save()
            if self.booking.status == 'confirmed':
                self.booking.status = 'cancelled'
                self.booking.save()
            return True
        return False


class BookingHistory(models.Model):
    """История изменений бронирования"""

    ACTION_CHOICES = [
        ('created', 'Создано'),
        ('confirmed', 'Подтверждено'),
        ('cancelled', 'Отменено'),
        ('payment_pending', 'Ожидает оплаты'),
        ('payment_paid', 'Оплачено'),
        ('payment_refunded', 'Оплата возвращена'),
        ('payment_failed', 'Ошибка оплаты'),
        ('modified', 'Изменено'),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='Бронирование'
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True,
        verbose_name='Действие'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Пользователь',
        help_text='Кто выполнил действие'
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Изменения',
        help_text='Данные о том, что изменилось'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Время'
    )

    class Meta:
        verbose_name = 'История бронирования'
        verbose_name_plural = 'История бронирований'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['booking', 'timestamp']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        return f"{self.booking} - {self.get_action_display()} - {self.timestamp}"


class BookingInvitation(models.Model):
    """Приглашение в бронирование"""

    STATUS_CHOICES = [
        ('pending', 'Ожидает ответа'),
        ('accepted', 'Принято'),
        ('declined', 'Отклонено'),
        ('cancelled', 'Отменено'),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='invitations',
        verbose_name='Бронирование'
    )
    inviter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        verbose_name='Отправитель'
    )
    invitee_phone = models.CharField(
        max_length=20,
        verbose_name='Телефон приглашённого',
        help_text='Номер телефона пользователя, которого приглашают'
    )
    invitee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_invitations',
        null=True,
        blank=True,
        verbose_name='Приглашённый пользователь'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name='Статус'
    )
    message = models.TextField(
        blank=True,
        verbose_name='Сообщение',
        help_text='Дополнительное сообщение для приглашённого'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата отправки'
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата ответа'
    )

    class Meta:
        verbose_name = 'Приглашение в бронирование'
        verbose_name_plural = 'Приглашения в бронирования'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invitee', 'status']),
            models.Index(fields=['booking', 'status']),
            models.Index(fields=['invitee_phone']),
            # Новый индекс для оптимизации
            models.Index(fields=['inviter', 'created_at']),  # Поиск отправленных приглашений
        ]
        # Нельзя приглашать одного и того же человека дважды в одно бронирование
        unique_together = [('booking', 'invitee_phone')]

    def __str__(self):
        inviter_name = f"{self.inviter.first_name} {self.inviter.last_name}".strip() or self.inviter.username
        return f"{inviter_name} → {self.invitee_phone} ({self.get_status_display()})"

    def accept(self):
        """Принять приглашение"""
        if self.status != 'pending':
            return False, "Приглашение уже обработано"

        if not self.invitee:
            return False, "Пользователь не найден"

        # Проверяем, можно ли присоединиться (пропускаем проверку рейтинга и поиска партнёров для приглашенных)
        can_join, message = self.booking.can_join(self.invitee, skip_rating_check=True, skip_partner_search_check=True)
        if not can_join:
            return False, message

        # Добавляем пользователя в партнёры вручную (т.к. add_partner снова вызовет can_join)
        if self.invitee not in self.booking.partners.all():
            self.booking.partners.add(self.invitee)

        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save()
        return True, "Приглашение принято"

    def decline(self):
        """Отклонить приглашение"""
        if self.status != 'pending':
            return False, "Приглашение уже обработано"

        self.status = 'declined'
        self.responded_at = timezone.now()
        self.save()
        return True, "Приглашение отклонено"

    def cancel(self):
        """Отменить приглашение (со стороны отправителя)"""
        if self.status != 'pending':
            return False, "Приглашение уже обработано"

        self.status = 'cancelled'
        self.save()
        return True, "Приглашение отменено"


class GameParticipant(models.Model):
    """Участник социальной игры (Americano/Mexicano)"""

    STATUS_CHOICES = [
        ('invited', 'Приглашен'),
        ('accepted', 'Принял'),
        ('declined', 'Отклонил'),
        ('joined', 'Присоединился'),
        ('left', 'Покинул'),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='game_participants',
        verbose_name='Бронирование'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='game_participations',
        verbose_name='Участник'
    )
    position = models.IntegerField(
        verbose_name='Позиция',
        help_text='Порядковый номер участника (1-4)'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='invited',
        db_index=True,
        verbose_name='Статус'
    )
    total_points = models.IntegerField(
        default=0,
        verbose_name='Всего очков',
        help_text='Сумма очков за все раунды'
    )
    rating_before = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        verbose_name='Рейтинг до игры',
        help_text='Рейтинг игрока перед началом игры'
    )
    rating_change = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        verbose_name='Изменение рейтинга',
        help_text='Изменение рейтинга после игры (может быть отрицательным)'
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Присоединился'
    )

    class Meta:
        verbose_name = 'Участник игры'
        verbose_name_plural = 'Участники игр'
        ordering = ['position']
        unique_together = [('booking', 'user'), ('booking', 'position')]
        indexes = [
            models.Index(fields=['booking', 'status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        display_name = full_name if full_name else self.user.username
        return f"{display_name} - Поз. {self.position} ({self.get_status_display()})"


class GameRound(models.Model):
    """Раунд социальной игры"""

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='game_rounds',
        verbose_name='Бронирование'
    )
    round_number = models.IntegerField(
        verbose_name='Номер раунда',
        help_text='Номер раунда (1, 2, 3, ...)'
    )
    match_number = models.IntegerField(
        default=1,
        verbose_name='Номер матча в раунде',
        help_text='Порядковый номер матча внутри раунда (для Mexicano с несколькими кортами)'
    )
    team1_player1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rounds_as_team1_player1',
        verbose_name='Команда 1 - Игрок 1'
    )
    team1_player2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rounds_as_team1_player2',
        verbose_name='Команда 1 - Игрок 2'
    )
    team2_player1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rounds_as_team2_player1',
        verbose_name='Команда 2 - Игрок 1'
    )
    team2_player2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rounds_as_team2_player2',
        verbose_name='Команда 2 - Игрок 2'
    )
    team1_score = models.IntegerField(
        default=0,
        verbose_name='Счет команды 1'
    )
    team2_score = models.IntegerField(
        default=0,
        verbose_name='Счет команды 2'
    )
    is_completed = models.BooleanField(
        default=False,
        verbose_name='Завершен'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время завершения'
    )

    class Meta:
        verbose_name = 'Раунд игры'
        verbose_name_plural = 'Раунды игр'
        ordering = ['round_number']
        unique_together = [('booking', 'round_number', 'match_number')]
        indexes = [
            models.Index(fields=['booking', 'round_number']),
            models.Index(fields=['booking', 'is_completed']),
        ]

    def __str__(self):
        return f"Раунд {self.round_number} - {self.booking}"

    def get_player_points(self, user):
        """Получить очки игрока в этом раунде"""
        if user in [self.team1_player1, self.team1_player2]:
            return self.team1_score
        elif user in [self.team2_player1, self.team2_player2]:
            return self.team2_score
        return 0


class WaitingList(models.Model):
    """Лист ожидания для присоединения к игре"""

    STATUS_CHOICES = [
        ('pending', 'Ожидает рассмотрения'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
        ('cancelled', 'Отменено'),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='waiting_list',
        verbose_name='Бронирование'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='waiting_list_entries',
        verbose_name='Пользователь'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name='Статус'
    )
    message = models.TextField(
        blank=True,
        verbose_name='Сообщение',
        help_text='Сообщение от игрока при запросе на присоединение'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата запроса'
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата ответа'
    )
    responded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='waiting_list_responses',
        verbose_name='Кто ответил'
    )

    class Meta:
        verbose_name = 'Запрос на присоединение'
        verbose_name_plural = 'Запросы на присоединение'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['booking', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
        # Один пользователь не может подать запрос дважды на одно бронирование
        unique_together = [('booking', 'user')]

    def __str__(self):
        user_name = f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
        return f"{user_name} → {self.booking} ({self.get_status_display()})"

    def approve(self, approved_by=None):
        """Одобрить запрос и добавить пользователя в игру"""
        if self.status != 'pending':
            return False, "Запрос уже обработан"

        booking = self.booking

        # Для социальных игр используем GameParticipant
        if booking.game_mode in ['americano', 'mexicano']:
            current_accepted = booking.game_participants.filter(status='accepted').count()
            if current_accepted >= 4:
                return False, "Нет свободных мест (максимум 4 участника)"

            # Проверяем, не является ли пользователь уже участником
            if booking.game_participants.filter(user=self.user).exists():
                return False, "Пользователь уже является участником"

            try:
                rating_before = self.user.rating.numeric_rating
            except Exception:
                rating_before = 1.00

            GameParticipant.objects.create(
                booking=booking,
                user=self.user,
                position=current_accepted + 1,
                status='accepted',
                rating_before=rating_before
            )

            # Проверяем, не пора ли менять статус игры
            if current_accepted + 1 >= 4:
                booking.game_status = 'ready'
                booking.save()
        else:
            # Для обычных игр используем старую систему партнёров
            if self.booking.is_full:
                return False, "Нет свободных мест"
            self.booking.partners.add(self.user)

        # Обновляем статус запроса
        self.status = 'approved'
        self.responded_at = timezone.now()
        self.responded_by = approved_by
        self.save()

        return True, "Запрос одобрен, игрок добавлен в игру"

    def reject(self, rejected_by=None, reason=''):
        """Отклонить запрос"""
        if self.status != 'pending':
            return False, "Запрос уже обработан"

        self.status = 'rejected'
        self.responded_at = timezone.now()
        self.responded_by = rejected_by
        if reason:
            self.message = f"{self.message}\n[Причина отклонения: {reason}]" if self.message else f"[Причина отклонения: {reason}]"
        self.save()

        return True, "Запрос отклонён"


class GameChat(models.Model):
    """Чат для игры"""

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name='Бронирование'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='game_messages',
        verbose_name='Пользователь'
    )
    message = models.TextField(
        verbose_name='Сообщение'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата отправки',
        db_index=True
    )
    is_system_message = models.BooleanField(
        default=False,
        verbose_name='Системное сообщение',
        help_text='Автоматическое сообщение от системы (например, "Игрок присоединился")'
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='Прочитано',
        help_text='Помечено как прочитанное всеми участниками'
    )

    class Meta:
        verbose_name = 'Сообщение в чате'
        verbose_name_plural = 'Сообщения в чате'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['booking', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['booking', 'is_read']),
        ]

    def __str__(self):
        user_name = f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
        return f"{user_name}: {self.message[:50]}..."

    @classmethod
    def send_system_message(cls, booking, message):
        """Отправить системное сообщение в чат игры"""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Используем первого пользователя (админа) или создателя бронирования
        system_user = booking.user

        return cls.objects.create(
            booking=booking,
            user=system_user,
            message=message,
            is_system_message=True
        )


@receiver(pre_save, sender=BookingInvitation)
def set_invitee_by_phone(sender, instance, **kwargs):
    """Автоматически определяет приглашённого пользователя по номеру телефона"""
    if instance.invitee_phone and not instance.invitee:
        from users.models import UserProfile
        # Нормализуем номер и ищем пользователя
        normalized_phone = UserProfile.objects.normalize_phone(instance.invitee_phone)
        if normalized_phone:
            user = UserProfile.objects.get_user_by_phone(normalized_phone)
            if user:
                instance.invitee = user
                instance.invitee_phone = normalized_phone