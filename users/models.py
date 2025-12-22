from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
import re


class UserProfileManager(models.Manager):
    def normalize_phone(self, phone):
        """Нормализует номер телефона для сравнения"""
        if not phone:
            return None

        # Убираем все нецифровые символы
        digits = re.sub(r'\D', '', str(phone))

        if not digits:
            return None

        # Нормализуем российский номер
        if len(digits) == 10 and digits.startswith('9'):
            digits = '7' + digits
        elif len(digits) == 11 and digits.startswith('8'):
            digits = '7' + digits[1:]
        elif len(digits) == 10:
            digits = '7' + digits

        # Должно быть 11 цифр для российского номера
        if len(digits) != 11:
            return None

        return '+' + digits

    def get_user_by_phone(self, phone):
        """Найти пользователя по номеру телефона"""
        # Нормализуем номер
        normalized_phone = self.normalize_phone(phone)
        if not normalized_phone:
            return None

        # Ищем профиль с таким номером
        try:
            profile = UserProfile.objects.get(phone=normalized_phone)
            return profile.user
        except UserProfile.DoesNotExist:
            # Пробуем другие форматы
            phone_digits = normalized_phone[1:]  # Убираем +

            # Формат без + в начале
            try:
                profile = UserProfile.objects.get(phone=phone_digits)
                return profile.user
            except UserProfile.DoesNotExist:
                pass

            # Формат с 8 в начале
            try:
                profile = UserProfile.objects.get(phone='8' + phone_digits[1:])
                return profile.user
            except UserProfile.DoesNotExist:
                pass

        return None


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Валидатор для номера телефона
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Номер телефона должен быть в формате: '+79123456789'"
    )

    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        unique=True,  # УНИКАЛЬНЫЙ
        verbose_name='Номер телефона'
    )

    phone_verified = models.BooleanField(default=False, verbose_name='Телефон подтвержден')
    verification_code = models.CharField(max_length=6, blank=True, null=True)

    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')

    # Дополнительные поля
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='Аватар')
    preferences = models.JSONField(default=dict, blank=True, verbose_name='Предпочтения')

    objects = UserProfileManager()

    class Meta:
        indexes = [
            models.Index(fields=['phone']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['phone'],
                name='unique_userprofile_phone'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.phone}"

    def clean(self):
        """Проверка перед сохранением - строгая проверка уникальности"""
        super().clean()

        if not self.phone:
            raise ValidationError({'phone': 'Номер телефона обязателен'})

        # Нормализуем телефон для проверки
        normalized = self.__class__.objects.normalize_phone(self.phone)
        if not normalized:
            raise ValidationError({'phone': 'Неверный формат номера телефона'})

        # Проверяем уникальность
        qs = UserProfile.objects.filter(phone=normalized)
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if qs.exists():
            existing_users = [p.user.username for p in qs]
            raise ValidationError({
                'phone': f'Номер телефона {normalized} уже используется пользователями: {", ".join(existing_users)}'
            })

        # Устанавливаем нормализованный номер
        self.phone = normalized

    def save(self, *args, **kwargs):
        """Сохраняем с атомарной проверкой уникальности"""
        # Всегда вызываем clean для валидации
        self.full_clean()

        # Сохраняем с блокировкой транзакции
        try:
            with transaction.atomic():
                super().save(*args, **kwargs)
        except IntegrityError as e:
            # Ловим ошибку уникальности из базы данных
            if 'unique' in str(e).lower() or 'phone' in str(e).lower():
                # Пытаемся найти, кто уже использует этот телефон
                try:
                    existing = UserProfile.objects.get(phone=self.phone)
                    raise ValidationError({
                        'phone': f'Номер телефона {self.phone} уже используется пользователем {existing.user.username}'
                    })
                except UserProfile.DoesNotExist:
                    raise ValidationError({
                        'phone': f'Номер телефона {self.phone} уже зарегистрирован'
                    })
            raise

    def generate_verification_code(self):
        """Генерация кода подтверждения телефона"""
        import random
        self.verification_code = f"{random.randint(1000, 9999)}"
        self.save()
        return self.verification_code

    def verify_phone(self, code):
        """Подтверждение телефона"""
        if self.verification_code == code:
            self.phone_verified = True
            self.verification_code = None
            self.save()
            return True
        return False


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Создать профиль при создании пользователя"""
    # Пропускаем создание профиля, если он уже создается через форму регистрации
    if created and not getattr(instance, '_creating_profile_via_form', False):
        try:
            with transaction.atomic():
                import time
                # Генерируем уникальный временный телефон
                timestamp = int(time.time() * 1000) % 1000000
                base_phone = f'+7980{timestamp:06d}'

                # Убеждаемся в уникальности
                phone = base_phone
                counter = 1
                while UserProfile.objects.filter(phone=phone).exists() and counter < 100:
                    phone = f'+7980{(timestamp + counter) % 1000000:06d}'
                    counter += 1

                if counter >= 100:
                    # Если не удалось найти уникальный, генерируем случайный
                    import random
                    phone = f'+7980{random.randint(1000000, 9999999)}'

                UserProfile.objects.create(user=instance, phone=phone)
        except Exception as e:
            # Если ошибка, логируем но не падаем
            import sys
            print(f"Ошибка создания профиля для {instance.username}: {e}", file=sys.stderr)