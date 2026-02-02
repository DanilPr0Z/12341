from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from booking.models import Court
import math


class Tournament(models.Model):
    """Турнир по паддлу"""

    FORMAT_CHOICES = [
        ('single_elimination', 'Олимпийская система'),
        ('double_elimination', 'Двойная олимпийская'),
        ('round_robin', 'Круговая система'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('registration_open', 'Регистрация открыта'),
        ('registration_closed', 'Регистрация закрыта'),
        ('in_progress', 'Идет турнир'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    # Основная информация
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')

    # Организатор
    organizer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='organized_tournaments',
        verbose_name='Организатор'
    )

    # Даты
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')
    registration_deadline = models.DateTimeField(verbose_name='Дедлайн регистрации')

    # Настройки
    max_participants = models.IntegerField(
        validators=[MinValueValidator(2), MaxValueValidator(128)],
        verbose_name='Макс. участников'
    )
    entry_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Взнос за участие'
    )
    prize_pool = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Призовой фонд'
    )

    # Формат
    format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        default='single_elimination',
        verbose_name='Формат турнира'
    )

    # Ограничения по рейтингу
    min_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(1.0), MaxValueValidator(7.0)],
        verbose_name='Минимальный рейтинг'
    )
    max_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(1.0), MaxValueValidator(7.0)],
        verbose_name='Максимальный рейтинг'
    )

    # Статус
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        verbose_name='Статус'
    )

    # Изображение
    image = models.ImageField(
        upload_to='tournaments/',
        null=True,
        blank=True,
        verbose_name='Постер турнира'
    )

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Турнир'
        verbose_name_plural = 'Турниры'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['registration_deadline']),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_date})"

    @property
    def is_registration_open(self):
        """Открыта ли регистрация"""
        return (
            self.status == 'registration_open' and
            timezone.now() <= self.registration_deadline
        )

    @property
    def participants_count(self):
        """Количество участников"""
        return self.participants.filter(payment_status='paid').count()

    @property
    def available_slots(self):
        """Свободные места"""
        return max(0, self.max_participants - self.participants_count)

    @property
    def is_full(self):
        """Заполнен ли турнир"""
        return self.available_slots == 0

    def can_register(self, user):
        """Может ли пользователь зарегистрироваться"""
        # Проверяем регистрацию
        if not self.is_registration_open:
            return False, "Регистрация закрыта"

        # Проверяем наличие мест
        if self.is_full:
            return False, "Нет свободных мест"

        # Проверяем, не зарегистрирован ли уже
        if self.participants.filter(user=user).exists():
            return False, "Вы уже зарегистрированы"

        # Проверяем рейтинг
        if hasattr(user, 'rating'):
            user_rating = float(user.rating.numeric_rating)
            if self.min_rating and user_rating < float(self.min_rating):
                return False, f"Минимальный рейтинг: {self.min_rating}"
            if self.max_rating and user_rating > float(self.max_rating):
                return False, f"Максимальный рейтинг: {self.max_rating}"

        return True, "OK"


class TournamentParticipant(models.Model):
    """Участник турнира"""

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачено'),
        ('refunded', 'Возвращено'),
    ]

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name='Турнир'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tournament_participations',
        verbose_name='Участник'
    )

    # Посев (для генерации сетки)
    seed = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Посев',
        help_text='Номер посева (1 - сильнейший)'
    )

    # Оплата
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name='Статус оплаты'
    )
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата оплаты'
    )

    # Результат
    final_position = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Итоговое место'
    )

    # Метаданные
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Участник турнира'
        verbose_name_plural = 'Участники турнира'
        unique_together = ['tournament', 'user']
        ordering = ['seed', 'registered_at']
        indexes = [
            models.Index(fields=['tournament', 'payment_status']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.tournament.name}"

    def mark_as_paid(self):
        """Отметить как оплаченный"""
        self.payment_status = 'paid'
        self.payment_date = timezone.now()
        self.save()


class TournamentMatch(models.Model):
    """Матч в турнире"""

    STATUS_CHOICES = [
        ('scheduled', 'Запланирован'),
        ('in_progress', 'Идет'),
        ('completed', 'Завершен'),
        ('walkover', 'Walkover'),
        ('cancelled', 'Отменен'),
    ]

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name='Турнир'
    )

    # Раунд и номер матча
    round = models.IntegerField(verbose_name='Раунд')
    match_number = models.IntegerField(verbose_name='Номер матча')

    # Игроки
    player1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tournament_matches_as_p1',
        null=True,
        blank=True,
        verbose_name='Игрок 1'
    )
    player2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tournament_matches_as_p2',
        null=True,
        blank=True,
        verbose_name='Игрок 2'
    )

    # Результат
    winner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournament_won_matches',
        verbose_name='Победитель'
    )
    score = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Счет',
        help_text='{"sets": ["6-4", "7-5"], "games": "13-9"}'
    )

    # Расписание
    scheduled_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата матча'
    )
    scheduled_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Время матча'
    )
    court = models.ForeignKey(
        Court,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Корт'
    )

    # Статус
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        db_index=True,
        verbose_name='Статус'
    )

    # Следующий матч (для олимпийской системы)
    next_match = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_matches',
        verbose_name='Следующий матч'
    )

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Матч турнира'
        verbose_name_plural = 'Матчи турнира'
        ordering = ['round', 'match_number']
        indexes = [
            models.Index(fields=['tournament', 'round']),
            models.Index(fields=['status', 'scheduled_date']),
        ]

    def __str__(self):
        p1_name = self.player1.get_full_name() if self.player1 else 'TBD'
        p2_name = self.player2.get_full_name() if self.player2 else 'TBD'
        return f"Раунд {self.round}, Матч {self.match_number}: {p1_name} vs {p2_name}"

    def set_winner(self, winner, score):
        """Установить победителя"""
        if winner not in [self.player1, self.player2]:
            raise ValueError("Победитель должен быть одним из игроков")

        self.winner = winner
        self.score = score
        self.status = 'completed'
        self.save()

        # Продвигаем победителя в следующий раунд
        if self.next_match:
            if self.match_number % 2 == 1:  # Нечетный матч -> первый игрок
                self.next_match.player1 = winner
            else:  # Четный матч -> второй игрок
                self.next_match.player2 = winner
            self.next_match.save()

    @property
    def is_ready_to_play(self):
        """Готов ли матч к игре (оба игрока определены)"""
        return self.player1 is not None and self.player2 is not None


class TournamentRound(models.Model):
    """Раунд турнира (для удобства)"""

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='rounds',
        verbose_name='Турнир'
    )
    round_number = models.IntegerField(verbose_name='Номер раунда')
    name = models.CharField(
        max_length=100,
        verbose_name='Название раунда',
        help_text='Например: 1/8 финала, 1/4 финала, Полуфинал, Финал'
    )

    # Расписание раунда
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата начала раунда'
    )

    class Meta:
        verbose_name = 'Раунд турнира'
        verbose_name_plural = 'Раунды турнира'
        unique_together = ['tournament', 'round_number']
        ordering = ['round_number']

    def __str__(self):
        return f"{self.tournament.name} - {self.name}"
