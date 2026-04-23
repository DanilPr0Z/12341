from django.urls import path
from . import views

urlpatterns = [
    path('', views.booking_page, name='booking'),
    path('available-slots/', views.get_available_slots, name='available_slots'),
    path('create/', views.create_booking, name='create_booking'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('confirm/<int:booking_id>/', views.confirm_booking, name='confirm_booking'),
    path('booking-info/<int:booking_id>/', views.get_booking_info, name='booking_info'),

    # Система поиска партнёров
    path('find-partners/', views.find_partners, name='find_partners'),
    path('join/<int:booking_id>/', views.join_booking, name='join_booking'),
    path('invite/<int:booking_id>/', views.send_invitation, name='send_invitation'),
    path('my-invitations/', views.my_invitations, name='my_invitations'),
    path('<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('invitation/<int:invitation_id>/accept/', views.accept_invitation, name='accept_invitation'),
    path('invitation/<int:invitation_id>/decline/', views.decline_invitation, name='decline_invitation'),
    path('invitation/<int:invitation_id>/cancel/', views.cancel_invitation, name='cancel_invitation'),

    # Статистика игрока
    path('statistics/', views.player_statistics, name='player_statistics'),

    # Проверка доступности слота
    path('check-availability/', views.check_availability, name='check_availability'),

    # API endpoints
    path('api/stats/', views.api_player_stats, name='api_player_stats'),
    path('api/calendar-events/', views.api_calendar_events, name='api_calendar_events'),
    path('api/available-slots/', views.api_available_slots, name='api_available_slots'),
    path('api/coaches/', views.get_coaches_list, name='api_coaches_list'),
    path('api/coaches/<int:coach_id>/', views.api_coach_detail, name='api_coach_detail'),
    path('api/courts/', views.api_courts_list, name='api_courts_list'),
    path('api/search-users/', views.api_search_users, name='api_search_users'),
    path('api/notifications/', views.api_get_notifications, name='api_get_notifications'),
    path('api/invitation/<int:invitation_id>/accept/', views.api_accept_invitation, name='api_accept_invitation'),
    path('api/invitation/<int:invitation_id>/decline/', views.api_decline_invitation, name='api_decline_invitation'),

    # Социальные игры (Americano/Mexicano)
    path('games/', views.games_list, name='games_list'),
    path('games/create/', views.create_game_page, name='create_game_page'),
    path('games/<int:booking_id>/', views.game_detail, name='game_detail'),
    path('games/<int:booking_id>/invite/', views.invite_to_game, name='invite_to_game'),
    path('games/<int:booking_id>/start/', views.start_game, name='start_game'),
    path('games/<int:booking_id>/round/<int:round_number>/score/', views.submit_round_score, name='submit_round_score'),
    path('games/invitation/<int:participant_id>/accept/', views.accept_game_invitation, name='accept_game_invitation'),
    path('games/invitation/<int:participant_id>/decline/', views.decline_game_invitation, name='decline_game_invitation'),

    # Лист ожидания (Waiting List)
    path('waiting-list/<int:booking_id>/join/', views.join_game_waiting_list, name='join_waiting_list'),
    path('waiting-list/<int:booking_id>/', views.get_waiting_list, name='get_waiting_list'),
    path('waiting-list/<int:waiting_id>/approve/', views.approve_waiting_list, name='approve_waiting'),
    path('waiting-list/<int:waiting_id>/reject/', views.reject_waiting_list, name='reject_waiting'),

    # Чат игры (Game Chat)
    path('chat/<int:booking_id>/', views.get_game_chat, name='get_game_chat'),
    path('chat/<int:booking_id>/send/', views.send_game_chat_message, name='send_chat_message'),

    # Управление участниками
    path('games/<int:booking_id>/remove/<int:user_id>/', views.remove_participant, name='remove_participant'),
    path('games/<int:booking_id>/leave/', views.leave_game, name='leave_game'),
    path('games/<int:booking_id>/transfer/<int:user_id>/', views.transfer_organizer, name='transfer_organizer'),
    path('games/<int:booking_id>/generate-round/', views.generate_round, name='generate_round'),
]