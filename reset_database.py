import os
import django
import sys

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paddle_booking.settings')
django.setup()

from django.core.management import execute_from_command_line


def reset_database():
    """Полный сброс базы данных"""
    print("=" * 60)
    print("ПОЛНЫЙ СБРОС БАЗЫ ДАННЫХ")
    print("=" * 60)

    # Удаляем файл базы данных
    db_file = 'db.sqlite3'
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"✓ Удален файл базы данных: {db_file}")

    # Удаляем старые миграции
    migrations_dir = 'users/migrations'
    if os.path.exists(migrations_dir):
        for file in os.listdir(migrations_dir):
            if file.endswith('.py') and file != '__init__.py':
                os.remove(os.path.join(migrations_dir, file))
                print(f"✓ Удален файл миграции: {file}")

    # Создаем новые миграции
    print("\nСоздание миграций...")
    execute_from_command_line(['manage.py', 'makemigrations'])

    # Применяем миграции
    print("\nПрименение миграций...")
    execute_from_command_line(['manage.py', 'migrate'])

    # Создаем суперпользователя
    print("\nСоздание суперпользователя...")
    print("Введите данные для суперпользователя:")

    from django.contrib.auth.models import User
    from users.models import UserProfile

    # Создаем суперпользователя
    superuser = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )

    # Обновляем телефон суперпользователя
    profile = UserProfile.objects.get(user=superuser)
    profile.phone = '+79100000001'
    profile.save()

    print(f"\n✓ Создан суперпользователь:")
    print(f"  Имя пользователя: admin")
    print(f"  Пароль: admin123")
    print(f"  Телефон: +79100000001")

    print("\n" + "=" * 60)
    print("БАЗА ДАННЫХ УСПЕШНО СБРОШЕНА И ПЕРЕСОЗДАНА")
    print("=" * 60)


if __name__ == "__main__":
    confirm = input("\nВы уверены, что хотите сбросить базу данных? Все данные будут удалены! (yes/no): ")

    if confirm.lower() == 'yes':
        reset_database()
    else:
        print("Отменено.")