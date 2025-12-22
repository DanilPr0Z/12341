from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from django.core.exceptions import ValidationError

from .forms import RegistrationForm, LoginForm
from .models import UserProfile
from booking.models import Booking


@require_POST
@csrf_exempt
def ajax_register(request):
    """AJAX регистрация - исправленная версия"""
    try:
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return JsonResponse({
                'success': True,
                'message': 'Регистрация успешна!',
                'username': user.username
            })

        # ИСПРАВЛЕНО: правильный формат ошибок для JavaScript
        errors = {}
        for field, error_list in form.errors.items():
            # Преобразуем ошибки в простые строки
            errors[field] = [str(error) for error in error_list]

        # Получаем общее сообщение об ошибке (первая ошибка)
        first_error = ''
        if errors:
            first_field = list(errors.keys())[0]
            if errors[first_field]:
                first_error = errors[first_field][0]

        return JsonResponse({
            'success': False,
            'errors': errors,
            'message': first_error or 'Пожалуйста, исправьте ошибки в форме'
        })

    except Exception as e:
        # Логируем ошибку для отладки
        print(f"Ошибка при регистрации: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Ошибка сервера: {str(e)}'
        }, status=500)


@require_POST
@csrf_exempt
def ajax_login(request):
    """AJAX вход по username или телефону"""
    try:
        form = LoginForm(request.POST)

        if form.is_valid():
            identifier_data = form.cleaned_data.get('identifier')
            password = form.cleaned_data.get('password')

            # Определяем username для аутентификации
            username = identifier_data['username']

            # Пытаемся аутентифицировать пользователя
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': 'Вход выполнен успешно!',
                    'username': user.username
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Неверный пароль'
                })

        # Возвращаем ошибки формы
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]

        first_error = ''
        if errors:
            first_field = list(errors.keys())[0]
            if errors[first_field]:
                first_error = errors[first_field][0]

        return JsonResponse({
            'success': False,
            'errors': errors,
            'message': first_error or 'Пожалуйста, исправьте ошибки в форме'
        })

    except Exception as e:
        print(f"Ошибка при входе: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Ошибка сервера: {str(e)}'
        }, status=500)


def user_login(request):
    """Стандартный вход (для обратной совместимости)"""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier_data = form.cleaned_data.get('identifier')
            password = form.cleaned_data.get('password')

            # Определяем username для аутентификации
            username = identifier_data['username']

            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
    else:
        form = LoginForm()

    return render(request, 'users/login.html', {'form': form})


def register(request):
    """Стандартная регистрация (для обратной совместимости)"""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegistrationForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'users/profile.html')


def user_logout(request):
    logout(request)
    return redirect('home')


@require_POST
@csrf_exempt
def ajax_logout(request):
    """AJAX выход"""
    logout(request)
    return JsonResponse({
        'success': True,
        'message': 'Вы успешно вышли из аккаунта'
    })