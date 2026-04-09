"""
Модуль аналитики для игроков и администраторов
Статистика игр, активности, предпочтений
"""

from django.db.models import Count, Sum, Q, Avg, F, Case, When, Value, IntegerField
from django.db.models.functions import TruncMonth, TruncWeek, TruncDate, ExtractWeekDay
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta
from collections import defaultdict
from booking.models import Booking, Court
from .models import PlayerRating
from django.contrib.auth.models import User


def get_player_stats(user):
    """
    Полная статистика игрока (кэшируется на 5 минут)

    Возвращает:
    - Общие показатели (игры, часы, траты)
    - Любимые корты и партнеры
    - Активность по месяцам/неделям
    - Прогресс рейтинга
    """
    cache_key = f'player_stats_{user.id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    result = _compute_player_stats(user)
    cache.set(cache_key, result, timeout=300)
    return result


def invalidate_player_stats_cache(user_id):
    """Сбросить кэш статистики игрока при обновлении данных"""
    cache.delete(f'player_stats_{user_id}')


def _compute_player_stats(user):
    """Внутренняя функция вычисления статистики (без кэша)"""
    today = timezone.now().date()

    # Все завершенные игры пользователя (как создатель или партнер)
    completed_bookings = Booking.objects.filter(
        Q(user=user) | Q(partners=user),
        status='confirmed',
        date__lte=today
    ).select_related('court').prefetch_related('partners')

    # Будущие игры
    upcoming_bookings = Booking.objects.filter(
        Q(user=user) | Q(partners=user),
        status__in=['pending', 'confirmed'],
        date__gte=today
    ).select_related('court').prefetch_related('partners')

    # Общая статистика
    total_games = completed_bookings.count()
    total_hours = sum(_calculate_duration(b) for b in completed_bookings)

    # Расчет затрат
    total_spent = 0
    for booking in completed_bookings:
        if booking.user == user:
            # Если создатель - платит за корт
            total_spent += float(booking.total_price)
        else:
            # Если партнер - платит свою долю
            total_spent += float(booking.price_per_person)

    # Любимый корт
    favorite_court = completed_bookings.values(
        'court__id', 'court__name'
    ).annotate(
        games_count=Count('id')
    ).order_by('-games_count').first()

    # Любимые партнеры (топ-5)
    favorite_partners = []
    partner_stats = defaultdict(int)

    for booking in completed_bookings:
        if booking.user == user:
            # Считаем партнеров из бронирований где мы создатель
            for partner in booking.partners.all():
                partner_stats[partner.id] += 1
        elif user in booking.partners.all():
            # Считаем создателя если мы партнер
            partner_stats[booking.user.id] += 1
            # И других партнеров
            for partner in booking.partners.all():
                if partner != user:
                    partner_stats[partner.id] += 1

    # Топ-5 партнеров
    sorted_partners = sorted(partner_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    for partner_id, games_count in sorted_partners:
        try:
            partner = User.objects.get(id=partner_id)
            favorite_partners.append({
                'user': partner,
                'games_count': games_count,
                'full_name': f"{partner.first_name} {partner.last_name}".strip() or partner.username
            })
        except User.DoesNotExist:
            continue

    # Активность по месяцам (последние 12 месяцев)
    twelve_months_ago = today - timedelta(days=365)
    monthly_activity = completed_bookings.filter(
        date__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        games=Count('id')
    ).order_by('month')

    # Активность по дням недели
    weekday_activity = completed_bookings.annotate(
        weekday=ExtractWeekDay('date')
    ).values('weekday').annotate(
        games=Count('id')
    ).order_by('weekday')

    weekday_names = {
        1: 'Воскресенье',
        2: 'Понедельник',
        3: 'Вторник',
        4: 'Среда',
        5: 'Четверг',
        6: 'Пятница',
        7: 'Суббота'
    }

    weekday_stats = [
        {
            'day': weekday_names.get(item['weekday'], 'Неизвестно'),
            'games': item['games']
        }
        for item in weekday_activity
    ]

    # Прогресс рейтинга (если есть история)
    rating_progress = []
    current_rating = None

    try:
        player_rating = user.rating
        rating_history = player_rating.rating_history or []

        # Берем последние 10 изменений
        rating_progress = rating_history[-10:] if len(rating_history) > 10 else rating_history

        current_rating = {
            'numeric': float(player_rating.numeric_rating),
            'level': player_rating.level,
            'progress_percentage': player_rating.get_progress_percentage()
        }
    except (PlayerRating.DoesNotExist, AttributeError):
        current_rating = None
        rating_progress = []

    # Частота игр (среднее за последние 4 недели)
    four_weeks_ago = today - timedelta(weeks=4)
    recent_games = completed_bookings.filter(date__gte=four_weeks_ago).count()
    games_per_week = round(recent_games / 4, 1)

    # Достижения (простая система бейджей)
    achievements = _calculate_achievements(
        total_games,
        total_hours,
        len(favorite_partners),
        games_per_week
    )

    # ========== ДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА ДЛЯ УЛУЧШЕННОГО ПРОФИЛЯ ==========

    # Количество уникальных партнеров
    unique_partners = len(partner_stats)

    # Игры в этом месяце
    first_day_of_month = today.replace(day=1)
    games_this_month = completed_bookings.filter(date__gte=first_day_of_month).count()

    # Статистика турниров (если есть связанная модель)
    try:
        from tournament.models import Tournament, TournamentParticipant

        # Участие в турнирах
        tournament_participations = TournamentParticipant.objects.filter(
            user=user
        ).select_related('tournament')

        tournaments_played = tournament_participations.count()
        tournaments_won = tournament_participations.filter(
            final_position=1  # Первое место
        ).count()
    except (ImportError, Exception):
        # Если модели турниров нет или ошибка
        tournaments_played = 0
        tournaments_won = 0

    # Победы и поражения (если есть данные в бронированиях или турнирах)
    # Пока используем простую оценку: половина игр = победы (можно улучшить)
    wins = total_games // 2
    win_rate = 50.0 if total_games > 0 else 0

    # Эффективность игрока (базируется на рейтинге и активности)
    # Формула: (рейтинг / 7.0) * 50% + (активность / максимум) * 50%
    if current_rating:
        rating_efficiency = (current_rating['numeric'] / 7.0) * 50
    else:
        rating_efficiency = 0

    # Активность: если играет >= 3 раз в неделю = 100%, иначе пропорционально
    activity_efficiency = min((games_per_week / 3.0) * 50, 50)

    efficiency = round(rating_efficiency + activity_efficiency, 1)

    # Детальная статистика игры (пока заглушки, можно добавить позже)
    # TODO: Добавить реальный трекинг этих метрик
    serve_accuracy = 0  # Точность подач (%)
    rallies_won = 0     # Выигранные розыгрыши (%)
    successful_shots = 0  # Успешные удары (%)

    return {
        'total_games': total_games,
        'total_hours': round(total_hours, 1),
        'total_spent': round(total_spent, 2),
        'upcoming_games': upcoming_bookings.count(),
        'games_per_week': games_per_week,

        'favorite_court': favorite_court,
        'favorite_partners': favorite_partners,

        'monthly_activity': list(monthly_activity),
        'weekday_stats': weekday_stats,

        'current_rating': current_rating,
        'rating_progress': rating_progress,

        'achievements': achievements,

        # Новые метрики для улучшенного профиля
        'unique_partners': unique_partners,
        'games_this_month': games_this_month,
        'tournaments_played': tournaments_played,
        'tournaments_won': tournaments_won,
        'wins': wins,
        'win_rate': win_rate,
        'efficiency': efficiency,
        'serve_accuracy': serve_accuracy,
        'rallies_won': rallies_won,
        'successful_shots': successful_shots,
    }


def get_calendar_events(user, start_date, end_date):
    """
    Получить события для календаря в формате FullCalendar

    Args:
        user: Пользователь
        start_date: Начало периода
        end_date: Конец периода

    Returns:
        List событий в формате FullCalendar

    ПОКАЗЫВАЕМ ТОЛЬКО:
    1. Свои бронирования (где пользователь создатель или партнёр)
    2. Брони "Найди партнёра" с подходящим уровнем игры
    """
    # Получаем рейтинг пользователя
    try:
        user_rating = user.rating.level
    except (AttributeError, PlayerRating.DoesNotExist):
        user_rating = None

    # Свои бронирования (создатель или партнёр)
    my_bookings = Booking.objects.filter(
        Q(user=user) | Q(partners=user),
        date__gte=start_date,
        date__lte=end_date
    ).select_related('court', 'user', 'user__profile').prefetch_related('partners')

    # Брони "Найди партнёра" с подходящим уровнем (не свои)
    partner_bookings = Booking.objects.filter(
        looking_for_partner=True,
        status__in=['pending', 'confirmed'],
        date__gte=start_date,
        date__lte=end_date
    ).exclude(
        Q(user=user) | Q(partners=user)
    ).select_related('court', 'user', 'user__profile').prefetch_related('partners')

    # Фильтруем брони "Найди партнёра" по уровню игры
    filtered_partner_bookings = []
    for booking in partner_bookings:
        # Если не заполнено и требуемые уровни не указаны - показываем
        if not booking.is_full:
            required_levels = booking.required_rating_levels or []
            if not required_levels:
                # Нет требования к уровню - доступно всем
                filtered_partner_bookings.append(booking)
            elif user_rating and user_rating in required_levels:
                # Уровень совпадает с одним из требуемых - показываем
                filtered_partner_bookings.append(booking)
            # Иначе не показываем

    events = []

    # Обрабатываем свои бронирования
    for booking in my_bookings:
        is_my_booking = True

        if booking.status == 'confirmed':
            color = '#10b981'  # Зеленый - моё подтвержденное
        elif booking.status == 'pending':
            color = '#f59e0b'  # Оранжевый - моё ожидает
        else:
            color = '#6b7280'  # Серый - отменено

        title = f"🎾 {booking.court.name}"
        if booking.partners.exists():
            title += f" ({booking.partners.count() + 1} игроков)"

        creator_name = f"{booking.user.first_name} {booking.user.last_name}".strip() or booking.user.username

        # Создаем datetime объекты
        start_datetime = timezone.make_aware(
            datetime.combine(booking.date, booking.start_time)
        )
        end_datetime = timezone.make_aware(
            datetime.combine(booking.date, booking.end_time)
        )

        event = {
            'id': booking.id,
            'title': title,
            'start': start_datetime.isoformat(),
            'end': end_datetime.isoformat(),
            'color': color,
            'extendedProps': {
                'bookingId': booking.id,
                'courtId': booking.court.id,
                'courtName': booking.court.name,
                'creatorName': creator_name,
                'status': booking.status,
                'price': float(booking.total_price),
                'isMine': is_my_booking,
                'canJoin': False,  # Свои брони - не можем присоединиться
                'partnersCount': booking.partners.count(),
                'maxPlayers': booking.max_players,
                'lookingForPartner': booking.looking_for_partner,
            }
        }

        events.append(event)

    # Обрабатываем брони "Найди партнёра"
    for booking in filtered_partner_bookings:
        is_my_booking = False
        color = '#3b82f6'  # Синий - можно присоединиться

        creator_name = f"{booking.user.first_name} {booking.user.last_name}".strip() or booking.user.username

        title = f"🔍 {booking.court.name} - Ищут партнёра"
        required_levels = booking.required_rating_levels or []
        if required_levels:
            levels_str = ", ".join(required_levels)
            title += f" ({levels_str})"

        # Создаем datetime объекты
        start_datetime = timezone.make_aware(
            datetime.combine(booking.date, booking.start_time)
        )
        end_datetime = timezone.make_aware(
            datetime.combine(booking.date, booking.end_time)
        )

        event = {
            'id': booking.id,
            'title': title,
            'start': start_datetime.isoformat(),
            'end': end_datetime.isoformat(),
            'color': color,
            'extendedProps': {
                'bookingId': booking.id,
                'courtId': booking.court.id,
                'courtName': booking.court.name,
                'creatorName': creator_name,
                'status': booking.status,
                'price': float(booking.price_per_person),
                'isMine': is_my_booking,
                'canJoin': True,  # Доступно для присоединения
                'partnersCount': booking.partners.count(),
                'maxPlayers': booking.max_players,
                'lookingForPartner': booking.looking_for_partner,
                'requiredRatings': booking.required_rating_levels or [],
            }
        }

        events.append(event)

    return events


def get_available_slots(court_id, date):
    """
    Получить доступные слоты для бронирования на конкретный день

    Args:
        court_id: ID корта
        date: Дата (date object)

    Returns:
        List доступных временных слотов
    """
    try:
        court = Court.objects.get(id=court_id)
    except Court.DoesNotExist:
        return []

    # Рабочие часы (можно вынести в настройки)
    WORKING_HOURS_START = 8
    WORKING_HOURS_END = 22
    SLOT_DURATION = 1  # часы

    # Получаем занятые слоты
    existing_bookings = Booking.objects.filter(
        court=court,
        date=date,
        status__in=['pending', 'confirmed']
    ).values('start_time', 'end_time')

    occupied_slots = []
    for booking in existing_bookings:
        start = booking['start_time'].hour + booking['start_time'].minute / 60
        end = booking['end_time'].hour + booking['end_time'].minute / 60
        occupied_slots.append((start, end))

    # Генерируем свободные слоты
    available_slots = []
    current_hour = WORKING_HOURS_START

    while current_hour < WORKING_HOURS_END:
        slot_start = current_hour
        slot_end = current_hour + SLOT_DURATION

        # Проверяем, не занят ли слот
        is_occupied = False
        for occupied_start, occupied_end in occupied_slots:
            if not (slot_end <= occupied_start or slot_start >= occupied_end):
                is_occupied = True
                break

        if not is_occupied:
            available_slots.append({
                'start': f"{int(slot_start):02d}:00",
                'end': f"{int(slot_end):02d}:00",
                'price': float(court.price_per_hour) * SLOT_DURATION
            })

        current_hour += SLOT_DURATION

    return available_slots


def get_admin_dashboard_stats():
    """
    Статистика для администратора
    """
    today = timezone.now().date()

    # Сегодняшние бронирования
    today_bookings = Booking.objects.filter(date=today)

    # Выручка за сегодня
    today_revenue = today_bookings.filter(
        status='confirmed'
    ).aggregate(
        total=Sum('court__price_per_hour')
    )['total'] or 0

    # Загруженность кортов (%)
    total_hours = (22 - 8)  # Рабочие часы
    courts_count = Court.objects.filter(is_available=True).count()
    total_possible_bookings = total_hours * courts_count

    actual_bookings = today_bookings.filter(status__in=['pending', 'confirmed']).count()
    occupancy_rate = round((actual_bookings / total_possible_bookings * 100) if total_possible_bookings > 0 else 0, 1)

    # Популярные времена
    popular_times = Booking.objects.filter(
        date__gte=today - timedelta(days=30),
        status='confirmed'
    ).annotate(
        hour=F('start_time__hour')
    ).values('hour').annotate(
        bookings=Count('id')
    ).order_by('-bookings')[:5]

    # Выручка по кортам (за месяц)
    revenue_by_court = Booking.objects.filter(
        date__gte=today - timedelta(days=30),
        status='confirmed'
    ).values(
        'court__name'
    ).annotate(
        revenue=Sum('court__price_per_hour'),
        bookings=Count('id')
    ).order_by('-revenue')

    # Новые пользователи за неделю
    new_users_week = User.objects.filter(
        date_joined__gte=today - timedelta(days=7)
    ).count()

    return {
        'today_bookings': today_bookings.count(),
        'today_revenue': float(today_revenue),
        'occupancy_rate': occupancy_rate,
        'popular_times': list(popular_times),
        'revenue_by_court': list(revenue_by_court),
        'new_users_this_week': new_users_week,
    }


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def _calculate_duration(booking):
    """Рассчитать продолжительность бронирования в часах"""
    start_dt = datetime.combine(booking.date, booking.start_time)
    end_dt = datetime.combine(booking.date, booking.end_time)

    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    duration_seconds = (end_dt - start_dt).total_seconds()
    return duration_seconds / 3600


def _calculate_achievements(total_games, total_hours, partners_count, games_per_week):
    """
    Рассчитать достижения (бейджи) игрока

    Returns:
        List словарей с достижениями
    """
    achievements = []

    # Достижения по количеству игр
    game_milestones = [
        (1, "🎾 Первая игра", "Сыграли первую игру!", "bronze"),
        (10, "🏆 Новичок", "10 игр сыграно", "bronze"),
        (50, "⭐ Любитель", "50 игр сыграно", "silver"),
        (100, "💎 Профи", "100 игр сыграно", "gold"),
        (250, "👑 Мастер", "250 игр сыграно", "platinum"),
        (500, "🔥 Легенда", "500 игр сыграно", "diamond"),
    ]

    for threshold, title, description, badge_type in game_milestones:
        if total_games >= threshold:
            achievements.append({
                'title': title,
                'description': description,
                'type': badge_type,
                'unlocked': True,
                'progress': 100,
            })
        else:
            # Следующее достижение с прогрессом
            progress = int((total_games / threshold) * 100)
            achievements.append({
                'title': title,
                'description': description,
                'type': badge_type,
                'unlocked': False,
                'progress': progress,
            })
            break  # Показываем только следующее недостигнутое

    # Достижения по часам
    if total_hours >= 100:
        achievements.append({
            'title': "⏰ Марафонец",
            'description': f"{int(total_hours)} часов на корте",
            'type': 'gold',
            'unlocked': True,
            'progress': 100,
        })

    # Достижения по социальности
    if partners_count >= 10:
        achievements.append({
            'title': "🤝 Командный игрок",
            'description': f"Играли с {partners_count} разными партнерами",
            'type': 'silver',
            'unlocked': True,
            'progress': 100,
        })

    # Достижения по регулярности
    if games_per_week >= 3:
        achievements.append({
            'title': "🔥 Активист",
            'description': f"{games_per_week} игр в неделю",
            'type': 'gold',
            'unlocked': True,
            'progress': 100,
        })

    return achievements


def get_rating_chart_data(user, months=3):
    """
    Получить данные для графика изменения рейтинга за последние N месяцев

    Args:
        user: Пользователь
        months: Количество месяцев для отображения (по умолчанию 3)

    Returns:
        Dict с данными для Chart.js:
        {
            'labels': ['2026-01-01', '2026-01-15', ...],
            'values': [3.5, 3.6, 3.7, ...],
            'levels': ['C', 'C', 'C+', ...]
        }
    """
    try:
        rating = user.rating
        history = rating.rating_history or []

        if not history:
            # Если истории нет, возвращаем только текущий рейтинг
            return {
                'labels': [timezone.now().date().isoformat()],
                'values': [float(rating.numeric_rating)],
                'levels': [rating.level]
            }

        # Вычисляем дату отсечения
        cutoff_date = timezone.now() - timedelta(days=30 * months)

        # Фильтруем историю за последние N месяцев
        filtered_history = []
        for entry in history:
            try:
                entry_date = datetime.fromisoformat(entry['date'])
                # Если дата без timezone, считаем её локальной
                if timezone.is_naive(entry_date):
                    entry_date = timezone.make_aware(entry_date)

                if entry_date >= cutoff_date:
                    filtered_history.append(entry)
            except (KeyError, ValueError, TypeError):
                continue

        # Сортируем по дате
        filtered_history.sort(key=lambda x: x.get('date', ''))

        # Формируем данные для графика
        labels = []
        values = []
        levels = []

        for entry in filtered_history:
            try:
                labels.append(entry['date'][:10])  # YYYY-MM-DD
                values.append(float(entry['new_rating']))
                levels.append(entry['new_level'])
            except (KeyError, ValueError, TypeError):
                continue

        # Добавляем текущий рейтинг в конец
        labels.append(timezone.now().date().isoformat())
        values.append(float(rating.numeric_rating))
        levels.append(rating.level)

        return {
            'labels': labels,
            'values': values,
            'levels': levels
        }

    except (AttributeError, PlayerRating.DoesNotExist):
        # Если у пользователя нет рейтинга
        return {
            'labels': [],
            'values': [],
            'levels': []
        }
