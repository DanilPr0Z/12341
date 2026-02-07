"""
Утилиты для турниров
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import Tournament, TournamentParticipant, TournamentMatch
import csv
from io import StringIO


def send_tournament_notification(tournament, participant, notification_type):
    """
    Отправка уведомлений участникам турнира

    Types:
    - 'registration_confirmed' - подтверждение регистрации
    - 'tournament_starting' - турнир скоро начнется
    - 'match_scheduled' - назначен матч
    - 'match_result' - результат матча
    """

    subject_map = {
        'registration_confirmed': f'Регистрация на турнир "{tournament.name}" подтверждена',
        'tournament_starting': f'Турнир "{tournament.name}" начинается завтра!',
        'match_scheduled': f'Ваш матч в турнире "{tournament.name}" назначен',
        'match_result': f'Результаты матча в турнире "{tournament.name}"',
    }

    subject = subject_map.get(notification_type, f'Уведомление о турнире "{tournament.name}"')

    # Здесь можно добавить рендеринг HTML шаблонов для красивых писем
    message = f"""
    Здравствуйте, {participant.user.get_full_name()}!

    {subject}

    Турнир: {tournament.name}
    Даты: {tournament.start_date} - {tournament.end_date}
    Место: [Адрес площадки]

    С уважением,
    Команда Paddle Booking
    """

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [participant.user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def export_tournament_results_csv(tournament):
    """Экспорт результатов турнира в CSV"""

    output = StringIO()
    writer = csv.writer(output)

    # Заголовки
    writer.writerow([
        'Место',
        'Участник',
        'Email',
        'Рейтинг',
        'Побед',
        'Поражений',
        'Посев'
    ])

    # Получаем участников с результатами
    participants = tournament.participants.all().order_by('final_position', '-seed')

    for participant in participants:
        # Подсчитываем статистику матчей
        wins = TournamentMatch.objects.filter(
            tournament=tournament,
            winner=participant.user
        ).count()

        losses = TournamentMatch.objects.filter(
            tournament=tournament,
            status='completed'
        ).filter(
            player1=participant.user
        ).exclude(winner=participant.user).count() + \
        TournamentMatch.objects.filter(
            tournament=tournament,
            status='completed'
        ).filter(
            player2=participant.user
        ).exclude(winner=participant.user).count()

        writer.writerow([
            participant.final_position or '-',
            participant.user.get_full_name(),
            participant.user.email,
            getattr(participant.user.rating, 'numeric_rating', '-') if hasattr(participant.user, 'rating') else '-',
            wins,
            losses,
            participant.seed or '-'
        ])

    return output.getvalue()


def calculate_tournament_statistics(tournament):
    """Расчет статистики турнира"""

    total_matches = tournament.matches.count()
    completed_matches = tournament.matches.filter(status='completed').count()
    scheduled_matches = tournament.matches.filter(status='scheduled').count()

    # Самый результативный игрок
    from django.db.models import Count
    top_winner = None
    max_wins = 0

    for participant in tournament.participants.all():
        wins = tournament.matches.filter(winner=participant.user).count()
        if wins > max_wins:
            max_wins = wins
            top_winner = participant.user

    return {
        'total_matches': total_matches,
        'completed_matches': completed_matches,
        'scheduled_matches': scheduled_matches,
        'completion_percentage': (completed_matches / total_matches * 100) if total_matches > 0 else 0,
        'top_winner': top_winner.get_full_name() if top_winner else None,
        'max_wins': max_wins,
        'total_participants': tournament.participants.count(),
        'paid_participants': tournament.participants.filter(payment_status='paid').count(),
    }


def auto_complete_tournament(tournament):
    """Автоматическое завершение турнира и определение мест"""

    # Проверяем что все матчи сыграны
    if tournament.matches.filter(status__in=['scheduled', 'in_progress']).exists():
        return False, "Не все матчи завершены"

    # Для олимпийской системы определяем места
    if tournament.format == 'single_elimination':
        # Финал - определяет 1 и 2 место
        final_round = tournament.rounds.order_by('-round_number').first()
        if final_round:
            final_match = tournament.matches.filter(round=final_round.round_number).first()
            if final_match and final_match.winner:
                # 1 место - победитель финала
                winner_participant = tournament.participants.get(user=final_match.winner)
                winner_participant.final_position = 1
                winner_participant.save()

                # 2 место - проигравший в финале
                loser = final_match.player1 if final_match.winner == final_match.player2 else final_match.player2
                loser_participant = tournament.participants.get(user=loser)
                loser_participant.final_position = 2
                loser_participant.save()

        # Полуфиналы - 3-4 места
        if tournament.rounds.count() >= 2:
            semifinal_round = tournament.rounds.order_by('-round_number')[1]
            position = 3
            for match in tournament.matches.filter(round=semifinal_round.round_number):
                if match.winner:
                    loser = match.player1 if match.winner == match.player2 else match.player2
                    if loser:
                        loser_participant = tournament.participants.get(user=loser)
                        loser_participant.final_position = position
                        loser_participant.save()
                        position += 1

    # Для круговой системы сортируем по победам
    elif tournament.format == 'round_robin':
        participants_with_wins = []
        for participant in tournament.participants.all():
            wins = tournament.matches.filter(winner=participant.user).count()
            participants_with_wins.append((participant, wins))

        # Сортируем по убыванию побед
        participants_with_wins.sort(key=lambda x: x[1], reverse=True)

        # Присваиваем места
        for position, (participant, wins) in enumerate(participants_with_wins, start=1):
            participant.final_position = position
            participant.save()

    # Меняем статус турнира
    tournament.status = 'completed'
    tournament.save()

    return True, "Турнир завершен"


def validate_match_schedule(tournament, scheduled_date, scheduled_time, court):
    """Проверка доступности корта для матча"""

    # Проверяем что дата в пределах турнира
    if scheduled_date < tournament.start_date or scheduled_date > tournament.end_date:
        return False, "Дата вне периода турнира"

    # Проверяем занятость корта
    from datetime import datetime, timedelta
    from booking.models import Booking

    # Создаем временной интервал (предполагаем матч длится 2 часа)
    start_datetime = datetime.combine(scheduled_date, scheduled_time)
    end_datetime = start_datetime + timedelta(hours=2)

    # Проверяем конфликты с бронированиями
    conflicts = Booking.objects.filter(
        court=court,
        date=scheduled_date,
        start_time__lt=end_datetime.time(),
        end_time__gt=scheduled_time
    ).exists()

    if conflicts:
        return False, "Корт занят в это время"

    # Проверяем конфликты с другими матчами турнира
    match_conflicts = TournamentMatch.objects.filter(
        court=court,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time
    ).exists()

    if match_conflicts:
        return False, "На этом корте уже назначен матч"

    return True, "Корт доступен"


def generate_tournament_bracket_pdf(tournament):
    """
    Генерация PDF с турнирной сеткой

    Args:
        tournament: Объект Tournament

    Returns:
        BytesIO buffer с PDF или None при ошибке
    """
    try:
        from .pdf_generator import generate_tournament_bracket_pdf as generate_pdf
        return generate_pdf(tournament)
    except ImportError:
        print("⚠️  ReportLab не установлен. Установите: pip install reportlab")
        return None
    except Exception as e:
        print(f"Ошибка генерации PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


def update_player_ratings_after_tournament(tournament):
    """
    Обновление рейтингов игроков после завершения турнира
    Использует систему Elo с учетом силы соперников

    Args:
        tournament: объект Tournament

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        from .rating_system import update_player_ratings_after_tournament as update_ratings
        return update_ratings(tournament)
    except Exception as e:
        print(f"Ошибка обновления рейтингов: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Ошибка: {str(e)}"
