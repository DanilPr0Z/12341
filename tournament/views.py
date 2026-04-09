"""
API Views для управления турнирами
Обновлено для поддержки паддл-турниров (2v2) с новыми форматами
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q, Count
from django.contrib.auth.models import User
from datetime import datetime
import json

from .models import (
    Tournament, TournamentParticipant, TournamentMatch,
    TournamentRound, PadelTeam
)
from .bracket_generator import (
    AmericanoGenerator
)


# Декоратор для проверки прав
def staff_required(view_func):
    """Decorator that checks if user is staff"""
    @login_required(login_url='/users/login/')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden(
                '<h1>403 Доступ запрещён</h1>'
                '<p>Эта страница доступна только администраторам.</p>'
                '<p><a href="/">Вернуться на главную</a></p>'
            )
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================================================
# СТРАНИЦЫ (HTML) - АДМИНКА
# =============================================================================

@staff_required
def tournaments_list(request):
    """Страница списка турниров"""
    context = {'current_page': 'tournaments'}
    return render(request, 'manager/tournaments.html', context)


@staff_required
def tournament_detail(request, tournament_id):
    """Детальная страница турнира"""
    tournament = get_object_or_404(Tournament, id=tournament_id)
    context = {
        'current_page': 'tournaments',
        'tournament': tournament
    }
    return render(request, 'manager/tournament_detail.html', context)


# =============================================================================
# ПУБЛИЧНЫЕ СТРАНИЦЫ ДЛЯ ИГРОКОВ
# =============================================================================

def public_tournaments_list(request):
    """Публичная страница списка турниров для игроков"""
    tournaments = Tournament.objects.filter(
        status__in=['registration_open', 'in_progress', 'completed']
    ).order_by('-start_date')

    context = {
        'tournaments': tournaments
    }
    return render(request, 'tournament/public_tournaments.html', context)


def public_tournament_detail(request, tournament_id):
    """Публичная детальная страница турнира"""
    tournament = get_object_or_404(Tournament, id=tournament_id)

    # Проверяем может ли пользователь зарегистрироваться
    can_register = False
    register_message = None

    if request.user.is_authenticated:
        can_register, register_message = tournament.can_register(request.user)

    # Загружаем участников для отображения на странице (серверный рендеринг)
    participants = tournament.participants.select_related(
        'user', 'user__profile', 'user__rating'
    ).order_by('-total_points', '-matches_won', 'registered_at')

    context = {
        'tournament': tournament,
        'can_register': can_register,
        'register_message': register_message,
        'is_registered': tournament.participants.filter(user=request.user).exists() if request.user.is_authenticated else False,
        'participants_list': participants,
    }
    return render(request, 'tournament/public_tournament_detail.html', context)


@require_POST
def public_tournament_register(request, tournament_id):
    """Регистрация игрока на турнир"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Необходимо войти в систему'}, status=401)

    tournament = get_object_or_404(Tournament, id=tournament_id)

    # Проверяем возможность регистрации
    can_register, message = tournament.can_register(request.user)
    if not can_register:
        return JsonResponse({'success': False, 'error': message}, status=400)

    # Для Team форматов нужен партнер
    if tournament.is_team_tournament:
        # Пока просто создаем, партнера можно указать позже
        participant = TournamentParticipant.objects.create(
            tournament=tournament,
            user=request.user,
            payment_status='pending' if tournament.entry_fee > 0 else 'paid'
        )
    else:
        # Индивидуальный зачет (Americano/Mexicano)
        participant = TournamentParticipant.objects.create(
            tournament=tournament,
            user=request.user,
            payment_status='pending' if tournament.entry_fee > 0 else 'paid'
        )

    return JsonResponse({
        'success': True,
        'message': 'Вы успешно зарегистрировались на турнир!',
        'participant_id': participant.id
    })


@require_POST
def public_tournament_unregister(request, tournament_id):
    """Отмена регистрации игрока"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Необходимо войти в систему'}, status=401)

    tournament = get_object_or_404(Tournament, id=tournament_id)
    participant = get_object_or_404(TournamentParticipant, tournament=tournament, user=request.user)

    # Проверяем что турнир еще не начался
    if tournament.status not in ['draft', 'registration_open', 'registration_closed']:
        return JsonResponse({'success': False, 'error': 'Нельзя отменить регистрацию после начала турнира'}, status=400)

    participant.delete()

    return JsonResponse({
        'success': True,
        'message': 'Регистрация отменена'
    })


# =============================================================================
# API ENDPOINTS - СПИСОК И CRUD ТУРНИРОВ
# =============================================================================

@staff_required
def api_tournaments_list(request):
    """API: Список всех турниров"""
    try:
        tournaments = Tournament.objects.all().order_by('-start_date')

        tournaments_data = []
        for tournament in tournaments:
            tournaments_data.append({
                'id': tournament.id,
                'name': tournament.name,
                'description': tournament.description,
                'start_date': tournament.start_date.isoformat(),
                'end_date': tournament.end_date.isoformat(),
                'registration_deadline': tournament.registration_deadline.isoformat(),
                'max_participants': tournament.max_participants,
                'participants_count': tournament.participants_count,
                'available_slots': tournament.available_slots,
                'entry_fee': float(tournament.entry_fee),
                'prize_pool': float(tournament.prize_pool),
                'format': tournament.format,
                'format_display': tournament.get_format_display(),
                'is_team_tournament': tournament.is_team_tournament,
                'is_mixed': tournament.is_mixed,
                'points_per_match': tournament.points_per_match,
                'status': tournament.status,
                'status_display': tournament.get_status_display(),
                'is_registration_open': tournament.is_registration_open,
                'is_full': tournament.is_full,
                'min_rating': float(tournament.min_rating) if tournament.min_rating else None,
                'max_rating': float(tournament.max_rating) if tournament.max_rating else None,
                'organizer_name': tournament.organizer.get_full_name(),
                'image': tournament.image.url if tournament.image else None,
            })

        # Статистика
        stats = {
            'total_tournaments': tournaments.count(),
            'active_tournaments': tournaments.filter(status='in_progress').count(),
            'upcoming_tournaments': tournaments.filter(status='registration_open').count(),
            'completed_tournaments': tournaments.filter(status='completed').count(),
        }

        return JsonResponse({
            'success': True,
            'tournaments': tournaments_data,
            'stats': stats
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
def api_tournament_detail(request, tournament_id):
    """API: Детали турнира"""
    try:
        tournament = get_object_or_404(Tournament, id=tournament_id)

        # Участники
        participants = []
        for participant in tournament.participants.all().order_by('-total_points', 'registered_at'):
            participants.append({
                'id': participant.id,
                'user_id': participant.user.id,
                'user_name': participant.user.get_full_name() or participant.user.username,
                'user_email': participant.user.email,
                'seed': participant.seed,
                'payment_status': participant.payment_status,
                'payment_date': participant.payment_date.isoformat() if participant.payment_date else None,
                'registered_at': participant.registered_at.isoformat(),
                'rating': float(participant.user.rating.numeric_rating) if hasattr(participant.user, 'rating') else None,
                # Для Americano/Mexicano
                'total_points': participant.total_points,
                'matches_played': participant.matches_played,
                'matches_won': participant.matches_won,
                'matches_lost': participant.matches_lost,
                'current_rank': participant.current_rank,
                # Для Team форматов
                'partner_id': participant.partner.id if participant.partner else None,
                'partner_name': participant.partner.get_full_name() if participant.partner else None,
                'team_name': participant.team_name,
            })

        # Матчи по раундам
        rounds = []
        for round_obj in tournament.rounds.all().order_by('round_number'):
            matches_in_round = []
            for match in tournament.matches.filter(round=round_obj.round_number).order_by('match_number'):
                match_data = {
                    'id': match.id,
                    'match_number': match.match_number,
                    'status': match.status,
                    'scheduled_date': match.scheduled_date.isoformat() if match.scheduled_date else None,
                    'scheduled_time': match.scheduled_time.strftime('%H:%M') if match.scheduled_time else None,
                    'court_id': match.court.id if match.court else None,
                    'court_name': match.court.name if match.court else None,
                    'is_ready_to_play': match.is_ready_to_play,
                    # НОВОЕ: Пары вместо индивидуальных игроков
                    'team1_id': match.team1.id if match.team1 else None,
                    'team1_name': str(match.team1) if match.team1 else 'TBD',
                    'team1_player1': match.team1.player1.get_full_name() if match.team1 else None,
                    'team1_player2': match.team1.player2.get_full_name() if match.team1 else None,
                    'team2_id': match.team2.id if match.team2 else None,
                    'team2_name': str(match.team2) if match.team2 else 'TBD',
                    'team2_player1': match.team2.player1.get_full_name() if match.team2 else None,
                    'team2_player2': match.team2.player2.get_full_name() if match.team2 else None,
                    'winning_team_id': match.winning_team.id if match.winning_team else None,
                    'score_team1': match.score_team1,
                    'score_team2': match.score_team2,
                    'score_display': match.score_display,
                }
                matches_in_round.append(match_data)

            rounds.append({
                'round_number': round_obj.round_number,
                'name': round_obj.name,
                'start_date': round_obj.start_date.isoformat() if round_obj.start_date else None,
                'is_completed': round_obj.is_completed,
                'completion_percentage': round_obj.completion_percentage,
                'matches': matches_in_round
            })

        tournament_data = {
            'id': tournament.id,
            'name': tournament.name,
            'description': tournament.description,
            'start_date': tournament.start_date.isoformat(),
            'end_date': tournament.end_date.isoformat(),
            'registration_deadline': tournament.registration_deadline.isoformat(),
            'max_participants': tournament.max_participants,
            'participants_count': tournament.participants_count,
            'available_slots': tournament.available_slots,
            'entry_fee': float(tournament.entry_fee),
            'prize_pool': float(tournament.prize_pool),
            'format': tournament.format,
            'format_display': tournament.get_format_display(),
            'is_team_tournament': tournament.is_team_tournament,
            'is_mixed': tournament.is_mixed,
            'points_per_match': tournament.points_per_match,
            'status': tournament.status,
            'status_display': tournament.get_status_display(),
            'is_registration_open': tournament.is_registration_open,
            'is_full': tournament.is_full,
            'min_rating': float(tournament.min_rating) if tournament.min_rating else None,
            'max_rating': float(tournament.max_rating) if tournament.max_rating else None,
            'organizer_id': tournament.organizer.id,
            'organizer_name': tournament.organizer.get_full_name(),
            'image': tournament.image.url if tournament.image else None,
            'participants': participants,
            'rounds': rounds,
        }

        return JsonResponse({
            'success': True,
            'tournament': tournament_data
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
@require_POST
def api_tournament_create(request):
    """API: Создать турнир"""
    try:
        data = json.loads(request.body)

        # Валидация
        required_fields = ['name', 'start_date', 'end_date', 'registration_deadline', 'max_participants']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'success': False, 'error': f'Поле {field} обязательно'}, status=400)

        # Парсим даты
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        registration_deadline = datetime.fromisoformat(data['registration_deadline'].replace('Z', '+00:00'))

        # Создаем турнир
        # Только Round-Robin формат (americano)
        tournament_format = 'americano'

        tournament = Tournament.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            organizer=request.user,
            start_date=start_date,
            end_date=end_date,
            registration_deadline=registration_deadline,
            max_participants=int(data['max_participants']),
            entry_fee=float(data.get('entry_fee', 0)),
            prize_pool=float(data.get('prize_pool', 0)),
            format=tournament_format,
            is_team_tournament=False,  # Round-robin - индивидуальный зачет
            is_mixed=False,
            points_per_match=int(data.get('points_per_match', 24)),
            min_rating=float(data['min_rating']) if data.get('min_rating') else None,
            max_rating=float(data['max_rating']) if data.get('max_rating') else None,
            status=data.get('status', 'draft')
        )

        return JsonResponse({
            'success': True,
            'message': 'Турнир успешно создан',
            'tournament': {
                'id': tournament.id,
                'name': tournament.name,
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
@require_POST
def api_tournament_update(request, tournament_id):
    """API: Обновить турнир"""
    try:
        tournament = get_object_or_404(Tournament, id=tournament_id)
        data = json.loads(request.body)

        # Обновляем поля
        if 'name' in data:
            tournament.name = data['name']
        if 'description' in data:
            tournament.description = data['description']
        if 'start_date' in data:
            tournament.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if 'end_date' in data:
            tournament.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        if 'registration_deadline' in data:
            tournament.registration_deadline = datetime.fromisoformat(data['registration_deadline'].replace('Z', '+00:00'))
        if 'max_participants' in data:
            tournament.max_participants = int(data['max_participants'])
        if 'entry_fee' in data:
            tournament.entry_fee = float(data['entry_fee'])
        if 'prize_pool' in data:
            tournament.prize_pool = float(data['prize_pool'])
        if 'format' in data:
            tournament.format = data['format']
        if 'points_per_match' in data:
            tournament.points_per_match = int(data['points_per_match'])
        if 'min_rating' in data:
            tournament.min_rating = float(data['min_rating']) if data['min_rating'] else None
        if 'max_rating' in data:
            tournament.max_rating = float(data['max_rating']) if data['max_rating'] else None
        if 'status' in data:
            tournament.status = data['status']

        tournament.save()

        return JsonResponse({
            'success': True,
            'message': 'Турнир обновлен'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
@require_POST
def api_tournament_delete(request, tournament_id):
    """API: Удалить турнир"""
    try:
        tournament = get_object_or_404(Tournament, id=tournament_id)
        tournament_name = tournament.name
        tournament.delete()

        return JsonResponse({
            'success': True,
            'message': f'Турнир "{tournament_name}" удален'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# API - УПРАВЛЕНИЕ УЧАСТНИКАМИ
# =============================================================================

@staff_required
@require_POST
def api_tournament_add_participant(request, tournament_id):
    """API: Добавить участника в турнир"""
    try:
        tournament = get_object_or_404(Tournament, id=tournament_id)
        data = json.loads(request.body)

        user_id = data.get('user_id')
        if not user_id:
            return JsonResponse({'success': False, 'error': 'user_id обязателен'}, status=400)

        user = get_object_or_404(User, id=user_id)

        # Для Team форматов нужен партнер
        partner = None
        if tournament.is_team_tournament and data.get('partner_id'):
            partner = get_object_or_404(User, id=data['partner_id'])

        # Создаем участника
        participant, created = TournamentParticipant.objects.get_or_create(
            tournament=tournament,
            user=user,
            defaults={
                'payment_status': 'paid' if tournament.entry_fee == 0 else 'pending',
                'partner': partner,
                'team_name': data.get('team_name', '')
            }
        )

        if not created:
            return JsonResponse({'success': False, 'error': 'Пользователь уже зарегистрирован'}, status=400)

        return JsonResponse({
            'success': True,
            'message': f'{user.get_full_name()} добавлен в турнир',
            'participant': {
                'id': participant.id,
                'user_name': user.get_full_name()
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
@require_POST
def api_tournament_remove_participant(request, tournament_id, participant_id):
    """API: Удалить участника из турнира"""
    try:
        participant = get_object_or_404(TournamentParticipant, id=participant_id, tournament_id=tournament_id)
        user_name = participant.user.get_full_name()
        participant.delete()

        return JsonResponse({
            'success': True,
            'message': f'{user_name} удален из турнира'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
@require_POST
def api_tournament_set_seed(request, tournament_id, participant_id):
    """API: Установить посев участнику"""
    try:
        participant = get_object_or_404(TournamentParticipant, id=participant_id, tournament_id=tournament_id)
        data = json.loads(request.body)

        seed = data.get('seed')
        if seed is not None:
            participant.seed = int(seed)
            participant.save()

        return JsonResponse({
            'success': True,
            'message': 'Посев установлен'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# API - ГЕНЕРАЦИЯ СЕТКИ
# =============================================================================

@staff_required
@require_POST
def api_tournament_generate_bracket(request, tournament_id):
    """API: Сгенерировать турнирную сетку"""
    try:
        tournament = get_object_or_404(Tournament, id=tournament_id)

        # Проверяем статус
        if tournament.status == 'in_progress':
            return JsonResponse({
                'success': False,
                'error': 'Сетка уже сгенерирована'
            }, status=400)

        # Проверяем количество участников
        paid_count = tournament.participants.filter(payment_status='paid').count()
        if paid_count < 4:
            return JsonResponse({
                'success': False,
                'error': f'Недостаточно участников (минимум 4, оплачено: {paid_count})'
            }, status=400)

        # Генерируем сетку для Round-Robin формата
        # Все раунды генерируются сразу, пары постоянно меняются
        matches = AmericanoGenerator.generate(tournament)

        # Меняем статус турнира
        tournament.status = 'in_progress'
        tournament.save()

        return JsonResponse({
            'success': True,
            'message': f'Сетка сгенерирована! Создано {len(matches)} матчей',
            'matches_count': len(matches),
            'format': tournament.format
        })

    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
@require_POST
def api_tournament_generate_next_round(request, tournament_id):
    """API: Сгенерировать следующий раунд (не используется для round-robin, т.к. все раунды генерируются сразу)"""
    return JsonResponse({
        'success': False,
        'error': 'Для Round-Robin формата все раунды генерируются сразу при создании сетки'
    }, status=400)


# =============================================================================
# API - УПРАВЛЕНИЕ МАТЧАМИ
# =============================================================================

@staff_required
@require_POST
def api_match_set_score(request, match_id):
    """API: Установить счет матча"""
    try:
        match = get_object_or_404(TournamentMatch, id=match_id)
        data = json.loads(request.body)

        score_team1 = data.get('score_team1')
        score_team2 = data.get('score_team2')

        if score_team1 is None or score_team2 is None:
            return JsonResponse({'success': False, 'error': 'Укажите счет обеих пар'}, status=400)

        # Устанавливаем счет (это также определит победителя)
        detailed_score = data.get('detailed_score')
        match.set_score(
            team1_score=int(score_team1),
            team2_score=int(score_team2),
            detailed_score=detailed_score
        )

        return JsonResponse({
            'success': True,
            'message': f'Счет установлен: {score_team1}-{score_team2}',
            'winning_team_id': match.winning_team.id if match.winning_team else None
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
@require_POST
def api_match_set_winner(request, match_id):
    """API: Установить победителя матча (legacy, использовать api_match_set_score)"""
    # Для обратной совместимости перенаправляем на set_score
    try:
        match = get_object_or_404(TournamentMatch, id=match_id)
        data = json.loads(request.body)

        winner_id = data.get('winner_id')
        if not winner_id:
            return JsonResponse({'success': False, 'error': 'winner_id обязателен'}, status=400)

        # Определяем какая пара победила
        # Эта функция устарела для новой модели, но оставляем для совместимости
        return JsonResponse({
            'success': False,
            'error': 'Используйте api_match_set_score для установки счета'
        }, status=400)

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
@require_POST
def api_match_schedule(request, match_id):
    """API: Назначить дату/время/корт для матча"""
    try:
        match = get_object_or_404(TournamentMatch, id=match_id)
        data = json.loads(request.body)

        if 'scheduled_date' in data:
            match.scheduled_date = datetime.strptime(data['scheduled_date'], '%Y-%m-%d').date()
        if 'scheduled_time' in data:
            match.scheduled_time = datetime.strptime(data['scheduled_time'], '%H:%M').time()
        if 'court_id' in data:
            from booking.models import Court
            match.court = get_object_or_404(Court, id=data['court_id'])

        match.save()

        return JsonResponse({
            'success': True,
            'message': 'Расписание обновлено'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
def api_tournament_bracket(request, tournament_id):
    """API: Получить сетку турнира для визуализации"""
    try:
        tournament = get_object_or_404(Tournament, id=tournament_id)

        # Группируем матчи по раундам
        bracket = []
        for round_obj in tournament.rounds.all().order_by('round_number'):
            matches_in_round = []
            for match in tournament.matches.filter(round=round_obj.round_number).order_by('match_number'):
                matches_in_round.append({
                    'id': match.id,
                    'team1': {
                        'id': match.team1.id if match.team1 else None,
                        'name': str(match.team1) if match.team1 else 'TBD',
                        'player1': match.team1.player1.get_full_name() if match.team1 else None,
                        'player2': match.team1.player2.get_full_name() if match.team1 else None,
                    },
                    'team2': {
                        'id': match.team2.id if match.team2 else None,
                        'name': str(match.team2) if match.team2 else 'TBD',
                        'player1': match.team2.player1.get_full_name() if match.team2 else None,
                        'player2': match.team2.player2.get_full_name() if match.team2 else None,
                    },
                    'winning_team_id': match.winning_team.id if match.winning_team else None,
                    'score_team1': match.score_team1,
                    'score_team2': match.score_team2,
                    'score_display': match.score_display,
                    'status': match.status,
                })

            bracket.append({
                'round_number': round_obj.round_number,
                'round_name': round_obj.name,
                'matches': matches_in_round
            })

        return JsonResponse({
            'success': True,
            'bracket': bracket,
            'format': tournament.format
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_required
def api_tournament_leaderboard(request, tournament_id):
    """API: Получить таблицу лидеров турнира (Round-Robin)"""
    try:
        tournament = get_object_or_404(Tournament, id=tournament_id)

        # Получаем участников, отсортированных по очкам
        participants = tournament.participants.filter(
            payment_status='paid'
        ).order_by('-total_points', '-matches_won', 'registered_at')

        leaderboard = []
        for rank, participant in enumerate(participants, start=1):
            leaderboard.append({
                'rank': rank,
                'user_id': participant.user.id,
                'user_name': participant.user.get_full_name() or participant.user.username,
                'total_points': participant.total_points,
                'matches_played': participant.matches_played,
                'matches_won': participant.matches_won,
                'matches_lost': participant.matches_lost,
                'win_rate': participant.win_rate,
                'average_points_per_match': participant.average_points_per_match,
            })

        return JsonResponse({
            'success': True,
            'leaderboard': leaderboard,
            'format': tournament.format
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# ПУБЛИЧНЫЕ API ENDPOINTS ДЛЯ УПРАВЛЕНИЯ ТУРНИРАМИ
# =============================================================================

@require_POST
@login_required
def ajax_generate_bracket(request, tournament_id):
    """
    API: Генерация сетки турнира (публичный endpoint)
    
    Доступ: только организатор турнира или staff
    """
    try:
        tournament = get_object_or_404(Tournament, id=tournament_id)
        
        # Проверка прав (только организатор или администратор)
        if request.user != tournament.organizer and not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'Нет прав для генерации сетки'
            }, status=403)
        
        # Проверка статуса турнира
        if tournament.status not in ['registration_closed', 'in_progress']:
            return JsonResponse({
                'success': False,
                'error': 'Турнир должен быть в статусе "регистрация закрыта"'
            }, status=400)
        
        # Проверяем, что сетка ещё не сгенерирована
        if tournament.matches.exists():
            return JsonResponse({
                'success': False,
                'error': 'Сетка уже сгенерирована'
            }, status=400)
        
        # Генерируем сетку в зависимости от формата
        if tournament.format == 'americano':
            matches = AmericanoGenerator.generate(tournament)
        elif tournament.format == 'mexicano':
            from tournament.bracket_generator import MexicanoGenerator
            matches = MexicanoGenerator.generate_first_round(tournament)
        elif tournament.format == 'doubles_elimination':
            from tournament.bracket_generator import DoublesEliminationGenerator
            matches = DoublesEliminationGenerator.generate(tournament)
        else:
            return JsonResponse({
                'success': False,
                'error': f'Формат "{tournament.format}" не поддерживается'
            }, status=400)
        
        # Обновляем статус турнира
        tournament.status = 'in_progress'
        tournament.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Сетка сгенерирована! Создано {len(matches)} матчей.',
            'matches_count': len(matches),
            'tournament_status': tournament.status
        })
    
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при генерации сетки: {str(e)}'
        }, status=500)


@require_POST
@login_required
def ajax_submit_match_score(request, match_id):
    """
    API: Ввод счета матча турнира (публичный endpoint)
    
    Доступ: организатор турнира, участники матча или staff
    """
    try:
        match = get_object_or_404(TournamentMatch, id=match_id)
        tournament = match.tournament
        
        # Проверка прав (организатор, участники матча или администратор)
        user_is_participant = False
        if match.team1 and match.team2:
            participants = [match.team1.player1, match.team1.player2,
                          match.team2.player1, match.team2.player2]
            user_is_participant = request.user in participants
        
        if not (request.user == tournament.organizer or user_is_participant or request.user.is_staff):
            return JsonResponse({
                'success': False,
                'error': 'Нет прав для ввода счета'
            }, status=403)
        
        # Получаем данные из запроса
        try:
            data = json.loads(request.body)
            score_team1 = int(data.get('score_team1'))
            score_team2 = int(data.get('score_team2'))
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Неверный формат данных. Ожидаются числовые значения.'
            }, status=400)
        
        # Валидация счета
        if score_team1 < 0 or score_team2 < 0:
            return JsonResponse({
                'success': False,
                'error': 'Счет не может быть отрицательным'
            }, status=400)
        
        # Устанавливаем счет
        match.score_team1 = score_team1
        match.score_team2 = score_team2
        match.status = 'completed'
        
        # Определяем победителя
        if score_team1 > score_team2:
            match.winning_team = match.team1
        elif score_team2 > score_team1:
            match.winning_team = match.team2
        
        match.save()
        
        # Обновляем статистику участников
        if match.team1:
            for player in [match.team1.player1, match.team1.player2]:
                try:
                    participant = TournamentParticipant.objects.get(
                        tournament=tournament,
                        user=player
                    )
                    participant.total_points += score_team1
                    participant.matches_played += 1
                    if match.winning_team == match.team1:
                        participant.matches_won += 1
                    else:
                        participant.matches_lost += 1
                    participant.save()
                except TournamentParticipant.DoesNotExist:
                    pass
        
        if match.team2:
            for player in [match.team2.player1, match.team2.player2]:
                try:
                    participant = TournamentParticipant.objects.get(
                        tournament=tournament,
                        user=player
                    )
                    participant.total_points += score_team2
                    participant.matches_played += 1
                    if match.winning_team == match.team2:
                        participant.matches_won += 1
                    else:
                        participant.matches_lost += 1
                    participant.save()
                except TournamentParticipant.DoesNotExist:
                    pass
        
        return JsonResponse({
            'success': True,
            'message': 'Счет сохранен!',
            'match': {
                'id': match.id,
                'score_team1': score_team1,
                'score_team2': score_team2,
                'winning_team_id': match.winning_team.id if match.winning_team else None,
                'status': match.status
            }
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при сохранении счета: {str(e)}'
        }, status=500)


def ajax_public_tournament_leaderboard(request, tournament_id):
    """
    API: Публичная таблица лидеров турнира
    
    Доступ: все авторизованные пользователи
    """
    try:
        tournament = get_object_or_404(Tournament, id=tournament_id)
        
        # Получаем участников, отсортированных по очкам
        participants = tournament.participants.filter(
            payment_status='paid'
        ).select_related('user').order_by(
            '-total_points',
            '-matches_won',
            'registered_at'
        )
        
        # Формируем данные для таблицы
        leaderboard = []
        for idx, participant in enumerate(participants, start=1):
            user = participant.user
            leaderboard.append({
                'rank': idx,
                'user_id': user.id,
                'name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'avatar': user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else None,
                'total_points': participant.total_points,
                'matches_played': participant.matches_played,
                'matches_won': participant.matches_won,
                'matches_lost': participant.matches_lost,
                'win_rate': participant.win_rate,
                'average_points': participant.average_points_per_match
            })
        
        return JsonResponse({
            'success': True,
            'leaderboard': leaderboard,
            'tournament': {
                'id': tournament.id,
                'name': tournament.name,
                'format': tournament.format,
                'status': tournament.status
            }
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при загрузке таблицы: {str(e)}'
        }, status=500)
