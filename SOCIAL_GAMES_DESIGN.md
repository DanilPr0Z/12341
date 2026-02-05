# 🎾 Социальные игры - Americano/Mexicano для обычных бронирований

**Дата:** 2026-02-05
**Версия:** 2.0 - Social Games System

---

## 📋 Концепция

Добавить режимы игры Americano/Mexicano для обычных бронирований:
- Игра на 4 человека
- Смена партнеров между раундами
- Подсчет индивидуальных очков
- Изменение рейтинга на основе результатов
- Публичная вкладка "Игры" для поиска игроков
- Система приглашений

---

## 🗄️ Модель данных

### 1. Расширение модели Booking

```python
class Booking(models.Model):
    # ... существующие поля ...

    # НОВОЕ: Режим игры
    GAME_MODE_CHOICES = [
        ('regular', 'Обычная игра'),
        ('americano', 'Americano - Меняющиеся пары'),
        ('mexicano', 'Mexicano - Пары по рейтингу'),
        ('training', 'Тренировка'),
    ]

    game_mode = models.CharField(
        max_length=20,
        choices=GAME_MODE_CHOICES,
        default='regular',
        verbose_name='Режим игры'
    )

    # НОВОЕ: Публичная игра (можно присоединиться)
    is_public = models.BooleanField(
        default=False,
        verbose_name='Публичная игра',
        help_text='Другие игроки могут присоединиться'
    )

    # НОВОЕ: Минимальный/максимальный рейтинг для публичной игры
    min_rating_required = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Мин. рейтинг'
    )
    max_rating_required = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Макс. рейтинг'
    )

    # НОВОЕ: Количество раундов (для Americano/Mexicano)
    rounds_count = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name='Количество раундов'
    )

    # НОВОЕ: Очков за раунд
    points_per_round = models.IntegerField(
        default=24,
        choices=[(16, '16'), (20, '20'), (24, '24'), (32, '32')],
        verbose_name='Очков за раунд'
    )

    # НОВОЕ: Статус игры
    game_status = models.CharField(
        max_length=20,
        choices=[
            ('waiting', 'Ожидание игроков'),
            ('ready', 'Готово к началу'),
            ('in_progress', 'Идет игра'),
            ('scoring', 'Ввод результатов'),
            ('completed', 'Завершено'),
        ],
        default='waiting',
        verbose_name='Статус игры'
    )

    # НОВОЕ: Текущий раунд
    current_round = models.IntegerField(default=0, verbose_name='Текущий раунд')

    class Meta:
        # ... существующие meta ...
        indexes = [
            # ... существующие индексы ...
            models.Index(fields=['is_public', 'game_status', 'date']),
            models.Index(fields=['game_mode', 'date']),
        ]

    def get_participants_count(self):
        """Количество подтвержденных участников"""
        count = 1  # Создатель
        count += self.participants.filter(status='accepted').count()
        return count

    def is_full(self):
        """Игра заполнена (4 игрока)"""
        return self.get_participants_count() >= 4

    def can_start(self):
        """Можно ли начать игру"""
        return self.is_full() and self.game_status == 'ready'
```

### 2. Модель для участников игры

```python
class GameParticipant(models.Model):
    """
    Участник социальной игры (Americano/Mexicano)
    Расширяет существующую модель BookingInvitation
    """

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
        verbose_name='Игрок'
    )

    # Позиция в игре (1-4)
    position = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        verbose_name='Позиция'
    )

    # Статус участия
    STATUS_CHOICES = [
        ('pending', 'Ожидание ответа'),
        ('accepted', 'Принято'),
        ('declined', 'Отклонено'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )

    # Индивидуальная статистика
    total_points = models.IntegerField(default=0, verbose_name='Всего очков')
    rounds_played = models.IntegerField(default=0, verbose_name='Сыграно раундов')
    rounds_won = models.IntegerField(default=0, verbose_name='Выиграно раундов')

    # Рейтинг до игры
    rating_before = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Рейтинг до'
    )

    # Изменение рейтинга после игры
    rating_change = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        verbose_name='Изменение рейтинга'
    )

    # Метаданные
    invited_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Участник игры'
        verbose_name_plural = 'Участники игры'
        unique_together = ['booking', 'user']
        ordering = ['position']

    def __str__(self):
        return f"{self.user.get_full_name()} - Позиция {self.position}"

    @property
    def final_rank(self):
        """Финальное место в игре"""
        if self.booking.game_status != 'completed':
            return None

        # Сортируем по очкам
        participants = self.booking.game_participants.all().order_by('-total_points')
        for rank, p in enumerate(participants, start=1):
            if p.id == self.id:
                return rank
        return None
```

### 3. Модель для раундов игры

```python
class GameRound(models.Model):
    """Раунд в социальной игре"""

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='game_rounds',
        verbose_name='Игра'
    )

    round_number = models.IntegerField(verbose_name='Номер раунда')

    # Пары в этом раунде
    team1_player1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rounds_team1_p1',
        verbose_name='Пара 1 - Игрок 1'
    )
    team1_player2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rounds_team1_p2',
        verbose_name='Пара 1 - Игрок 2'
    )
    team2_player1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rounds_team2_p1',
        verbose_name='Пара 2 - Игрок 1'
    )
    team2_player2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rounds_team2_p2',
        verbose_name='Пара 2 - Игрок 2'
    )

    # Счет
    team1_score = models.IntegerField(default=0, verbose_name='Счет пары 1')
    team2_score = models.IntegerField(default=0, verbose_name='Счет пары 2')

    # Статус раунда
    STATUS_CHOICES = [
        ('pending', 'Ожидание'),
        ('in_progress', 'Идет'),
        ('scoring', 'Ввод счета'),
        ('completed', 'Завершен'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )

    # Кто ввел счет (для верификации)
    score_entered_by = models.ManyToManyField(
        User,
        related_name='entered_scores',
        blank=True,
        verbose_name='Счет подтвержден'
    )

    # Метаданные
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Раунд игры'
        verbose_name_plural = 'Раунды игры'
        unique_together = ['booking', 'round_number']
        ordering = ['round_number']

    def __str__(self):
        return f"Раунд {self.round_number} - {self.booking}"

    @property
    def team1_players(self):
        return [self.team1_player1, self.team1_player2]

    @property
    def team2_players(self):
        return [self.team2_player1, self.team2_player2]

    def is_score_verified(self):
        """Счет подтвержден минимум 3 игроками"""
        return self.score_entered_by.count() >= 3
```

---

## 🎨 UI Дизайн

### 1. Новая вкладка "Игры" (как на скриншоте)

```html
<!-- templates/games.html -->
{% extends 'base.html' %}

{% block content %}
<div class="games-page">
    <!-- Баннер -->
    <div class="games-banner">
        <div class="tennis-balls"></div>
        <h1>Выставьте результаты своей недавней игры!</h1>
    </div>

    <!-- Приглашения -->
    <div class="section-header">
        <h2>Приглашения <span class="badge">{{ pending_invitations_count }}</span></h2>
        <a href="{% url 'games_all_invitations' %}">Все →</a>
    </div>

    {% for invitation in pending_invitations %}
    <div class="game-card invitation-card">
        <div class="game-header">
            <h3>Вас пригласили на матч!</h3>
        </div>

        <div class="game-info">
            <div class="info-item">
                <i class="fas fa-clock"></i>
                {{ invitation.booking.date|date:"d E" }} | {{ invitation.booking.time }}
            </div>
            <div class="info-item">
                <i class="fas fa-map-marker-alt"></i>
                {{ invitation.booking.court.club.name }} | {{ invitation.booking.court.club.address }}
            </div>
            <div class="info-item">
                <i class="fas fa-gamepad"></i>
                {{ invitation.booking.get_game_mode_display }}
            </div>
            {% if invitation.booking.min_rating_required %}
            <div class="info-item">
                <i class="fas fa-star"></i>
                Рейтинг: {{ invitation.booking.min_rating_required }} - {{ invitation.booking.max_rating_required }}
            </div>
            {% endif %}
        </div>

        <!-- Участники -->
        <div class="participants">
            {% for participant in invitation.booking.get_all_participants %}
            <div class="participant {% if participant.user == user %}current-user{% endif %}">
                <div class="participant-avatar">
                    {% if participant.user.profile.avatar %}
                    <img src="{{ participant.user.profile.avatar.url }}" alt="{{ participant.user.get_full_name }}">
                    {% else %}
                    <div class="avatar-placeholder">{{ participant.user.first_name.0 }}{{ participant.user.last_name.0 }}</div>
                    {% endif %}
                    {% if participant.user.rating %}
                    <div class="rating-badge">{{ participant.user.rating.numeric_rating }}</div>
                    {% endif %}
                </div>
                <div class="participant-name">
                    {% if participant.user == user %}
                    Справа<br>Вы
                    {% else %}
                    {{ participant.user.get_full_name }}
                    {% endif %}
                </div>
            </div>
            {% endfor %}

            <!-- Пустые слоты -->
            {% for i in invitation.booking.get_empty_slots %}
            <div class="participant empty-slot">
                <button class="add-participant-btn" onclick="showInviteModal({{ invitation.booking.id }})">
                    <i class="fas fa-plus"></i>
                </button>
                <div class="participant-name">Пригласить</div>
            </div>
            {% endfor %}
        </div>

        <!-- Действия -->
        <div class="game-actions">
            <button class="btn btn-primary btn-accept" onclick="acceptInvitation({{ invitation.id }})">
                Принять
            </button>
            <button class="btn btn-secondary btn-decline" onclick="declineInvitation({{ invitation.id }})">
                Отклонить
            </button>
        </div>
    </div>
    {% endfor %}

    <!-- Мои игры -->
    <div class="section-header">
        <h2>Мои игры <span class="badge">{{ my_games_count }}</span></h2>
        <a href="{% url 'games_my_games' %}">Все →</a>
    </div>

    {% for game in my_games %}
    <div class="game-card my-game-card">
        <div class="game-info">
            <div class="info-item">
                <i class="fas fa-clock"></i>
                {{ game.date|date:"d E" }} | {{ game.time }}
            </div>
            <div class="info-item">
                <i class="fas fa-map-marker-alt"></i>
                {{ game.court.club.name }}
            </div>
            <div class="game-mode-badge">
                <i class="fas fa-gamepad"></i>
                {{ game.get_game_mode_display }}
            </div>
        </div>

        <!-- Участники -->
        <div class="participants">
            {% for participant in game.get_all_participants %}
            <div class="participant {% if participant.user == user %}current-user{% endif %}">
                <div class="participant-avatar">
                    {% if participant.user.profile.avatar %}
                    <img src="{{ participant.user.profile.avatar.url }}" alt="{{ participant.user.get_full_name }}">
                    {% else %}
                    <div class="avatar-placeholder">{{ participant.user.first_name.0 }}{{ participant.user.last_name.0 }}</div>
                    {% endif %}
                    <div class="rating-badge">{{ participant.user.rating.numeric_rating }}</div>
                </div>
                <div class="participant-name">
                    {% if participant.user == user %}Справа<br>Вы{% else %}{{ participant.user.get_full_name }}{% endif %}
                </div>
            </div>
            {% endfor %}

            <!-- Пустые слоты -->
            {% for i in game.get_empty_slots %}
            <div class="participant empty-slot">
                <button class="add-participant-btn" onclick="showInviteModal({{ game.id }})">
                    <i class="fas fa-plus"></i>
                </button>
                <div class="participant-name">Пригласить</div>
            </div>
            {% endfor %}
        </div>

        <!-- Кнопка действия -->
        {% if game.game_status == 'completed' and game.current_round < game.rounds_count %}
        <button class="btn btn-primary" onclick="enterScores({{ game.id }})">
            Ввести результаты раунда {{ game.current_round }}
        </button>
        {% elif game.game_status == 'completed' %}
        <button class="btn btn-success" onclick="viewResults({{ game.id }})">
            Посмотреть результаты
        </button>
        {% endif %}
    </div>
    {% endfor %}

    <!-- Публичные игры -->
    <div class="section-header">
        <h2>Открытые игры</h2>
        <button class="btn btn-primary" onclick="createPublicGame()">
            <i class="fas fa-plus"></i> Создать игру
        </button>
    </div>

    {% for game in public_games %}
    <div class="game-card public-game-card">
        <!-- Аналогично карточкам выше -->
    </div>
    {% endfor %}
</div>
{% endblock %}
```

### 2. CSS стили (как на скриншоте)

```css
/* games.css */

.games-page {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
    background: linear-gradient(180deg, #1a2332 0%, #0f1419 100%);
    min-height: 100vh;
}

.games-banner {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8a 100%);
    border-radius: 16px;
    padding: 30px 20px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}

.games-banner h1 {
    color: white;
    font-size: 24px;
    font-weight: 700;
    margin: 0;
    position: relative;
    z-index: 2;
}

.tennis-balls {
    position: absolute;
    right: -20px;
    top: -20px;
    width: 120px;
    height: 120px;
    background: url('/static/images/tennis-ball.png') no-repeat;
    background-size: contain;
    opacity: 0.3;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 24px 0 16px;
}

.section-header h2 {
    color: white;
    font-size: 20px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
}

.section-header .badge {
    background: #ff3b30;
    color: white;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 14px;
    font-weight: 700;
}

.section-header a {
    color: #9ef01a;
    text-decoration: none;
    font-size: 16px;
}

/* Карточка игры */
.game-card {
    background: linear-gradient(135deg, #2a3f5f 0%, #1f2f45 100%);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
    border: 2px solid transparent;
}

.invitation-card {
    border-color: #d4e815;
    background: linear-gradient(135deg, #3a4f2f 0%, #2f3f25 100%);
}

.my-game-card {
    border-color: #4a90e2;
}

.game-header h3 {
    color: #d4e815;
    font-size: 18px;
    font-weight: 700;
    margin: 0 0 16px 0;
}

.game-info {
    margin-bottom: 20px;
}

.info-item {
    color: #a8b4c8;
    font-size: 14px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.info-item i {
    color: #9ef01a;
    width: 16px;
}

/* Участники */
.participants {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    justify-content: space-between;
}

.participant {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
}

.participant-avatar {
    position: relative;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    overflow: hidden;
    border: 3px solid #9ef01a;
}

.participant.current-user .participant-avatar {
    border-color: #d4e815;
}

.participant-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.avatar-placeholder {
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 20px;
    font-weight: 700;
}

.rating-badge {
    position: absolute;
    bottom: -4px;
    left: 50%;
    transform: translateX(-50%);
    background: #9ef01a;
    color: #1a2332;
    border-radius: 10px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: 700;
}

.participant-name {
    color: #a8b4c8;
    font-size: 12px;
    text-align: center;
    line-height: 1.3;
}

.participant.current-user .participant-name {
    color: #d4e815;
}

/* Пустой слот */
.empty-slot .participant-avatar {
    border: 2px dashed rgba(158, 240, 26, 0.3);
    background: transparent;
}

.add-participant-btn {
    width: 100%;
    height: 100%;
    background: rgba(158, 240, 26, 0.1);
    border: none;
    border-radius: 50%;
    color: #9ef01a;
    font-size: 24px;
    cursor: pointer;
    transition: all 0.3s;
}

.add-participant-btn:hover {
    background: rgba(158, 240, 26, 0.2);
    transform: scale(1.05);
}

/* Действия */
.game-actions {
    display: flex;
    gap: 12px;
}

.btn-accept {
    flex: 1;
    background: #9ef01a;
    color: #1a2332;
    border: none;
    border-radius: 12px;
    padding: 14px 20px;
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.3s;
}

.btn-accept:hover {
    background: #b5ff35;
    transform: translateY(-2px);
}

.btn-decline {
    flex: 1;
    background: transparent;
    color: #a8b4c8;
    border: 2px solid rgba(168, 180, 200, 0.3);
    border-radius: 12px;
    padding: 14px 20px;
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.3s;
}

.btn-decline:hover {
    border-color: rgba(168, 180, 200, 0.6);
}

.game-mode-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(158, 240, 26, 0.15);
    color: #9ef01a;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    margin-top: 8px;
}
```

---

---

## 🎯 Интеграция в форму бронирования

### Шаг 1: Выбор типа бронирования

```html
<!-- В форме бронирования корта -->
<div class="booking-type-selector">
    <div class="type-option" data-type="game">
        <i class="fas fa-gamepad"></i>
        <h3>Игра</h3>
        <p>Обычная или рейтинговая игра</p>
    </div>

    <div class="type-option" data-type="training">
        <i class="fas fa-dumbbell"></i>
        <h3>Тренировка</h3>
        <p>С тренером</p>
    </div>
</div>
```

### Шаг 2: Выбор режима игры (если выбрана "Игра")

```html
<!-- Появляется если выбран тип "Игра" -->
<div id="game-mode-options" style="display: none;">
    <h4>Режим игры</h4>

    <div class="game-mode-selector">
        <label class="mode-card">
            <input type="radio" name="game_mode" value="regular" checked>
            <div class="mode-content">
                <i class="fas fa-users"></i>
                <h5>Обычная игра</h5>
                <p>2 на 2, фиксированные пары</p>
            </div>
        </label>

        <label class="mode-card mode-featured">
            <input type="radio" name="game_mode" value="americano">
            <div class="mode-content">
                <i class="fas fa-sync-alt"></i>
                <h5>Americano</h5>
                <p>4 игрока, меняющиеся пары</p>
                <span class="badge">Популярно</span>
            </div>
        </label>

        <label class="mode-card">
            <input type="radio" name="game_mode" value="mexicano">
            <div class="mode-content">
                <i class="fas fa-chart-line"></i>
                <h5>Mexicano</h5>
                <p>4 игрока, пары по рейтингу</p>
            </div>
        </label>
    </div>

    <!-- Настройки для Americano/Mexicano -->
    <div id="social-game-settings" style="display: none;">
        <div class="form-group">
            <label>Количество раундов</label>
            <select name="rounds_count" class="form-control">
                <option value="3" selected>3 раунда (быстрая игра)</option>
                <option value="5">5 раундов (стандарт)</option>
                <option value="7">7 раундов (полный формат)</option>
            </select>
        </div>

        <div class="form-group">
            <label>Очков за раунд</label>
            <select name="points_per_round" class="form-control">
                <option value="16">16 очков (~7 мин)</option>
                <option value="20">20 очков (~9 мин)</option>
                <option value="24" selected>24 очка (~11 мин)</option>
                <option value="32">32 очка (~15 мин)</option>
            </select>
        </div>

        <div class="form-group">
            <label class="checkbox-label">
                <input type="checkbox" name="is_public" id="is_public">
                <span>Публичная игра (другие могут присоединиться)</span>
            </label>
        </div>

        <!-- Требования по рейтингу (если публичная) -->
        <div id="rating-requirements" style="display: none;">
            <div class="form-row">
                <div class="form-group col-6">
                    <label>Мин. рейтинг</label>
                    <select name="min_rating" class="form-control">
                        <option value="">Без ограничений</option>
                        <option value="2.0">2.0</option>
                        <option value="2.5">2.5</option>
                        <option value="3.0">3.0</option>
                        <option value="3.5">3.5</option>
                        <option value="4.0">4.0</option>
                        <option value="4.5">4.5</option>
                        <option value="5.0">5.0</option>
                    </select>
                </div>
                <div class="form-group col-6">
                    <label>Макс. рейтинг</label>
                    <select name="max_rating" class="form-control">
                        <option value="">Без ограничений</option>
                        <option value="3.0">3.0</option>
                        <option value="3.5">3.5</option>
                        <option value="4.0">4.0</option>
                        <option value="4.5">4.5</option>
                        <option value="5.0">5.0</option>
                        <option value="5.5">5.5</option>
                        <option value="6.0">6.0</option>
                    </select>
                </div>
            </div>
        </div>
    </div>
</div>
```

### JavaScript для формы

```javascript
// booking-form.js

document.addEventListener('DOMContentLoaded', function() {
    const gameTypeRadios = document.querySelectorAll('input[name="game_mode"]');
    const socialGameSettings = document.getElementById('social-game-settings');
    const isPublicCheckbox = document.getElementById('is_public');
    const ratingRequirements = document.getElementById('rating-requirements');

    // Показать настройки для Americano/Mexicano
    gameTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'americano' || this.value === 'mexicano') {
                socialGameSettings.style.display = 'block';
            } else {
                socialGameSettings.style.display = 'none';
            }
        });
    });

    // Показать требования по рейтингу для публичных игр
    if (isPublicCheckbox) {
        isPublicCheckbox.addEventListener('change', function() {
            ratingRequirements.style.display = this.checked ? 'block' : 'none';
        });
    }
});
```

---

## 📱 Полный функционал

### 1. Создание игры

**Endpoint:** `POST /bookings/create/`

```python
def create_booking(request):
    if request.method == 'POST':
        # ... существующая логика ...

        # Новые поля
        game_mode = request.POST.get('game_mode', 'regular')
        is_public = request.POST.get('is_public') == 'on'

        booking = Booking.objects.create(
            user=request.user,
            court=court,
            date=date,
            start_time=start_time,
            end_time=end_time,
            booking_type=booking_type,
            game_mode=game_mode,
            is_public=is_public,
            # ... другие поля ...
        )

        # Если Americano/Mexicano
        if game_mode in ['americano', 'mexicano']:
            booking.rounds_count = int(request.POST.get('rounds_count', 3))
            booking.points_per_round = int(request.POST.get('points_per_round', 24))

            if is_public:
                booking.min_rating_required = request.POST.get('min_rating')
                booking.max_rating_required = request.POST.get('max_rating')

            booking.game_status = 'waiting'
            booking.save()

        return JsonResponse({'success': True, 'booking_id': booking.id})
```

### 2. Приглашение игроков

**UI в карточке игры:**
```html
<button onclick="invitePlayer({{ booking.id }})">
    <i class="fas fa-plus"></i> Пригласить игрока
</button>
```

**Modal для приглашения:**
```html
<div id="inviteModal" class="modal">
    <div class="modal-content">
        <h3>Пригласить игрока</h3>

        <input type="text" id="playerSearch" placeholder="Поиск по имени..."
               oninput="searchPlayers(this.value)">

        <div id="playersResults">
            <!-- Список найденных игроков -->
        </div>

        <!-- ИЛИ пригласить по телефону -->
        <div class="divider">или</div>

        <input type="tel" id="phoneInvite" placeholder="+7 (___) ___-__-__">
        <button onclick="inviteByPhone()">Пригласить по телефону</button>
    </div>
</div>
```

**API:**
```python
@login_required
def invite_player(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Проверка прав
    if booking.user != request.user:
        return JsonResponse({'error': 'Access denied'}, status=403)

    user_id = request.POST.get('user_id')
    phone = request.POST.get('phone')

    if user_id:
        invitee = User.objects.get(id=user_id)
    elif phone:
        invitee = UserProfile.objects.get(phone=phone).user

    # Создаем приглашение
    GameParticipant.objects.create(
        booking=booking,
        user=invitee,
        position=booking.get_next_position(),
        status='pending'
    )

    # Отправляем уведомление
    # ... логика уведомления ...

    return JsonResponse({'success': True})
```

### 3. Принятие/Отклонение приглашения

```python
@login_required
def respond_to_invitation(request, invitation_id):
    participant = get_object_or_404(GameParticipant, id=invitation_id, user=request.user)

    action = request.POST.get('action')  # 'accept' or 'decline'

    if action == 'accept':
        participant.status = 'accepted'
        participant.responded_at = timezone.now()
        participant.save()

        # Проверяем, все ли на месте
        if participant.booking.is_full():
            participant.booking.game_status = 'ready'
            participant.booking.save()

            # Генерируем раунды
            if participant.booking.game_mode in ['americano', 'mexicano']:
                generate_game_rounds(participant.booking)

    elif action == 'decline':
        participant.status = 'declined'
        participant.responded_at = timezone.now()
        participant.save()

    return JsonResponse({'success': True})
```

### 4. Генерация раундов

```python
def generate_game_rounds(booking):
    """Генерация раундов для Americano/Mexicano"""

    participants = list(booking.game_participants.filter(status='accepted').order_by('position'))

    if len(participants) != 4:
        raise ValueError("Нужно ровно 4 игрока")

    players = [p.user for p in participants]

    if booking.game_mode == 'americano':
        # Americano: ротация партнеров
        rounds_config = [
            # Раунд 1: P1+P2 vs P3+P4
            ((players[0], players[1]), (players[2], players[3])),
            # Раунд 2: P1+P3 vs P2+P4
            ((players[0], players[2]), (players[1], players[3])),
            # Раунд 3: P1+P4 vs P2+P3
            ((players[0], players[3]), (players[1], players[2])),
        ]
    elif booking.game_mode == 'mexicano':
        # Mexicano: пары по рейтингу после каждого раунда
        # Первый раунд - случайные пары
        import random
        random.shuffle(players)
        rounds_config = [
            ((players[0], players[1]), (players[2], players[3])),
        ]

    # Создаем раунды
    for round_num, (team1, team2) in enumerate(rounds_config, start=1):
        GameRound.objects.create(
            booking=booking,
            round_number=round_num,
            team1_player1=team1[0],
            team1_player2=team1[1],
            team2_player1=team2[0],
            team2_player2=team2[1],
            status='pending'
        )

    booking.current_round = 1
    booking.game_status = 'ready'
    booking.save()
```

### 5. Ввод счета после раунда

**UI (Modal):**
```html
<div id="scoreModal" class="modal">
    <div class="modal-content">
        <h3>Раунд {{ round_number }}: Результаты</h3>

        <div class="teams-score">
            <div class="team">
                <div class="team-players">
                    <div class="player-avatar">...</div>
                    <div class="player-avatar">...</div>
                </div>
                <h4>{{ team1.player1 }} + {{ team1.player2 }}</h4>
                <input type="number" name="team1_score" min="0" max="32"
                       placeholder="Счет" class="score-input">
            </div>

            <div class="vs">VS</div>

            <div class="team">
                <div class="team-players">
                    <div class="player-avatar">...</div>
                    <div class="player-avatar">...</div>
                </div>
                <h4>{{ team2.player1 }} + {{ team2.player2 }}</h4>
                <input type="number" name="team2_score" min="0" max="32"
                       placeholder="Счет" class="score-input">
            </div>
        </div>

        <button onclick="submitScore()">Сохранить результат</button>
    </div>
</div>
```

**API:**
```python
@login_required
def submit_round_score(request, round_id):
    game_round = get_object_or_404(GameRound, id=round_id)

    # Проверка прав (только участники могут вводить счет)
    participants = game_round.booking.game_participants.all()
    if request.user not in [p.user for p in participants]:
        return JsonResponse({'error': 'Access denied'}, status=403)

    team1_score = int(request.POST.get('team1_score'))
    team2_score = int(request.POST.get('team2_score'))

    # Сохраняем счет
    game_round.team1_score = team1_score
    game_round.team2_score = team2_score
    game_round.score_entered_by.add(request.user)
    game_round.save()

    # Если минимум 3 игрока подтвердили счет
    if game_round.is_score_verified():
        game_round.status = 'completed'
        game_round.completed_at = timezone.now()
        game_round.save()

        # Обновляем очки участников
        update_participant_scores(game_round)

        # Переход к следующему раунду
        booking = game_round.booking
        booking.current_round += 1

        if booking.current_round <= booking.rounds_count:
            # Генерируем следующий раунд (для Mexicano)
            if booking.game_mode == 'mexicano':
                generate_next_mexicano_round(booking)
            booking.game_status = 'in_progress'
        else:
            # Игра завершена
            booking.game_status = 'completed'
            calculate_rating_changes(booking)

        booking.save()

    return JsonResponse({'success': True})
```

### 6. Обновление очков участников

```python
def update_participant_scores(game_round):
    """Обновить индивидуальные очки после раунда"""

    booking = game_round.booking

    # Пара 1
    for player in [game_round.team1_player1, game_round.team1_player2]:
        participant = booking.game_participants.get(user=player)
        participant.total_points += game_round.team1_score
        participant.rounds_played += 1
        if game_round.team1_score > game_round.team2_score:
            participant.rounds_won += 1
        participant.save()

    # Пара 2
    for player in [game_round.team2_player1, game_round.team2_player2]:
        participant = booking.game_participants.get(user=player)
        participant.total_points += game_round.team2_score
        participant.rounds_played += 1
        if game_round.team2_score > game_round.team1_score:
            participant.rounds_won += 1
        participant.save()
```

### 7. Расчет изменения рейтинга

```python
def calculate_rating_changes(booking):
    """Рассчитать изменение рейтинга для всех участников"""

    participants = list(booking.game_participants.all().order_by('-total_points'))

    # Сохраняем рейтинг до игры
    for p in participants:
        p.rating_before = p.user.rating.numeric_rating
        p.save()

    # Простая формула: победитель +0.1, второе место 0, третье -0.05, четвертое -0.1
    rating_changes = [0.15, 0.05, -0.05, -0.15]

    for i, participant in enumerate(participants):
        change = rating_changes[i]
        participant.rating_change = change
        participant.save()

        # Обновляем рейтинг пользователя
        rating = participant.user.rating
        new_rating = float(rating.numeric_rating) + change
        new_rating = max(1.0, min(7.0, new_rating))  # Ограничиваем 1.0-7.0
        rating.numeric_rating = new_rating
        rating.save()
```

### 8. Страница результатов

```html
<div class="game-results">
    <h2>Результаты игры</h2>

    <div class="final-standings">
        {% for participant in participants %}
        <div class="standing-row rank-{{ forloop.counter }}">
            <div class="rank">{{ forloop.counter }}</div>
            <div class="player-info">
                <img src="{{ participant.user.profile.avatar.url }}" class="avatar">
                <div>
                    <h4>{{ participant.user.get_full_name }}</h4>
                    <div class="rating-change {% if participant.rating_change > 0 %}positive{% elif participant.rating_change < 0 %}negative{% endif %}">
                        {{ participant.rating_before }} → {{ participant.rating_before|add:participant.rating_change }}
                        ({% if participant.rating_change > 0 %}+{% endif %}{{ participant.rating_change }})
                    </div>
                </div>
            </div>
            <div class="stats">
                <div>{{ participant.total_points }} очков</div>
                <div>{{ participant.rounds_won }}/{{ participant.rounds_played }} побед</div>
            </div>
        </div>
        {% endfor %}
    </div>

    <h3>Раунды</h3>
    {% for round in game_rounds %}
    <div class="round-result">
        <h4>Раунд {{ round.round_number }}</h4>
        <div class="match-score">
            <div class="team">
                {{ round.team1_player1.get_full_name }} + {{ round.team1_player2.get_full_name }}
            </div>
            <div class="score">{{ round.team1_score }} - {{ round.team2_score }}</div>
            <div class="team">
                {{ round.team2_player1.get_full_name }} + {{ round.team2_player2.get_full_name }}
            </div>
        </div>
    </div>
    {% endfor %}
</div>
```

---

## 🎯 Итого: что получается

1. **В форме бронирования** выбираешь "Игра" → режим (Americano/Mexicano)
2. **Настраиваешь**: раунды, очки, публичная/приватная, рейтинг
3. **Приглашаешь 3 игроков** (или они сами присоединяются если публичная)
4. **Система генерирует раунды** со сменой партнеров
5. **После каждого раунда** вводите счет (нужно подтверждение 3+ игроков)
6. **В конце** видите итоговую таблицу и изменение рейтинга

Всё как в турнире, но для обычной игры на 4 человека!

Начать реализацию?

