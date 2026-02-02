"""
Manager App URLs
"""

from django.urls import path
from . import views

app_name = 'manager'

urlpatterns = [
    # Pages
    path('', views.dashboard, name='dashboard'),
    path('bookings/', views.bookings_list, name='bookings'),
    path('schedule/', views.schedule, name='schedule'),
    path('analytics/', views.analytics, name='analytics'),
    path('users/', views.users_list, name='users'),
    path('courts/', views.courts_list, name='courts'),
    path('trainers/', views.trainers_list, name='trainers'),
    path('payments/', views.payments_list, name='payments'),

    # API - Dashboard
    path('api/metrics/', views.api_metrics, name='api_metrics'),

    # API - Bookings
    path('api/bookings/', views.api_bookings_list, name='api_bookings_list'),
    path('api/bookings/create/', views.api_booking_create, name='api_booking_create'),
    path('api/bookings/<int:booking_id>/', views.api_booking_detail, name='api_booking_detail'),
    path('api/bookings/<int:booking_id>/update/', views.api_booking_update, name='api_booking_update'),
    path('api/bookings/<int:booking_id>/confirm/', views.api_booking_confirm, name='api_booking_confirm'),
    path('api/bookings/<int:booking_id>/cancel/', views.api_booking_cancel, name='api_booking_cancel'),
    path('api/bookings/<int:booking_id>/delete/', views.api_booking_delete, name='api_booking_delete'),
    path('api/bookings/export/', views.api_bookings_export, name='api_bookings_export'),

    # API - Courts
    path('api/courts/', views.api_courts_list, name='api_courts_list'),
    path('api/courts/create/', views.api_court_create, name='api_court_create'),
    path('api/courts/<int:court_id>/', views.api_court_detail, name='api_court_detail'),
    path('api/courts/<int:court_id>/update/', views.api_court_update, name='api_court_update'),
    path('api/courts/<int:court_id>/delete/', views.api_court_delete, name='api_court_delete'),

    # API - Analytics
    path('api/analytics/', views.api_analytics, name='api_analytics'),
    path('api/analytics/export/', views.api_analytics_export, name='api_analytics_export'),

    # API - Users
    path('api/users/', views.api_users_list, name='api_users_list'),
    path('api/users/create/', views.api_user_create, name='api_user_create'),
    path('api/users/<int:user_id>/', views.api_user_detail, name='api_user_detail'),
    path('api/users/<int:user_id>/update/', views.api_user_update, name='api_user_update'),
    path('api/users/<int:user_id>/delete/', views.api_user_delete, name='api_user_delete'),
    path('api/users/export/', views.api_users_export, name='api_users_export'),

    # API - Schedule
    path('api/schedule/', views.api_schedule, name='api_schedule'),
    path('api/schedule/events/', views.api_schedule_events, name='api_schedule_events'),
    path('api/bookings/<int:booking_id>/update-time/', views.api_booking_update_time, name='api_booking_update_time'),

    # API - Trainers
    path('api/trainers/', views.api_trainers_list, name='api_trainers_list'),
    path('api/trainers/create/', views.api_trainer_create, name='api_trainer_create'),
    path('api/trainers/<int:trainer_id>/', views.api_trainer_detail, name='api_trainer_detail'),
    path('api/trainers/<int:trainer_id>/update/', views.api_trainer_update, name='api_trainer_update'),
    path('api/trainers/<int:trainer_id>/delete/', views.api_trainer_delete, name='api_trainer_delete'),
    path('api/trainers/<int:trainer_id>/schedule/', views.api_trainer_schedule, name='api_trainer_schedule'),

    # API - Payments
    path('api/payments/', views.api_payments_list, name='api_payments_list'),
    path('api/payments/<int:payment_id>/', views.api_payment_detail, name='api_payment_detail'),
    path('api/payments/<int:payment_id>/mark-paid/', views.api_payment_mark_paid, name='api_payment_mark_paid'),
    path('api/payments/<int:payment_id>/refund/', views.api_payment_refund, name='api_payment_refund'),
    path('api/payments/export/', views.api_payments_export, name='api_payments_export'),
]
