# 🚀 Идеи для развития Paddle Booking System

**Дата:** 2026-02-05
**Версия:** 2.0 - Future Features Roadmap

---

## 🎯 1. РЕЙТИНГОВЫЕ ИГРЫ

### Концепция
Добавить возможность играть матчи "на рейтинг" - официальные игры, которые влияют на рейтинг игроков.

### Модель данных

```python
class RankedMatch(models.Model):
    """Рейтинговая игра"""

    # Пара 1
    team1_player1 = models.ForeignKey(User, related_name='ranked_team1_p1')
    team1_player2 = models.ForeignKey(User, related_name='ranked_team1_p2')

    # Пара 2
    team2_player1 = models.ForeignKey(User, related_name='ranked_team2_p1')
    team2_player2 = models.ForeignKey(User, related_name='ranked_team2_p2')

    # Счет
    team1_score = models.IntegerField(default=0)
    team2_score = models.IntegerField(default=0)

    # Рейтинги до матча
    team1_avg_rating_before = models.DecimalField(max_digits=4, decimal_places=2)
    team2_avg_rating_before = models.DecimalField(max_digits=4, decimal_places=2)

    # Изменение рейтинга
    rating_change = models.DecimalField(max_digits=3, decimal_places=2)

    # Связь с бронированием
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)

    # Верификация результата
    verified_by_players = models.ManyToManyField(User, related_name='verified_matches')
    is_verified = models.BooleanField(default=False)

    # Метаданные
    played_at = models.DateTimeField(auto_now_add=True)
```

### Функционал

#### 1.1 Создание рейтингового матча
- При бронировании корта галочка "Рейтинговая игра"
- Требуется указать всех 4 игроков
- Система проверяет, что все игроки подтвердили участие

#### 1.2 Ввод результата
- После игры игроки вводят счет через мобильное приложение
- Требуется подтверждение от минимум 3 из 4 игроков
- Защита от накрутки: если счет сомнительный (слишком большая разница), требуется фото/видео

#### 1.3 Расчет изменения рейтинга
Используем модифицированную систему Elo для пар:

```python
def calculate_rating_change(team1_avg_rating, team2_avg_rating, score1, score2):
    """
    K-фактор зависит от разницы в счете:
    - Победа с минимальным отрывом: меньше очков
    - Разгром: больше очков
    """
    K = 32  # Базовый K-фактор

    # Ожидаемый результат
    expected_team1 = 1 / (1 + 10 ** ((team2_avg_rating - team1_avg_rating) / 400))

    # Фактический результат
    actual = 1 if score1 > score2 else 0

    # Множитель за разгром
    score_diff = abs(score1 - score2)
    multiplier = 1 + (score_diff / 24) * 0.3  # До +30% за разгром

    # Изменение рейтинга
    change = K * multiplier * (actual - expected_team1)

    return round(change, 2)
```

#### 1.4 UI для рейтинговых игр

**Страница "Рейтинговые матчи":**
```
┌─────────────────────────────────────────┐
│ МОИ РЕЙТИНГОВЫЕ МАТЧИ                   │
├─────────────────────────────────────────┤
│ ✅ 02.02.2026 | Корт 1                  │
│    Вы + Петров (4.5 ⭐)                 │
│       VS                                 │
│    Сидоров + Иванов (4.8 ⭐)            │
│    Счет: 18 - 12 (Победа)               │
│    Изменение: +0.15 ⭐                  │
│                                          │
│ ⏳ 03.02.2026 | Корт 2                  │
│    Вы + Смирнов (4.3 ⭐)                │
│       VS                                 │
│    Морозов + Федоров (4.6 ⭐)           │
│    [Ввести результат]                   │
└─────────────────────────────────────────┘
```

---

## 🏆 2. ВИРТУАЛЬНЫЕ НАГРАДЫ И ДОСТИЖЕНИЯ

### Концепция
Система ачивок (achievements) и виртуальных наград для мотивации игроков.

### Модель данных

```python
class Achievement(models.Model):
    """Достижение/Ачивка"""

    CATEGORY_CHOICES = [
        ('games', 'Количество игр'),
        ('wins', 'Победы'),
        ('tournaments', 'Турниры'),
        ('social', 'Социальные'),
        ('special', 'Специальные'),
    ]

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    # Иконка/badge
    icon = models.CharField(max_length=50)  # emoji или icon class
    badge_image = models.ImageField(upload_to='badges/', null=True, blank=True)

    # Условия получения
    requirement_type = models.CharField(max_length=50)  # games_played, wins, etc.
    requirement_value = models.IntegerField()

    # Награда за получение
    points_reward = models.IntegerField(default=0)

    # Редкость
    rarity = models.CharField(max_length=20, choices=[
        ('common', 'Обычное'),
        ('rare', 'Редкое'),
        ('epic', 'Эпическое'),
        ('legendary', 'Легендарное'),
    ])


class UserAchievement(models.Model):
    """Полученное достижение"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)

    # Прогресс
    current_progress = models.IntegerField(default=0)
    is_unlocked = models.BooleanField(default=False)
    unlocked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'achievement']
```

### Примеры достижений

#### Категория: Количество игр
- 🎾 **Новичок** - Сыграть 1 игру
- 🏸 **Любитель** - Сыграть 10 игр
- 🎯 **Энтузиаст** - Сыграть 50 игр
- 🔥 **Фанат** - Сыграть 100 игр
- 👑 **Легенда** - Сыграть 500 игр

#### Категория: Победы
- ✅ **Первая кровь** - Первая победа
- 🏆 **Победитель** - 10 побед
- 💪 **Доминатор** - 50 побед
- ⚡ **Серия побед** - 5 побед подряд
- 🎯 **Снайпер** - Выиграть 10 раз со счетом 18:0

#### Категория: Турниры
- 🥉 **Бронза** - 3 место в турнире
- 🥈 **Серебро** - 2 место в турнире
- 🥇 **Золото** - 1 место в турнире
- 👑 **Чемпион** - Выиграть 5 турниров
- 🌟 **Grand Slam** - Выиграть турниры всех форматов

#### Категория: Социальные
- 🤝 **Командный игрок** - Сыграть с 10 разными партнерами
- 👥 **Социальная бабочка** - Сыграть против 50 разных игроков
- 💬 **Организатор** - Создать 5 открытых игр
- 📱 **Пригласил друга** - Пригласить 3 друзей в систему

#### Категория: Специальные
- 🌙 **Полуночник** - Сыграть после 23:00
- ☀️ **Ранняя пташка** - Сыграть до 7:00
- 📅 **Марафонец** - Играть 7 дней подряд
- 🎂 **С днем рождения!** - Сыграть в свой день рождения
- 🎄 **Новогодний** - Сыграть 31 декабря

### UI для достижений

**Страница профиля - Вкладка "Достижения":**
```
┌───────────────────────────────────────────┐
│ ДОСТИЖЕНИЯ                    [45 / 120]  │
├───────────────────────────────────────────┤
│ ✅ ОТКРЫТЫЕ (45)                          │
│                                            │
│ 🏆 Победитель                             │
│    10 побед  ⚫⚫⚫⚫⚫⚫⚫⚫⚫⚫ 10/10        │
│    Открыто: 15.01.2026                    │
│                                            │
│ 🔥 Фанат                                  │
│    100 игр   ⚫⚫⚫⚫⚫⚫⚫⚫⚫⚫ 100/100       │
│    Открыто: 28.01.2026                    │
│                                            │
│ ⏳ В ПРОЦЕССЕ (12)                        │
│                                            │
│ 👑 Легенда                                │
│    500 игр   ⚫⚫⚫⚫⚫⚪⚪⚪⚪⚪ 247/500       │
│    49% завершено                           │
│                                            │
│ 🔒 ЗАКРЫТЫЕ (63)                          │
│                                            │
│ 🌟 Grand Slam                             │
│    Выиграть турниры всех форматов         │
│    0 / 7 форматов                          │
└───────────────────────────────────────────┘
```

### Система очков (Gamification Points)

```python
class UserPoints(models.Model):
    """Игровые очки пользователя"""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)

    # История начисления очков
    points_history = models.JSONField(default=list)

    def add_points(self, points, reason):
        self.total_points += points
        self.points_history.append({
            'date': timezone.now().isoformat(),
            'points': points,
            'reason': reason
        })
        self._update_level()
        self.save()

    def _update_level(self):
        # Уровень = sqrt(очки / 100)
        self.level = int((self.total_points / 100) ** 0.5) + 1
```

**Как начисляются очки:**
- Сыграть игру: +10 очков
- Победа: +20 очков
- Победа в рейтинговой игре: +50 очков
- Участие в турнире: +100 очков
- Победа в турнире: +500 очков
- Открытие достижения: +50-500 очков (зависит от редкости)
- Пригласить друга: +200 очков

---

## 🎾 3. АРЕНДА ОБОРУДОВАНИЯ

### Концепция
Возможность арендовать ракетки, мячи и другое оборудование вместе с кортом.

### Модель данных

```python
class Equipment(models.Model):
    """Инвентарь для аренды"""

    CATEGORY_CHOICES = [
        ('racket', 'Ракетка'),
        ('balls', 'Мячи'),
        ('shoes', 'Обувь'),
        ('bag', 'Сумка'),
        ('accessories', 'Аксессуары'),
    ]

    CONDITION_CHOICES = [
        ('new', 'Новое'),
        ('excellent', 'Отличное'),
        ('good', 'Хорошее'),
        ('fair', 'Удовлетворительное'),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()

    # Характеристики (для ракеток)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    weight = models.IntegerField(null=True, blank=True, help_text='Вес в граммах')
    balance = models.CharField(max_length=50, blank=True)  # Баланс

    # Размер (для обуви)
    size = models.CharField(max_length=20, blank=True)

    # Состояние
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)

    # Цена аренды
    price_per_hour = models.DecimalField(max_digits=6, decimal_places=2)
    deposit = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Количество
    total_quantity = models.IntegerField(default=1)
    available_quantity = models.IntegerField(default=1)

    # Изображения
    image = models.ImageField(upload_to='equipment/', null=True, blank=True)

    # Метаданные
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Инвентарь'
        verbose_name_plural = 'Инвентарь'


class EquipmentRental(models.Model):
    """Аренда оборудования"""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='equipment_rentals')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)

    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    # Цены
    price_per_hour = models.DecimalField(max_digits=6, decimal_places=2)
    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Статус
    is_returned = models.BooleanField(default=False)
    returned_at = models.DateTimeField(null=True, blank=True)

    # Состояние при возврате
    return_condition = models.CharField(max_length=20, choices=Equipment.CONDITION_CHOICES, blank=True)
    damage_notes = models.TextField(blank=True)
    penalty_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Аренда инвентаря'
        verbose_name_plural = 'Аренды инвентаря'
```

### Функционал

#### 3.1 Каталог оборудования
```
┌──────────────────────────────────────────┐
│ АРЕНДА ОБОРУДОВАНИЯ                      │
├──────────────────────────────────────────┤
│ [Ракетки] [Мячи] [Обувь] [Аксессуары]   │
│                                           │
│ ┌────────────────────────────────────┐   │
│ │ 🎾 HEAD Graphene 360                │   │
│ │    Профессиональная ракетка         │   │
│ │    300₽/час | Залог: 5000₽         │   │
│ │    Состояние: Отличное              │   │
│ │    Доступно: 3 шт.                  │   │
│ │    [Добавить к бронированию]        │   │
│ └────────────────────────────────────┘   │
│                                           │
│ ┌────────────────────────────────────┐   │
│ │ 🎾 Wilson Pro Staff 97              │   │
│ │    Для продвинутых игроков          │   │
│ │    250₽/час | Залог: 4000₽         │   │
│ │    Состояние: Хорошее               │   │
│ │    Доступно: 5 шт.                  │   │
│ │    [Добавить к бронированию]        │   │
│ └────────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

#### 3.2 Добавление к бронированию
При бронировании корта:
```
┌──────────────────────────────────────────┐
│ ШАГ 3: ДОПОЛНИТЕЛЬНЫЕ УСЛУГИ             │
├──────────────────────────────────────────┤
│ ✅ Арендовать оборудование               │
│                                           │
│ Ракетки:                                  │
│ ┌─────────────────────┐                  │
│ │ HEAD Graphene 360   │ [+] [-]  2 шт.  │
│ │ 300₽/час            │ = 600₽          │
│ └─────────────────────┘                  │
│                                           │
│ Мячи:                                     │
│ ┌─────────────────────┐                  │
│ │ HEAD Pro (3 шт.)    │ [+] [-]  1 шт.  │
│ │ 150₽/сессию         │ = 150₽          │
│ └─────────────────────┘                  │
│                                           │
│ Итого доп. услуг: 750₽                   │
│ Залог: 10 000₽                           │
│                                           │
│ [Продолжить]                              │
└──────────────────────────────────────────┘
```

#### 3.3 Возврат оборудования
После игры администратор проверяет состояние:
```
┌──────────────────────────────────────────┐
│ ВОЗВРАТ ОБОРУДОВАНИЯ                     │
│ Бронирование #1234                       │
├──────────────────────────────────────────┤
│ HEAD Graphene 360 (x2)                   │
│                                           │
│ Состояние:                                │
│ ○ Отличное (без штрафа)                  │
│ ○ Хорошее (без штрафа)                   │
│ ○ Повреждено (-1000₽ от залога)         │
│ ○ Утеряно/Сильно повреждено (залог)     │
│                                           │
│ Примечания:                               │
│ [_________________________________]       │
│                                           │
│ Возврат залога: 10 000₽                  │
│                                           │
│ [Подтвердить возврат]                     │
└──────────────────────────────────────────┘
```

---

## 🎮 4. ДОПОЛНИТЕЛЬНЫЕ ИДЕИ

### 4.1 Челленджи (Challenges)
Еженедельные/ежемесячные вызовы для игроков:

```python
class Challenge(models.Model):
    """Челлендж/Вызов"""

    name = models.CharField(max_length=200)
    description = models.TextField()

    # Временные рамки
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    # Условие выполнения
    goal_type = models.CharField(max_length=50)  # games, wins, points
    goal_value = models.IntegerField()

    # Награда
    reward_points = models.IntegerField()
    reward_badge = models.ForeignKey(Achievement, null=True, blank=True)

    # Участники
    participants = models.ManyToManyField(User, through='ChallengeProgress')
```

**Примеры челленджей:**
- 📅 "Играй каждый день" - Сыграть 7 дней подряд (награда: 500 очков)
- 🏆 "Король недели" - Выиграть 10 игр за неделю (награда: badge + 1000 очков)
- 🤝 "Социальная сеть" - Сыграть с 5 новыми партнерами (награда: 300 очков)
- ⚡ "Скоростной" - Сыграть 5 игр за один день (награда: badge)

### 4.2 Лига/Дивизионы

Разделение игроков по лигам на основе рейтинга:

```
🥉 BRONZE (1.0 - 2.9)
🥈 SILVER (3.0 - 3.9)
🥇 GOLD (4.0 - 4.9)
💎 PLATINUM (5.0 - 5.9)
👑 DIAMOND (6.0 - 7.0)
```

**Бонусы по лигам:**
- Silver: +5% скидка на бронирование
- Gold: +10% скидка + приоритетное бронирование
- Platinum: +15% скидка + бесплатная аренда мячей
- Diamond: +20% скидка + VIP статус

### 4.3 Реферальная программа

```python
class Referral(models.Model):
    """Реферальная программа"""

    referrer = models.ForeignKey(User, related_name='referrals')
    referred_user = models.ForeignKey(User, related_name='referred_by')

    # Статус
    is_active = models.BooleanField(default=True)
    completed_first_booking = models.BooleanField(default=False)

    # Награды
    referrer_bonus = models.DecimalField(max_digits=8, decimal_places=2, default=500)
    referred_bonus = models.DecimalField(max_digits=8, decimal_places=2, default=300)

    created_at = models.DateTimeField(auto_now_add=True)
```

**Механика:**
- Пригласи друга → получи 500₽ на счет
- Друг получает 300₽ на первое бронирование
- После 5 приглашений → VIP статус на месяц

### 4.4 Абонементы

```python
class Subscription(models.Model):
    """Абонемент"""

    PLAN_CHOICES = [
        ('basic', 'Базовый - 10 часов/мес'),
        ('standard', 'Стандарт - 20 часов/мес'),
        ('premium', 'Премиум - безлимит'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)

    hours_included = models.IntegerField()
    hours_used = models.IntegerField(default=0)

    price = models.DecimalField(max_digits=8, decimal_places=2)

    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(default=True)
```

**Тарифы:**
- 🥉 Базовый: 3000₽/мес (10 часов) - 300₽/час
- 🥈 Стандарт: 5000₽/мес (20 часов) - 250₽/час
- 🥇 Премиум: 8000₽/мес (безлимит) + бонусы

### 4.5 Мастер-классы и тренировки

```python
class MasterClass(models.Model):
    """Мастер-класс/Групповая тренировка"""

    title = models.CharField(max_length=200)
    description = models.TextField()

    coach = models.ForeignKey('Trainer', on_delete=models.CASCADE)
    court = models.ForeignKey(Court, on_delete=models.CASCADE)

    # Расписание
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Участники
    max_participants = models.IntegerField(default=8)
    participants = models.ManyToManyField(User, related_name='attended_classes')

    # Цена
    price_per_person = models.DecimalField(max_digits=6, decimal_places=2)

    # Уровень
    min_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    max_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True)

    # Статус
    is_published = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
```

### 4.6 Социальные функции

#### Группы/Команды
```python
class Team(models.Model):
    """Команда игроков"""

    name = models.CharField(max_length=200)
    description = models.TextField()
    logo = models.ImageField(upload_to='teams/', null=True)

    captain = models.ForeignKey(User, related_name='team_captain')
    members = models.ManyToManyField(User, related_name='teams')

    # Статистика команды
    total_games = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
```

#### Чат/Сообщения
- Внутренний чат для координации игр
- Уведомления о новых играх
- Приглашения в команду

---

## 📊 ПРИОРИТИЗАЦИЯ

### Высокий приоритет (3-4 месяца)
1. ✅ Рейтинговые игры
2. ✅ Базовые достижения (20-30 ачивок)
3. ✅ Аренда оборудования

### Средний приоритет (6 месяцев)
4. Челленджи
5. Реферальная программа
6. Абонементы

### Низкий приоритет (12 месяцев)
7. Лиги/Дивизионы
8. Мастер-классы
9. Команды и социальные функции

---

**Автор:** Claude Sonnet 4.5
**Дата:** 2026-02-05
