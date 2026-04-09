from django.apps import AppConfig


class TournamentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tournament'

    def ready(self):
        """Подключение сигналов при инициализации приложения"""
        import tournament.signals  # noqa
