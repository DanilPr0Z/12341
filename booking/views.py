from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from datetime import datetime, timedelta
from django.urls import reverse
from django.db.models import Q
from .models import Court, Booking
from users.analytics import (
    get_player_stats,
    get_calendar_events,
    get_available_slots as get_available_slots_analytics
)
import traceback

# Импортируем profile из users.views для обратной совместимости
from users.views import profile


import logging
logger = logging.getLogger(__name__)



from .utils import (
    create_error_message,
    create_success_message,
    validate_booking_times,
    validate_booking_duration,
    validate_working_hours,
    check_time_conflicts,
    pluralize_hours
)
from .decorators import (
    api_data_ratelimit,
    api_write_ratelimit,
    auth_ratelimit
)

@login_required
@require_POST
def check_availability(request):
    """Проверка доступности временного слота для бронирования"""
    court_id = request.POST.get('court_id')
    date_str = request.POST.get('date')
    start_time_str = request.POST.get('start_time')
    duration_str = request.POST.get('duration')

    if not all([court_id, date_str, start_time_str, duration_str]):
        return JsonResponse({
            'success': False,
            'available': False,
            'message': 'Необходимо указать корт, дату, время начала и продолжительность'
        })

    try:
        court = Court.objects.filter(id=court_id, is_available=True).first()
        if not court:
            return JsonResponse({
                'success': False,
                'available': False,
                'message': 'Корт не найден или недоступен'
            })

        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()

        duration_hours = float(str(duration_str).replace(',', '.'))
        total_minutes = int(start_time.hour * 60 + start_time.minute + round(duration_hours * 60))
        end_hour = total_minutes // 60
        end_minute = total_minutes % 60
        from datetime import time as dt_time
        end_time = dt_time(hour=end_hour, minute=end_minute)

        today = timezone.now().date()
        current_time = timezone.now().time()

        is_valid, error_msg = validate_booking_times(booking_date, start_time, end_time, today, current_time)
        if not is_valid:
            return JsonResponse({
                'success': True,
                'available': False,
                'message': error_msg
            })

        is_valid, error_msg = validate_working_hours(start_time, end_time)
        if not is_valid:
            return JsonResponse({
                'success': True,
                'available': False,
                'message': error_msg
            })

        has_conflict, conflicting = check_time_conflicts(court, booking_date, start_time, end_time)
        if has_conflict:
            return JsonResponse({
                'success': True,
                'available': False,
                'message': 'Выбранное время уже занято'
            })

        return JsonResponse({
            'success': True,
            'available': True,
            'message': 'Время доступно'
        })

    except (ValueError, TypeError) as e:
        logger.warning(f"check_availability: invalid input — {e}")
        return JsonResponse({
            'success': False,
            'available': False,
            'message': 'Некорректные данные запроса'
        })


@login_required
def booking_page(request):
    """Страница бронирования кортов"""
    courts = Court.objects.filter(is_available=True).order_by('name')
    today_date = timezone.now().date()

    # Получаем приглашения для текущего пользователя
    pending_invitations = []
    from booking.models import BookingInvitation
    pending_invitations = BookingInvitation.objects.filter(
        invitee=request.user,
        status='pending',
        booking__date__gte=today_date
    ).select_related(
        'booking', 'booking__court', 'inviter', 'inviter__profile'
    ).order_by('booking__date', 'booking__start_time')

    return render(request, 'booking.html', {
        'courts': courts,
        'today_date': today_date,
        'pending_invitations': pending_invitations
    })


@require_GET
@api_data_ratelimit(rate='60/m')
def get_available_slots(request):
    # Поддерживаем оба имени параметра для совместимости:
    # - старый фронт: court
    # - новый аккордеон: court_id (и мы тоже используем court)
    court_id = request.GET.get('court') or request.GET.get('court_id')
    date_str = request.GET.get('date')
    duration_raw = request.GET.get('duration')

    logger.debug(f"get_available_slots called with court={court_id}, date={date_str}")
    logger.debug(f"Current time: {timezone.now().time()}")

    if not court_id or not date_str:
        return JsonResponse({
            'success': False,
            'message': 'Необходимо указать корт и дату'
        })

    try:
        # Длительность (часов) для генерации слотов (аккордеон).
        # Если не передано или некорректно — по умолчанию 1 час.
        duration_hours = 1.0
        if duration_raw is not None and duration_raw != '':
            try:
                duration_hours = float(str(duration_raw).replace(',', '.'))
            except (TypeError, ValueError):
                duration_hours = 1.0

        # Разрешаем только сетку 0.5 часа (1, 1.5, 2, 2.5, 3)
        allowed_durations = {1.0, 1.5, 2.0, 2.5, 3.0}
        if duration_hours not in allowed_durations:
            duration_hours = 1.0

        court = Court.objects.filter(id=court_id, is_available=True).first()
        if not court:
            logger.warning(f"Court not found or not available: {court_id}")
            return JsonResponse({
                'success': False,
                'message': 'Корт не найден или недоступен'
            })

        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = timezone.now().date()
        current_time = timezone.now().time()

        logger.debug(f"booking_date={booking_date}, today={today}, current_time={current_time}")

        if booking_date < today:
            logger.warning(f"Booking date is in the past: {booking_date}")
            return JsonResponse({
                'success': False,
                'message': 'Нельзя бронировать корт на прошедшую дату'
            })

        # Получаем существующие бронирования
        existing_bookings = Booking.objects.filter(
            court=court,
            date=booking_date,
            status__in=['pending', 'confirmed']
        ).select_related('user', 'user__profile', 'user__rating').prefetch_related('partners')

        logger.debug(f"Found {existing_bookings.count()} existing bookings for court {court.name} on {booking_date}")

        # Занятые интервалы в минутах (start, end)
        booked_intervals = []
        for booking in existing_bookings:
            start_minutes = booking.start_time.hour * 60 + booking.start_time.minute
            end_minutes = booking.end_time.hour * 60 + booking.end_time.minute
            booked_intervals.append((start_minutes, end_minutes))
            logger.debug(
                f"Booking slot: {booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}"
            )

        def overlaps(a_start, a_end, b_start, b_end):
            return a_start < b_end and b_start < a_end

        # Рабочие часы: 8:00 - 22:00
        WORKING_HOURS_START = 8
        WORKING_HOURS_END = 22
        working_start_minutes = WORKING_HOURS_START * 60
        working_end_minutes = WORKING_HOURS_END * 60

        # Генерация слотов для аккордеона (free slots) с учётом длительности
        slot_duration_minutes = int(duration_hours * 60)
        slots = []

        # Только если сегодняшняя дата
        if booking_date == today:
            current_minutes = current_time.hour * 60 + current_time.minute
            logger.debug(f"Booking for today - current minutes: {current_minutes}")
        else:
            current_minutes = -1  # Будущая дата, все время доступно
            logger.debug(f"Booking for future date - all hours available")

        # Стартовые времена: каждые 30 минут (под длительности 1.5/2.5)
        step_minutes = 30
        start_min = working_start_minutes
        last_start = working_end_minutes - slot_duration_minutes
        if last_start < start_min:
            last_start = start_min - step_minutes  # не будет слотов

        start_m = start_min
        while start_m <= last_start:
            end_m = start_m + slot_duration_minutes

            is_available = True

            # Нельзя бронировать в прошлом (для сегодня)
            if booking_date == today and start_m < current_minutes:
                is_available = False

            # Проверяем пересечения с существующими бронированиями
            if is_available and booked_intervals:
                for b_start, b_end in booked_intervals:
                    if overlaps(start_m, end_m, b_start, b_end):
                        is_available = False
                        break

            if is_available:
                slots.append({
                    'start_time': f"{start_m // 60:02d}:{start_m % 60:02d}",
                    'booked': False
                })

            start_m += step_minutes

        # Получаем рейтинг текущего пользователя (если залогинен)
        user_rating = None
        if request.user.is_authenticated:
            try:
                user_rating = request.user.rating.level
            except (AttributeError, ObjectDoesNotExist):
                user_rating = None

        # Ищем бронирования с "Найти партнёра"
        partner_bookings = []
        for booking in existing_bookings:
            # Пропускаем, если не ищет партнёра или уже полное
            if not booking.looking_for_partner or booking.is_full:
                continue

            # Пропускаем свои бронирования
            if request.user.is_authenticated and (booking.user == request.user or request.user in booking.partners.all()):
                continue

            # Проверяем рейтинг
            can_join = True
            join_message = ""

            if request.user.is_authenticated:
                can_join, join_message = booking.can_join(request.user)

            # Формируем информацию о бронировании
            user_full_name = f"{booking.user.first_name} {booking.user.last_name}".strip() or booking.user.username

            partner_bookings.append({
                'type': 'partner_booking',
                'booking_id': booking.id,
                'start_time': booking.start_time.strftime('%H:%M'),
                'end_time': booking.end_time.strftime('%H:%M'),
                'hour': booking.start_time.hour,
                'creator_name': user_full_name,
                'creator_rating': booking.user.rating.level if hasattr(booking.user, 'rating') else None,
                'required_rating': booking.required_rating_level,
                'current_players': 1 + booking.partners.count(),
                'max_players': booking.max_players,
                'available_slots': booking.available_slots,
                'price_per_person': float(booking.price_per_person),
                'can_join': can_join,
                'join_message': join_message
            })

        # Объединяем свободные слоты и бронирования с партнёрами
        # Legacy items (для старого UI): слоты по часам + записи с поиском партнера
        free_slots = []
        for hour in range(WORKING_HOURS_START, WORKING_HOURS_END):
            # свободен ли целый час (старый формат), без учёта дробных минут
            hour_start = hour * 60
            hour_end = (hour + 1) * 60
            hour_available = True
            if booking_date == today and hour_start < current_minutes:
                hour_available = False
            if hour_available and booked_intervals:
                for b_start, b_end in booked_intervals:
                    if overlaps(hour_start, hour_end, b_start, b_end):
                        hour_available = False
                        break
            if hour_available:
                free_slots.append({
                    'type': 'free_slot',
                    'start_time': f"{hour:02d}:00",
                    'end_time': f"{(hour + 1):02d}:00",
                    'duration': 1,
                    'hour': hour
                })

        all_items = free_slots + partner_bookings
        # Сортируем по времени начала
        all_items.sort(key=lambda x: x['hour'])

        logger.debug(f"Free slots: {len(free_slots)}, Partner bookings: {len(partner_bookings)}")

        result = {
            'success': True,
            # Новый формат для аккордеона
            'slots': slots,
            'items': all_items,  # Смешанный список: свободные слоты + бронирования с партнёрами
            'court_price': float(court.price_per_hour),
            'court_name': court.name,
            'court_id': court.id,
            'date': date_str,
            'date_formatted': booking_date.strftime('%d.%m.%Y'),
            'free_slots_count': len(free_slots),
            'partner_bookings_count': len(partner_bookings),
            'user_rating': user_rating,
            'duration': duration_hours
        }

        logger.debug(f"Returning {len(all_items)} total items (free slots + partner bookings)")

        response = JsonResponse(result)
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except Exception as e:
        logger.error(f"Error in get_available_slots: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка загрузки слотов'
        }, status=500)

@login_required
@require_POST
@api_write_ratelimit(rate='10/m')
def create_booking(request):
    """
    Создание бронирования (рефакторенная версия)

    Улучшения:
    - Код сократился с 350 строк до ~220
    - Переиспользуемые функции валидации
    - Единая генерация HTML сообщений
    - Улучшенная читаемость
    """
    try:
        # Получаем данные из формы
        court_id = request.POST.get('court_id')
        date_str = request.POST.get('date')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        duration = request.POST.get('duration', '1')

        # 1. Валидация обязательных полей
        if not all([court_id, date_str, start_time_str]):
            messages.error(request, create_error_message("Ошибка", "Все поля должны быть заполнены"))
            return redirect('booking')

        court = get_object_or_404(Court, id=court_id, is_available=True)

        # 2. Парсим дату и время
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()

        # Рассчитываем end_time если не указан
        if not end_time_str and duration:
            try:
                duration_hours = float(str(duration).replace(',', '.'))
            except (TypeError, ValueError):
                duration_hours = 1.0

            # Приводим к минутам, поддерживаем шаг 30 минут
            duration_minutes = int(round(duration_hours * 60))
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = start_minutes + duration_minutes
            end_hour = end_minutes // 60
            end_minute = end_minutes % 60
            end_time = datetime.strptime(f"{end_hour:02d}:{end_minute:02d}", '%H:%M').time()
        else:
            end_time = datetime.strptime(end_time_str, '%H:%M').time()

        today = timezone.now().date()
        current_time = timezone.now().time()

        # 3. Валидация времени
        is_valid, error_msg = validate_booking_times(
            booking_date, start_time, end_time, today, current_time
        )
        if not is_valid:
            messages.error(request, create_error_message("Ошибка", error_msg))
            return redirect('booking')

        # 4. Валидация продолжительности
        is_valid, duration_hours, error_msg = validate_booking_duration(
            start_time, end_time, booking_date
        )
        if not is_valid:
            messages.error(request, create_error_message("Ошибка", error_msg))
            return redirect('booking')

        # 5. Проверка рабочих часов
        is_valid, error_msg = validate_working_hours(start_time, end_time)
        if not is_valid:
            messages.error(request, create_error_message("Ошибка", error_msg))
            return redirect('booking')

        # 6. Создание бронирования в транзакции
        with transaction.atomic():
            # Проверка конфликтов
            has_conflict, conflicting_booking = check_time_conflicts(
                court, booking_date, start_time, end_time
            )

            if has_conflict:
                conflict_start = conflicting_booking.start_time.strftime('%H:%M')
                conflict_end = conflicting_booking.end_time.strftime('%H:%M')
                error_msg = f"Выбранное время уже занято с {conflict_start} до {conflict_end}"
                messages.error(request, create_error_message("Время занято", error_msg))
                return redirect('booking')

            # Получаем данные для поиска партнеров
            looking_for_partner = bool(request.POST.get('looking_for_partner'))
            max_players = int(request.POST.get('max_players', 4))

            # Получаем выбранные уровни рейтинга (множественные чекбоксы)
            required_rating_levels = request.POST.getlist('required_rating_levels')
            logger.info(f"Selected rating levels: {required_rating_levels}")

            # Получаем приглашенных участников
            invited_participants_str = request.POST.get('invited_participants', '')
            invited_participant_ids = [int(pid) for pid in invited_participants_str.split(',') if pid.strip()]
            logger.info(f"Invited participants: {invited_participant_ids}")

            # Получаем тип бронирования и тренера
            booking_type = request.POST.get('booking_type', 'game')
            coach_id = request.POST.get('coach')
            coach = None

            if coach_id and booking_type == 'training':
                from django.contrib.auth.models import User
                try:
                    coach = User.objects.get(id=coach_id, groups__name='Тренеры')
                except User.DoesNotExist:
                    coach = None

            # Получаем параметры игрового режима
            game_mode = request.POST.get('game_mode', 'regular')
            is_public = request.POST.get('is_public') == '1'
            rounds_count = int(request.POST.get('rounds_count', 3))
            points_per_round = int(request.POST.get('points_per_round', 24))

            # Создаем бронирование
            booking = Booking.objects.create(
                user=request.user,
                court=court,
                date=booking_date,
                start_time=start_time,
                end_time=end_time,
                status='pending',
                booking_type=booking_type,
                coach=coach,
                looking_for_partner=looking_for_partner if booking_type == 'game' else False,
                max_players=max_players if booking_type == 'game' else 1,
                required_rating_levels=required_rating_levels if (required_rating_levels and booking_type == 'game') else [],
                game_mode=game_mode,
                is_public=is_public if game_mode in ['americano', 'mexicano'] else False,
                rounds_count=rounds_count if game_mode in ['americano', 'mexicano'] else 3,
                points_per_round=points_per_round if game_mode in ['americano', 'mexicano'] else 24,
                game_status='pending'
            )

            # Повторная проверка (защита от race condition)
            has_conflict, _ = check_time_conflicts(
                court, booking_date, start_time, end_time, exclude_booking_id=booking.id
            )

            if has_conflict:
                booking.delete()
                error_msg = "Это время было забронировано другим пользователем. Пожалуйста, выберите другое время."
                messages.error(request, create_error_message("Время занято", error_msg))
                return redirect('booking')

            # Для социальных игр (Americano/Mexicano) добавляем создателя как первого участника
            if game_mode in ['americano', 'mexicano']:
                from .models import GameParticipant
                try:
                    creator_rating = request.user.rating.numeric_rating
                except Exception:
                    creator_rating = 1.00
                GameParticipant.objects.create(
                    booking=booking,
                    user=request.user,
                    position=1,
                    status='accepted',
                    rating_before=creator_rating
                )

            # Отправляем приглашения выбранным участникам
            if invited_participant_ids:
                from django.contrib.auth.models import User
                from booking.models import BookingInvitation

                invitations_sent = 0
                for user_id in invited_participant_ids:
                    try:
                        invited_user = User.objects.get(id=user_id)
                        # Создаем приглашение
                        BookingInvitation.objects.create(
                            booking=booking,
                            inviter=request.user,
                            invitee=invited_user,
                            invitee_phone=invited_user.profile.phone if hasattr(invited_user, 'profile') else '',
                            message=f"Приглашение присоединиться к игре {booking_date.strftime('%d.%m.%Y')} в {start_time_str}"
                        )
                        # Создаем уведомление в базе для приглашённого
                        try:
                            from users.models import Notification
                            from booking.models import BookingInvitation as BI
                            inviter_name = request.user.get_full_name() or request.user.username
                            inv_obj = BI.objects.filter(
                                booking=booking, invitee=invited_user
                            ).order_by('-id').first()
                            Notification.objects.create(
                                user=invited_user,
                                type='booking_invitation',
                                title='Приглашение в игру',
                                message=(
                                    f"{inviter_name} приглашает вас на игру "
                                    f"{booking_date.strftime('%d.%m.%Y')} в {start_time_str} "
                                    f"на корте {court.name}"
                                ),
                                metadata={
                                    'booking_id': booking.id,
                                    'invitation_id': inv_obj.id if inv_obj else None,
                                }
                            )
                        except Exception as ne:
                            logger.error(f"Error creating invitation notification: {str(ne)}")
                        invitations_sent += 1
                        logger.info(f"Invitation sent to user {invited_user.username} for booking {booking.id}")
                    except User.DoesNotExist:
                        logger.warning(f"User with id {user_id} not found for invitation")
                    except Exception as e:
                        logger.error(f"Error sending invitation to user {user_id}: {str(e)}")

                if invitations_sent > 0:
                    logger.info(f"Sent {invitations_sent} invitations for booking {booking.id}")

        # 7. Очищаем кэш
        clear_slots_cache(court_id=court_id, date_str=date_str)
        try:
            from users.analytics import invalidate_player_stats_cache
            invalidate_player_stats_cache(request.user.id)
        except Exception:
            pass

        # 8. Логируем успех
        logger.info(
            f"Booking created: User {request.user.username} booked court {court.name} "
            f"on {booking_date} from {start_time_str} to {end_time.strftime('%H:%M')} "
            f"(Duration: {duration_hours}h, Price: {booking.total_price} руб., Type: {booking_type})"
        )

        # 9. Формируем красивое сообщение об успехе
        duration_text = pluralize_hours(duration_hours)
        booking_type_text = "Тренировка" if booking_type == 'training' else "Игра"
        coach_info = f" с тренером {coach.get_full_name() or coach.username}" if coach else ""

        success_details = (
            f"{court.name} · {booking_date.strftime('%d.%m.%Y')} · "
            f"{start_time_str}–{end_time.strftime('%H:%M')} · "
            f"{duration_text} · {int(booking.total_price)} руб."
        )

        messages.success(request, f"Бронирование создано! {success_details}")
        return redirect(f"{reverse('profile')}#bookings")

    except Exception as e:
        logger.error(
            f"Error creating booking for user {request.user.username}: {str(e)}",
            exc_info=True
        )
        messages.error(request, create_error_message(
            "Ошибка при бронировании",
            "Произошла ошибка. Пожалуйста, попробуйте еще раз или обратитесь в поддержку."
        ))
        return redirect('booking')


@login_required
@require_POST
def cancel_booking(request, booking_id):
    """Отмена бронирования"""
    try:
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

        if booking.status == 'cancelled':
            return JsonResponse({
                'success': False,
                'message': 'Это бронирование уже отменено'
            })

        today = timezone.now().date()
        if booking.date < today:
            return JsonResponse({
                'success': False,
                'message': 'Нельзя отменить прошедшее бронирование'
            })

        # Проверяем время (нельзя отменить менее чем за 1 час до начала)
        if booking.date == today:
            current_time = timezone.now().time()
            time_until_start = datetime.combine(today, booking.start_time) - datetime.combine(today, current_time)
            if time_until_start.total_seconds() < 3600:
                return JsonResponse({
                    'success': False,
                    'message': 'Нельзя отменить бронирование менее чем за 1 час до начала'
                })

        # Сохраняем данные для очистки кэша
        court_id = booking.court.id
        date_str = booking.date.strftime('%Y-%m-%d')

        # Отменяем бронирование
        booking.status = 'cancelled'
        booking.save()

        # Уведомляем всех партнёров/приглашённых об отмене
        try:
            from users.models import Notification
            from booking.models import BookingInvitation
            date_fmt = booking.date.strftime('%d.%m.%Y')
            time_fmt = booking.start_time.strftime('%H:%M')
            cancel_msg = (
                f"Игра {date_fmt} в {time_fmt} на корте {booking.court.name} отменена"
            )
            # Партнёры (обычные игры)
            for partner in booking.partners.all():
                Notification.objects.create(
                    user=partner,
                    type='booking_cancelled',
                    title='Игра отменена',
                    message=cancel_msg,
                    metadata={'booking_id': booking.id}
                )
            # Приглашённые
            for inv in BookingInvitation.objects.filter(booking=booking, status='pending'):
                if inv.invitee is None:
                    continue
                Notification.objects.create(
                    user=inv.invitee,
                    type='booking_cancelled',
                    title='Игра отменена',
                    message=cancel_msg,
                    metadata={'booking_id': booking.id}
                )
        except Exception as ne:
            logger.error(f"Error creating cancellation notifications: {str(ne)}")

        # Очищаем кэш
        clear_slots_cache(court_id=court_id, date_str=date_str)
        try:
            from users.analytics import invalidate_player_stats_cache
            invalidate_player_stats_cache(request.user.id)
        except Exception:
            pass

        logger.info(f"Booking {booking_id} cancelled by user {request.user.username}")

        return JsonResponse({
            'success': True,
            'message': 'Бронирование успешно отменено',
            'booking_id': booking_id
        })

    except Exception as e:
        logger.error(f"Error cancelling booking {booking_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при отмене бронирования'
        })


@login_required
@require_POST
def confirm_booking(request, booking_id):
    """Подтверждение бронирования за 24 часа до начала"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status != 'pending':
        return JsonResponse({
            'success': False,
            'message': 'Это бронирование уже подтверждено или отменено'
        })

    if not booking.can_confirm:
        return JsonResponse({
            'success': False,
            'message': f'Подтверждение возможно только за 24 часа до начала. Доступно через {booking.hours_until_confirmation} ч.'
        })

    if booking.confirm():
        return JsonResponse({
            'success': True,
            'message': 'Бронирование успешно подтверждено!'
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Не удалось подтвердить бронирование'
        })


@login_required
@require_GET
def get_booking_info(request, booking_id):
    """Получить информацию о бронировании"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    return JsonResponse({
        'success': True,
        'booking': {
            'id': booking.id,
            'court_name': booking.court.name,
            'date': booking.date.strftime('%d.%m.%Y'),
            'time': f"{booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}",
            'price': booking.total_price,
            'status': booking.status,
            'can_confirm': booking.can_confirm
        }
    })


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def clear_slots_cache(court_id=None, date_str=None):
    """Очистка кэша слотов"""
    try:
        if court_id and date_str:
            cache.delete(f'slots_{court_id}_{date_str}')
            cache.delete(f'court_{court_id}')

        elif court_id:
            today = timezone.now().date()
            keys_to_delete = []

            for i in range(90):
                future_date = today + timedelta(days=i)
                date_key = future_date.strftime('%Y-%m-%d')
                keys_to_delete.append(f'slots_{court_id}_{date_key}')

            for i in range(0, len(keys_to_delete), 100):
                cache.delete_many(keys_to_delete[i:i + 100])

            cache.delete(f'court_{court_id}')

    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")


# ========== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ ==========
# УДАЛЕНО: Дублирующая функция profile() - используем версию из users.views (импорт в начале файла)


# ========== ДОПОЛНИТЕЛЬНЫЕ VIEW ==========
# УДАЛЕНО: my_bookings() - дублировало функционал profile()


# ========== ПОИСК ПАРТНЁРОВ И ПРИГЛАШЕНИЯ ==========

@login_required
def find_partners(request):
    """Страница поиска партнёров - бронирования, которые ищут игроков"""
    today = timezone.now().date()

    # ОПТИМИЗАЦИЯ: Загружаем рейтинг пользователя один раз
    try:
        user_rating = request.user.rating.level
    except (AttributeError, ObjectDoesNotExist):
        user_rating = None

    # ОПТИМИЗАЦИЯ: Используем Prefetch для оптимизации запросов
    from django.db.models import Prefetch
    from django.contrib.auth.models import User

    # Получаем бронирования, которые ищут партнёров
    available_bookings = Booking.objects.filter(
        looking_for_partner=True,
        status__in=['pending', 'confirmed'],
        date__gte=today
    ).select_related(
        'user', 'user__profile', 'user__rating', 'court'
    ).prefetch_related(
        Prefetch('partners', queryset=User.objects.all(), to_attr='partners_list')
    ).order_by('date', 'start_time')

    # Фильтруем бронирования, в которых есть свободные места
    bookings_with_slots = []

    for booking in available_bookings:
        # ИСПРАВЛЕНА N+1: Проверяем через предзагруженный список
        partner_ids = [p.id for p in booking.partners_list]

        # Пропускаем свои бронирования
        if booking.user == request.user or request.user.id in partner_ids:
            continue

        # Проверяем наличие мест
        if not booking.is_full:
            can_join, message = booking.can_join(request.user)
            booking.can_join_flag = can_join
            booking.join_message = message
            bookings_with_slots.append(booking)

    context = {
        'bookings': bookings_with_slots,
        'user_rating': user_rating,
        'today': today
    }

    return render(request, 'booking/find_partners.html', context)


@login_required
@require_POST
def join_booking(request, booking_id):
    """Присоединиться к бронированию"""
    try:
        booking = get_object_or_404(Booking, id=booking_id)

        # Проверяем, можно ли присоединиться
        can_join, message = booking.can_join(request.user)
        if not can_join:
            return JsonResponse({
                'success': False,
                'message': message
            })

        # Добавляем пользователя в партнёры
        success, msg = booking.add_partner(request.user)

        if success:
            # Отправляем уведомление создателю бронирования
            from users.services import NotificationService
            NotificationService.send_partner_joined_notification(booking, request.user)

            return JsonResponse({
                'success': True,
                'message': f'Вы успешно присоединились! Стоимость на человека: {booking.price_per_person} руб.',
                'price_per_person': booking.price_per_person,
                'available_slots': booking.available_slots
            })
        else:
            return JsonResponse({
                'success': False,
                'message': msg
            })

    except Exception as e:
        logger.error(f"Error joining booking {booking_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Произошла ошибка при присоединении'
        })


@login_required
def send_invitation(request, booking_id):
    """Отправить приглашение другу"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if request.method == 'POST':
        from .forms import InviteFriendForm
        form = InviteFriendForm(request.POST, booking=booking, inviter=request.user)

        if form.is_valid():
            invitation = form.save()

            # Отправляем уведомление приглашённому
            from users.services import NotificationService
            if invitation.invitee:
                NotificationService.send_booking_invitation_notification(invitation)

            messages.success(request, 'Приглашение успешно отправлено!')
            return redirect('booking_detail', booking_id=booking_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return redirect('booking_detail', booking_id=booking_id)

    else:
        from .forms import InviteFriendForm
        form = InviteFriendForm(booking=booking, inviter=request.user)

    context = {
        'form': form,
        'booking': booking
    }

    return render(request, 'booking/send_invitation.html', context)


@login_required
def my_invitations(request):
    """Список приглашений пользователя"""
    from .models import BookingInvitation

    # Полученные приглашения
    received_invitations = BookingInvitation.objects.filter(
        invitee=request.user,
        status='pending'
    ).select_related('booking', 'booking__court', 'inviter', 'inviter__profile').order_by('-created_at')

    # Отправленные приглашения
    sent_invitations = BookingInvitation.objects.filter(
        inviter=request.user
    ).select_related('booking', 'booking__court', 'invitee', 'invitee__profile').order_by('-created_at')[:10]

    context = {
        'received_invitations': received_invitations,
        'sent_invitations': sent_invitations
    }

    return render(request, 'booking/my_invitations.html', context)


@login_required
@require_POST
def accept_invitation(request, invitation_id):
    """Принять приглашение"""
    from .models import BookingInvitation

    try:
        invitation = get_object_or_404(BookingInvitation, id=invitation_id, invitee=request.user)

        success, message = invitation.accept()

        if success:
            # Уведомляем отправителя
            from users.services import NotificationService
            NotificationService.send_invitation_accepted_notification(invitation)

            return JsonResponse({
                'success': True,
                'message': message,
                'booking_id': invitation.booking.id
            })
        else:
            return JsonResponse({
                'success': False,
                'message': message
            })

    except Exception as e:
        logger.error(f"Error accepting invitation {invitation_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Произошла ошибка при принятии приглашения'
        })


@login_required
@require_POST
def decline_invitation(request, invitation_id):
    """Отклонить приглашение"""
    from .models import BookingInvitation

    try:
        invitation = get_object_or_404(BookingInvitation, id=invitation_id, invitee=request.user)

        success, message = invitation.decline()

        if success:
            # Уведомляем отправителя
            from users.services import NotificationService
            NotificationService.send_invitation_declined_notification(invitation)

            return JsonResponse({
                'success': True,
                'message': message
            })
        else:
            return JsonResponse({
                'success': False,
                'message': message
            })

    except Exception as e:
        logger.error(f"Error declining invitation {invitation_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Произошла ошибка при отклонении приглашения'
        })


@login_required
@require_POST
def cancel_invitation(request, invitation_id):
    """Отменить отправленное приглашение"""
    from .models import BookingInvitation

    try:
        invitation = get_object_or_404(BookingInvitation, id=invitation_id, inviter=request.user)

        success, message = invitation.cancel()

        if success:
            return JsonResponse({
                'success': True,
                'message': message
            })
        else:
            return JsonResponse({
                'success': False,
                'message': message
            })

    except Exception as e:
        logger.error(f"Error cancelling invitation {invitation_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Произошла ошибка при отмене приглашения'
        })


@login_required
def booking_detail(request, booking_id):
    """Детальная страница бронирования с возможностью приглашения друзей"""
    from .models import BookingInvitation
    from .forms import InviteFriendForm

    # Получаем бронирование (создатель или партнёр)
    booking = get_object_or_404(
        Booking.objects.prefetch_related('partners', 'invitations'),
        Q(user=request.user) | Q(partners=request.user),
        id=booking_id
    )

    # Проверяем права доступа
    is_creator = booking.user == request.user
    is_partner = request.user in booking.partners.all()

    if not (is_creator or is_partner):
        messages.error(request, 'У вас нет доступа к этому бронированию')
        return redirect('profile')

    # Получаем все приглашения для этого бронирования
    invitations = booking.invitations.all().order_by('-created_at')

    # Форма для приглашения (только для создателя)
    invite_form = None
    if is_creator and not booking.is_full:
        invite_form = InviteFriendForm(booking=booking, inviter=request.user)

    context = {
        'booking': booking,
        'is_creator': is_creator,
        'is_partner': is_partner,
        'invitations': invitations,
        'invite_form': invite_form,
        'today': timezone.now().date()
    }

    return render(request, 'booking/booking_detail.html', context)

# ========== API ENDPOINTS ДЛЯ СТАТИСТИКИ И КАЛЕНДАРЯ ==========

@login_required
@require_GET
@api_data_ratelimit(rate='30/m')
def api_player_stats(request):
    """API: Получить статистику игрока"""
    try:
        stats = get_player_stats(request.user)
        
        # Преобразуем datetime объекты для JSON
        if stats['monthly_activity']:
            for item in stats['monthly_activity']:
                if 'month' in item and item['month']:
                    item['month'] = item['month'].strftime('%Y-%m')
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting player stats: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Ошибка получения статистики'
        }, status=500)


@login_required
@require_GET
def api_calendar_events(request):
    """API: Получить события для календаря"""
    try:
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')

        if not start_str or not end_str:
            return JsonResponse({
                'success': False,
                'message': 'Требуются параметры start и end'
            }, status=400)

        # Парсим даты - FullCalendar может отправить разные форматы
        try:
            from dateutil import parser as date_parser
            # Используем dateutil для надежного парсинга любых форматов дат
            start_date = date_parser.parse(start_str).date()
            end_date = date_parser.parse(end_str).date()
        except ImportError:
            # Если dateutil не установлен, используем базовый парсинг
            try:
                # Извлекаем только дату из ISO строки
                start_date = datetime.fromisoformat(start_str.split('T')[0]).date()
                end_date = datetime.fromisoformat(end_str.split('T')[0]).date()
            except Exception as date_error:
                logger.error(f"Date parsing error: {date_error}, start={start_str}, end={end_str}")
                return JsonResponse({
                    'success': False,
                    'message': 'Неверный формат даты'
                }, status=400)
        except Exception as date_error:
            logger.error(f"Date parsing error: {date_error}, start={start_str}, end={end_str}")
            return JsonResponse({
                'success': False,
                'message': 'Неверный формат даты'
            }, status=400)

        events = get_calendar_events(request.user, start_date, end_date)

        return JsonResponse(events, safe=False)

    except Exception as e:
        logger.error(f"Error getting calendar events: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': 'Ошибка получения событий календаря'
        }, status=500)


@login_required
@require_GET
def api_available_slots(request):
    """API: Получить доступные слоты для бронирования"""
    try:
        court_id = request.GET.get('court_id')
        date_str = request.GET.get('date')
        
        if not court_id or not date_str:
            return JsonResponse({
                'success': False,
                'message': 'Требуются параметры court_id и date'
            }, status=400)
        
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        slots = get_available_slots_analytics(court_id, date)
        
        return JsonResponse({
            'success': True,
            'slots': slots
        })
    
    except Exception as e:
        logger.error(f"Error getting available slots: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Ошибка получения доступных слотов'
        }, status=500)



@login_required
def player_statistics(request):
    """Страница со статистикой игрока"""
    try:
        import json
        stats = get_player_stats(request.user)

        # Сериализуем данные для JavaScript
        # Преобразуем QuerySet и datetime объекты в JSON-совместимые форматы
        monthly_activity_json = json.dumps([
            {
                'month': item['month'].strftime('%Y-%m') if item.get('month') else '',
                'games': item.get('games', 0)
            }
            for item in stats.get('monthly_activity', [])
        ])

        weekday_stats_json = json.dumps(stats.get('weekday_stats', []))
        rating_progress_json = json.dumps(stats.get('rating_progress', []))

        context = {
            'stats': stats,
            'user': request.user,
            'monthly_activity_json': monthly_activity_json,
            'weekday_stats_json': weekday_stats_json,
            'rating_progress_json': rating_progress_json,
        }

        return render(request, 'booking/player_stats.html', context)

    except Exception as e:
        import traceback
        logger.error(f"Error rendering player statistics: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, 'Ошибка загрузки статистики')
        return redirect('profile')


@login_required
@require_GET
def get_coaches_list(request):
    """API endpoint для получения списка тренеров"""
    try:
        from users.models import CoachProfile

        coaches = CoachProfile.objects.filter(
            is_active=True
        ).select_related('user').order_by('-coach_rating', 'user__first_name')

        coaches_data = []
        for coach in coaches:
            full_name = f"{coach.user.first_name} {coach.user.last_name}".strip()
            display_name = full_name if full_name else coach.user.username

            coaches_data.append({
                'id': coach.user.id,
                'name': display_name,
                'rating': float(coach.coach_rating),
                'hourly_rate': float(coach.hourly_rate),
                'specialization': coach.specialization,
                'experience_years': coach.experience_years,
            })

        return JsonResponse({
            'success': True,
            'coaches': coaches_data,
            'count': len(coaches_data)
        })

    except Exception as e:
        logger.error(f"Error fetching coaches list: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Ошибка загрузки списка тренеров'
        }, status=500)


@login_required
def api_search_users(request):
    """
    API: Умный поиск пользователей по имени, фамилии или телефону
    """
    try:
        query = request.GET.get('q', '').strip()

        logger.info(f"Search query from user {request.user.username}: '{query}'")

        if len(query) < 2:
            return JsonResponse({
                'success': False,
                'message': 'Запрос должен содержать минимум 2 символа',
                'users': []
            })

        # Ищем пользователей по имени, фамилии или телефону
        from django.db.models import Q
        from users.models import UserProfile

        # Два отдельных запроса для надежности
        # 1. Поиск по имени и фамилии
        users_by_name = User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )

        # 2. Поиск по телефону (только если есть профиль)
        users_by_phone = User.objects.filter(
            profile__phone__icontains=query
        )

        # Объединяем результаты и убираем дубликаты
        users = (users_by_name | users_by_phone).distinct().select_related('profile')[:10]

        logger.info(f"Found {users.count()} users matching query '{query}'")

        users_data = []
        for user in users:
            full_name = f"{user.first_name} {user.last_name}".strip()
            display_name = full_name if full_name else user.username

            # Безопасно получаем телефон
            try:
                phone = user.profile.phone
            except (AttributeError, UserProfile.DoesNotExist):
                phone = 'Не указан'

            # Помечаем если это текущий пользователь
            is_current_user = user.id == request.user.id

            users_data.append({
                'id': user.id,
                'full_name': display_name,
                'phone': phone,
                'is_current_user': is_current_user,
            })

            logger.debug(f"User found: {display_name} ({phone}) {'[current user]' if is_current_user else ''}")

        return JsonResponse({
            'success': True,
            'users': users_data,
            'count': len(users_data)
        })

    except Exception as e:
        logger.error(f"Error searching users: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка поиска пользователей',
            'users': []
        }, status=500)


@login_required
def api_get_notifications(request):
    """
    API: Получить уведомления пользователя (приглашения в игры)
    """
    try:
        from booking.models import BookingInvitation

        # Получаем все непрочитанные приглашения
        invitations = BookingInvitation.objects.filter(
            invitee=request.user,
            status='pending'
        ).select_related('booking', 'booking__court', 'inviter').order_by('-created_at')[:10]

        notifications_data = []
        for invitation in invitations:
            booking = invitation.booking
            inviter_name = f"{invitation.inviter.first_name} {invitation.inviter.last_name}".strip() or invitation.inviter.username

            # Форматируем дату и время
            booking_date = booking.date.strftime('%d.%m.%Y')
            booking_time = booking.start_time.strftime('%H:%M')

            notifications_data.append({
                'id': invitation.id,
                'type': 'invitation',
                'title': f'Приглашение в игру',
                'message': f'{inviter_name} приглашает вас на игру {booking_date} в {booking_time}',
                'inviter_name': inviter_name,
                'court_name': booking.court.name,
                'date': booking_date,
                'time': booking_time,
                'booking_id': booking.id,
                'created_at': invitation.created_at.isoformat(),
            })

        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'count': len(notifications_data)
        })

    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка загрузки уведомлений',
            'notifications': []
        }, status=500)


@login_required
@require_POST
def api_accept_invitation(request, invitation_id):
    """
    API: Принять приглашение в игру
    """
    try:
        from booking.models import BookingInvitation

        logger.info(f"User {request.user.username} trying to accept invitation {invitation_id}")

        invitation = get_object_or_404(BookingInvitation, id=invitation_id, invitee=request.user)

        logger.info(f"Invitation found: booking={invitation.booking.id}, status={invitation.status}")

        if invitation.status != 'pending':
            logger.warning(f"Invitation {invitation_id} status is {invitation.status}, not pending")
            return JsonResponse({
                'success': False,
                'message': 'Приглашение уже обработано'
            }, status=400)

        # Принимаем приглашение
        success, message = invitation.accept()

        logger.info(f"Invitation.accept() result: success={success}, message={message}")

        if success:
            logger.info(f"User {request.user.username} accepted invitation {invitation_id}")
            return JsonResponse({
                'success': True,
                'message': 'Вы успешно присоединились к игре!'
            })
        else:
            logger.warning(f"Failed to accept invitation {invitation_id}: {message}")
            return JsonResponse({
                'success': False,
                'message': message
            }, status=400)

    except Exception as e:
        logger.error(f"Error accepting invitation: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при принятии приглашения'
        }, status=500)


@login_required
@require_POST
def api_decline_invitation(request, invitation_id):
    """
    API: Отклонить приглашение в игру
    """
    try:
        from booking.models import BookingInvitation

        invitation = get_object_or_404(BookingInvitation, id=invitation_id, invitee=request.user)

        if invitation.status != 'pending':
            return JsonResponse({
                'success': False,
                'message': 'Приглашение уже обработано'
            }, status=400)

        # Отклоняем приглашение
        success, message = invitation.decline()

        if success:
            logger.info(f"User {request.user.username} declined invitation {invitation_id}")
            return JsonResponse({
                'success': True,
                'message': 'Приглашение отклонено'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': message
            }, status=400)

    except Exception as e:
        logger.error(f"Error declining invitation: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при отклонении приглашения'
        }, status=500)


# ========== СОЦИАЛЬНЫЕ ИГРЫ (AMERICANO) ==========

@login_required
@login_required
def games_list(request):
    """Страница со списком социальных игр и бронирований"""
    from .models import GameParticipant

    today = timezone.now().date()

    # Публичные игры (americano/mexicano), в которых можно участвовать
    public_games = Booking.objects.filter(
        is_public=True,
        game_mode__in=['americano', 'mexicano'],
        date__gte=today,
        game_status__in=['pending', 'ready']
    ).exclude(
        user=request.user
    ).select_related('user', 'court', 'user__rating').prefetch_related(
        'game_participants__user__rating'
    ).order_by('date', 'start_time')

    # Публичные бронирования, которые ищут партнёров (обычные игры)
    public_bookings = Booking.objects.filter(
        looking_for_partner=True,
        status__in=['pending', 'confirmed'],
        date__gte=today
    ).exclude(
        user=request.user
    ).exclude(
        partners=request.user
    ).exclude(
        game_mode__in=['americano', 'mexicano']
    ).select_related('user', 'court', 'user__profile', 'user__rating').prefetch_related(
        'partners'
    ).order_by('date', 'start_time')

    # Приглашения пользователя в социальные игры
    game_invitations = GameParticipant.objects.filter(
        user=request.user,
        status='invited',
        booking__date__gte=today
    ).select_related('booking', 'booking__court', 'booking__user').order_by('booking__date', 'booking__start_time')

    # Мои игры (americano/mexicano) через GameParticipant
    my_games = GameParticipant.objects.filter(
        user=request.user,
        status__in=['accepted', 'joined'],
        booking__date__gte=today
    ).select_related('booking', 'booking__court').prefetch_related(
        'booking__game_participants__user__rating'
    ).order_by('booking__date', 'booking__start_time')

    # Мои обычные бронирования (как создатель или партнёр)
    my_bookings = Booking.objects.filter(
        Q(user=request.user) | Q(partners=request.user),
        date__gte=today,
        status__in=['pending', 'confirmed']
    ).exclude(
        game_mode__in=['americano', 'mexicano']
    ).select_related('court', 'user').prefetch_related(
        'partners'
    ).distinct().order_by('date', 'start_time')

    context = {
        'public_games': public_games,
        'public_bookings': public_bookings,
        'game_invitations': game_invitations,
        'my_games': my_games,
        'my_bookings': my_bookings,
        'today': today
    }

    return render(request, 'booking/games_list.html', context)


@login_required
@require_POST
def invite_to_game(request, booking_id):
    """Пригласить игрока в социальную игру"""
    from .models import GameParticipant

    try:
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

        if booking.game_mode not in ['americano', 'mexicano']:
            return JsonResponse({
                'success': False,
                'message': 'Это не социальная игра'
            })

        user_id = request.POST.get('user_id')
        invited_user = get_object_or_404(User, id=user_id)

        # Проверяем, что игрок еще не приглашен
        existing = GameParticipant.objects.filter(booking=booking, user=invited_user).first()
        if existing:
            return JsonResponse({
                'success': False,
                'message': 'Этот игрок уже приглашен'
            })

        # Проверяем количество участников
        participants_count = GameParticipant.objects.filter(booking=booking).count()
        if participants_count >= 4:
            return JsonResponse({
                'success': False,
                'message': 'Достигнуто максимальное количество участников (4)'
            })

        # Получаем рейтинг приглашаемого
        try:
            rating_before = invited_user.rating.numeric_rating
        except Exception:
            rating_before = 1.00

        # Создаем приглашение
        participant = GameParticipant.objects.create(
            booking=booking,
            user=invited_user,
            position=participants_count + 1,
            status='invited',
            rating_before=rating_before
        )

        logger.info(f"User {request.user.username} invited {invited_user.username} to game {booking_id}")

        return JsonResponse({
            'success': True,
            'message': f'Приглашение отправлено пользователю {invited_user.get_full_name() or invited_user.username}'
        })

    except Exception as e:
        logger.error(f"Error inviting to game: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при отправке приглашения'
        }, status=500)


@login_required
@require_POST
def accept_game_invitation(request, participant_id):
    """Принять приглашение в социальную игру"""
    from .models import GameParticipant

    try:
        participant = get_object_or_404(GameParticipant, id=participant_id, user=request.user, status='invited')

        participant.status = 'accepted'
        participant.save()

        # Проверяем, готова ли игра к началу (4 принятых участника, нет ожидающих)
        booking = participant.booking
        accepted_count = booking.game_participants.filter(status='accepted').count()
        has_pending = booking.game_participants.filter(status='invited').exists()

        if accepted_count >= 4 and not has_pending:
            booking.game_status = 'ready'
            booking.save()

        logger.info(f"User {request.user.username} accepted game invitation {participant_id}")

        return JsonResponse({
            'success': True,
            'message': 'Вы присоединились к игре!'
        })

    except Exception as e:
        logger.error(f"Error accepting game invitation: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при принятии приглашения'
        }, status=500)


@login_required
@require_POST
def decline_game_invitation(request, participant_id):
    """Отклонить приглашение в социальную игру"""
    from .models import GameParticipant

    try:
        participant = get_object_or_404(GameParticipant, id=participant_id, user=request.user, status='invited')

        participant.status = 'declined'
        participant.save()

        logger.info(f"User {request.user.username} declined game invitation {participant_id}")

        return JsonResponse({
            'success': True,
            'message': 'Приглашение отклонено'
        })

    except Exception as e:
        logger.error(f"Error declining game invitation: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при отклонении приглашения'
        }, status=500)


@login_required
@require_POST
def start_game(request, booking_id):
    """Начать игру и сгенерировать раунды"""
    from .models import GameParticipant, GameRound

    try:
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

        if booking.game_status != 'ready':
            return JsonResponse({
                'success': False,
                'message': 'Игра не готова к началу'
            })

        # Получаем всех участников
        participants = list(booking.game_participants.filter(status='accepted').order_by('position'))

        if len(participants) != 4:
            return JsonResponse({
                'success': False,
                'message': 'Для начала игры требуется 4 участника'
            })

        # Обновляем статус участников
        for participant in participants:
            participant.status = 'joined'
            participant.save()

        # Генерируем раунды
        players = [p.user for p in participants]

        # Americano: каждый играет с каждым в паре
        rounds_data = [
            # Раунд 1: 1-2 vs 3-4
            (players[0], players[1], players[2], players[3]),
            # Раунд 2: 1-3 vs 2-4
            (players[0], players[2], players[1], players[3]),
            # Раунд 3: 1-4 vs 2-3
            (players[0], players[3], players[1], players[2]),
        ]

        # Создаем раунды
        for round_num, (p1, p2, p3, p4) in enumerate(rounds_data, start=1):
            if round_num <= booking.rounds_count:
                GameRound.objects.create(
                    booking=booking,
                    round_number=round_num,
                    team1_player1=p1,
                    team1_player2=p2,
                    team2_player1=p3,
                    team2_player2=p4
                )

        booking.game_status = 'in_progress'
        booking.current_round = 1
        booking.save()

        logger.info(f"Game {booking_id} started by user {request.user.username}")

        return JsonResponse({
            'success': True,
            'message': 'Игра началась!',
            'current_round': 1
        })

    except Exception as e:
        logger.error(f"Error starting game: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при начале игры'
        }, status=500)


@login_required
@require_POST
def submit_round_score(request, booking_id, round_number):
    """Ввести счет раунда"""
    from .models import GameParticipant, GameRound

    try:
        booking = get_object_or_404(Booking, id=booking_id)

        # Проверяем, что пользователь является участником
        participant = GameParticipant.objects.filter(booking=booking, user=request.user, status='joined').first()
        if not participant:
            return JsonResponse({
                'success': False,
                'message': 'Вы не являетесь участником этой игры'
            })

        game_round = get_object_or_404(GameRound, booking=booking, round_number=round_number)

        if game_round.is_completed:
            return JsonResponse({
                'success': False,
                'message': 'Этот раунд уже завершен'
            })

        team1_score = int(request.POST.get('team1_score', 0))
        team2_score = int(request.POST.get('team2_score', 0))

        # Валидация счета
        if team1_score < 0 or team2_score < 0:
            return JsonResponse({
                'success': False,
                'message': 'Счет не может быть отрицательным'
            })

        if team1_score + team2_score != booking.points_per_round:
            return JsonResponse({
                'success': False,
                'message': f'Сумма очков должна быть {booking.points_per_round}'
            })

        # Сохраняем счет
        game_round.team1_score = team1_score
        game_round.team2_score = team2_score
        game_round.is_completed = True
        game_round.completed_at = timezone.now()
        game_round.save()

        # Обновляем очки участников
        participants = booking.game_participants.filter(status='joined')
        for participant in participants:
            points = game_round.get_player_points(participant.user)
            participant.total_points += points
            participant.save()

        # Проверяем, все ли раунды завершены
        all_completed = not booking.game_rounds.filter(is_completed=False).exists()

        if all_completed:
            booking.game_status = 'completed'
            booking.save()

            # Рассчитываем изменения рейтинга
            calculate_rating_changes(booking)

            logger.info(f"Game {booking_id} completed")

            return JsonResponse({
                'success': True,
                'message': 'Игра завершена! Рейтинги обновлены.',
                'game_completed': True
            })
        else:
            # Переходим к следующему раунду
            booking.current_round = round_number + 1
            booking.save()

            logger.info(f"Round {round_number} of game {booking_id} completed")

            return JsonResponse({
                'success': True,
                'message': f'Раунд {round_number} завершен!',
                'next_round': round_number + 1,
                'game_completed': False
            })

    except Exception as e:
        logger.error(f"Error submitting round score: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при сохранении счета'
        }, status=500)

def calculate_rating_changes(booking):
    """Рассчитать изменения рейтинга после завершения игры"""
    from .models import GameParticipant
    from users.models import PlayerRating

    participants = list(booking.game_participants.filter(status='joined').order_by('-total_points'))

    if len(participants) != 4:
        return

    # Простая система: победитель +0.05, второй +0.02, третий -0.02, четвертый -0.05
    rating_changes = [0.05, 0.02, -0.02, -0.05]

    for i, participant in enumerate(participants):
        change = rating_changes[i]
        participant.rating_change = change
        participant.save()

        # Обновляем рейтинг пользователя
        try:
            rating = participant.user.rating
            old_rating = rating.numeric_rating
            new_rating = max(1.00, min(7.00, float(old_rating) + change))
            rating.numeric_rating = new_rating
            rating.save()

            # Добавляем в историю
            rating.add_to_history(
                old_rating=old_rating,
                new_rating=new_rating,
                updated_by=None,
                comment=f'Игра {booking.game_mode}: {i+1} место, {participant.total_points} очков'
            )

            logger.info(f"Updated rating for {participant.user.username}: {old_rating} -> {new_rating} ({change:+.2f})")
        except Exception as e:
            logger.error(f"Error updating rating for user {participant.user.id}: {str(e)}")


@login_required
@login_required
def game_detail(request, booking_id):
    """Детальная страница игры"""
    from .models import GameParticipant, GameRound

    booking = get_object_or_404(Booking, id=booking_id)

    # Проверяем доступ - поддерживаем оба типа игр
    # 1. Социальные игры (Americano) с GameParticipant
    is_game_participant = GameParticipant.objects.filter(booking=booking, user=request.user).exists()

    # 2. Обычные игры с partners (ManyToMany)
    is_partner = request.user in booking.partners.all()

    # Общая проверка участника
    is_participant = is_game_participant or is_partner or booking.user == request.user
    is_creator = booking.user == request.user

    if not (is_participant or booking.is_public or booking.looking_for_partner):
        return JsonResponse({
            'success': False,
            'message': 'У вас нет доступа к этой игре'
        }, status=403)

    # Для americano/mexicano — используем GameParticipant
    game_participants = booking.game_participants.all().select_related('user', 'user__rating', 'user__profile').order_by('position')

    # Для обычных бронирований — строим список из owner + partners
    partners_list = []
    if not game_participants.exists():
        # Добавляем создателя
        partners_list.append({
            'user': booking.user,
            'is_creator': True,
        })
        # Добавляем партнёров
        for partner in booking.partners.select_related('profile', 'rating').all():
            partners_list.append({
                'user': partner,
                'is_creator': False,
            })

    rounds = booking.game_rounds.all().order_by('round_number')

    context = {
        'booking': booking,
        'participants': game_participants,
        'partners_list': partners_list,
        'rounds': rounds,
        'is_creator': is_creator,
        'is_participant': is_participant
    }

    return render(request, 'booking/game_detail.html', context)


@login_required
def create_game_page(request):
    """Страница создания игры с современным интерфейсом"""
    return render(request, 'booking/create_game.html')


# ===========================
# COACH BOOKING API
# ===========================

@login_required
@require_GET
def api_coach_detail(request, coach_id):
    """API: Получить информацию о тренере"""
    try:
        from django.contrib.auth.models import User
        coach = get_object_or_404(User, id=coach_id, groups__name='Тренеры')

        data = {
            'success': True,
            'coach': {
                'id': coach.id,
                'username': coach.username,
                'full_name': coach.get_full_name() or coach.username,
                'email': coach.email,
            }
        }

        # Добавляем профиль если есть
        if hasattr(coach, 'profile'):
            profile = coach.profile
            data['coach']['specialization'] = profile.specialization if hasattr(profile, 'specialization') else None
            data['coach']['price_per_hour'] = float(profile.price_per_hour) if hasattr(profile, 'price_per_hour') else None
            data['coach']['bio'] = profile.bio if hasattr(profile, 'bio') else None
            data['coach']['phone'] = profile.phone if hasattr(profile, 'phone') else None

        return JsonResponse(data)

    except Exception as e:
        logger.error(f"Error getting coach info: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Ошибка получения информации о тренере'
        }, status=500)


@login_required
@require_GET
def api_courts_list(request):
    """API: Получить список доступных кортов"""
    try:
        courts = Court.objects.filter(is_available=True).order_by('name')

        data = {
            'success': True,
            'courts': [
                {
                    'id': court.id,
                    'name': court.name,
                    'description': court.description,
                    'price_per_hour': float(court.price_per_hour),
                    'is_available': court.is_available
                }
                for court in courts
            ]
        }

        return JsonResponse(data)

    except Exception as e:
        logger.error(f"Error getting courts list: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Ошибка получения списка кортов'
        }, status=500)


# ===========================
# WAITING LIST API
# ===========================

@login_required
@require_POST
def join_game_waiting_list(request, booking_id):
    """Добавить запрос на присоединение к игре (в лист ожидания)"""
    from .models import WaitingList

    booking = get_object_or_404(Booking, id=booking_id)

    # Проверяем, что пользователь не создатель
    if booking.user == request.user:
        return JsonResponse({
            'success': False,
            'message': 'Вы создатель этой игры'
        })

    # Проверяем, что пользователь не партнёр
    if request.user in booking.partners.all():
        return JsonResponse({
            'success': False,
            'message': 'Вы уже участник этой игры'
        })

    # Проверяем, что игра ищет партнёров
    if not booking.looking_for_partner:
        return JsonResponse({
            'success': False,
            'message': 'Игра не ищет партнёров'
        })

    # Проверяем, что есть свободные места
    if booking.is_full:
        return JsonResponse({
            'success': False,
            'message': 'Нет свободных мест'
        })

    # Проверяем, нет ли уже запроса
    existing = WaitingList.objects.filter(
        booking=booking,
        user=request.user,
        status='pending'
    ).exists()

    if existing:
        return JsonResponse({
            'success': False,
            'message': 'Вы уже отправили запрос на присоединение'
        })

    # Получаем сообщение из запроса
    message = request.POST.get('message', '').strip()

    # Создаём запрос в лист ожидания
    waiting = WaitingList.objects.create(
        booking=booking,
        user=request.user,
        message=message,
        status='pending'
    )

    # Отправляем системное сообщение в чат
    from .models import GameChat
    user_name = request.user.get_full_name() or request.user.username
    GameChat.send_system_message(
        booking=booking,
        message=f"{user_name} хочет присоединиться к игре"
    )

    logger.info(f"User {request.user.username} joined waiting list for booking {booking.id}")

    return JsonResponse({
        'success': True,
        'message': 'Запрос отправлен владельцу игры',
        'waiting_id': waiting.id
    })


@login_required
def get_waiting_list(request, booking_id):
    """Получить лист ожидания для игры"""
    from .models import WaitingList

    booking = get_object_or_404(Booking, id=booking_id)

    # Проверяем, что пользователь - владелец игры
    if booking.user != request.user:
        return JsonResponse({
            'success': False,
            'message': 'Только владелец может просматривать лист ожидания'
        }, status=403)

    # Получаем pending запросы
    waiting_list = WaitingList.objects.filter(
        booking=booking,
        status='pending'
    ).select_related('user', 'user__rating').order_by('created_at')

    data = []
    for waiting in waiting_list:
        user_data = {
            'id': waiting.id,
            'user': {
                'id': waiting.user.id,
                'username': waiting.user.username,
                'full_name': waiting.user.get_full_name() or waiting.user.username,
                'rating': None
            },
            'message': waiting.message,
            'created_at': waiting.created_at.isoformat()
        }

        # Добавляем рейтинг если есть
        if hasattr(waiting.user, 'rating'):
            user_data['user']['rating'] = {
                'level': waiting.user.rating.level,
                'numeric': float(waiting.user.rating.numeric_rating)
            }

        data.append(user_data)

    return JsonResponse({
        'success': True,
        'waiting_list': data,
        'count': len(data)
    })


@login_required
@require_POST
def approve_waiting_list(request, waiting_id):
    """Одобрить запрос из листа ожидания"""
    from .models import WaitingList, GameChat

    waiting = get_object_or_404(WaitingList, id=waiting_id)
    booking = waiting.booking

    # Проверяем, что пользователь - владелец игры
    if booking.user != request.user:
        return JsonResponse({
            'success': False,
            'message': 'Только владелец может одобрять запросы'
        }, status=403)

    # Одобряем запрос
    success, message = waiting.approve(approved_by=request.user)

    if success:
        # Отправляем системное сообщение в чат
        user_name = waiting.user.get_full_name() or waiting.user.username
        GameChat.send_system_message(
            booking=booking,
            message=f"{user_name} присоединился к игре"
        )

        logger.info(f"User {waiting.user.username} approved for booking {booking.id}")

    return JsonResponse({
        'success': success,
        'message': message
    })


@login_required
@require_POST
def reject_waiting_list(request, waiting_id):
    """Отклонить запрос из листа ожидания"""
    from .models import WaitingList

    waiting = get_object_or_404(WaitingList, id=waiting_id)
    booking = waiting.booking

    # Проверяем, что пользователь - владелец игры
    if booking.user != request.user:
        return JsonResponse({
            'success': False,
            'message': 'Только владелец может отклонять запросы'
        }, status=403)

    # Получаем причину отклонения
    reason = request.POST.get('reason', '').strip()

    # Отклоняем запрос
    success, message = waiting.reject(rejected_by=request.user, reason=reason)

    if success:
        logger.info(f"Waiting request {waiting_id} rejected for booking {booking.id}")

    return JsonResponse({
        'success': success,
        'message': message
    })


# ===========================
# GAME CHAT API
# ===========================

@login_required
def get_game_chat(request, booking_id):
    """Получить сообщения чата игры"""
    from .models import GameChat, GameParticipant

    booking = get_object_or_404(Booking, id=booking_id)

    # Проверяем, что пользователь - участник игры (обычная или Americano/Mexicano)
    is_participant = (
        booking.user == request.user or
        request.user in booking.partners.all() or
        GameParticipant.objects.filter(booking=booking, user=request.user).exists()
    )

    if not is_participant:
        return JsonResponse({
            'success': False,
            'message': 'Только участники игры могут видеть чат'
        }, status=403)

    # Получаем сообщения
    messages = GameChat.objects.filter(
        booking=booking
    ).select_related('user').order_by('created_at')

    # Ограничиваем последними 100 сообщениями
    messages = messages[:100]

    data = []
    for msg in messages:
        data.append({
            'id': msg.id,
            'user': {
                'id': msg.user.id,
                'username': msg.user.username,
                'full_name': msg.user.get_full_name() or msg.user.username
            },
            'message': msg.message,
            'is_system': msg.is_system_message,
            'created_at': msg.created_at.isoformat(),
            'is_own': msg.user == request.user
        })

    return JsonResponse({
        'success': True,
        'messages': data,
        'count': len(data)
    })


@login_required
@require_POST
def send_game_chat_message(request, booking_id):
    """Отправить сообщение в чат игры"""
    from .models import GameChat, GameParticipant

    booking = get_object_or_404(Booking, id=booking_id)

    # Проверяем, что пользователь - участник игры (обычная или Americano/Mexicano)
    is_participant = (
        booking.user == request.user or
        request.user in booking.partners.all() or
        GameParticipant.objects.filter(booking=booking, user=request.user).exists()
    )

    if not is_participant:
        return JsonResponse({
            'success': False,
            'message': 'Только участники игры могут отправлять сообщения'
        }, status=403)

    # Получаем сообщение
    message_text = request.POST.get('message', '').strip()

    if not message_text:
        return JsonResponse({
            'success': False,
            'message': 'Сообщение не может быть пустым'
        })

    if len(message_text) > 1000:
        return JsonResponse({
            'success': False,
            'message': 'Сообщение слишком длинное (максимум 1000 символов)'
        })

    # Создаём сообщение
    chat_message = GameChat.objects.create(
        booking=booking,
        user=request.user,
        message=message_text,
        is_system_message=False
    )

    logger.info(f"Chat message sent by {request.user.username} for booking {booking.id}")

    return JsonResponse({
        'success': True,
        'message': 'Сообщение отправлено',
        'chat_message': {
            'id': chat_message.id,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'full_name': request.user.get_full_name() or request.user.username
            },
            'message': chat_message.message,
            'is_system': False,
            'created_at': chat_message.created_at.isoformat(),
            'is_own': True
        }
    })


@login_required
@require_POST
def remove_participant(request, booking_id, user_id):
    """Удалить участника из игры (только для организатора)"""
    from .models import GameParticipant
    from django.contrib.auth.models import User

    try:
        booking = get_object_or_404(Booking, id=booking_id)

        # Только организатор может удалять участников
        if booking.user != request.user:
            return JsonResponse({
                'success': False,
                'message': 'Только организатор может удалять участников'
            }, status=403)

        # Нельзя удалить себя через этот endpoint
        if int(user_id) == request.user.id:
            return JsonResponse({
                'success': False,
                'message': 'Организатор не может удалить себя'
            })

        # Нельзя удалять участников из уже начатой игры
        if booking.game_status in ('in_progress', 'completed'):
            return JsonResponse({
                'success': False,
                'message': 'Нельзя удалять участников из начавшейся игры'
            })

        target_user = get_object_or_404(User, id=user_id)

        # Для americano/mexicano — удаляем GameParticipant
        participant = GameParticipant.objects.filter(booking=booking, user=target_user).first()
        if participant:
            participant.delete()

        # Для обычных бронирований — удаляем из partners
        if target_user in booking.partners.all():
            booking.partners.remove(target_user)

        # Обновляем статус игры если нужно
        if booking.game_status == 'ready':
            booking.game_status = 'pending'
            booking.save()

        logger.info(f"User {target_user.username} removed from booking {booking_id} by {request.user.username}")

        return JsonResponse({
            'success': True,
            'message': f'Участник {target_user.get_full_name() or target_user.username} удалён из игры'
        })

    except Exception as e:
        logger.error(f"Error removing participant: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при удалении участника'
        }, status=500)


@login_required
@require_POST
def leave_game(request, booking_id):
    """Выйти из игры (для обычного участника, не организатора)"""
    from .models import GameParticipant

    try:
        booking = get_object_or_404(Booking, id=booking_id)

        # Организатор не может использовать этот endpoint
        if booking.user == request.user:
            return JsonResponse({
                'success': False,
                'message': 'Организатор не может выйти из игры. Передайте роль другому участнику.'
            })

        # Нельзя выходить из начавшейся игры
        if booking.game_status in ('in_progress', 'completed'):
            return JsonResponse({
                'success': False,
                'message': 'Нельзя выйти из уже начавшейся игры'
            })

        removed = False

        # Для americano/mexicano — удаляем GameParticipant
        participant = GameParticipant.objects.filter(booking=booking, user=request.user).first()
        if participant:
            participant.delete()
            removed = True

        # Для обычных бронирований — удаляем из partners
        if request.user in booking.partners.all():
            booking.partners.remove(request.user)
            removed = True

        if not removed:
            return JsonResponse({
                'success': False,
                'message': 'Вы не являетесь участником этой игры'
            })

        # Обновляем статус если нужно
        if booking.game_status == 'ready':
            booking.game_status = 'pending'
            booking.save()

        logger.info(f"User {request.user.username} left booking {booking_id}")

        return JsonResponse({
            'success': True,
            'message': 'Вы вышли из игры'
        })

    except Exception as e:
        logger.error(f"Error leaving game: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при выходе из игры'
        }, status=500)


@login_required
@require_POST
def transfer_organizer(request, booking_id, user_id):
    """Передать роль организатора другому участнику"""
    from django.contrib.auth.models import User

    try:
        booking = get_object_or_404(Booking, id=booking_id)

        # Только текущий организатор может передать роль
        if booking.user != request.user:
            return JsonResponse({
                'success': False,
                'message': 'Только организатор может передать свою роль'
            }, status=403)

        # Нельзя передать себе
        if int(user_id) == request.user.id:
            return JsonResponse({
                'success': False,
                'message': 'Нельзя передать роль самому себе'
            })

        # Нельзя менять организатора в начавшейся игре
        if booking.game_status in ('in_progress', 'completed'):
            return JsonResponse({
                'success': False,
                'message': 'Нельзя менять организатора в начавшейся игре'
            })

        target_user = get_object_or_404(User, id=user_id)

        # Проверяем что target_user является участником
        is_partner = target_user in booking.partners.all()
        is_game_participant = booking.game_participants.filter(user=target_user).exists()

        if not (is_partner or is_game_participant):
            return JsonResponse({
                'success': False,
                'message': 'Пользователь не является участником этой игры'
            })

        old_organizer = booking.user

        # Добавляем старого организатора в partners, удаляем нового из partners
        booking.partners.add(old_organizer)
        booking.partners.remove(target_user)
        booking.user = target_user
        booking.save()

        logger.info(
            f"Organizer of booking {booking_id} transferred from {old_organizer.username} to {target_user.username}"
        )

        return JsonResponse({
            'success': True,
            'message': f'Роль организатора передана {target_user.get_full_name() or target_user.username}'
        })

    except Exception as e:
        logger.error(f"Error transferring organizer: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при передаче роли организатора'
        }, status=500)


@login_required
@require_POST
def generate_round(request, booking_id):
    """Сгенерировать следующий раунд для игры в процессе (только организатор)"""
    from .models import GameParticipant, GameRound
    import random

    try:
        booking = get_object_or_404(Booking, id=booking_id)

        if booking.user != request.user:
            return JsonResponse({
                'success': False,
                'message': 'Только организатор может генерировать раунды'
            }, status=403)

        if booking.game_status != 'in_progress':
            return JsonResponse({
                'success': False,
                'message': 'Генерация раунда возможна только в активной игре'
            })

        # Проверяем незавершённые раунды
        pending_rounds = booking.game_rounds.filter(is_completed=False)
        if pending_rounds.exists():
            return JsonResponse({
                'success': False,
                'message': 'Завершите текущий раунд перед генерацией нового'
            })

        # Проверяем лимит раундов
        current_rounds_count = booking.game_rounds.count()
        if current_rounds_count >= booking.rounds_count:
            return JsonResponse({
                'success': False,
                'message': f'Достигнут лимит раундов ({booking.rounds_count})'
            })

        players = list(
            GameParticipant.objects.filter(booking=booking, status='joined')
            .select_related('user')
            .values_list('user', flat=True)
        )

        if len(players) < 4:
            return JsonResponse({
                'success': False,
                'message': 'Для генерации раунда нужно минимум 4 игрока'
            })

        from django.contrib.auth.models import User
        player_users = list(User.objects.filter(id__in=players))
        random.shuffle(player_users)

        next_round_number = current_rounds_count + 1

        GameRound.objects.create(
            booking=booking,
            round_number=next_round_number,
            team1_player1=player_users[0],
            team1_player2=player_users[1],
            team2_player1=player_users[2],
            team2_player2=player_users[3],
        )

        booking.current_round = next_round_number
        booking.save()

        logger.info(f"Round {next_round_number} generated for booking {booking_id}")

        return JsonResponse({
            'success': True,
            'message': f'Раунд {next_round_number} сгенерирован',
            'round_number': next_round_number
        })

    except Exception as e:
        logger.error(f"Error generating round: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Ошибка при генерации раунда'
        }, status=500)
