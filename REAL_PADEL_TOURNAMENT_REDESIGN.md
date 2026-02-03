# 🎾 Переделка системы турниров под РЕАЛЬНЫЙ ПАДДЛ

**Дата:** 2026-02-02
**Исследование:** Реальные форматы паддл-турниров

---

## 🔍 Что я узнал о настоящих паддл-турнирах

### Ключевые факты о паддле:

1. **Паддл = ПАРНЫЙ спорт** 🎾🎾
   - Всегда играют 2 на 2 (doubles)
   - НЕТ индивидуальных матчей
   - Пара (team/pair) - это основная единица

2. **Специальные форматы турниров:**

#### 🔄 **Americano** (самый популярный)
```
✅ Игроки соревнуются ИНДИВИДУАЛЬНО
✅ Но играют в ПАРАХ (2v2)
✅ Партнеры МЕНЯЮТСЯ каждый раунд
✅ Каждый игрок набирает очки лично
✅ Победитель = игрок с наибольшими очками

ПРИМЕР (8 игроков):
Раунд 1: (A+B vs C+D), (E+F vs G+H)
Раунд 2: (A+C vs B+D), (E+G vs F+H)
Раунд 3: (A+D vs B+C), (E+H vs F+G)
...каждый играет с каждым и против каждого

Очки: Если пара выиграла 18:12, оба игрока получают 18 очков
```

#### 📊 **Mexicano** (с динамическим рейтингом)
```
✅ Почти как Americano
✅ НО пары формируются по РЕЙТИНГУ
✅ После каждого раунда игроки ранжируются
✅ Следующие пары: 1+2 vs 3+4, 5+6 vs 7+8
✅ Матчи становятся более сбалансированными

ПРИМЕР после Раунда 1:
Рейтинг: A(20), B(18), C(16), D(14), E(12), F(10), G(8), H(6)
Раунд 2: (A+B vs C+D), (E+F vs G+H)  ← Топы играют с топами
```

#### 🏆 **Team Americano/Mexicano**
```
✅ Фиксированные пары
✅ Пары не меняются
✅ Очки суммируются для пары
```

#### 🎯 **Traditional Bracket** (олимпийская система)
```
✅ Фиксированные пары
✅ Single/Double elimination
✅ Используется в профессиональных турнирах (Premier Padel)
```

3. **Подсчет очков:**
   - Матчи играются до N очков (16, 20, 24, 32)
   - НЕ по сетам/геймам как в теннисе
   - Быстрый формат: 24 очка ≈ 10 минут

4. **Профессиональный паддл (Premier Padel 2024):**
   - Majors (2000 очков)
   - P1 (1000 очков)
   - P2 (500 очков)
   - Tour Finals (1500 очков)

---

## ❌ Проблемы текущей системы

### Критичные несоответствия:

1. **НЕТ модели для ПАР** ❌
   ```python
   # Текущая модель:
   class TournamentMatch:
       player1 = ForeignKey(User)  # ← ИНДИВИДУАЛЬНЫЙ игрок
       player2 = ForeignKey(User)  # ← ИНДИВИДУАЛЬНЫЙ игрок

   # Должно быть:
   class TournamentMatch:
       team1 = ForeignKey(Team)  # ← ПАРА игроков
       team2 = ForeignKey(Team)  # ← ПАРА игроков
   ```

2. **НЕТ форматов Americano/Mexicano** ❌
   ```python
   # Текущие форматы:
   FORMAT_CHOICES = [
       ('single_elimination', ...),  # ✅ Есть
       ('round_robin', ...),          # ⚠️ Неправильно (для индивидуалов)
   ]

   # Нужно добавить:
   ('americano', 'Americano'),
   ('mexicano', 'Mexicano'),
   ('team_americano', 'Team Americano'),
   ('team_mexicano', 'Team Mexicano'),
   ('doubles_bracket', 'Doubles Bracket'),
   ```

3. **НЕТ ротации партнеров** ❌
   - Нет механизма смены пар между раундами
   - Нет индивидуального подсчета очков

4. **Неправильный подсчет счета** ❌
   ```python
   # Текущий:
   score = {"sets": ["6-4", "7-5"]}  # ← Теннисный формат

   # Должно быть:
   score = {"team1": 18, "team2": 12}  # ← Паддл формат (до N очков)
   ```

---

## ✅ НОВАЯ АРХИТЕКТУРА

### 1. Новые модели

#### PadelTeam (Пара игроков)
```python
class PadelTeam(models.Model):
    """
    Пара игроков в паддле
    Может быть постоянной (для bracket) или временной (для Americano)
    """

    # Связь с турниром
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='teams'
    )

    # Игроки (всегда 2)
    player1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='padel_teams_as_p1'
    )
    player2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='padel_teams_as_p2'
    )

    # Название (опционально для постоянных команд)
    name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Например: "Los Campeones" (для постоянных пар)'
    )

    # Для генерации сетки
    seed = models.IntegerField(null=True, blank=True)

    # Для Americano/Mexicano (временная пара)
    is_temporary = models.BooleanField(
        default=False,
        help_text='True для Americano/Mexicano (пара на 1 раунд)'
    )
    round_number = models.IntegerField(
        null=True,
        blank=True,
        help_text='В каком раунде эта пара играет (для Americano)'
    )

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Padel Team (Пара)'
        verbose_name_plural = 'Padel Teams (Пары)'
        # Уникальность: одна пара игроков на турнир/раунд
        unique_together = ['tournament', 'player1', 'player2', 'round_number']
        indexes = [
            models.Index(fields=['tournament', 'is_temporary']),
        ]

    def __str__(self):
        if self.name:
            return f"{self.name} ({self.player1.get_full_name()} + {self.player2.get_full_name()})"
        return f"{self.player1.get_full_name()} + {self.player2.get_full_name()}"

    @property
    def players(self):
        """Список игроков в паре"""
        return [self.player1, self.player2]
```

#### Обновленный Tournament
```python
class Tournament(models.Model):
    """Турнир по паддлу"""

    FORMAT_CHOICES = [
        # Americano форматы (индивидуальный зачет, меняющиеся пары)
        ('americano', 'Americano'),
        ('mexicano', 'Mexicano'),
        ('mixed_americano', 'Mixed Americano'),

        # Team форматы (постоянные пары)
        ('team_americano', 'Team Americano'),
        ('team_mexicano', 'Team Mexicano'),

        # Bracket форматы (постоянные пары, playoff)
        ('doubles_elimination', 'Doubles Elimination'),
        ('doubles_round_robin', 'Doubles Round Robin'),
    ]

    # ... существующие поля ...

    format = models.CharField(
        max_length=30,
        choices=FORMAT_CHOICES,
        default='americano'
    )

    # Настройки для Americano/Mexicano
    points_per_match = models.IntegerField(
        default=24,
        choices=[
            (16, '16 points'),
            (20, '20 points'),
            (24, '24 points'),
            (32, '32 points'),
        ],
        help_text='До скольки очков играется матч (для Americano/Mexicano)'
    )

    # Новое поле: тип турнира
    is_team_tournament = models.BooleanField(
        default=False,
        help_text='True = постоянные пары, False = индивидуальный зачет'
    )

    # Для Mixed Americano
    is_mixed = models.BooleanField(
        default=False,
        help_text='True = обязательно мужчина+женщина в паре'
    )
```

#### Обновленный TournamentParticipant
```python
class TournamentParticipant(models.Model):
    """
    Участник турнира
    Для Americano/Mexicano - индивидуальный игрок
    Для Team форматов - представитель пары
    """

    tournament = models.ForeignKey(Tournament, ...)
    user = models.ForeignKey(User, ...)

    # Новое: партнер для постоянной пары
    partner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partner_in_tournaments',
        help_text='Постоянный партнер (для Team форматов)'
    )

    # Название пары
    team_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Название пары (для Team форматов)'
    )

    # Индивидуальные очки (для Americano/Mexicano)
    total_points = models.IntegerField(
        default=0,
        help_text='Сумма очков за все раунды (для Americano/Mexicano)'
    )

    # Текущая позиция в рейтинге (для Mexicano)
    current_rank = models.IntegerField(
        null=True,
        blank=True,
        help_text='Текущая позиция после последнего раунда'
    )

    # ... остальные поля ...

    class Meta:
        ordering = ['-total_points', 'registered_at']  # Сортировка по очкам
```

#### Обновленный TournamentMatch
```python
class TournamentMatch(models.Model):
    """Матч в турнире паддл (всегда 2v2)"""

    tournament = models.ForeignKey(Tournament, ...)
    round = models.IntegerField(...)
    match_number = models.IntegerField(...)

    # ГЛАВНОЕ ИЗМЕНЕНИЕ: вместо индивидуальных игроков - ПАРЫ
    team1 = models.ForeignKey(
        'PadelTeam',
        on_delete=models.CASCADE,
        related_name='matches_as_team1',
        null=True,
        blank=True,
        verbose_name='Пара 1'
    )
    team2 = models.ForeignKey(
        'PadelTeam',
        on_delete=models.CASCADE,
        related_name='matches_as_team2',
        null=True,
        blank=True,
        verbose_name='Пара 2'
    )

    # Победитель - тоже пара
    winning_team = models.ForeignKey(
        'PadelTeam',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='won_matches',
        verbose_name='Победившая пара'
    )

    # НОВЫЙ ФОРМАТ СЧЕТА для паддл
    score_team1 = models.IntegerField(
        default=0,
        help_text='Очки первой пары'
    )
    score_team2 = models.IntegerField(
        default=0,
        help_text='Очки второй пары'
    )

    # Детальный счет (опционально)
    detailed_score = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"sets": [{"team1": 6, "team2": 4}, {"team1": 7, "team2": 5}]}'
    )

    # ... остальные поля ...

    def set_winner_by_score(self, team1_score, team2_score):
        """Установить победителя по счету"""
        self.score_team1 = team1_score
        self.score_team2 = team2_score

        if team1_score > team2_score:
            self.winning_team = self.team1
        else:
            self.winning_team = self.team2

        self.status = 'completed'
        self.save()

        # Обновляем индивидуальные очки для Americano/Mexicano
        if self.tournament.format in ['americano', 'mexicano', 'mixed_americano']:
            self._update_player_points(team1_score, team2_score)

        # Продвигаем в следующий раунд (для bracket форматов)
        if self.tournament.format in ['doubles_elimination'] and self.next_match:
            # ... логика продвижения ...

    def _update_player_points(self, team1_score, team2_score):
        """Обновить индивидуальные очки игроков (для Americano)"""
        # Пара 1: оба игрока получают очки пары
        for player in self.team1.players:
            participant = TournamentParticipant.objects.get(
                tournament=self.tournament,
                user=player
            )
            participant.total_points += team1_score
            participant.save()

        # Пара 2: оба игрока получают очки пары
        for player in self.team2.players:
            participant = TournamentParticipant.objects.get(
                tournament=self.tournament,
                user=player
            )
            participant.total_points += team2_score
            participant.save()
```

---

## 🔧 Генераторы турнирных сеток

### 1. AmericanoGenerator

```python
class AmericanoGenerator:
    """
    Генератор для формата Americano

    Принцип:
    - Каждый игрок играет с каждым И против каждого
    - Партнеры меняются каждый раунд
    - Алгоритм: Round Robin с ротацией
    """

    @staticmethod
    def generate(tournament):
        """Генерация раундов для Americano"""

        # Получаем всех участников
        participants = list(
            tournament.participants.filter(payment_status='paid')
            .order_by('seed', 'registered_at')
        )

        num_players = len(participants)

        # Проверки
        if num_players < 4:
            raise ValueError("Минимум 4 участника для Americano")

        if num_players % 4 != 0:
            # Лучше если кратно 4, но можно и 6, 10 и т.д.
            pass

        # Удаляем старые матчи и команды
        tournament.matches.all().delete()
        tournament.teams.filter(is_temporary=True).delete()
        tournament.rounds.all().delete()

        # Генерируем раунды
        players_list = [p.user for p in participants]

        # Количество раундов для Americano
        # Формула: (n-1) раундов для n игроков
        num_rounds = num_players - 1

        all_matches = []

        for round_num in range(1, num_rounds + 1):
            # Создаем раунд
            round_obj = TournamentRound.objects.create(
                tournament=tournament,
                round_number=round_num,
                name=f'Раунд {round_num}'
            )

            # Формируем пары для этого раунда
            pairs = AmericanoGenerator._create_round_pairings(
                players_list,
                round_num
            )

            # Создаем матчи
            match_num = 1
            for i in range(0, len(pairs), 2):
                if i+1 < len(pairs):
                    # Создаем временные команды
                    team1 = PadelTeam.objects.create(
                        tournament=tournament,
                        player1=pairs[i][0],
                        player2=pairs[i][1],
                        is_temporary=True,
                        round_number=round_num
                    )

                    team2 = PadelTeam.objects.create(
                        tournament=tournament,
                        player1=pairs[i+1][0],
                        player2=pairs[i+1][1],
                        is_temporary=True,
                        round_number=round_num
                    )

                    # Создаем матч
                    match = TournamentMatch.objects.create(
                        tournament=tournament,
                        round=round_num,
                        match_number=match_num,
                        team1=team1,
                        team2=team2,
                        status='scheduled'
                    )
                    all_matches.append(match)
                    match_num += 1

            # Ротация игроков для следующего раунда
            # Первый остается, остальные ротируются
            players_list = [players_list[0]] + [players_list[-1]] + players_list[1:-1]

        return all_matches

    @staticmethod
    def _create_round_pairings(players, round_num):
        """
        Создать пары для раунда используя алгоритм Round Robin

        Пример для 8 игроков:
        Раунд 1: (1,8) vs (2,7), (3,6) vs (4,5)
        Раунд 2: (1,7) vs (8,6), (2,5) vs (3,4)
        ...
        """
        n = len(players)
        pairs = []

        # Используем классический алгоритм круговой системы
        for i in range(n // 2):
            pairs.append((players[i], players[n - 1 - i]))

        return pairs
```

### 2. MexicanoGenerator

```python
class MexicanoGenerator:
    """
    Генератор для формата Mexicano

    Принцип:
    - Как Americano, но пары формируются по рейтингу
    - После каждого раунда игроки ранжируются по очкам
    - Следующие пары: 1+2 vs 3+4, 5+6 vs 7+8 и т.д.
    """

    @staticmethod
    def generate_next_round(tournament, round_num):
        """Генерация следующего раунда Mexicano"""

        # Получаем участников, отсортированных по очкам
        participants = list(
            tournament.participants.filter(payment_status='paid')
            .order_by('-total_points', 'registered_at')
        )

        num_players = len(participants)

        if num_players < 4:
            raise ValueError("Минимум 4 участника")

        # Создаем раунд
        round_obj = TournamentRound.objects.create(
            tournament=tournament,
            round_number=round_num,
            name=f'Раунд {round_num}'
        )

        # Обновляем текущий ранк участников
        for rank, participant in enumerate(participants, start=1):
            participant.current_rank = rank
            participant.save()

        # Формируем пары по рейтингу
        matches = []
        match_num = 1

        for i in range(0, num_players, 4):
            if i + 3 < num_players:
                # Берем 4 игрока подряд
                p1, p2, p3, p4 = participants[i:i+4]

                # Формируем пары: 1+2 vs 3+4
                team1 = PadelTeam.objects.create(
                    tournament=tournament,
                    player1=p1.user,
                    player2=p2.user,
                    is_temporary=True,
                    round_number=round_num
                )

                team2 = PadelTeam.objects.create(
                    tournament=tournament,
                    player1=p3.user,
                    player2=p4.user,
                    is_temporary=True,
                    round_number=round_num
                )

                match = TournamentMatch.objects.create(
                    tournament=tournament,
                    round=round_num,
                    match_number=match_num,
                    team1=team1,
                    team2=team2,
                    status='scheduled'
                )
                matches.append(match)
                match_num += 1

        return matches
```

### 3. DoublesEliminationGenerator

```python
class DoublesEliminationGenerator:
    """
    Генератор для Doubles Elimination (паддл-версия)

    Принцип:
    - Олимпийская система
    - Постоянные пары
    - Как текущий SingleElimination, но для пар
    """

    @staticmethod
    def generate(tournament):
        """Почти как текущий, но работает с PadelTeam вместо User"""

        # Получаем постоянные пары
        participants = list(
            tournament.participants.filter(payment_status='paid')
            .order_by('seed', 'registered_at')
        )

        # Создаем постоянные команды
        teams = []
        for participant in participants:
            if participant.partner:
                team = PadelTeam.objects.create(
                    tournament=tournament,
                    player1=participant.user,
                    player2=participant.partner,
                    name=participant.team_name or '',
                    seed=participant.seed,
                    is_temporary=False
                )
                teams.append(team)

        num_teams = len(teams)
        if num_teams < 2:
            raise ValueError("Минимум 2 пары")

        # Генерация сетки (как в SingleElimination, но для teams)
        # ... (аналогично текущему BracketGenerator) ...
```

---

## 📊 API Changes

### Новые endpoints:

```python
# Управление парами
POST /tournament/api/<id>/create-team/
    {
        "player1_id": 1,
        "player2_id": 2,
        "name": "Los Campeones"  # optional
    }

# Для Americano - генерация всех раундов сразу
POST /tournament/api/<id>/generate-americano/

# Для Mexicano - генерация следующего раунда
POST /tournament/api/<id>/generate-next-mexicano-round/

# Установка счета (новый формат)
POST /tournament/api/matches/<id>/set-score/
    {
        "team1_score": 18,
        "team2_score": 12
    }

# Таблица Americano/Mexicano (leaderboard)
GET /tournament/api/<id>/leaderboard/
    Response: [
        {
            "rank": 1,
            "user_id": 5,
            "user_name": "John Doe",
            "total_points": 156,
            "matches_played": 7,
            "wins": 5,
            "losses": 2
        },
        ...
    ]
```

---

## 🎨 UI Changes

### Новые элементы интерфейса:

1. **Выбор формата при создании турнира:**
   ```
   Тип турнира:
   ○ Индивидуальный зачет (Americano/Mexicano)
   ○ Командный (постоянные пары)

   Формат:
   [v] Americano        - Все играют со всеми, партнеры меняются
   [ ] Mexicano         - Пары по рейтингу после каждого раунда
   [ ] Team Americano   - Постоянные пары, все играют со всеми
   [ ] Doubles Bracket  - Постоянные пары, playoff

   Очков за матч: [24 ▼] (16/20/24/32)
   ```

2. **Страница регистрации:**
   ```
   Для Team форматов:
   ┌─────────────────────────────────┐
   │ Ваш партнер: [Выбрать...    ▼] │
   │ Название пары: [____________  ] │
   │                                 │
   │ [Зарегистрироваться]            │
   └─────────────────────────────────┘

   Для Americano:
   ┌─────────────────────────────────┐
   │ Вы играете индивидуально        │
   │ Партнеры будут меняться каждый  │
   │ раунд автоматически             │
   │                                 │
   │ [Зарегистрироваться]            │
   └─────────────────────────────────┘
   ```

3. **Таблица лидеров (для Americano/Mexicano):**
   ```
   ┌──────┬───────────────┬──────┬──────┬──────┬──────┐
   │ Rank │ Игрок         │ Очки │ Игры │ В    │ П    │
   ├──────┼───────────────┼──────┼──────┼──────┼──────┤
   │  1   │ John Doe      │ 156  │  7   │  5   │  2   │
   │  2   │ Jane Smith    │ 148  │  7   │  4   │  3   │
   │  3   │ Bob Johnson   │ 142  │  7   │  4   │  3   │
   └──────┴───────────────┴──────┴──────┴──────┴──────┘
   ```

4. **Карточка матча:**
   ```
   Раунд 3, Матч 2
   ┌─────────────────────────────────┐
   │  John + Jane      18            │
   │                   vs             │
   │  Bob + Alice      12            │
   └─────────────────────────────────┘

   Установить счет:
   Пара 1: [18] очков
   Пара 2: [12] очков
   [Сохранить результат]
   ```

---

## 🚀 План миграции

### Шаг 1: Создать новые модели (1-2 часа)
```bash
# Создать миграцию
python manage.py makemigrations tournament

# Применить
python manage.py migrate
```

### Шаг 2: Обновить генераторы (3-4 часа)
- AmericanoGenerator
- MexicanoGenerator
- DoublesEliminationGenerator

### Шаг 3: Обновить API (2-3 часа)
- Новые endpoints для пар
- Обновленная логика установки счета
- Leaderboard для Americano

### Шаг 4: Обновить UI (4-5 часов)
- Форма создания турнира
- Страница регистрации
- Таблица лидеров
- Карточки матчей

### Шаг 5: Тестирование (2-3 часа)
- Создать тестовый турнир Americano
- Сгенерировать раунды
- Установить результаты
- Проверить подсчет очков

**Итого:** ~15-20 часов работы (2-3 дня)

---

## 📚 Источники

Исследование основано на реальных источниках:

- [Padel Americano: Rules and Formats](https://padelmix.app/americano-padel)
- [Mexicano Padel Tournament Format](https://padelmix.app/mexicano-padel)
- [Mixed Americano Format](https://padelmix.app/mixed-americano)
- [Padel Tournament Styles Guide](https://padeltelegraph.com/padel-tournament-styles/)
- [How to Play Americano in Padel](https://simplepadel.com/how-to-play-an-americano-in-padel/)
- [Premier Padel 2024 Calendar](https://www.padelfip.com/2023/12/premier-padel-announces-2024-calendar/)
- [USPA Competition Structure 2025](https://padelusa.org/wp-content/uploads/2025/06/USPA-Competition-Structure-June-2025.pdf)

---

**Вывод:** Текущая система НЕ соответствует реальному паддлу. Нужна переделка под парный формат + добавление Americano/Mexicano.

**Статус:** План готов, можно начинать реализацию!

---

**Автор:** Claude Sonnet 4.5
**Дата:** 2026-02-02
