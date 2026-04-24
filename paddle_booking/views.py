from django.shortcuts import render
from booking.models import Court
from django.utils import timezone


def home(request):
    return render(request, 'home.html')


def news(request):
    return render(request, 'news.html')


def booking_page(request):
    """Страница бронирования кортов"""
    # Получаем все доступные корты
    courts = Court.objects.filter(is_available=True).order_by('name')
    today_date = timezone.now().date()

    return render(request, 'booking.html', {
        'courts': courts,
        'today_date': today_date
    })


def tournaments(request):
    return render(request, 'tournaments.html')


def about(request):
    """Страница О нас"""
    return render(request, 'pages/about.html')


def rules(request):
    """Страница Правила"""
    return render(request, 'pages/rules.html')


def privacy_policy(request):
    """Страница Политика конфиденциальности"""
    return render(request, 'pages/privacy.html')


def terms_of_service(request):
    """Страница Пользовательское соглашение"""
    return render(request, 'pages/terms.html')
