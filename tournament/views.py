"""
API Views для управления турнирами
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime
import json

from .models import Tournament, TournamentParticipant, TournamentMatch, TournamentRound
from .bracket_generator import BracketGenerator


# Декоратор для проверки прав
def staff_required(view_func):
    """Decorator that checks if user is staff"""
    decorated_view = user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url='/users/login/'
    )(view_func)
    return decorated_view


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

    context = {
        'tournament': tournament,
        'can_register': can_register,
        'register_message': register_message,
        'is_registered': tournament.participants.filter(user=request.user).exists() if request.user.is_authenticated else False
    }
    return render(request, 'tournament/public_tournament_detail.html', context)


def public_tournament_register(request, tournament_id):
    """Регистрация игрока на турнир"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Необходимо войти в систему'}, status=401)

    tournament = get_object_or_404(Tournament, id=tournament_id)

    # Проверяем возможность регистрации
    can_register, message = tournament.can_register(request.user)
    if not can_register:
        return JsonResponse({'success': False, 'error': message}, status=400)

    # Создаем участника
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
                'is_team_tournament': tournament.is_team_tournament,  # НОВОЕ
                'is_mixed': tournament.is_mixed,  # НОВОЕ
                'points_per_match': tournament.points_per_match,  # НОВОЕ
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
        for participant in tournament.participants.all():
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
            })

        # Матчи по раундам
        rounds = []
        for round_obj in tournament.rounds.all():
            matches_in_round = []
            for match in tournament.matches.filter(round=round_obj.round_number):
                matches_in_round.append({
                    'id': match.id,
                    'match_number': match.match_number,
                    'player1_id': match.player1.id if match.player1 else None,
                    'player1_name': match.player1.get_full_name() if match.player1 else 'TBD',
                    'player2_id': match.player2.id if match.player2 else None,
                    'player2_name': match.player2.get_full_name() if match.player2 else 'TBD',
                    'winner_id': match.winner.id if match.winner else None,
                    'score': match.score,
                    'status': match.status,
                    'scheduled_date': match.scheduled_date.isoformat() if match.scheduled_date else None,
                    'scheduled_time': match.scheduled_time.strftime('%H:%M') if match.scheduled_time else None,
                    'court_id': match.court.id if match.court else None,
                    'court_name': match.court.name if match.court else None,
                    'is_ready_to_play': match.is_ready_to_play,
                })

            rounds.append({
                'round_number': round_obj.round_number,
                'name': round_obj.name,
                'start_date': round_obj.start_date.isoformat() if round_obj.start_date else None,
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
        tournament_format = data.get('format', 'americano')  # По умолчанию Americano
        is_team = tournament_format in ['team_americano', 'team_mexicano', 'doubles_elimination', 'doubles_round_robin']

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
            is_team_tournament=is_team,  # НОВОЕ
            is_mixed=tournament_format == 'mixed_americano',  # НОВОЕ
            points_per_match=int(data.get('points_per_match', 24)),  # НОВОЕ
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

        from django.contrib.auth.models import User
        user = get_object_or_404(User, id=user_id)

        # Проверяем возможность регистрации
        can_register, message = tournament.can_register(user)
        if not can_register and message != "Вы уже зарегистрированы":
            # Разрешаем добавление через админку даже если регистрация закрыта
            pass

        # Создаем участника
        participant, created = TournamentParticipant.objects.get_or_create(
            tournament=tournament,
            user=user,
            defaults={'payment_status': 'paid' if tournament.entry_fee == 0 else 'pending'}
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
        if tournament.status not in ['registration_closed', 'draft', 'registration_open']:
            return JsonResponse({
                'success': False,
                'error': 'Сетку можно генерировать только после закрытия регистрации'
            }, status=400)

        # Проверяем количество участников
        if tournament.participants_count < 2:
            return JsonResponse({
                'success': False,
                'error': 'Недостаточно участников (минимум 2)'
            }, status=400)

        # Генерируем сетку
        generator = BracketGenerator()
        if tournament.format == 'single_elimination':
            matches = generator.generate_single_elimination(tournament)
        elif tournament.format == 'round_robin':
            matches = generator.generate_round_robin(tournament)
        else:
            return JsonResponse({
                'success': False,
                'error': f'Формат {tournament.format} не поддерживается'
            }, status=400)

        # Меняем статус турнира
        tournament.status = 'in_progress'
        tournament.save()

        return JsonResponse({
            'success': True,
            'message': f'Сетка сгенерирована! Создано {len(matches)} матчей',
            'matches_count': len(matches)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =============================================================================
# API - УПРАВЛЕНИЕ МАТЧАМИ
# =============================================================================

@staff_required
@require_POST
def api_match_set_winner(request, match_id):
    """API: Установить победителя матча"""
    try:
        match = get_object_or_404(TournamentMatch, id=match_id)
        data = json.loads(request.body)

        winner_id = data.get('winner_id')
        score = data.get('score', {})

        if not winner_id:
            return JsonResponse({'success': False, 'error': 'winner_id обязателен'}, status=400)

        from django.contrib.auth.models import User
        winner = get_object_or_404(User, id=winner_id)

        # Проверяем что победитель - один из игроков
        if winner not in [match.player1, match.player2]:
            return JsonResponse({
                'success': False,
                'error': 'Победитель должен быть одним из игроков матча'
            }, status=400)

        # Устанавливаем победителя
        match.set_winner(winner, score)

        return JsonResponse({
            'success': True,
            'message': f'Победитель: {winner.get_full_name()}'
        })
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
                    'player1': {
                        'id': match.player1.id if match.player1 else None,
                        'name': match.player1.get_full_name() if match.player1 else 'TBD',
                    },
                    'player2': {
                        'id': match.player2.id if match.player2 else None,
                        'name': match.player2.get_full_name() if match.player2 else 'TBD',
                    },
                    'winner_id': match.winner.id if match.winner else None,
                    'score': match.score,
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
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
