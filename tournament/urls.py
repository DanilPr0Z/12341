"""
URLs для приложения tournament
"""
from django.urls import path
from . import views

app_name = 'tournament'

urlpatterns = [
    # HTML страницы - Админка
    path('', views.tournaments_list, name='tournaments_list'),
    path('<int:tournament_id>/', views.tournament_detail, name='tournament_detail'),

    # Публичные страницы для игроков
    path('public/', views.public_tournaments_list, name='public_tournaments_list'),
    path('public/<int:tournament_id>/', views.public_tournament_detail, name='public_tournament_detail'),
    path('public/<int:tournament_id>/register/', views.public_tournament_register, name='public_tournament_register'),
    path('public/<int:tournament_id>/unregister/', views.public_tournament_unregister, name='public_tournament_unregister'),

    # API - CRUD турниров
    path('api/list/', views.api_tournaments_list, name='api_tournaments_list'),
    path('api/<int:tournament_id>/', views.api_tournament_detail, name='api_tournament_detail'),
    path('api/create/', views.api_tournament_create, name='api_tournament_create'),
    path('api/<int:tournament_id>/update/', views.api_tournament_update, name='api_tournament_update'),
    path('api/<int:tournament_id>/delete/', views.api_tournament_delete, name='api_tournament_delete'),

    # API - Участники
    path('api/<int:tournament_id>/add-participant/', views.api_tournament_add_participant, name='api_add_participant'),
    path('api/<int:tournament_id>/participants/<int:participant_id>/remove/', views.api_tournament_remove_participant, name='api_remove_participant'),
    path('api/<int:tournament_id>/participants/<int:participant_id>/set-seed/', views.api_tournament_set_seed, name='api_set_seed'),

    # API - Сетка турнира
    path('api/<int:tournament_id>/generate-bracket/', views.api_tournament_generate_bracket, name='api_generate_bracket'),
    path('api/<int:tournament_id>/generate-next-round/', views.api_tournament_generate_next_round, name='api_generate_next_round'),
    path('api/<int:tournament_id>/bracket/', views.api_tournament_bracket, name='api_tournament_bracket'),
    path('api/<int:tournament_id>/leaderboard/', views.api_tournament_leaderboard, name='api_tournament_leaderboard'),

    # API - Матчи
    path('api/matches/<int:match_id>/set-score/', views.api_match_set_score, name='api_match_set_score'),
    path('api/matches/<int:match_id>/set-winner/', views.api_match_set_winner, name='api_match_set_winner'),  # legacy
    path('api/matches/<int:match_id>/schedule/', views.api_match_schedule, name='api_match_schedule'),

    # Публичный список турниров (без авторизации)
    path('api/public/list/', views.api_public_tournaments_list, name='api_public_tournaments_list'),

    # Публичные API endpoints (для игроков)
    path('ajax/tournament/<int:tournament_id>/generate-bracket/', views.ajax_generate_bracket, name='ajax_generate_bracket'),
    path('ajax/match/<int:match_id>/submit-score/', views.ajax_submit_match_score, name='ajax_submit_match_score'),
    path('ajax/tournament/<int:tournament_id>/leaderboard/', views.ajax_public_tournament_leaderboard, name='ajax_public_tournament_leaderboard'),
]
