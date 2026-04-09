"""
Новые модели для РЕАЛЬНОГО паддл-турнира
Поддержка форматов: Americano, Mexicano, Doubles Bracket

ВАЖНО: Паддл = ПАРНЫЙ спорт (2v2)
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from booking.models import Court
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Tournament(models.Model):
    """Турнир по паддлу"""

    FORMAT_CHOICES = [
        # Round-robin формат (индивидуальный зачет, пары меняются)
        ('americano', 'Round-Robin - Каждый с каждым, пары постоянно меняются'),
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
        validators=[MinValueValidator(4), MaxValueValidator(128)],
        verbose_name='Макс. участников',
        help_text='Для Americano лучше кратно 4'
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

    # НОВОЕ: Формат турнира
    format = models.CharField(
        max_length=30,
        choices=FORMAT_CHOICES,
        default='americano',
        verbose_name='Формат турнира'
    )

    # НОВОЕ: Тип турнира
    is_team_tournament = models.BooleanField(
        default=False,
        verbose_name='Командный турнир',
        help_text='True = постоянные пары, False = индивидуальный зачет с ротацией'
    )

    # НОВОЕ: Для Mixed форматов
    is_mixed = models.BooleanField(
        default=False,
        verbose_name='Смешанный формат',
        help_text='True = обязательно мужчина+женщина в паре'
    )

    # НОВОЕ: Настройки для Americano/Mexicano
    points_per_match = models.IntegerField(
        default=24,
        choices=[
            (16, '16 очков за матч'),
            (20, '20 очков за матч'),
            (24, '24 очка за матч'),
            (32, '32 очка за матч'),
        ],
        verbose_name='Очков за матч',
        help_text='До скольки очков играется матч (для Americano/Mexicano)'
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
            models.Index(fields=['format']),
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

    @property
    def requires_partner(self):
        """Требуется ли указание партнера при регистрации"""
        return self.is_team_tournament

    def can_register(self, user, partner=None):
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

        # Для командных турниров проверяем партнера
        if self.is_team_tournament and not partner:
            return False, "Необходимо указать партнера"

        if self.is_team_tournament and partner == user:
            return False, "Нельзя быть партнером самому себе"

        # Проверяем рейтинг
        if hasattr(user, 'rating'):
            user_rating = float(user.rating.numeric_rating)
            if self.min_rating and user_rating < float(self.min_rating):
                return False, f"Минимальный рейтинг: {self.min_rating}"
            if self.max_rating and user_rating > float(self.max_rating):
                return False, f"Максимальный рейтинг: {self.max_rating}"

        # Для mixed проверяем пол
        if self.is_mixed and self.is_team_tournament and partner:
            user_gender = getattr(user.profile, 'gender', None)
            partner_gender = getattr(partner.profile, 'gender', None)
            if user_gender and partner_gender and user_gender == partner_gender:
                return False, "Для mixed формата нужна пара мужчина+женщина"

        return True, "OK"


class PadelTeam(models.Model):
    """
    Пара игроков в паддле (всегда 2 человека)

    Может быть:
    - Постоянной (для Team форматов и Bracket)
    - Временной (для Americano/Mexicano - создается на 1 раунд)
    """

    # Связь с турниром
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='teams',
        verbose_name='Турнир'
    )

    # Игроки (всегда ровно 2)
    player1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='padel_teams_as_p1',
        verbose_name='Игрок 1'
    )
    player2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='padel_teams_as_p2',
        verbose_name='Игрок 2'
    )

    # Название пары (опционально для постоянных команд)
    name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Название пары',
        help_text='Например: "Los Campeones" (для постоянных пар)'
    )

    # Для генерации сетки (Bracket форматы)
    seed = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Посев'
    )

    # НОВОЕ: Тип пары
    is_temporary = models.BooleanField(
        default=False,
        verbose_name='Временная пара',
        help_text='True для Americano/Mexicano (пара на 1 раунд)'
    )

    # НОВОЕ: Раунд для временной пары
    round_number = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Номер раунда',
        help_text='В каком раунде эта временная пара играет'
    )

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Padel пара'
        verbose_name_plural = 'Padel пары'
        ordering = ['tournament', 'seed', 'created_at']
        indexes = [
            models.Index(fields=['tournament', 'is_temporary']),
            models.Index(fields=['tournament', 'round_number']),
        ]

    def __str__(self):
        if self.name:
            return f"{self.name}"
        return f"{self.player1.get_full_name()} + {self.player2.get_full_name()}"

    @property
    def players(self):
        """Список игроков в паре"""
        return [self.player1, self.player2]

    @property
    def display_name(self):
        """Отображаемое название"""
        if self.name:
            return f"{self.name} ({self.player1.get_full_name()} / {self.player2.get_full_name()})"
        return f"{self.player1.get_full_name()} / {self.player2.get_full_name()}"


class TournamentParticipant(models.Model):
    """
    Участник турнира

    Для Americano/Mexicano - индивидуальный игрок (партнеры меняются)
    Для Team форматов - представитель пары
    """

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

    # НОВОЕ: Партнер для постоянной пары (Team форматы)
    partner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partner_in_tournaments',
        verbose_name='Постоянный партнер',
        help_text='Используется для Team форматов'
    )

    # НОВОЕ: Название пары
    team_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Название пары',
        help_text='Для Team форматов'
    )

    # НОВОЕ: Индивидуальные очки (для Americano/Mexicano)
    total_points = models.IntegerField(
        default=0,
        verbose_name='Всего очков',
        help_text='Сумма очков за все раунды (для Americano/Mexicano)'
    )

    # НОВОЕ: Статистика (для Americano/Mexicano)
    matches_played = models.IntegerField(
        default=0,
        verbose_name='Матчей сыграно'
    )
    matches_won = models.IntegerField(
        default=0,
        verbose_name='Матчей выиграно'
    )
    matches_lost = models.IntegerField(
        default=0,
        verbose_name='Матчей проиграно'
    )

    # НОВОЕ: Текущая позиция в рейтинге (для Mexicano)
    current_rank = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Текущая позиция',
        help_text='Позиция после последнего раунда (для Mexicano)'
    )

    # Посев (для Bracket форматов с постоянными парами)
    seed = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Посев пары',
        help_text='Номер посева для пары (1 - сильнейшая)'
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

    # Результат (для всех форматов)
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
        ordering = ['-total_points', '-matches_won', 'registered_at']
        indexes = [
            models.Index(fields=['tournament', 'payment_status']),
            models.Index(fields=['tournament', '-total_points']),
            models.Index(fields=['tournament', 'current_rank']),
        ]

    def __str__(self):
        if self.partner:
            return f"{self.user.get_full_name()} + {self.partner.get_full_name()} - {self.tournament.name}"
        return f"{self.user.get_full_name()} - {self.tournament.name}"

    def mark_as_paid(self):
        """Отметить как оплаченный"""
        self.payment_status = 'paid'
        self.payment_date = timezone.now()
        self.save()

    @property
    def win_rate(self):
        """Процент побед"""
        if self.matches_played == 0:
            return 0
        return round((self.matches_won / self.matches_played) * 100, 1)

    @property
    def average_points_per_match(self):
        """Среднее количество очков за матч"""
        if self.matches_played == 0:
            return 0
        return round(self.total_points / self.matches_played, 1)


class TournamentMatch(models.Model):
    """
    Матч в паддл-турнире (всегда 2v2 - пара против пары)
    """

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

    # ГЛАВНОЕ ИЗМЕНЕНИЕ: Пары вместо индивидуальных игроков
    team1 = models.ForeignKey(
        PadelTeam,
        on_delete=models.CASCADE,
        related_name='matches_as_team1',
        null=True,
        blank=True,
        verbose_name='Пара 1'
    )
    team2 = models.ForeignKey(
        PadelTeam,
        on_delete=models.CASCADE,
        related_name='matches_as_team2',
        null=True,
        blank=True,
        verbose_name='Пара 2'
    )

    # Победитель - тоже пара
    winning_team = models.ForeignKey(
        PadelTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='won_matches',
        verbose_name='Победившая пара'
    )

    # НОВОЕ: Счет в формате паддл (просто очки)
    score_team1 = models.IntegerField(
        default=0,
        verbose_name='Очки пары 1'
    )
    score_team2 = models.IntegerField(
        default=0,
        verbose_name='Очки пары 2'
    )

    # Детальный счет (опционально, для сетов/геймов)
    detailed_score = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Детальный счет',
        help_text='{"sets": [{"team1": 6, "team2": 4}]} - если играли по сетам'
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

    # Следующий матч (для Bracket форматов)
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
        t1_name = self.team1.display_name if self.team1 else 'TBD'
        t2_name = self.team2.display_name if self.team2 else 'TBD'
        return f"Раунд {self.round}, Матч {self.match_number}: {t1_name} vs {t2_name}"

    def set_score(self, team1_score, team2_score, detailed_score=None):
        """
        Установить счет и определить победителя

        Args:
            team1_score: Очки первой пары
            team2_score: Очки второй пары
            detailed_score: Детальный счет (опционально)
        """
        self.score_team1 = team1_score
        self.score_team2 = team2_score

        if detailed_score:
            self.detailed_score = detailed_score

        # Определяем победителя
        if team1_score > team2_score:
            self.winning_team = self.team1
        elif team2_score > team1_score:
            self.winning_team = self.team2
        # Если равный счет - ничья (rare in padel)

        self.status = 'completed'
        self.save()

        # Обновляем статистику участников (для Americano/Mexicano)
        if self.tournament.format in ['americano', 'mexicano', 'mixed_americano']:
            self._update_individual_stats()

        # Продвигаем победителя в следующий раунд (для Bracket)
        if self.tournament.format in ['doubles_elimination', 'doubles_round_robin']:
            self._advance_winner_to_next_round()

    def _update_individual_stats(self):
        """Обновить индивидуальную статистику игроков (для Americano)"""
        if not self.team1 or not self.team2:
            return

        # Пара 1: оба игрока получают одинаковые очки
        for player in self.team1.players:
            try:
                participant = TournamentParticipant.objects.get(
                    tournament=self.tournament,
                    user=player
                )
                participant.total_points += self.score_team1
                participant.matches_played += 1

                if self.winning_team == self.team1:
                    participant.matches_won += 1
                else:
                    participant.matches_lost += 1

                participant.save()
            except TournamentParticipant.DoesNotExist:
                # Игрок не является участником турнира - пропускаем
                logger.warning(f"Player {player.username} is not a participant of tournament {self.tournament.id}")

        # Пара 2: оба игрока получают одинаковые очки
        for player in self.team2.players:
            try:
                participant = TournamentParticipant.objects.get(
                    tournament=self.tournament,
                    user=player
                )
                participant.total_points += self.score_team2
                participant.matches_played += 1

                if self.winning_team == self.team2:
                    participant.matches_won += 1
                else:
                    participant.matches_lost += 1

                participant.save()
            except TournamentParticipant.DoesNotExist:
                # Игрок не является участником турнира - пропускаем
                logger.warning(f"Player {player.username} is not a participant of tournament {self.tournament.id}")

    def _advance_winner_to_next_round(self):
        """Продвинуть победителя в следующий раунд (для Bracket)"""
        if not self.winning_team or not self.next_match:
            return

        # Определяем позицию в следующем матче
        if self.match_number % 2 == 1:  # Нечетный матч -> team1
            self.next_match.team1 = self.winning_team
        else:  # Четный матч -> team2
            self.next_match.team2 = self.winning_team

        self.next_match.save()

    @property
    def is_ready_to_play(self):
        """Готов ли матч к игре (обе пары определены)"""
        return self.team1 is not None and self.team2 is not None

    @property
    def score_display(self):
        """Отображение счета"""
        if self.status == 'completed':
            return f"{self.score_team1} - {self.score_team2}"
        return "vs"


class TournamentRound(models.Model):
    """Раунд турнира"""

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
        help_text='Раунд 1, 1/4 финала, Полуфинал, Финал и т.д.'
    )

    # Расписание раунда
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата начала раунда'
    )

    # Статус раунда
    is_completed = models.BooleanField(
        default=False,
        verbose_name='Раунд завершен'
    )

    class Meta:
        verbose_name = 'Раунд турнира'
        verbose_name_plural = 'Раунды турнира'
        unique_together = ['tournament', 'round_number']
        ordering = ['round_number']

    def __str__(self):
        return f"{self.tournament.name} - {self.name}"

    @property
    def matches_count(self):
        """Количество матчей в раунде"""
        return self.tournament.matches.filter(round=self.round_number).count()

    @property
    def completed_matches_count(self):
        """Количество завершенных матчей"""
        return self.tournament.matches.filter(
            round=self.round_number,
            status='completed'
        ).count()

    @property
    def completion_percentage(self):
        """Процент завершения раунда"""
        if self.matches_count == 0:
            return 0
        return round((self.completed_matches_count / self.matches_count) * 100, 1)
