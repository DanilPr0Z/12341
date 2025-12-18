from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import UserProfile
import re


class RegistrationForm(UserCreationForm):
    phone = forms.CharField(
        max_length=20,
        required=False,  # Сделали необязательным
        label='Номер телефона',
        widget=forms.TextInput(attrs={
            'placeholder': '+7 (999) 123-45-67 (необязательно)',
            'class': 'form-input',
            'id': 'regPhone'
        }),
        help_text='Российский номер телефона (необязательно)'
    )

    class Meta:
        model = User
        fields = ['username', 'phone', 'password1', 'password2']
        help_texts = {
            'username': 'Обязательное поле. Не более 150 символов. Только буквы, цифры и @/./+/-/_',
            'password1': 'Пароль должен содержать минимум 8 символов',
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        # Если поле пустое - возвращаем пустую строку
        if not phone or phone.strip() == '':
            return ''

        # Удаляем все нецифровые символы
        phone_digits = re.sub(r'\D', '', phone)

        # Если после очистки ничего не осталось - возвращаем пустую строку
        if not phone_digits:
            return ''

        # Проверяем базовую длину (российский номер: 11 цифр, включая код страны)
        if len(phone_digits) < 10:
            raise ValidationError('Номер слишком короткий. Введите 10-11 цифр или оставьте поле пустым.')

        if len(phone_digits) > 11:
            raise ValidationError('Номер слишком длинный. Введите 10-11 цифр или оставьте поле пустым.')

        # Преобразуем к стандартному формату +7XXXXXXXXXX
        if phone_digits.startswith('8'):
            # Если начинается с 8 (российский формат), меняем на 7
            phone_digits = '7' + phone_digits[1:]
        elif phone_digits.startswith('9'):
            # Если начинается с 9, добавляем 7
            phone_digits = '7' + phone_digits

        # Если после преобразований не начинается с 7, добавляем
        if not phone_digits.startswith('7'):
            phone_digits = '7' + phone_digits

        # Проверяем, что теперь 11 цифр
        if len(phone_digits) != 11:
            raise ValidationError(f'После форматирования получилось {len(phone_digits)} цифр. Нужно 11 цифр.')

        formatted_phone = '+' + phone_digits

        # Проверка уникальности только если номер не пустой
        if formatted_phone and formatted_phone != '+7' and formatted_phone != '+':
            if UserProfile.objects.filter(phone=formatted_phone).exists():
                raise ValidationError('Этот номер телефона уже зарегистрирован')

        return formatted_phone

    def clean_username(self):
        username = self.cleaned_data.get('username')

        # Проверяем, что имя пользователя не слишком короткое
        if len(username) < 3:
            raise ValidationError('Имя пользователя должно содержать минимум 3 символа')

        # Проверяем, что имя пользователя содержит только допустимые символы
        if not re.match(r'^[\w.@+-]+$', username):
            raise ValidationError('Имя пользователя содержит недопустимые символы')

        return username

    def save(self, commit=True):
        user = super().save(commit=False)

        if commit:
            user.save()
            # Получаем или создаем профиль
            profile, created = UserProfile.objects.get_or_create(user=user)

            # Устанавливаем телефон только если он есть
            phone = self.cleaned_data.get('phone')
            if phone:
                profile.phone = phone
                profile.generate_verification_code()
                profile.save()

            # Логируем код для отладки (в проде нужно отправлять SMS)
            print(f"=== ДЕБАГ ИНФОРМАЦИЯ ===")
            print(f"Пользователь: {user.username}")
            print(f"Телефон: {profile.phone if profile.phone else 'не указан'}")
            if profile.phone:
                print(f"Код подтверждения: {profile.verification_code}")
            print(f"=======================")

        return user


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        label='Имя пользователя',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите имя пользователя'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Введите пароль'
        }),
        label='Пароль'
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('Введите имя пользователя')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password:
            raise ValidationError('Введите пароль')
        return password


# Дополнительная форма для редактирования профиля
class ProfileUpdateForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=20,
        required=False,  # Сделали необязательным
        label='Номер телефона',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+7 (999) 123-45-67 (необязательно)'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['phone'].initial = self.instance.profile.phone

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        # Если поле пустое
        if not phone or phone.strip() == '':
            return ''

        # Удаляем все нецифровые символы
        phone_digits = re.sub(r'\D', '', phone)

        # Если после очистки ничего нет
        if not phone_digits:
            return ''

        # Проверяем базовую длину
        if len(phone_digits) < 10 or len(phone_digits) > 11:
            raise ValidationError('Введите 10-11 цифр номера телефона или оставьте поле пустым')

        # Преобразуем к стандартному формату +7XXXXXXXXXX
        if phone_digits.startswith('8'):
            phone_digits = '7' + phone_digits[1:]
        elif phone_digits.startswith('9'):
            phone_digits = '7' + phone_digits

        if not phone_digits.startswith('7'):
            phone_digits = '7' + phone_digits

        if len(phone_digits) != 11:
            raise ValidationError('Номер телефона должен содержать 11 цифр')

        formatted_phone = '+' + phone_digits

        # Проверка уникальности (исключая текущего пользователя, и только если номер не пустой)
        if (formatted_phone and formatted_phone != '+7' and
                self.instance and
                hasattr(self.instance, 'profile') and
                UserProfile.objects.filter(phone=formatted_phone)
                        .exclude(user=self.instance)
                        .exists()):
            raise ValidationError('Этот номер телефона уже используется другим пользователем')

        return formatted_phone